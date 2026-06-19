"""Auth business logic — Mongo + JWT. Ports legacy backend/routes/auth.py."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import HTTPException, Request, status

from config.database import otp, reset_tokens, twofa, users
from models.common import serialize
from services import email_service
from utils.audit import log_event
from utils.security import (
    create_access_token,
    hash_password,
    validate_email_address,
    validate_password,
    verify_password,
)

OTP_TTL_MIN = 10
RESET_TOKEN_TTL_HOURS = 1


def _public_user(doc: dict) -> dict:
    """Strip secrets from a user doc before returning to the client."""
    safe = serialize(doc) or {}
    safe.pop("password_hash", None)
    return safe


async def register(email: str, password: str, name: str | None, request: Request) -> dict:
    email = (email or "").strip().lower()
    err = validate_email_address(email) or validate_password(password)
    if err:
        raise HTTPException(status_code=400, detail=err)

    if await users().find_one({"email": email}):
        await log_event("register_email_taken", request=request, metadata={"email": email})
        raise HTTPException(status_code=409, detail="An account with that email already exists")

    # OTP resend rate-limit: max 3 within the TTL window.
    window_start = datetime.now(timezone.utc) - timedelta(minutes=OTP_TTL_MIN)
    recent = await otp().count_documents({"email": email, "created_at": {"$gt": window_start}})
    if recent >= 3:
        await log_event("register_otp_rate_limited", request=request, metadata={"email": email})
        raise HTTPException(
            status_code=429, detail="Too many verification attempts — try again in a few minutes"
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    now = datetime.now(timezone.utc)
    await otp().delete_many({"email": email})
    await otp().insert_one(
        {
            "email": email,
            "otp": code,
            "password_hash": hash_password(password),
            "name": (name or "").strip() or None,
            "expires_at": now + timedelta(minutes=OTP_TTL_MIN),
            "created_at": now,
        }
    )
    email_service.send_otp(email, code)
    await log_event("register_otp_sent", request=request, metadata={"email": email})
    return {"status": "success", "message": "OTP sent to your email"}


async def verify_otp(email: str, code: str, request: Request) -> dict:
    email = (email or "").strip().lower()
    code = (code or "").strip()
    rec = await otp().find_one(
        {"email": email, "otp": code, "expires_at": {"$gt": datetime.now(timezone.utc)}},
        sort=[("_id", -1)],
    )
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    now = datetime.now(timezone.utc)
    existing = await users().find_one({"email": email})
    if existing:
        user = existing
    else:
        doc = {
            "email": rec["email"],
            "password_hash": rec["password_hash"],
            "name": rec.get("name"),
            "alert_threshold_pct": 5.0,
            "digest_frequency": "weekly",
            "digest_day": 5,
            "is_admin": False,
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
        }
        res = await users().insert_one(doc)
        doc["_id"] = res.inserted_id
        user = doc

    await otp().delete_many({"email": email})
    email_service.send_welcome(email, rec.get("name"))
    await log_event("register_success", user_id=str(user["_id"]), request=request)
    token = create_access_token(str(user["_id"]), email)
    return {"status": "success", "token": token, "user": _public_user(user)}


async def login(email: str, password: str, request: Request) -> dict:
    email = (email or "").strip().lower()
    user = await users().find_one({"email": email})
    if not user or not verify_password(password, user.get("password_hash", "")):
        await log_event("login_failed", request=request, metadata={"email": email})
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await users().update_one(
        {"_id": user["_id"]}, {"$set": {"last_login_at": datetime.now(timezone.utc)}}
    )
    await log_event("login_success", user_id=str(user["_id"]), request=request)
    token = create_access_token(str(user["_id"]), email)
    return {"status": "success", "token": token, "user": _public_user(user)}


async def forgot_password(email: str, request: Request) -> dict:
    email = (email or "").strip().lower()
    user = await users().find_one({"email": email})
    if user:
        token = secrets.token_urlsafe(32)
        await reset_tokens().insert_one(
            {
                "user_id": str(user["_id"]),
                "token": token,
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_TTL_HOURS),
                "used": False,
                "created_at": datetime.now(timezone.utc),
            }
        )
        email_service.send_password_reset(email, token)
        await log_event("password_reset_requested", user_id=str(user["_id"]), request=request)
    # Always succeed (don't leak which emails exist).
    return {"status": "success", "message": "If that email exists, a reset link has been sent"}


async def reset_password(token: str, new_password: str, request: Request) -> dict:
    token = (token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token required")
    err = validate_password(new_password)
    if err:
        raise HTTPException(status_code=400, detail=err)

    rec = await reset_tokens().find_one(
        {"token": token, "used": False, "expires_at": {"$gt": datetime.now(timezone.utc)}}
    )
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    await users().update_one(
        {"_id": ObjectId(rec["user_id"])},
        {"$set": {"password_hash": hash_password(new_password), "updated_at": datetime.now(timezone.utc)}},
    )
    await reset_tokens().update_one({"_id": rec["_id"]}, {"$set": {"used": True}})
    await log_event("password_reset_completed", user_id=rec["user_id"], request=request)
    return {"status": "success", "message": "Password updated"}


# ---- TOTP 2FA ----
async def twofa_setup(user: dict, request: Request) -> dict:
    import pyotp

    secret = pyotp.random_base32()
    await twofa().update_one(
        {"user_id": str(user["_id"])},
        {"$set": {"secret": secret, "enabled": False, "created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user["email"], issuer_name="StockSense")
    return {"status": "success", "secret": secret, "otpauth": uri}


async def twofa_verify(user: dict, code: str, request: Request) -> dict:
    import pyotp

    code = (code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Code required")
    row = await twofa().find_one({"user_id": str(user["_id"])})
    if not row:
        raise HTTPException(status_code=400, detail="Run /auth/2fa/setup first")
    if not pyotp.TOTP(row["secret"]).verify(code, valid_window=1):
        await log_event("2fa_verify_failed", user_id=str(user["_id"]), request=request)
        raise HTTPException(status_code=400, detail="Invalid code")
    await twofa().update_one(
        {"user_id": str(user["_id"])},
        {"$set": {"enabled": True, "verified_at": datetime.now(timezone.utc)}},
    )
    await log_event("2fa_enabled", user_id=str(user["_id"]), request=request)
    return {"status": "success", "message": "2FA enabled"}


async def twofa_disable(user: dict, request: Request) -> dict:
    await twofa().delete_one({"user_id": str(user["_id"])})
    await log_event("2fa_disabled", user_id=str(user["_id"]), request=request)
    return {"status": "success", "message": "2FA disabled"}
