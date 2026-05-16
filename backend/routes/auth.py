import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional

import bcrypt
from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, current_app, g, jsonify, request, session

from services import email_service
from services.audit import log_event
from db import get_db_connection, get_dict_cursor

auth_bp = Blueprint("auth", __name__)

EMAIL_KEY = "user_email"
USER_ID_KEY = "user_id"

OTP_TTL_MIN = 10
RESET_TOKEN_TTL_HOURS = 1
# Bumped from 8 → 10 per plan.md §4a password strength requirement.
PASSWORD_MIN_LEN = 10


def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def _check_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _validate_password(pw: str) -> Optional[str]:
    """Stricter password rules per plan.md §4a.
    - min PASSWORD_MIN_LEN (10) characters
    - at least one letter
    - at least one digit
    - at least one symbol OR length >= 14
    """
    if not pw or len(pw) < PASSWORD_MIN_LEN:
        return f"Password must be at least {PASSWORD_MIN_LEN} characters"
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Password must contain at least one letter and one digit"
    if len(pw) < 14 and not re.search(r"[^A-Za-z0-9]", pw):
        return "Password must contain a symbol (or be at least 14 characters)"
    return None


def _validate_email(em: str) -> Optional[str]:
    try:
        validate_email(em, check_deliverability=False)
        return None
    except EmailNotValidError as e:
        return str(e)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if USER_ID_KEY not in session:
            return jsonify({"status": "error", "message": "Authentication required"}), 401
        g.user_id = session[USER_ID_KEY]
        g.user_email = session.get(EMAIL_KEY)
        return fn(*args, **kwargs)

    return wrapper


def current_user() -> Optional[dict]:
    """Load current user from DB; cached on g for the request."""
    if not session.get(USER_ID_KEY):
        return None
    if getattr(g, "_user_row", None):
        return g._user_row
    conn = get_db_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute("SELECT * FROM users WHERE id=%s", (session[USER_ID_KEY],))
            row = cur.fetchone()
        g._user_row = dict(row) if row else None
        return g._user_row
    finally:
        conn.close()


# -------------------- Routes --------------------

