"""MongoDB (Motor) async client + collection accessors + index bootstrap.

Replaces the legacy psycopg2 layer in `backend/db.py`. Postgres tables map
1:1 to Mongo collections; SERIAL ids become ObjectId `_id`, and foreign-key
`user_id` columns become a stored ObjectId reference on each document.
"""
from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from config.settings import settings

log = logging.getLogger("stocksense.db")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def connect() -> AsyncIOMotorDatabase:
    """Create the Motor client (idempotent) and return the database handle."""
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000)
        _db = _client[settings.MONGO_DB_NAME]
        log.info("Connected to MongoDB db=%s", settings.MONGO_DB_NAME)
    return _db


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        return connect()
    return _db


def close() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None


# ---- Collection accessors (one per legacy table) ----
def users():
    return get_db()["users"]


def otp():
    return get_db()["otp_verification"]


def reset_tokens():
    return get_db()["password_reset_tokens"]


def watchlist():
    return get_db()["watchlist"]


def portfolio():
    return get_db()["portfolio"]


def alert_history():
    return get_db()["alert_history"]


def alert_rules():
    return get_db()["alert_rules"]


def audit_events():
    return get_db()["audit_events"]


def twofa():
    return get_db()["user_2fa_secrets"]


def notifications():
    return get_db()["notifications"]


def push_subs():
    return get_db()["push_subscriptions"]


async def ensure_indexes() -> None:
    """Create unique/lookup indexes mirroring the legacy SQL schema."""
    await users().create_index([("email", ASCENDING)], unique=True)
    await otp().create_index([("email", ASCENDING)])
    await otp().create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
    await reset_tokens().create_index([("token", ASCENDING)], unique=True)
    await watchlist().create_index(
        [("user_id", ASCENDING), ("symbol", ASCENDING)], unique=True
    )
    await portfolio().create_index([("user_id", ASCENDING)])
    await alert_history().create_index(
        [("user_id", ASCENDING), ("symbol", ASCENDING), ("sent_at", DESCENDING)]
    )
    await alert_rules().create_index([("user_id", ASCENDING)])
    await audit_events().create_index([("user_id", ASCENDING), ("occurred_at", DESCENDING)])
    await audit_events().create_index([("action", ASCENDING), ("occurred_at", DESCENDING)])
    await twofa().create_index([("user_id", ASCENDING)], unique=True)
    await notifications().create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await push_subs().create_index([("endpoint", ASCENDING)], unique=True)
    log.info("MongoDB indexes ensured")
