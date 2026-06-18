"""Application settings loaded from environment (.env).

Uses pydantic-settings so values are validated and typed. Mirrors the
config surface of the legacy Flask `config.py`, but swaps Postgres for
MongoDB and Flask sessions for JWT.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Core ----
    APP_NAME: str = "StockSense"
    DEBUG: bool = True
    APP_BASE_URL: str = "http://127.0.0.1:8000"
    # Comma-separated list of allowed CORS origins (the Vite dev server, etc.)
    FRONTEND_ORIGIN: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ---- MongoDB ----
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "stocksense"

    # ---- JWT auth ----
    JWT_SECRET: str = "dev-secret-please-change-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 4  # matches legacy 4-hour session window

    # ---- SMTP / email ----
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "StockSense Alerts"

    # ---- Market data ----
    ALPHA_VANTAGE_KEY: str = ""

    # ---- Cache / observability ----
    REDIS_URL: str = ""
    SENTRY_DSN: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.FRONTEND_ORIGIN.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
