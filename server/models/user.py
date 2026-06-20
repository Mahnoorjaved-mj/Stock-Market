"""Pydantic request/response schemas for auth + profile."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ---- Auth requests ----
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class TwoFAVerifyRequest(BaseModel):
    code: str


# ---- Profile update ----
class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    alert_threshold_pct: Optional[float] = Field(default=None, ge=0, le=100)
    digest_frequency: Optional[str] = None  # off | daily | weekly
    digest_day: Optional[int] = Field(default=None, ge=0, le=6)


# ---- Responses ----
class TokenResponse(BaseModel):
    status: str = "success"
    token: str
    user: dict
