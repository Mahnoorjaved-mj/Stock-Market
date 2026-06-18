"""In-app notification center. Ports legacy app.py notification endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from config.database import notifications


async def list_notifications(user_id: str) -> dict:
    rows = (
        await notifications()
        .find({"user_id": user_id})
        .sort("created_at", -1)
        .to_list(length=30)
    )
    items = [
        {
            "id": str(r["_id"]),
            "title": r.get("title"),
            "body": r.get("body"),
            "kind": r.get("kind", "info"),
            "href": r.get("href"),
            "read_at": r["read_at"].isoformat() if r.get("read_at") else None,
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
        }
        for r in rows
    ]
    return {
        "status": "success",
        "items": items,
        "unread": sum(1 for i in items if not i["read_at"]),
    }


async def read_all(user_id: str) -> dict:
    await notifications().update_many(
        {"user_id": user_id, "read_at": None},
        {"$set": {"read_at": datetime.now(timezone.utc)}},
    )
    return {"status": "success"}
