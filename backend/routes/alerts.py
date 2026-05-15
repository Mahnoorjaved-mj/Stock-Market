"""Alert history + manual sweep trigger for testing."""
from flask import Blueprint, g, jsonify, request

from services import alerts_engine as alerts
from routes.auth import login_required
from db import get_db_connection, get_dict_cursor

alerts_bp = Blueprint("alerts_bp", __name__)


@alerts_bp.route("/api/alerts/history")
@login_required
def alert_history():
    try:
        limit = max(1, min(200, int(request.args.get("limit", 50))))
    except (TypeError, ValueError):
        limit = 50
    conn = get_db_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute(
                """SELECT id, symbol, alert_type, price, change_pct, sent_at
                   FROM alert_history WHERE user_id=%s
                   ORDER BY sent_at DESC LIMIT %s""",
                (g.user_id, limit),
            )
            rows = cur.fetchall()
        items = []
        for r in rows:
            d = dict(r)
            d["price"] = float(d["price"])
            d["change_pct"] = float(d["change_pct"]) if d["change_pct"] is not None else None
            d["sent_at"] = d["sent_at"].isoformat()
            items.append(d)
        return jsonify({"status": "success", "items": items})
    finally:
        conn.close()


@alerts_bp.route("/api/alerts/run-now", methods=["POST"])
@login_required
def run_now():
    """Manual trigger - useful for testing. Runs the sweep across ALL users."""
    summary = alerts.evaluate_user_alerts()
    return jsonify({"status": "success", "summary": summary})
