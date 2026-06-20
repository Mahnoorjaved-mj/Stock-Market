"""Portfolio CRUD + PnL enrichment. Ports legacy routes/portfolio.py."""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from config.database import portfolio
from controllers.watchlist_controller import validate_symbol
from services import stock_data as sd


def _pos(v, name: str) -> float:
    try:
        d = float(v)
        if d <= 0:
            raise ValueError
        return d
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"{name} must be a positive number")


def _parse_date(v) -> str:
    try:
        datetime.strptime(v, "%Y-%m-%d")
        return v
    except Exception:
        raise HTTPException(status_code=400, detail="buy_date must be YYYY-MM-DD")


def _oid(entry_id: str) -> ObjectId:
    try:
        return ObjectId(entry_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Not found")


def _enrich(rows: list[dict]):
    out, total_cost, total_value = [], 0.0, 0.0
    for r in rows:
        symbol = r["symbol"]
        qty = float(r["quantity"])
        buy_price = float(r["buy_price"])
        meta = sd.SYMBOL_LOOKUP.get(symbol.upper())
        try:
            live = sd.fetcher.get_stock_data(symbol)
            current = float(live.get("price") or 0)
        except Exception:
            current = 0.0
        cost = buy_price * qty
        value = current * qty
        out.append(
            {
                "id": str(r["_id"]),
                "symbol": symbol,
                "quantity": qty,
                "buy_price": buy_price,
                "buy_date": r.get("buy_date"),
                "notes": r.get("notes"),
                "name": meta["name"] if meta else symbol,
                "currency": meta["currency"] if meta else "USD",
                "current_price": current,
                "cost_basis": cost,
                "current_value": value,
                "pnl": value - cost,
                "pnl_pct": ((value - cost) / cost * 100) if cost > 0 else 0.0,
            }
        )
        total_cost += cost
        total_value += value
    totals = {
        "cost_basis": total_cost,
        "current_value": total_value,
        "pnl": total_value - total_cost,
        "pnl_pct": ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0.0,
    }
    return out, totals


async def list_holdings(user_id: str) -> dict:
    rows = await portfolio().find({"user_id": user_id}).sort("buy_date", -1).to_list(length=1000)
    items, totals = _enrich(rows)
    return {"status": "success", "items": items, "totals": totals}


async def add_holding(user_id: str, data: dict) -> dict:
    symbol = validate_symbol(data.get("symbol"))
    qty = _pos(data.get("quantity"), "quantity")
    buy_price = _pos(data.get("buy_price"), "buy_price")
    buy_date = _parse_date(data.get("buy_date"))
    notes = (data.get("notes") or "").strip() or None

    now = datetime.now(timezone.utc)
    res = await portfolio().insert_one(
        {
            "user_id": user_id,
            "symbol": symbol,
            "quantity": qty,
            "buy_price": buy_price,
            "buy_date": buy_date,
            "notes": notes,
            "created_at": now,
            "updated_at": now,
        }
    )
    return {"status": "success", "id": str(res.inserted_id)}


async def update_holding(user_id: str, entry_id: str, data: dict) -> dict:
    fields = {}
    if "quantity" in data:
        fields["quantity"] = _pos(data["quantity"], "quantity")
    if "buy_price" in data:
        fields["buy_price"] = _pos(data["buy_price"], "buy_price")
    if "buy_date" in data:
        fields["buy_date"] = _parse_date(data["buy_date"])
    if "notes" in data:
        fields["notes"] = (data["notes"] or "").strip() or None
    if not fields:
        raise HTTPException(status_code=400, detail="Nothing to update")
    fields["updated_at"] = datetime.now(timezone.utc)

    res = await portfolio().update_one(
        {"_id": _oid(entry_id), "user_id": user_id}, {"$set": fields}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "success"}


async def delete_holding(user_id: str, entry_id: str) -> dict:
    res = await portfolio().delete_one({"_id": _oid(entry_id), "user_id": user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "success"}


async def export_csv(user_id: str) -> str:
    from io import StringIO
    import csv

    rows = await portfolio().find({"user_id": user_id}).sort("buy_date", -1).to_list(length=5000)
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["symbol", "quantity", "buy_price", "buy_date", "notes"])
    for r in rows:
        w.writerow(
            [r.get("symbol"), r.get("quantity"), r.get("buy_price"), r.get("buy_date"), r.get("notes")]
        )
    return buf.getvalue()
