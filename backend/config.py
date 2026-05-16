import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "insecure-dev-key")
    DEBUG = _bool("FLASK_DEBUG", True)
    BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000")

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "stock_alert_db")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "StockSense Alerts")

    ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")

    DROP_AND_REBUILD_SCHEMA = _bool("DROP_AND_REBUILD_SCHEMA", False)

    # Session config — plan.md §4a
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = not _bool("FLASK_DEBUG", True)
    # 4-hour sliding window (was 7 days)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=4)

    # Rate-limit storage backend; defaults to in-memory but recommend redis in prod.
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per minute")

    # Redis cache (Phase 4e). Optional — falls back to in-process dict if absent.
    REDIS_URL = os.getenv("REDIS_URL", "")

    # Sentry DSN (Phase 4b).
    SENTRY_DSN = os.getenv("SENTRY_DSN", "")

    # CSRF
    WTF_CSRF_TIME_LIMIT = None  # CSRF tokens valid for session lifetime
    WTF_CSRF_HEADERS = ["X-CSRFToken"]


config = Config()
