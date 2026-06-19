"""APScheduler (async) bootstrap: alert sweeps + digest jobs.

Uses AsyncIOScheduler so it can run the async Mongo coroutines directly on
the FastAPI event loop. Trigger cadence matches the legacy scheduler.
"""
from __future__ import annotations

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from services import alerts_engine as alerts
from services import digests

ET = pytz.timezone("US/Eastern")
_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    sched = AsyncIOScheduler(timezone=ET)

    # Alert sweep every 15 min, 09:30–15:xx ET Mon–Fri, plus a 16:00 close tick.
    sched.add_job(
        alerts.evaluate_user_alerts,
        CronTrigger(day_of_week="mon-fri", hour="9-15", minute="*/15", timezone=ET),
        id="alert_sweep_intraday",
        replace_existing=True,
    )
    sched.add_job(
        alerts.evaluate_user_alerts,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=0, timezone=ET),
        id="alert_sweep_close",
        replace_existing=True,
    )
    # Daily digest 17:00 ET Mon–Fri; weekly digest Friday 17:15 ET.
    sched.add_job(
        digests.send_daily_digest,
        CronTrigger(day_of_week="mon-fri", hour=17, minute=0, timezone=ET),
        id="daily_digest",
        replace_existing=True,
    )
    sched.add_job(
        digests.send_weekly_digest,
        CronTrigger(day_of_week="fri", hour=17, minute=15, timezone=ET),
        id="weekly_digest",
        replace_existing=True,
    )

    sched.start()
    _scheduler = sched
    print("⏰ Scheduler started: alert sweeps every 15 min during US market hours; digests scheduled")
    return sched


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def is_running() -> bool:
    return bool(_scheduler and _scheduler.running)
