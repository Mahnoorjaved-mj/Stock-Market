"""APScheduler bootstrap: alert sweeps + digest jobs."""
from __future__ import annotations

import atexit
import traceback

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from services import alerts_engine as alerts
from services import digests

ET = pytz.timezone("US/Eastern")
_scheduler: BackgroundScheduler | None = None


def _safe(fn):
    def wrapped():
        try:
            fn()
        except Exception:
            traceback.print_exc()
    return wrapped


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    sched = BackgroundScheduler(timezone=ET, daemon=True)

    # Alert sweep: every 15 min between 09:30 and 16:00 ET, Mon-Fri
    sched.add_job(
        _safe(alerts.evaluate_user_alerts),
        CronTrigger(day_of_week="mon-fri", hour="9-15", minute="*/15", timezone=ET),
        id="alert_sweep_intraday",
        replace_existing=True,
    )
    # 16:00 final tick (the hour="9-15" rule excludes hour 16)
    sched.add_job(
        _safe(alerts.evaluate_user_alerts),
        CronTrigger(day_of_week="mon-fri", hour=16, minute=0, timezone=ET),
        id="alert_sweep_close",
        replace_existing=True,
    )

    # Daily digest: 17:00 ET Mon-Fri
    sched.add_job(
        _safe(digests.send_daily_digest),
        CronTrigger(day_of_week="mon-fri", hour=17, minute=0, timezone=ET),
        id="daily_digest",
        replace_existing=True,
    )

    # Weekly digest: Friday 17:00 ET (kept separate from per-user digest_day for now)
    sched.add_job(
        _safe(digests.send_weekly_digest),
        CronTrigger(day_of_week="fri", hour=17, minute=15, timezone=ET),
        id="weekly_digest",
        replace_existing=True,
    )

    sched.start()
    atexit.register(lambda: sched.shutdown(wait=False))
    _scheduler = sched
    print("⏰ Scheduler started: alert sweeps every 15 min during US market hours; digests scheduled")
    return sched
