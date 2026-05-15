import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional

import bcrypt
from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, current_app, g, jsonify, request, session

from services import email_service
from db import get_db_connection, get_dict_cursor

auth_bp = Blueprint("auth", __name__)

EMAIL_KEY = "user_email"
USER_ID_KEY = "user_id"

OTP_TTL_MIN = 10
RESET_TOKEN_TTL_HOURS = 1
PASSWORD_MIN_LEN = 8

# Very small in-memory rate limiter: ip -> list[timestamps]
_rate_log: dict[str, list[float]] = {}


def _rate_limit(key: str, max_attempts: int = 5, window_sec: int = 300) -> bool:
    """Return True if the request is allowed, False if rate-limited."""
    now = time.time()
    bucket = [t for t in _rate_log.get(key, []) if now - t < window_sec]
    if len(bucket) >= max_attempts:
        _rate_log[key] = bucket
        return False
    bucket.append(now)
    _rate_log[key] = bucket
    return True


def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def _check_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _validate_password(pw: str) -> Optional[str]:
    if not pw or len(pw) < PASSWORD_MIN_LEN:
        return f"Password must be at least {PASSWORD_MIN_LEN} characters"
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Password must contain at least one letter and one digit"
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
    """Step 1 of registration: validate inputs, store OTP, email it."""
    if not _rate_limit(f"register:{request.remote_addr}", max_attempts=10, window_sec=600):
        return jsonify({"status": "error", "message": "Too many attempts, try again later"}), 429
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
                return jsonify({"status": "error", "message": "An account with that email already exists"}), 409

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
    return jsonify({"status": "success", "message": "Account created", "email": email})


@auth_bp.route("/login", methods=["POST"])
def login():
    if not _rate_limit(f"login:{request.remote_addr}", max_attempts=5, window_sec=300):
        return jsonify({"status": "error", "message": "Too many attempts, try again later"}), 429
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
                return jsonify({"status": "error", "message": "Invalid email or password"}), 401
            cur.execute("UPDATE users SET last_login_at=NOW() WHERE id=%s", (user["id"],))
        conn.commit()
    finally:
        conn.close()

    session.permanent = True
    session[USER_ID_KEY] = user["id"]
    session[EMAIL_KEY] = email
    return jsonify({"status": "success", "message": "Login successful", "email": email})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.pop(USER_ID_KEY, None)
    session.pop(EMAIL_KEY, None)
    return jsonify({"status": "success"})


@auth_bp.route("/check-auth")
def check_auth():
    if USER_ID_KEY in session:
        return jsonify({"logged_in": True, "email": session.get(EMAIL_KEY)})
    return jsonify({"logged_in": False})


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    if not _rate_limit(f"forgot:{request.remote_addr}", max_attempts=5, window_sec=600):
        return jsonify({"status": "error", "message": "Too many attempts, try again later"}), 429
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

    return jsonify({"status": "success", "message": "Password updated"})
