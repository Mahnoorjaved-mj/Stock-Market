"""Auth routes — JWT-based. Mounted at /auth."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from controllers import auth_controller as ctrl
from models.common import serialize
from models.user import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TwoFAVerifyRequest,
    VerifyOtpRequest,
)
from utils.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(body: RegisterRequest, request: Request):
    return await ctrl.register(body.email, body.password, body.name, request)


@router.post("/verify-otp")
async def verify_otp(body: VerifyOtpRequest, request: Request):
    return await ctrl.verify_otp(body.email, body.otp, request)


@router.post("/login")
async def login(body: LoginRequest, request: Request):
    return await ctrl.login(body.email, body.password, request)


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    return await ctrl.forgot_password(body.email, request)


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, request: Request):
    return await ctrl.reset_password(body.token, body.password, request)


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    safe = serialize(user) or {}
    safe.pop("password_hash", None)
    return {"status": "success", "user": safe}


@router.post("/logout")
async def logout(request: Request, user: dict = Depends(get_current_user)):
    from utils.audit import log_event

    await log_event("logout", user_id=str(user["_id"]), request=request)
    return {"status": "success"}


@router.post("/2fa/setup")
async def twofa_setup(request: Request, user: dict = Depends(get_current_user)):
    return await ctrl.twofa_setup(user, request)


@router.post("/2fa/verify")
async def twofa_verify(
    body: TwoFAVerifyRequest, request: Request, user: dict = Depends(get_current_user)
):
    return await ctrl.twofa_verify(user, body.code, request)


@router.post("/2fa/disable")
async def twofa_disable(request: Request, user: dict = Depends(get_current_user)):
    return await ctrl.twofa_disable(user, request)
