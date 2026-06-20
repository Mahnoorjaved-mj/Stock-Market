"""Admin routes — gated by require_admin."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from controllers import admin_controller as ctrl
from utils.deps import require_admin

router = APIRouter(tags=["admin"])


@router.get("/api/admin/metrics")
async def metrics(admin: dict = Depends(require_admin)):
    return await ctrl.metrics()
