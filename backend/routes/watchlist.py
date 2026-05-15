import re
from decimal import Decimal, InvalidOperation

from flask import Blueprint, g, jsonify, request

from routes.auth import login_required
from db import get_db_connection, get_dict_cursor

watchlist_bp = Blueprint("watchlist", __name__)

SYMBOL_RE = re.compile(r"^[A-Z0-9.\-]{1,15}$")


def _opt_decimal(val, name: str):
    if val in (None, "", "null"):
        return None
    try:
        d = Decimal(str(val))
        if d <= 0:
            raise ValueError
        return d
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{name} must be a positive number")


def _validate_symbol(sym: str) -> str:
    sym = (sym or "").strip().upper()
    if not SYMBOL_RE.match(sym):
        raise ValueError("Invalid symbol")
    return sym


@watchlist_bp.route("/api/watchlist", methods=["GET"])
@login_required
def list_watchlist():
    conn = get_db_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute(
                """SELECT id, symbol, threshold_pct, target_price_high, target_price_low, added_at
                   FROM watchlist WHERE user_id=%s ORDER BY added_at DESC""",
                (g.user_id,),
            )
            rows = cur.fetchall()
        # Enrich with live data + company metadata
        import stock_data as sd

        # Build a lookup of {symbol -> definition} from stock_data when available
        items = []
        for r in rows:
            d = dict(r)
            for k in ("threshold_pct", "target_price_high", "target_price_low"):
                d[k] = float(d[k]) if d[k] is not None else None
            try:
                live = sd.fetcher.get_stock_data(d["symbol"])
                d["price"] = float(live.get("price") or 0)
                d["change_percent"] = float(live.get("change_percent") or 0)
            except Exception:
                d["price"] = None
                d["change_percent"] = None
            meta = sd.SYMBOL_LOOKUP.get(d["symbol"]) if hasattr(sd, "SYMBOL_LOOKUP") else None
            d["name"] = meta["name"] if meta else d["symbol"]
            d["sector"] = meta["sector"] if meta else None
            d["currency"] = meta["currency"] if meta else "USD"
            items.append(d)
        return jsonify({"status": "success", "items": items})
    finally:
        conn.close()


@watchlist_bp.route("/api/watchlist", methods=["POST"])
@login_required
def add_watchlist():
    data = request.get_json(silent=True) or {}
    try:
        symbol = _validate_symbol(data.get("symbol"))
        threshold = _opt_decimal(data.get("threshold_pct"), "threshold_pct")
        t_high = _opt_decimal(data.get("target_price_high"), "target_price_high")
        t_low = _opt_decimal(data.get("target_price_low"), "target_price_low")
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO watchlist (user_id, symbol, threshold_pct, target_price_high, target_price_low)
                   VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (user_id, symbol) DO UPDATE
                   SET threshold_pct=EXCLUDED.threshold_pct,
                       target_price_high=EXCLUDED.target_price_high,
                       target_price_low=EXCLUDED.target_price_low
                   RETURNING id""",
                (g.user_id, symbol, threshold, t_high, t_low),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    return jsonify({"status": "success", "id": new_id})


@watchlist_bp.route("/api/watchlist/<int:entry_id>", methods=["PUT"])
@login_required
def update_watchlist(entry_id):
    data = request.get_json(silent=True) or {}
    fields, values = [], []
    try:
        if "threshold_pct" in data:
            fields.append("threshold_pct=%s"); values.append(_opt_decimal(data["threshold_pct"], "threshold_pct"))
        if "target_price_high" in data:
            fields.append("target_price_high=%s"); values.append(_opt_decimal(data["target_price_high"], "target_price_high"))
        if "target_price_low" in data:
            fields.append("target_price_low=%s"); values.append(_opt_decimal(data["target_price_low"], "target_price_low"))
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    if not fields:
        return jsonify({"status": "error", "message": "Nothing to update"}), 400

    values.extend([entry_id, g.user_id])
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE watchlist SET {', '.join(fields)} WHERE id=%s AND user_id=%s",
                values,
            )
            if cur.rowcount == 0:
                return jsonify({"status": "error", "message": "Not found"}), 404
        conn.commit()
    finally:
        conn.close()
    return jsonify({"status": "success"})


@watchlist_bp.route("/api/watchlist/<int:entry_id>", methods=["DELETE"])
@login_required
def delete_watchlist(entry_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM watchlist WHERE id=%s AND user_id=%s", (entry_id, g.user_id))
            if cur.rowcount == 0:
                return jsonify({"status": "error", "message": "Not found"}), 404
        conn.commit()
    finally:
        conn.close()
    return jsonify({"status": "success"})


@watchlist_bp.route("/api/symbols")
def list_symbols():
    """Public endpoint: returns known symbols for autocomplete."""
    import stock_data as sd
    out = []
    if hasattr(sd, "SYMBOL_LOOKUP"):
        for sym, meta in sd.SYMBOL_LOOKUP.items():
            out.append({"symbol": sym, "name": meta["name"], "sector": meta["sector"], "country": meta["country"]})
    return jsonify({"status": "success", "symbols": out})