@auth_bp.route("/register", methods=["POST"])
def register():
    """Step 1 of registration: validate inputs, store OTP, email it.
    Rate-limiting is applied via Flask-Limiter from app.py.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip() or None

    err = _validate_email(email) or _validate_password(password)
    if err:
        return jsonify({"status": "error", "message": err}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                log_event("register_email_taken", request=request, metadata={"email": email})
                return jsonify({"status": "error", "message": "An account with that email already exists"}), 409

            # OTP resend rate-limit: max 3 OTPs for the same email per OTP_TTL_MIN window.
            cur.execute(
                """SELECT COUNT(*) FROM otp_verification
                   WHERE email=%s AND created_at > NOW() - INTERVAL '%s minutes'""",
                (email, OTP_TTL_MIN),
            )
            (recent_count,) = cur.fetchone()
            if recent_count >= 3:
                log_event("register_otp_rate_limited", request=request, metadata={"email": email})
                return jsonify({"status": "error", "message": "Too many verification attempts — try again in a few minutes"}), 429

            otp = f"{secrets.randbelow(1_000_000):06d}"
            pw_hash = _hash_password(password)
            expires = datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MIN)

            cur.execute("DELETE FROM otp_verification WHERE email=%s", (email,))
            cur.execute(
                """INSERT INTO otp_verification (email, otp, password_hash, name, expires_at)
                   VALUES (%s,%s,%s,%s,%s)""",
                (email, otp, pw_hash, name, expires),
            )
        conn.commit()
    finally:
        conn.close()

    email_service.send_otp(email, otp)
    log_event("register_otp_sent", request=request, metadata={"email": email})
    return jsonify({"status": "success", "message": "OTP sent to your email"})


@auth_bp.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    otp = (data.get("otp") or "").strip()
    if not email or not otp:
        return jsonify({"status": "error", "message": "Email and OTP are required"}), 400

    conn = get_db_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute(
                """SELECT * FROM otp_verification
                   WHERE email=%s AND otp=%s AND expires_at > NOW()
                   ORDER BY id DESC LIMIT 1""",
                (email, otp),
            )
            rec = cur.fetchone()
            if not rec:
                return jsonify({"status": "error", "message": "Invalid or expired OTP"}), 400

            cur.execute(
                """INSERT INTO users (email, password_hash, name)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (email) DO NOTHING
                   RETURNING id""",
                (rec["email"], rec["password_hash"], rec["name"]),
            )
            inserted = cur.fetchone()
            if inserted:
                user_id = inserted["id"]
            else:
                cur.execute("SELECT id FROM users WHERE email=%s", (email,))
                row = cur.fetchone()
                if not row:
                    return jsonify({"status": "error", "message": "Account creation failed, please try again"}), 500
                user_id = row["id"]

            cur.execute("DELETE FROM otp_verification WHERE email=%s", (email,))
        conn.commit()
    finally:
        conn.close()

    session.permanent = True
    session[USER_ID_KEY] = user_id
    session[EMAIL_KEY] = email
    email_service.send_welcome(email, rec.get("name"))
    log_event("register_success", user_id=user_id, request=request)
    return jsonify({"status": "success", "message": "Account created", "email": email})


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password required"}), 400

    conn = get_db_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
            if not user or not _check_password(password, user["password_hash"]):
                log_event("login_failed", request=request, metadata={"email": email})
                return jsonify({"status": "error", "message": "Invalid email or password"}), 401
            cur.execute("UPDATE users SET last_login_at=NOW() WHERE id=%s", (user["id"],))
        conn.commit()
    finally:
        conn.close()

    session.permanent = True
    session[USER_ID_KEY] = user["id"]
    session[EMAIL_KEY] = email
    log_event("login_success", user_id=user["id"], request=request)
    return jsonify({"status": "success", "message": "Login successful", "email": email})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    uid = session.get(USER_ID_KEY)
    session.pop(USER_ID_KEY, None)
    session.pop(EMAIL_KEY, None)
    if uid:
        log_event("logout", user_id=uid, request=request)
    return jsonify({"status": "success"})


@auth_bp.route("/check-auth")
def check_auth():
    if USER_ID_KEY in session:
        return jsonify({"logged_in": True, "email": session.get(EMAIL_KEY)})
    return jsonify({"logged_in": False})


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"status": "error", "message": "Email required"}), 400

    conn = get_db_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            row = cur.fetchone()
            if row:
                token = secrets.token_urlsafe(32)
                expires = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_TTL_HOURS)
                cur.execute(
                    """INSERT INTO password_reset_tokens (user_id, token, expires_at)
                       VALUES (%s,%s,%s)""",
                    (row["id"], token, expires),
                )
                conn.commit()
                email_service.send_password_reset(email, token)
                log_event("password_reset_requested", user_id=row["id"], request=request)
    finally:
        conn.close()

    # Always succeed to avoid leaking which emails exist
    return jsonify({"status": "success", "message": "If that email exists, a reset link has been sent"})


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    new_password = data.get("password") or ""
    if not token:
        return jsonify({"status": "error", "message": "Token required"}), 400
    err = _validate_password(new_password)
    if err:
        return jsonify({"status": "error", "message": err}), 400

    conn = get_db_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute(
                """SELECT * FROM password_reset_tokens
                   WHERE token=%s AND used=FALSE AND expires_at > NOW()""",
                (token,),
            )
            rec = cur.fetchone()
            if not rec:
                return jsonify({"status": "error", "message": "Invalid or expired token"}), 400
            pw_hash = _hash_password(new_password)
            cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (pw_hash, rec["user_id"]))
            cur.execute("UPDATE password_reset_tokens SET used=TRUE WHERE id=%s", (rec["id"],))
        conn.commit()
    finally:
        conn.close()

    log_event("password_reset_completed", user_id=rec["user_id"], request=request)
    return jsonify({"status": "success", "message": "Password updated"})


# -------------------- TOTP 2FA (opt-in) --------------------

@auth_bp.route("/api/2fa/setup", methods=["POST"])
@login_required
def twofa_setup():
    """Generate a fresh TOTP secret and return the otpauth URI for QR rendering.
    Secret is stored as `enabled=FALSE` until the user confirms with /verify.
    """
    try:
        import pyotp
    except ImportError:
        return jsonify({"status": "error", "message": "2FA not available on this server"}), 501

    secret = pyotp.random_base32()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO user_2fa_secrets (user_id, secret, enabled)
                   VALUES (%s, %s, FALSE)
                   ON CONFLICT (user_id) DO UPDATE SET secret=EXCLUDED.secret, enabled=FALSE""",
                (g.user_id, secret),
            )
        conn.commit()
    finally:
        conn.close()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=g.user_email, issuer_name="StockSense")
    return jsonify({"status": "success", "secret": secret, "otpauth": uri})


@auth_bp.route("/api/2fa/verify", methods=["POST"])
@login_required
def twofa_verify():
    try:
        import pyotp
    except ImportError:
        return jsonify({"status": "error", "message": "2FA not available on this server"}), 501

    code = (request.get_json(silent=True) or {}).get("code", "").strip()
    if not code:
        return jsonify({"status": "error", "message": "Code required"}), 400

    conn = get_db_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute("SELECT secret FROM user_2fa_secrets WHERE user_id=%s", (g.user_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"status": "error", "message": "Run /api/2fa/setup first"}), 400
            totp = pyotp.TOTP(row["secret"])
            if not totp.verify(code, valid_window=1):
                log_event("2fa_verify_failed", user_id=g.user_id, request=request)
                return jsonify({"status": "error", "message": "Invalid code"}), 400
            cur.execute(
                "UPDATE user_2fa_secrets SET enabled=TRUE, verified_at=NOW() WHERE user_id=%s",
                (g.user_id,),
            )
        conn.commit()
    finally:
        conn.close()
    log_event("2fa_enabled", user_id=g.user_id, request=request)
    return jsonify({"status": "success", "message": "2FA enabled"})


@auth_bp.route("/api/2fa/disable", methods=["POST"])
@login_required
def twofa_disable():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_2fa_secrets WHERE user_id=%s", (g.user_id,))
        conn.commit()
    finally:
        conn.close()
    log_event("2fa_disabled", user_id=g.user_id, request=request)
    return jsonify({"status": "success", "message": "2FA disabled"})
