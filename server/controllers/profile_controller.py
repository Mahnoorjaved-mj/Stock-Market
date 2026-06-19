"""Profile read/update/delete + password change. Ports legacy routes/profile.py."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from config.database import (
    alert_history,
    notifications,
    portfolio,
    twofa,
    users,
    watchlist,
)
from models.user import ProfileUpdate
from utils.security import hash_password, validate_password, verify_password

VALID_DIGEST = {"off", "daily", "weekly"}


async def get_profile(user: dict) -> dict:
    return {
        "status": "success",
        "profile": {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("name"),
            "alert_threshold_pct": float(user.get("alert_threshold_pct", 5)),
            "digest_frequency": user.get("digest_frequency", "weekly"),
            "digest_day": user.get("digest_day", 5),
            "is_admin": bool(user.get("is_admin")),
            "created_at": user["created_at"].isoformat() if user.get("created_at") else None,
            "last_login_at": user["last_login_at"].isoformat() if user.get("last_login_at") else None,
        },
    }


async def update_profile(user: dict, body: ProfileUpdate) -> dict:
    fields: dict = {}
    if body.name is not None:
        fields["name"] = body.name.strip() or None
    if body.alert_threshold_pct is not None:
        fields["alert_threshold_pct"] = float(body.alert_threshold_pct)
    if body.digest_frequency is not None:
        freq = body.digest_frequency.lower()
        if freq not in VALID_DIGEST:
            raise HTTPException(status_code=400, detail="digest_frequency must be off|daily|weekly")
        fields["digest_frequency"] = freq
    if body.digest_day is not None:
        fields["digest_day"] = int(body.digest_day)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    fields["updated_at"] = datetime.now(timezone.utc)
    await users().update_one({"_id": user["_id"]}, {"$set": fields})
    return {"status": "success"}


async def change_password(user: dict, old_pw: str, new_pw: str) -> dict:
    if not old_pw:
        raise HTTPException(status_code=400, detail="Current password required")
    err = validate_password(new_pw)
    if err:
        raise HTTPException(status_code=400, detail=err)
    if not verify_password(old_pw, user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    await users().update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hash_password(new_pw), "updated_at": datetime.now(timezone.utc)}},
    )
    return {"status": "success", "message": "Password updated"}


async def delete_account(user: dict) -> dict:
    uid = str(user["_id"])
    # Cascade-delete the user's owned documents.
    await watchlist().delete_many({"user_id": uid})
    await portfolio().delete_many({"user_id": uid})
    await alert_history().delete_many({"user_id": uid})
    await notifications().delete_many({"user_id": uid})
    await twofa().delete_many({"user_id": uid})
    await users().delete_one({"_id": user["_id"]})
    return {"status": "success", "message": "Account deleted"}
