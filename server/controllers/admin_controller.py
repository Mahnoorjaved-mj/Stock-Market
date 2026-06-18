"""Admin metrics dashboard. Ports legacy app.py /api/admin/metrics (Mongo)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from config.database import audit_events, alert_history, users, watchlist


async def metrics() -> dict:
    day_ago = datetime.now(timezone.utc) - timedelta(hours=24)

    users_count = await users().count_documents({})
    wl_count = await watchlist().count_documents({})
    alerts_24h = await alert_history().count_documents({"sent_at": {"$gt": day_ago}})
    login_fail = await audit_events().count_documents(
        {"action": "login_failed", "occurred_at": {"$gt": day_ago}}
    )

    audit_rows = (
        await audit_events().find({}).sort("occurred_at", -1).to_list(length=50)
    )
    audit = [
        {
            "occurred_at": r["occurred_at"].isoformat() if r.get("occurred_at") else None,
            "action": r.get("action"),
            "user_id": r.get("user_id"),
            "ip": r.get("ip"),
        }
        for r in audit_rows
    ]

    return {
        "status": "success",
        "metrics": {
            "users": users_count,
            "watchlist": wl_count,
            "alerts_24h": alerts_24h,
            "login_failures_24h": login_fail,
        },
        "audit": audit,
    }
