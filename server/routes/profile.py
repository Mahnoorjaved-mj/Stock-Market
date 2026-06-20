"""Profile routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from controllers import profile_controller as ctrl
from models.user import ChangePasswordRequest, ProfileUpdate
from utils.deps import get_current_user

router = APIRouter(tags=["profile"])


@router.get("/api/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    return await ctrl.get_profile(user)


@router.put("/api/profile")
async def update_profile(body: ProfileUpdate, user: dict = Depends(get_current_user)):
    return await ctrl.update_profile(user, body)


@router.delete("/api/profile")
async def delete_account(user: dict = Depends(get_current_user)):
    return await ctrl.delete_account(user)


@router.post("/api/change-password")
async def change_password(
    body: ChangePasswordRequest, user: dict = Depends(get_current_user)
):
    return await ctrl.change_password(user, body.old_password, body.new_password)
