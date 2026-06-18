"""Notification routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from controllers import notification_controller as ctrl
from utils.deps import get_current_user

router = APIRouter(tags=["notifications"])


@router.get("/api/notifications")
async def list_notifications(user: dict = Depends(get_current_user)):
    return await ctrl.list_notifications(str(user["_id"]))


@router.post("/api/notifications/read-all")
async def read_all(user: dict = Depends(get_current_user)):
    return await ctrl.read_all(str(user["_id"]))
