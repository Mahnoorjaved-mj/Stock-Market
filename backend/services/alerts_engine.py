"""Alert engine: evaluate every user's watchlist and send email alerts."""
from __future__ import annotations

import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional

from services import email_service
from db import get_db_connection, get_dict_cursor

# Dedup window: don't fire the same (user, symbol, alert_type) within this many hours
DEDUP_HOURS = 4


def _fetch_live(symbol: str) -> Optional[dict]:
    try:
        import stock_data as sd
        d = sd.fetcher.get_stock_data(symbol)
        if not d or not d.get("success") or not d.get("price"):
            return None
        return d
    except Exception:
        traceback.print_exc()
        return None


def _meta(symbol: str) -> dict:
    try:
        import stock_data as sd
        return sd.SYMBOL_LOOKUP.get(symbol.upper()) or {}
    except Exception:
        return {}


def _was_recently_sent(cur, user_id: int, symbol: str, alert_type: str) -> bool:
    # DEDUP_HOURS is a trusted integer constant, safe to format directly
    cur.execute(
        f"""SELECT 1 FROM alert_history
            WHERE user_id=%s AND symbol=%s AND alert_type=%s
              AND sent_at > NOW() - INTERVAL '{int(DEDUP_HOURS)} hours'
            LIMIT 1""",
        (user_id, symbol, alert_type),
    )
    return cur.fetchone() is not None


def _record_sent(cur, user_id: int, symbol: str, alert_type: str, price: float, change_pct: Optional[float]):
    cur.execute(
        """INSERT INTO alert_history (user_id, symbol, alert_type, price, change_pct)
           VALUES (%s, %s, %s, %s, %s)""",
        (user_id, symbol, alert_type, price, change_pct),
    )


def evaluate_user_alerts() -> dict:
    """Run one sweep across all watchlist entries. Returns summary stats."""
    started = datetime.now(timezone.utc)
    print(f"\n🔔 [alert_sweep] starting at {started.isoformat()}")

    conn = get_db_connection()
    sent = 0
    skipped = 0
    errors = 0
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute(
                """SELECT w.id, w.user_id, w.symbol, w.threshold_pct,
                          w.target_price_high, w.target_price_low,
                          u.email, u.name, u.alert_threshold_pct
                   FROM watchlist w
                   JOIN users u ON u.id = w.user_id"""
            )
            rows = cur.fetchall()

        print(f"   {len(rows)} watchlist entries to evaluate")

        for r in rows:
            try:
                live = _fetch_live(r["symbol"])
                if not live:
                    continue
                price = float(live["price"])
                change_pct = float(live.get("change_percent") or 0)
                eff_threshold = r["threshold_pct"] if r["threshold_pct"] is not None else r["alert_threshold_pct"]
                eff_threshold = float(eff_threshold) if eff_threshold is not None else 5.0

                meta = _meta(r["symbol"])
                name = meta.get("name", r["symbol"])
                currency = meta.get("currency", "USD")

                triggers = []
                if abs(change_pct) >= eff_threshold:
                    direction = "up" if change_pct >= 0 else "down"
                    triggers.append((
                        "pct_move",
                        f"Moved {change_pct:+.2f}% (threshold ±{eff_threshold:g}%)",
                        eff_threshold,
                    ))
                if r["target_price_high"] is not None and price >= float(r["target_price_high"]):
                    triggers.append((
                        "target_high",
                        f"Crossed above target {currency} {float(r['target_price_high']):.2f}",
                        float(r["target_price_high"]),
                    ))
                if r["target_price_low"] is not None and price <= float(r["target_price_low"]):
                    triggers.append((
                        "target_low",
                        f"Dropped below target {currency} {float(r['target_price_low']):.2f}",
                        float(r["target_price_low"]),
                    ))

                if not triggers:
                    continue

                # Per-trigger dedup, fire and record
                with conn.cursor() as wcur:
                    for alert_type, headline, threshold in triggers:
                        with conn.cursor() as ccur:
                            if _was_recently_sent(ccur, r["user_id"], r["symbol"], alert_type):
                                skipped += 1
                                continue
                        ok = email_service.send_alert(r["email"], {
                            "symbol": r["symbol"],
                            "name": name,
                            "price": price,
                            "change_pct": change_pct,
                            "alert_type": alert_type,
                            "threshold": threshold,
                            "currency": currency,
                            "headline": headline,
                        })
                        if ok:
                            _record_sent(wcur, r["user_id"], r["symbol"], alert_type, price, change_pct)
                            sent += 1
                conn.commit()
            except Exception as e:
                errors += 1
                print(f"   ❌ alert error for user={r['user_id']} sym={r['symbol']}: {e}")
                conn.rollback()
    finally:
        conn.close()

    duration = (datetime.now(timezone.utc) - started).total_seconds()
    summary = {"sent": sent, "skipped": skipped, "errors": errors, "duration_s": round(duration, 2)}
    print(f"🔔 [alert_sweep] done: {summary}")
    return summary
