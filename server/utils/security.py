"""Password hashing, JWT tokens, and validation helpers.

Ports the security primitives from legacy `backend/routes/auth.py`:
bcrypt rounds=12, the same password strength rules, and email validation.
Flask sessions are replaced with stateless JWT (HS256).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from email_validator import EmailNotValidError, validate_email
from jose import JWTError, jwt

from config.settings import settings

PASSWORD_MIN_LEN = 10


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def validate_password(pw: str) -> Optional[str]:
    """Return an error string if invalid, else None.

    Rules (from legacy §4a): min 10 chars, at least one letter and one digit,
    and a symbol unless length >= 14.
    """
    if not pw or len(pw) < PASSWORD_MIN_LEN:
        return f"Password must be at least {PASSWORD_MIN_LEN} characters"
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Password must contain at least one letter and one digit"
    if len(pw) < 14 and not re.search(r"[^A-Za-z0-9]", pw):
        return "Password must contain a symbol (or be at least 14 characters)"
    return None


def validate_email_address(em: str) -> Optional[str]:
    try:
        validate_email(em, check_deliverability=False)
        return None
    except EmailNotValidError as e:
        return str(e)


def create_access_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
