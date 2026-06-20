"""Alert routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from controllers import alert_controller as ctrl
from utils.deps import get_current_user

router = APIRouter(tags=["alerts"])


@router.get("/api/alerts/history")
async def history(limit: int = Query(50), user: dict = Depends(get_current_user)):
    return await ctrl.history(str(user["_id"]), limit)


@router.post("/api/alerts/run-now")
async def run_now(user: dict = Depends(get_current_user)):
    return await ctrl.run_now()
