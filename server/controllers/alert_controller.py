"""Alert history + manual sweep trigger. Ports legacy routes/alerts.py."""
from __future__ import annotations

from config.database import alert_history


async def history(user_id: str, limit: int = 50) -> dict:
    limit = max(1, min(200, limit))
    rows = (
        await alert_history()
        .find({"user_id": user_id})
        .sort("sent_at", -1)
        .to_list(length=limit)
    )
    items = [
        {
            "id": str(r["_id"]),
            "symbol": r.get("symbol"),
            "alert_type": r.get("alert_type"),
            "price": float(r.get("price") or 0),
            "change_pct": float(r["change_pct"]) if r.get("change_pct") is not None else None,
            "sent_at": r["sent_at"].isoformat() if r.get("sent_at") else None,
        }
        for r in rows
    ]
    return {"status": "success", "items": items}


async def run_now() -> dict:
    from services import alerts_engine

    summary = await alerts_engine.evaluate_user_alerts()
    return {"status": "success", "summary": summary}
