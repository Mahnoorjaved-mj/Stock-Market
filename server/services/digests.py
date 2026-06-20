"""Daily / weekly digest email jobs. Mongo rewrite of legacy digests.py."""
from __future__ import annotations

import asyncio
import traceback

from services import email_service


def _fetch_live_safe(symbol: str):
    try:
        from services import stock_data as sd

        return sd.fetcher.get_stock_data(symbol)
    except Exception:
        return None


async def _build_user_digest(user: dict, period: str) -> dict:
    from config.database import portfolio, watchlist
    from services import stock_data as sd

    uid = str(user["_id"])
    wl = await watchlist().find({"user_id": uid}).sort("added_at", -1).to_list(length=12)
    pf = await portfolio().find({"user_id": uid}).to_list(length=1000)

    watchlist_rows = []
    for r in wl:
        live = await asyncio.to_thread(_fetch_live_safe, r["symbol"]) or {}
        if not live.get("success"):
            continue
        meta = sd.SYMBOL_LOOKUP.get(r["symbol"].upper()) or {}
        watchlist_rows.append(
            {
                "symbol": r["symbol"],
                "name": meta.get("name", r["symbol"]),
                "price": float(live.get("price") or 0),
                "change_pct": float(live.get("change_percent") or 0),
            }
        )

    total_cost = total_value = 0.0
    for r in pf:
        live = await asyncio.to_thread(_fetch_live_safe, r["symbol"]) or {}
        price = float(live.get("price") or 0)
        qty = float(r["quantity"])
        buy = float(r["buy_price"])
        total_cost += buy * qty
        total_value += price * qty

    totals = None
    if total_cost > 0:
        pnl = total_value - total_cost
        totals = {"value": total_value, "pnl": pnl, "pnl_pct": (pnl / total_cost) * 100}

    top_picks = []
    try:
        from services.ai_predictions import ai_predictor

        for p in (ai_predictor.get_top_picks(5) or []):
            top_picks.append(
                {
                    "symbol": p.get("symbol"),
                    "sentiment": p.get("sentiment"),
                    "confidence": float(p.get("confidence") or 0),
                    "predicted_change": float(p.get("predicted_change") or 0),
                }
            )
    except Exception:
        pass

    return {
        "name": user.get("name") or user["email"],
        "period": period,
        "watchlist_rows": watchlist_rows,
        "totals": totals,
        "top_picks": top_picks,
    }


async def _send_for_users(period: str, frequency: str) -> int:
    from config.database import users

    candidates = await users().find({"digest_frequency": frequency}).to_list(length=10000)
    sent = 0
    for u in candidates:
        try:
            payload = await _build_user_digest(u, period)
            if not payload["watchlist_rows"] and not payload["totals"]:
                continue
            ok = await asyncio.to_thread(email_service.send_digest, u["email"], payload)
            if ok:
                sent += 1
        except Exception:
            traceback.print_exc()
    print(f"📨 [{period} digest] sent={sent} / candidates={len(candidates)}")
    return sent


async def send_daily_digest() -> int:
    return await _send_for_users("Daily", "daily")


async def send_weekly_digest() -> int:
    return await _send_for_users("Weekly", "weekly")
