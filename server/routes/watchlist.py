"""Watchlist routes."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends

from controllers import watchlist_controller as ctrl
from utils.deps import get_current_user

router = APIRouter(tags=["watchlist"])


@router.get("/api/watchlist")
async def list_watchlist(user: dict = Depends(get_current_user)):
    return await ctrl.list_watchlist(str(user["_id"]))


@router.post("/api/watchlist")
async def add_watchlist(data: dict = Body(...), user: dict = Depends(get_current_user)):
    return await ctrl.add_watchlist(str(user["_id"]), data)


@router.put("/api/watchlist/{entry_id}")
async def update_watchlist(
    entry_id: str, data: dict = Body(...), user: dict = Depends(get_current_user)
):
    return await ctrl.update_watchlist(str(user["_id"]), entry_id, data)


@router.delete("/api/watchlist/{entry_id}")
async def delete_watchlist(entry_id: str, user: dict = Depends(get_current_user)):
    return await ctrl.delete_watchlist(str(user["_id"]), entry_id)


@router.get("/api/symbols")
async def list_symbols():
    return ctrl.list_symbols()
