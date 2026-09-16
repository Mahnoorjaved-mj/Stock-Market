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


def connect() -> AsyncIOMotorDatabase | None:
    """Create the Motor client (idempotent) and return the database handle."""
    global _client, _db
    if _db is None:
        uri = (settings.MONGO_URI or "").strip()
        if not uri:
            log.warning("MONGO_URI is not set. MongoDB features are currently inactive.")
            return None

        client_kwargs = {
            "serverSelectionTimeoutMS": 10000,
        }
        # For MongoDB Atlas (mongodb+srv:// or TLS connections), provide certifi CA bundle
        # to ensure reliable SSL handshakes on Windows.
        if "mongodb+srv://" in uri or "ssl=true" in uri.lower() or "tls=true" in uri.lower():
            try:
                import certifi
                client_kwargs["tlsCAFile"] = certifi.where()
            except Exception:
                pass

        _client = AsyncIOMotorClient(uri, **client_kwargs)
        _db = _client[settings.MONGO_DB_NAME]
        log.info("Connected to MongoDB Atlas db=%s", settings.MONGO_DB_NAME)
    return _db


def get_db() -> AsyncIOMotorDatabase | None:
    if _db is None:
        return connect()
    return _db


def close() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None


def _require_db() -> AsyncIOMotorDatabase:
    db = get_db()
    if db is None:
        raise RuntimeError("MongoDB connection is not configured. Please set MONGO_URI in server/.env.")
    return db


# ---- Collection accessors ----
def users():
    return _require_db()["users"]


def otp():
    return _require_db()["otp_verification"]


def reset_tokens():
    return _require_db()["password_reset_tokens"]


def watchlist():
    return _require_db()["watchlist"]


def portfolio():
    return _require_db()["portfolio"]


def alert_history():
    return _require_db()["alert_history"]


def alert_rules():
    return _require_db()["alert_rules"]


def audit_events():
    return _require_db()["audit_events"]


def twofa():
    return _require_db()["user_2fa_secrets"]


def notifications():
    return _require_db()["notifications"]


def push_subs():
    return _require_db()["push_subscriptions"]


def stock_quotes():
    return _require_db()["stock_quotes"]


def predictions_history():
    return _require_db()["predictions_history"]


async def ensure_indexes() -> None:
    """Create unique/lookup indexes mirroring the application schema."""
    db = get_db()
    if db is None:
        log.warning("Skipping MongoDB index creation: MONGO_URI is not set.")
        return

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
    await stock_quotes().create_index([("symbol", ASCENDING)], unique=True)
    await stock_quotes().create_index([("updated_at", DESCENDING)])
    await predictions_history().create_index([("symbol", ASCENDING), ("created_at", DESCENDING)])
    log.info("MongoDB indexes ensured")
