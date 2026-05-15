from decimal import Decimal, InvalidOperation

from flask import Blueprint, g, jsonify, request, session

from routes.auth import _check_password, _hash_password, _validate_password, login_required
from db import get_db_connection, get_dict_cursor

profile_bp = Blueprint("profile", __name__)

VALID_DIGEST = {"off", "daily", "weekly"}


def _to_decimal(val, name: str):
    try:
        d = Decimal(str(val))
        if d < 0 or d > 100:
            raise ValueError
        return d
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{name} must be a number between 0 and 100")


@profile_bp.route("/api/profile", methods=["GET"])
@login_required
def get_profile():
    conn = get_db_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute(
                """SELECT id, email, name, alert_threshold_pct, digest_frequency,
                          digest_day, created_at, last_login_at
                   FROM users WHERE id=%s""",
                (g.user_id,),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"status": "error", "message": "User not found"}), 404
        return jsonify({"status": "success", "profile": dict(row, alert_threshold_pct=float(row["alert_threshold_pct"]))})
    finally:
        conn.close()


@profile_bp.route("/api/profile", methods=["PUT"])
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    fields, values = [], []

    if "name" in data:
        name = (data.get("name") or "").strip() or None
        fields.append("name=%s")
        values.append(name)

    if "alert_threshold_pct" in data:
        try:
            thr = _to_decimal(data["alert_threshold_pct"], "alert_threshold_pct")
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        fields.append("alert_threshold_pct=%s")
        values.append(thr)

    if "digest_frequency" in data:
        freq = (data["digest_frequency"] or "").lower()
        if freq not in VALID_DIGEST:
            return jsonify({"status": "error", "message": "digest_frequency must be off|daily|weekly"}), 400
        fields.append("digest_frequency=%s")
        values.append(freq)

    if "digest_day" in data:
        try:
            day = int(data["digest_day"])
            if day < 0 or day > 6:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({"status": "error", "message": "digest_day must be 0..6"}), 400
        fields.append("digest_day=%s")
        values.append(day)

    if not fields:
        return jsonify({"status": "error", "message": "No fields to update"}), 400

    values.append(g.user_id)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=%s", values)
        conn.commit()
    finally:
        conn.close()
    return jsonify({"status": "success"})


@profile_bp.route("/api/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    old_pw = data.get("old_password") or ""
    new_pw = data.get("new_password") or ""
    if not old_pw:
        return jsonify({"status": "error", "message": "Current password required"}), 400
    err = _validate_password(new_pw)
    if err:
        return jsonify({"status": "error", "message": err}), 400

    conn = get_db_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute("SELECT password_hash FROM users WHERE id=%s", (g.user_id,))
            row = cur.fetchone()
            if not row or not _check_password(old_pw, row["password_hash"]):
                return jsonify({"status": "error", "message": "Current password is incorrect"}), 400
            cur.execute("UPDATE users SET password_hash=%s WHERE id=%s",
                        (_hash_password(new_pw), g.user_id))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"status": "success", "message": "Password updated"})


@profile_bp.route("/api/profile", methods=["DELETE"])
@login_required
def delete_account():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id=%s", (g.user_id,))
        conn.commit()
    finally:
        conn.close()
    session.clear()
    return jsonify({"status": "success", "message": "Account deleted"})
