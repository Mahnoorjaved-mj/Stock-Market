from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, g, jsonify, request

from routes.auth import login_required
from db import get_db_connection, get_dict_cursor

portfolio_bp = Blueprint("portfolio", __name__)


def _pos_decimal(v, name: str) -> Decimal:
    try:
        d = Decimal(str(v))
        if d <= 0:
            raise ValueError
        return d
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{name} must be a positive number")


def _parse_date(v) -> date:
    try:
        return datetime.strptime(v, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("buy_date must be YYYY-MM-DD")


def _enrich(rows):
    import stock_data as sd

    out, total_cost, total_value = [], Decimal(0), Decimal(0)
    for r in rows:
        d = dict(r)
        d["quantity"] = float(d["quantity"])
        d["buy_price"] = float(d["buy_price"])
        d["buy_date"] = d["buy_date"].isoformat() if d["buy_date"] else None
        meta = sd.SYMBOL_LOOKUP.get(d["symbol"]) if hasattr(sd, "SYMBOL_LOOKUP") else None
        d["name"] = meta["name"] if meta else d["symbol"]
        d["currency"] = meta["currency"] if meta else "USD"
        try:
            live = sd.fetcher.get_stock_data(d["symbol"])
            current = float(live.get("price") or 0)
        except Exception:
            current = 0.0
        d["current_price"] = current
        cost = Decimal(str(d["buy_price"])) * Decimal(str(d["quantity"]))
        value = Decimal(str(current)) * Decimal(str(d["quantity"]))
        d["cost_basis"] = float(cost)
        d["current_value"] = float(value)
        d["pnl"] = float(value - cost)
        d["pnl_pct"] = float(((value - cost) / cost) * 100) if cost > 0 else 0.0
        total_cost += cost
        total_value += value
        out.append(d)
    totals = {
        "cost_basis": float(total_cost),
        "current_value": float(total_value),
        "pnl": float(total_value - total_cost),
        "pnl_pct": float(((total_value - total_cost) / total_cost) * 100) if total_cost > 0 else 0.0,
    }
    return out, totals


@portfolio_bp.route("/api/portfolio", methods=["GET"])
@login_required
def list_holdings():
    conn = get_db_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute(
                """SELECT id, symbol, quantity, buy_price, buy_date, notes, created_at
                   FROM portfolio WHERE user_id=%s ORDER BY buy_date DESC, id DESC""",
                (g.user_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    items, totals = _enrich(rows)
    return jsonify({"status": "success", "items": items, "totals": totals})


@portfolio_bp.route("/api/portfolio", methods=["POST"])
@login_required
def add_holding():
    data = request.get_json(silent=True) or {}
    try:
        from routes.watchlist import _validate_symbol
        symbol = _validate_symbol(data.get("symbol"))
        qty = _pos_decimal(data.get("quantity"), "quantity")
        buy_price = _pos_decimal(data.get("buy_price"), "buy_price")
        buy_date = _parse_date(data.get("buy_date"))
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    notes = (data.get("notes") or "").strip() or None

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO portfolio (user_id, symbol, quantity, buy_price, buy_date, notes)
                   VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
                (g.user_id, symbol, qty, buy_price, buy_date, notes),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    return jsonify({"status": "success", "id": new_id})


@portfolio_bp.route("/api/portfolio/<int:entry_id>", methods=["PUT"])
@login_required
def update_holding(entry_id):
    data = request.get_json(silent=True) or {}
    fields, values = [], []
    try:
        if "quantity" in data:
            fields.append("quantity=%s"); values.append(_pos_decimal(data["quantity"], "quantity"))
        if "buy_price" in data:
            fields.append("buy_price=%s"); values.append(_pos_decimal(data["buy_price"], "buy_price"))
        if "buy_date" in data:
            fields.append("buy_date=%s"); values.append(_parse_date(data["buy_date"]))
        if "notes" in data:
            fields.append("notes=%s"); values.append((data["notes"] or "").strip() or None)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    if not fields:
        return jsonify({"status": "error", "message": "Nothing to update"}), 400

    values.extend([entry_id, g.user_id])
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE portfolio SET {', '.join(fields)} WHERE id=%s AND user_id=%s",
                values,
            )
            if cur.rowcount == 0:
                return jsonify({"status": "error", "message": "Not found"}), 404
        conn.commit()
    finally:
        conn.close()
    return jsonify({"status": "success"})


@portfolio_bp.route("/api/portfolio/<int:entry_id>", methods=["DELETE"])
@login_required
def delete_holding(entry_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM portfolio WHERE id=%s AND user_id=%s", (entry_id, g.user_id))
            if cur.rowcount == 0:
                return jsonify({"status": "error", "message": "Not found"}), 404
        conn.commit()
    finally:
        conn.close()
    return jsonify({"status": "success"})
