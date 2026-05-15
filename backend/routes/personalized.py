"""Personalized AI picks: rank-boost top_picks by sectors in user's watchlist."""
from __future__ import annotations

from collections import Counter

from flask import Blueprint, g, jsonify

from routes.auth import login_required
from db import get_db_connection, get_dict_cursor

personalized_bp = Blueprint("personalized", __name__)

SECTOR_BOOST = 12.0  # confidence/score boost for sector match


@personalized_bp.route("/api/ai/personalized-picks")
@login_required
def personalized_picks():
    import stock_data as sd
    try:
        from ai_predictions import ai_predictor
    except Exception:
        return jsonify({"status": "error", "message": "AI predictor unavailable"}), 500

    # 1) User's watchlist sectors
    conn = get_db_connection()
    try:
        with get_dict_cursor(conn) as cur:
            cur.execute("SELECT symbol FROM watchlist WHERE user_id=%s", (g.user_id,))
            symbols = [r["symbol"] for r in cur.fetchall()]
    finally:
        conn.close()

    sector_weights = Counter()
    for s in symbols:
        meta = sd.SYMBOL_LOOKUP.get(s) if hasattr(sd, "SYMBOL_LOOKUP") else None
        if meta and meta.get("sector"):
            sector_weights[meta["sector"]] += 1

    # 2) Fetch a broad pool of top picks (ask for more so we can re-rank)
    try:
        raw_picks = ai_predictor.get_top_picks(15) or []
    except Exception:
        raw_picks = []

    if not raw_picks:
        return jsonify({"status": "success", "top_picks": [], "boosted_sectors": dict(sector_weights)})

    # 3) Re-rank: boost confidence when sector matches a watchlist sector
    for p in raw_picks:
        sym = (p.get("symbol") or "").upper()
        meta = sd.SYMBOL_LOOKUP.get(sym) if hasattr(sd, "SYMBOL_LOOKUP") else None
        sector = meta.get("sector") if meta else None
        boost = SECTOR_BOOST * sector_weights.get(sector, 0) if sector else 0
        p["_score"] = float(p.get("confidence") or 0) + boost
        p["personalized_boost"] = boost
        p["sector"] = sector

    raw_picks.sort(key=lambda p: p["_score"], reverse=True)
    out = raw_picks[:5]

    return jsonify({
        "status": "success",
        "top_picks": out,
        "boosted_sectors": dict(sector_weights),
        "source": "Personalized AI (sector-weighted)",
    })
