"""Alert engine — evaluate every watchlist entry and email alerts.

Mongo rewrite of legacy backend/services/alerts_engine.py. Blocking work
(market-data fetch, SMTP) is offloaded to threads so the event loop stays
responsive when triggered from the async scheduler or an API request.
"""
from __future__ import annotations

import asyncio
import traceback
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from config.database import alert_history, users, watchlist
from services import email_service

DEDUP_HOURS = 4


def _fetch_live(symbol: str):
    try:
        from services import stock_data as sd

        d = sd.fetcher.get_stock_data(symbol)
        if not d or not d.get("success") or not d.get("price"):
            return None
        return d
    except Exception:
        traceback.print_exc()
        return None


def _meta(symbol: str) -> dict:
    try:
        from services import stock_data as sd

        return sd.SYMBOL_LOOKUP.get(symbol.upper()) or {}
    except Exception:
        return {}


async def _was_recently_sent(user_id: str, symbol: str, alert_type: str) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=DEDUP_HOURS)
    found = await alert_history().find_one(
        {"user_id": user_id, "symbol": symbol, "alert_type": alert_type, "sent_at": {"$gt": cutoff}}
    )
    return found is not None


async def evaluate_user_alerts() -> dict:
    started = datetime.now(timezone.utc)
    print(f"\n🔔 [alert_sweep] starting at {started.isoformat()}")

    sent = skipped = errors = 0
    user_cache: dict[str, dict] = {}

    rows = await watchlist().find({}).to_list(length=10000)
    print(f"   {len(rows)} watchlist entries to evaluate")

    for r in rows:
        try:
            uid = r["user_id"]
            user = user_cache.get(uid)
            if user is None:
                user = await users().find_one({"_id": ObjectId(uid)})
                user_cache[uid] = user or {}
            if not user:
                continue

            live = await asyncio.to_thread(_fetch_live, r["symbol"])
            if not live:
                continue
            price = float(live["price"])
            change_pct = float(live.get("change_percent") or 0)

            eff = r.get("threshold_pct")
            if eff is None:
                eff = user.get("alert_threshold_pct")
            eff_threshold = float(eff) if eff is not None else 5.0

            meta = _meta(r["symbol"])
            name = meta.get("name", r["symbol"])
            currency = meta.get("currency", "USD")

            triggers = []
            if abs(change_pct) >= eff_threshold:
                triggers.append(
                    ("pct_move", f"Moved {change_pct:+.2f}% (threshold ±{eff_threshold:g}%)", eff_threshold)
                )
            if r.get("target_price_high") is not None and price >= float(r["target_price_high"]):
                triggers.append(
                    ("target_high", f"Crossed above target {currency} {float(r['target_price_high']):.2f}", float(r["target_price_high"]))
                )
            if r.get("target_price_low") is not None and price <= float(r["target_price_low"]):
                triggers.append(
                    ("target_low", f"Dropped below target {currency} {float(r['target_price_low']):.2f}", float(r["target_price_low"]))
                )
            if not triggers:
                continue

            for alert_type, headline, threshold in triggers:
                if await _was_recently_sent(uid, r["symbol"], alert_type):
                    skipped += 1
                    continue
                ok = await asyncio.to_thread(
                    email_service.send_alert,
                    user["email"],
                    {
                        "symbol": r["symbol"],
                        "name": name,
                        "price": price,
                        "change_pct": change_pct,
                        "alert_type": alert_type,
                        "threshold": threshold,
                        "currency": currency,
                        "headline": headline,
                    },
                )
                if ok:
                    await alert_history().insert_one(
                        {
                            "user_id": uid,
                            "symbol": r["symbol"],
                            "alert_type": alert_type,
                            "price": price,
                            "change_pct": change_pct,
                            "sent_at": datetime.now(timezone.utc),
                        }
                    )
                    sent += 1
        except Exception as e:
            errors += 1
            print(f"   ❌ alert error sym={r.get('symbol')}: {e}")

    duration = (datetime.now(timezone.utc) - started).total_seconds()
    summary = {"sent": sent, "skipped": skipped, "errors": errors, "duration_s": round(duration, 2)}
    print(f"🔔 [alert_sweep] done: {summary}")
    return summary
