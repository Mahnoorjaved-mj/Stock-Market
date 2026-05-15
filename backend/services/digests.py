"""Daily and weekly digest email jobs."""
from __future__ import annotations

import traceback
from datetime import datetime, timezone
from decimal import Decimal

from services import email_service
from db import get_db_connection, get_dict_cursor


def _fetch_live_safe(symbol: str):
    try:
        import stock_data as sd
        return sd.fetcher.get_stock_data(symbol)
    except Exception:
        return None


def _build_user_digest(user: dict, period: str) -> dict:
    """Build the digest payload for a single user."""
    import stock_data as sd

    conn = get_db_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute(
                "SELECT symbol FROM watchlist WHERE user_id=%s ORDER BY added_at DESC LIMIT 12",
                (user["id"],),
            )
            wl = cur.fetchall()
            cur.execute(
                "SELECT symbol, quantity, buy_price FROM portfolio WHERE user_id=%s",
                (user["id"],),
            )
            pf = cur.fetchall()
    finally:
        conn.close()

    watchlist_rows = []
    for r in wl:
        live = _fetch_live_safe(r["symbol"]) or {}
        if not live.get("success"):
            continue
        meta = sd.SYMBOL_LOOKUP.get(r["symbol"]) or {}
        watchlist_rows.append({
            "symbol": r["symbol"],
            "name": meta.get("name", r["symbol"]),
            "price": float(live.get("price") or 0),
            "change_pct": float(live.get("change_percent") or 0),
        })

    total_cost = Decimal(0)
    total_value = Decimal(0)
    for r in pf:
        live = _fetch_live_safe(r["symbol"]) or {}
        price = Decimal(str(live.get("price") or 0))
        qty = Decimal(str(r["quantity"]))
        buy = Decimal(str(r["buy_price"]))
        total_cost += buy * qty
        total_value += price * qty

    totals = None
    if total_cost > 0:
        pnl = total_value - total_cost
        totals = {
            "value": float(total_value),
            "pnl": float(pnl),
            "pnl_pct": float((pnl / total_cost) * 100),
        }

    # AI top picks
    top_picks = []
    try:
        from ai_predictions import ai_predictor
        ai_picks = ai_predictor.get_top_picks(5) or []
        for p in ai_picks:
            top_picks.append({
                "symbol": p.get("symbol"),
                "sentiment": p.get("sentiment"),
                "confidence": float(p.get("confidence") or 0),
                "predicted_change": float(p.get("predicted_change") or 0),
            })
    except Exception:
        pass

    return {
        "name": user.get("name") or user["email"],
        "period": period,
        "watchlist_rows": watchlist_rows,
        "totals": totals,
        "top_picks": top_picks,
    }


def _send_for_users(period: str, where_clause: str):
    started = datetime.now(timezone.utc)
    print(f"\n📨 [{period} digest] starting at {started.isoformat()}")
    conn = get_db_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute(f"SELECT id, email, name, digest_frequency FROM users WHERE {where_clause}")
            users = cur.fetchall()
    finally:
        conn.close()

    sent = 0
    for u in users:
        try:
            payload = _build_user_digest(u, period)
            if not payload["watchlist_rows"] and not payload["totals"]:
                # Nothing to report
                continue
            ok = email_service.send_digest(u["email"], payload)
            if ok:
                sent += 1
        except Exception:
            traceback.print_exc()
    print(f"📨 [{period} digest] sent={sent} / candidates={len(users)}")
    return sent


def send_daily_digest():
    return _send_for_users("Daily", "digest_frequency='daily'")


def send_weekly_digest():
    return _send_for_users("Weekly", "digest_frequency='weekly'")
