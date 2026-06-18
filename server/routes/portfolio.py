"""Portfolio routes."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from fastapi.responses import Response

from controllers import portfolio_controller as ctrl
from utils.deps import get_current_user

router = APIRouter(tags=["portfolio"])


@router.get("/api/portfolio")
async def list_holdings(user: dict = Depends(get_current_user)):
    return await ctrl.list_holdings(str(user["_id"]))


@router.post("/api/portfolio")
async def add_holding(data: dict = Body(...), user: dict = Depends(get_current_user)):
    return await ctrl.add_holding(str(user["_id"]), data)


@router.put("/api/portfolio/{entry_id}")
async def update_holding(
    entry_id: str, data: dict = Body(...), user: dict = Depends(get_current_user)
):
    return await ctrl.update_holding(str(user["_id"]), entry_id, data)


@router.delete("/api/portfolio/{entry_id}")
async def delete_holding(entry_id: str, user: dict = Depends(get_current_user)):
    return await ctrl.delete_holding(str(user["_id"]), entry_id)


@router.get("/api/portfolio/export.csv")
async def export_csv(user: dict = Depends(get_current_user)):
    csv_text = await ctrl.export_csv(str(user["_id"]))
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=portfolio.csv"},
    )
