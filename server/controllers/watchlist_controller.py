"""Watchlist CRUD + symbol catalog. Ports legacy routes/watchlist.py."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from config.database import watchlist
from services import stock_data as sd

SYMBOL_RE = re.compile(r"^[A-Z0-9.\-]{1,15}$")


def validate_symbol(sym: str) -> str:
    sym = (sym or "").strip().upper()
    if not SYMBOL_RE.match(sym):
        raise HTTPException(status_code=400, detail="Invalid symbol")
    return sym


def _opt_positive(val, name: str):
    if val in (None, "", "null"):
        return None
    try:
        d = float(val)
        if d <= 0:
            raise ValueError
        return d
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"{name} must be a positive number")


def _oid(entry_id: str) -> ObjectId:
    try:
        return ObjectId(entry_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Not found")


async def list_watchlist(user_id: str) -> dict:
    cursor = watchlist().find({"user_id": user_id}).sort("added_at", -1)
    items = []
    async for r in cursor:
        symbol = r["symbol"]
        d = {
            "id": str(r["_id"]),
            "symbol": symbol,
            "threshold_pct": r.get("threshold_pct"),
            "target_price_high": r.get("target_price_high"),
            "target_price_low": r.get("target_price_low"),
            "added_at": r["added_at"].isoformat() if r.get("added_at") else None,
        }
        try:
            live = sd.fetcher.get_stock_data(symbol)
            d["price"] = float(live.get("price") or 0)
            d["change_percent"] = float(live.get("change_percent") or 0)
        except Exception:
            d["price"] = None
            d["change_percent"] = None
        meta = sd.SYMBOL_LOOKUP.get(symbol.upper())
        d["name"] = meta["name"] if meta else symbol
        d["sector"] = meta["sector"] if meta else None
        d["currency"] = meta["currency"] if meta else "USD"
        items.append(d)
    return {"status": "success", "items": items}


async def add_watchlist(user_id: str, data: dict) -> dict:
    symbol = validate_symbol(data.get("symbol"))
    threshold = _opt_positive(data.get("threshold_pct"), "threshold_pct")
    t_high = _opt_positive(data.get("target_price_high"), "target_price_high")
    t_low = _opt_positive(data.get("target_price_low"), "target_price_low")

    now = datetime.now(timezone.utc)
    res = await watchlist().update_one(
        {"user_id": user_id, "symbol": symbol},
        {
            "$set": {
                "threshold_pct": threshold,
                "target_price_high": t_high,
                "target_price_low": t_low,
                "updated_at": now,
            },
            "$setOnInsert": {"user_id": user_id, "symbol": symbol, "added_at": now},
        },
        upsert=True,
    )
    doc = await watchlist().find_one({"user_id": user_id, "symbol": symbol})
    return {"status": "success", "id": str(doc["_id"])}


async def update_watchlist(user_id: str, entry_id: str, data: dict) -> dict:
    fields = {}
    if "threshold_pct" in data:
        fields["threshold_pct"] = _opt_positive(data["threshold_pct"], "threshold_pct")
    if "target_price_high" in data:
        fields["target_price_high"] = _opt_positive(data["target_price_high"], "target_price_high")
    if "target_price_low" in data:
        fields["target_price_low"] = _opt_positive(data["target_price_low"], "target_price_low")
    if not fields:
        raise HTTPException(status_code=400, detail="Nothing to update")
    fields["updated_at"] = datetime.now(timezone.utc)

    res = await watchlist().update_one(
        {"_id": _oid(entry_id), "user_id": user_id}, {"$set": fields}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "success"}


async def delete_watchlist(user_id: str, entry_id: str) -> dict:
    res = await watchlist().delete_one({"_id": _oid(entry_id), "user_id": user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "success"}


def list_symbols() -> dict:
    out = [
        {"symbol": sym, "name": meta["name"], "sector": meta["sector"], "country": meta["country"]}
        for sym, meta in sd.SYMBOL_LOOKUP.items()
    ]
    return {"status": "success", "symbols": out}
