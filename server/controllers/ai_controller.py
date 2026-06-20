"""AI prediction endpoints (public) + personalized picks (auth).

Wraps the ported LSTM predictor. Blocking torch/yfinance work runs in a
thread. Fallback payloads mirror legacy app.py behavior when the model is
unavailable.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timedelta

from services import stock_data as sd
from services.ai_predictions import ai_predictor

SECTOR_BOOST = 12.0


async def predict(symbol: str, days: int = 7) -> dict:
    result = await asyncio.to_thread(ai_predictor.predict_future, symbol.upper(), days)
    if result and result.get("success"):
        return result
    now = datetime.now()
    return {
        "success": True,
        "symbol": symbol.upper(),
        "current_price": 100.00,
        "predictions": {
            "dates": [(now + timedelta(days=i + 1)).strftime("%Y-%m-%d") for i in range(days)],
            "prices": [100.00 + i * 0.5 for i in range(days)],
            "prediction_change": 3.5,
        },
        "confidence": 75.5,
        "model_type": "Statistical Analysis",
        "note": "Fallback predictions",
        "generated_at": now.isoformat(),
    }


async def sentiment(symbol: str) -> dict:
    result = await asyncio.to_thread(ai_predictor.get_sentiment_analysis, symbol.upper())
    if result and result.get("success"):
        return result
    return {
        "success": True,
        "symbol": symbol.upper(),
        "sentiment": {
            "sentiment": "HOLD",
            "confidence": 65.0,
            "color": "#f59e0b",
            "emoji": "⚖️",
            "predicted_change": 0.5,
            "current_price": 100.00,
            "model": "Statistical Analysis",
        },
        "generated_at": datetime.now().isoformat(),
    }


async def top_picks() -> dict:
    picks = await asyncio.to_thread(ai_predictor.get_top_picks, 5)
    if picks:
        return {
            "success": True,
            "top_picks": picks,
            "count": len(picks),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "LSTM AI Model",
        }
    fallback = [
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "sentiment": "STRONG_BUY", "confidence": 85.6,
         "color": "#16a34a", "emoji": "🚀", "current_price": 650.45, "predicted_change": 4.5},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "sentiment": "STRONG_BUY", "confidence": 82.7,
         "color": "#16a34a", "emoji": "🚀", "current_price": 438.92, "predicted_change": 3.2},
        {"symbol": "AAPL", "name": "Apple Inc.", "sentiment": "BUY", "confidence": 74.3,
         "color": "#22c55e", "emoji": "📈", "current_price": 192.34, "predicted_change": 1.8},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "sentiment": "BUY", "confidence": 71.2,
         "color": "#22c55e", "emoji": "📈", "current_price": 176.95, "predicted_change": 2.3},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "sentiment": "HOLD", "confidence": 68.5,
         "color": "#f59e0b", "emoji": "⚖️", "current_price": 152.89, "predicted_change": 0.8},
    ]
    return {
        "success": True,
        "top_picks": fallback,
        "count": len(fallback),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "Fallback Analysis",
    }


async def train_model(symbol: str) -> dict:
    result = await asyncio.to_thread(ai_predictor.train_model, symbol.upper(), 25)
    if result and result.get("success"):
        return {
            "success": True,
            "message": f"LSTM model trained successfully for {symbol}",
            "symbol": symbol.upper(),
            "timestamp": datetime.now().isoformat(),
        }
    return {"success": False, "error": f"Failed to train model for {symbol}"}


async def backtest(symbol: str) -> dict:
    def _run():
        import yfinance as yf

        hist = yf.Ticker(symbol.upper()).history(period="6mo")
        if hist.empty:
            return None
        closes = hist["Close"].tolist()
        wins = losses = trades = 0
        last_pos = 0
        entry = None
        for i in range(20, len(closes)):
            ma5 = sum(closes[i - 5:i]) / 5
            ma20 = sum(closes[i - 20:i]) / 20
            pos = 1 if ma5 > ma20 else 0
            if pos != last_pos:
                if last_pos == 1 and entry is not None:
                    pnl = closes[i] - entry
                    wins += 1 if pnl > 0 else 0
                    losses += 1 if pnl <= 0 else 0
                    trades += 1
                if pos == 1:
                    entry = closes[i]
                last_pos = pos
        win_rate = (wins / trades * 100) if trades else 0
        return {
            "success": True,
            "symbol": symbol.upper(),
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "win_rate_pct": round(win_rate, 2),
            "period": "6mo (MA5/MA20 baseline)",
        }

    data = await asyncio.to_thread(_run)
    return data or {"success": False, "error": "No history"}


async def bulk_predict(symbols: str) -> dict:
    symbols_list = [s.strip().upper() for s in symbols.split(",")][:5]

    def _run():
        out = []
        for symbol in symbols_list:
            try:
                pred = ai_predictor.predict_future(symbol, days=3)
                if pred and pred.get("success"):
                    out.append(
                        {
                            "symbol": symbol,
                            "current_price": pred["current_price"],
                            "predicted_change": pred["predictions"]["prediction_change"],
                            "confidence": pred["confidence"],
                        }
                    )
            except Exception:
                continue
        return out

    predictions = await asyncio.to_thread(_run)
    return {"success": True, "predictions": predictions, "count": len(predictions)}


def model_info() -> dict:
    return {
        "success": True,
        "ai_system": "LSTM Neural Network Predictor",
        "device": str(getattr(ai_predictor, "device", "cpu")),
        "loaded_models": list(getattr(ai_predictor, "models", {}).keys()),
        "model_count": len(getattr(ai_predictor, "models", {})),
        "status": "active",
        "timestamp": datetime.now().isoformat(),
    }


async def personalized_picks(user_id: str) -> dict:
    from config.database import watchlist

    symbols = [r["symbol"] for r in await watchlist().find({"user_id": user_id}).to_list(length=500)]
    sector_weights = Counter()
    for s in symbols:
        meta = sd.SYMBOL_LOOKUP.get(s.upper())
        if meta and meta.get("sector"):
            sector_weights[meta["sector"]] += 1

    raw = await asyncio.to_thread(ai_predictor.get_top_picks, 15) or []
    if not raw:
        return {"status": "success", "top_picks": [], "boosted_sectors": dict(sector_weights)}

    for p in raw:
        meta = sd.SYMBOL_LOOKUP.get((p.get("symbol") or "").upper())
        sector = meta.get("sector") if meta else None
        boost = SECTOR_BOOST * sector_weights.get(sector, 0) if sector else 0
        p["_score"] = float(p.get("confidence") or 0) + boost
        p["personalized_boost"] = boost
        p["sector"] = sector
    raw.sort(key=lambda p: p["_score"], reverse=True)
    return {
        "status": "success",
        "top_picks": raw[:5],
        "boosted_sectors": dict(sector_weights),
        "source": "Personalized AI (sector-weighted)",
    }
