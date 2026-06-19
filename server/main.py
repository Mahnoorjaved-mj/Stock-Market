"""StockSense FastAPI application entrypoint.

Wires CORS, mounts routers, bootstraps MongoDB indexes, and starts the
APScheduler jobs + background AI training during the app lifespan.
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

# Force UTF-8 stdout/stderr so emoji log lines don't crash on the Windows
# console (cp1252). Must run before any module prints unicode.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config.database import close, connect, ensure_indexes
from config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("stocksense")

limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- Startup ----
    connect()
    try:
        await ensure_indexes()
    except Exception as e:
        # Don't hard-fail boot if Mongo is unreachable; /api/health will
        # report "degraded" and DB-backed routes will surface a clear error.
        log.warning("Could not ensure MongoDB indexes (is MongoDB running?): %s", e)

    # Optional Sentry
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk

            sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)
            log.info("Sentry initialized")
        except Exception as e:  # pragma: no cover
            log.warning("Sentry init failed: %s", e)

    # Scheduler (alert sweeps + digests) and background AI training
    try:
        from services.scheduler import start_scheduler

        start_scheduler()
    except Exception as e:  # pragma: no cover
        log.warning("Scheduler failed to start: %s", e)

    try:
        from services.ai_training import start_background_training

        start_background_training()
    except Exception as e:  # pragma: no cover
        log.warning("Background AI training failed to start: %s", e)

    log.info("%s API ready", settings.APP_NAME)
    yield

    # ---- Shutdown ----
    try:
        from services.scheduler import stop_scheduler

        stop_scheduler()
    except Exception:
        pass
    close()


app = FastAPI(title=f"{settings.APP_NAME} API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routers ----
from routes import (  # noqa: E402
    admin,
    ai,
    alerts,
    auth,
    market,
    notifications,
    portfolio,
    profile,
    watchlist,
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(watchlist.router)
app.include_router(portfolio.router)
app.include_router(alerts.router)
app.include_router(notifications.router)
app.include_router(market.router)
app.include_router(ai.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health():
    from config.database import get_db

    db_ok, db_error = False, None
    try:
        await get_db().command("ping")
        db_ok = True
    except Exception as e:
        db_error = str(e)

    scheduler_ok = False
    try:
        from services.scheduler import is_running

        scheduler_ok = is_running()
    except Exception:
        scheduler_ok = False

    payload = {
        "status": "healthy" if db_ok else "degraded",
        "db": {"ok": db_ok, "error": db_error},
        "scheduler": {"ok": scheduler_ok},
    }
    return payload


if __name__ == "__main__":
    # So you can just run `python main.py` instead of the long uvicorn command.
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=settings.DEBUG)
