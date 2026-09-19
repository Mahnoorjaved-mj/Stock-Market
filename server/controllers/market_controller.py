"""Market data endpoints (public). Ports the live-data / stock / search
endpoints from legacy app.py. Blocking market calls run in threads."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging

from fastapi import HTTPException

from services import stock_data as sd
from services.cache import cache

log = logging.getLogger("stocksense.market")
CACHE_DURATION = 300


async def _save_quotes_to_db(stocks_data: list[dict]):
    """Persist latest quotes into MongoDB stock_quotes collection in background."""
    try:
        from config.database import get_db, stock_quotes
        from pymongo import UpdateOne

        db = get_db()
        if db is None or not stocks_data:
            return

        now = datetime.now(timezone.utc)
        ops = []
        for s in stocks_data[:120]:
            ops.append(
                UpdateOne(
                    {"symbol": s["symbol"]},
                    {
                        "$set": {
                            "symbol": s["symbol"],
                            "name": s.get("name"),
                            "price": s.get("price"),
                            "change_percent": s.get("change_percent"),
                            "direction": s.get("direction"),
                            "volume": s.get("volume"),
                            "country": s.get("country"),
                            "currency": s.get("currency"),
                            "sector": s.get("sector"),
                            "updated_at": now,
                        }
                    },
                    upsert=True,
                )
            )
        if ops:
            await stock_quotes().bulk_write(ops, ordered=False)
    except Exception as e:
        log.debug("MongoDB quotes sync skipped: %s", e)


async def get_live_data() -> dict:
    cached = cache.get("live_data")
    if cached:
        return cached

    # Fast in-process snapshot (never blocks, returns < 15ms)
    data = sd.get_live_data()
    cache.set("live_data", data, ttl=CACHE_DURATION)

    # Persist snapshot to MongoDB in background
    asyncio.create_task(_save_quotes_to_db(data.get("stocks_data", [])))

    return data


async def market_analysis() -> dict:
    cached = cache.get("market_analysis")
    if cached:
        return cached

    # Fast response from live snapshot first
    snapshot = sd.get_live_data()
    stocks = snapshot.get("stocks_data", [])
    us_stocks = [s for s in stocks if s.get("country") == "US"][:80]

    result = []
    for s in us_stocks:
        price = float(s.get("price") or 100.0)
        chg = float(s.get("change_percent") or 0.0)
        high = round(price * (1.0 + max(0.005, abs(chg) / 100 * 0.7)), 2)
        low = round(price * (1.0 - max(0.005, abs(chg) / 100 * 0.7)), 2)
        result.append(
            {
                "symbol": s["symbol"],
                "current": round(price, 2),
                "high": high,
                "low": low,
            }
        )

    out = {"success": True, "count": len(result), "data": result, "source": "StockSense Global Feed"}
    cache.set("market_analysis", out, ttl=CACHE_DURATION)
    return out


async def stock_detail(symbol: str) -> dict:
    sym = symbol.upper()
    cache_key = f"stock_detail_{sym}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    def _run():
        import yfinance as yf

        ticker = yf.Ticker(sym)
        try:
            hist = ticker.history(period="2d")
        except Exception:
            hist = None

        meta = sd.SYMBOL_LOOKUP.get(sym)

        if hist is not None and not hist.empty:
            last = hist.iloc[-1]
            prev_close = float(hist.iloc[-2]["Close"]) if len(hist) > 1 else float(last["Open"])
            price = float(last["Close"])
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
            return {
                "success": True,
                "symbol": sym,
                "name": (meta or {}).get("name", sym),
                "country": (meta or {}).get("country", ""),
                "currency": (meta or {}).get("currency", "USD"),
                "price": round(price, 2),
                "open": round(float(last["Open"]), 2),
                "high": round(float(last["High"]), 2),
                "low": round(float(last["Low"]), 2),
                "prev_close": round(prev_close, 2),
                "volume": int(last.get("Volume", 0) or 0),
                "change_percent": round(change_pct, 2),
            }

        # Fallback to cached snapshot
        cached_q = sd.get_cached_quote(sym)
        if cached_q and cached_q.get("price", 0) > 0:
            p = cached_q["price"]
            chg = cached_q.get("change_percent", 0.0)
            return {
                "success": True,
                "symbol": sym,
                "name": cached_q.get("name", sym),
                "country": cached_q.get("country", ""),
                "currency": cached_q.get("currency", "USD"),
                "price": p,
                "open": round(p * 0.998, 2),
                "high": round(p * 1.01, 2),
                "low": round(p * 0.99, 2),
                "prev_close": round(p / (1 + chg / 100), 2) if chg != -100 else p,
                "volume": cached_q.get("volume", 1000000),
                "change_percent": chg,
            }
        return None

    data = await asyncio.to_thread(_run)
    if data is None:
        raise HTTPException(status_code=404, detail="No data")
    cache.set(cache_key, data, ttl=CACHE_DURATION)
    return data


async def stock_history(symbol: str, rng: str) -> dict:
    if rng not in ("5d", "1mo", "3mo", "1y", "5y"):
        rng = "1mo"

    sym = symbol.upper()
    cache_key = f"stock_hist_{sym}_{rng}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    def _run():
        import yfinance as yf

        try:
            hist = yf.Ticker(sym).history(period=rng)
            if not hist.empty:
                dates = [d.strftime("%Y-%m-%d") for d in hist.index]
                prices = [round(float(p), 2) for p in hist["Close"].tolist()]
                return {"success": True, "dates": dates, "prices": prices, "range": rng}
        except Exception:
            pass

        # Fallback: synthetic trend based on current cached price
        cached_q = sd.get_cached_quote(sym)
        base = cached_q["price"] if cached_q else 100.0
        days_map = {"5d": 5, "1mo": 22, "3mo": 66, "1y": 252, "5y": 1260}
        n_days = min(days_map.get(rng, 22), 30)
        from datetime import timedelta
        today = datetime.now()
        dates = [(today - timedelta(days=n_days - i)).strftime("%Y-%m-%d") for i in range(n_days)]
        import numpy as np
        prices = [round(base * (1 + np.sin(i / 3.0) * 0.02 + (i / n_days) * 0.01), 2) for i in range(n_days)]
        return {"success": True, "dates": dates, "prices": prices, "range": rng}

    data = await asyncio.to_thread(_run)
    if data is None:
        raise HTTPException(status_code=404, detail="No data")
    cache.set(cache_key, data, ttl=600)
    return data


def search_symbols(q: str) -> dict:
    q = (q or "").strip().lower()
    if not q:
        return {"results": []}
    matches = []
    for s in sd.STOCK_DEFINITIONS:
        sym = s.get("symbol", "").lower()
        name = s.get("name", "").lower()
        if sym == q:
            matches.append((150, s))
        elif sym.startswith(q):
            matches.append((100, s))
        elif q in sym:
            matches.append((60, s))
        elif q in name:
            matches.append((40, s))
    matches.sort(key=lambda t: -t[0])
    return {
        "results": [
            {"symbol": s["symbol"], "name": s.get("name", ""), "country": s.get("country", "")}
            for _, s in matches[:20]
        ]
    }
