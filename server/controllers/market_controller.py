"""Market data endpoints (public). Ports the live-data / stock / search
endpoints from legacy app.py. Blocking market calls run in threads."""
from __future__ import annotations

import asyncio

from fastapi import HTTPException

from services import stock_data as sd
from services.cache import cache

CACHE_DURATION = 300


async def get_live_data() -> dict:
    cached = cache.get("live_data")
    if cached:
        return cached
    data = await asyncio.to_thread(sd.get_live_data)
    cache.set("live_data", data, ttl=CACHE_DURATION)
    return data


async def market_analysis() -> dict:
    def _run():
        import yfinance as yf

        symbols = [s["symbol"] for s in sd.STOCK_DEFINITIONS if s["country"] == "US"][:80]
        result = []
        for symbol in symbols:
            try:
                hist = yf.Ticker(symbol).history(period="1d")
                if hist.empty:
                    continue
                row = hist.iloc[-1]
                result.append(
                    {
                        "symbol": symbol,
                        "current": round(float(row["Close"]), 2),
                        "high": round(float(row["High"]), 2),
                        "low": round(float(row["Low"]), 2),
                    }
                )
            except Exception:
                continue
        return result

    data = await asyncio.to_thread(_run)
    return {"success": True, "count": len(data), "data": data, "source": "yfinance (Daily OHLC)"}


async def stock_detail(symbol: str) -> dict:
    def _run():
        import yfinance as yf

        sym = symbol.upper()
        ticker = yf.Ticker(sym)
        hist = ticker.history(period="2d")
        if hist.empty:
            return None
        last = hist.iloc[-1]
        prev_close = float(hist.iloc[-2]["Close"]) if len(hist) > 1 else float(last["Open"])
        price = float(last["Close"])
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
        meta = sd.SYMBOL_LOOKUP.get(sym)
        return {
            "success": True,
            "symbol": sym,
            "name": (meta or {}).get("name", sym),
            "country": (meta or {}).get("country", ""),
            "currency": (meta or {}).get("currency", "USD"),
            "price": price,
            "open": float(last["Open"]),
            "high": float(last["High"]),
            "low": float(last["Low"]),
            "prev_close": prev_close,
            "volume": int(last.get("Volume", 0) or 0),
            "change_percent": change_pct,
        }

    data = await asyncio.to_thread(_run)
    if data is None:
        raise HTTPException(status_code=404, detail="No data")
    return data


async def stock_history(symbol: str, rng: str) -> dict:
    if rng not in ("5d", "1mo", "3mo", "1y", "5y"):
        rng = "1mo"

    def _run():
        import yfinance as yf

        hist = yf.Ticker(symbol.upper()).history(period=rng)
        if hist.empty:
            return None
        dates = [d.strftime("%Y-%m-%d") for d in hist.index]
        prices = [float(p) for p in hist["Close"].tolist()]
        return {"success": True, "dates": dates, "prices": prices, "range": rng}

    data = await asyncio.to_thread(_run)
    if data is None:
        raise HTTPException(status_code=404, detail="No data")
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
