"""AI prediction routes (public) + personalized picks (auth)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from controllers import ai_controller as ctrl
from utils.deps import get_current_user

router = APIRouter(tags=["ai"])


@router.get("/api/predict/{symbol}")
async def predict(symbol: str, days: int = Query(7)):
    return await ctrl.predict(symbol, days)


@router.get("/api/sentiment/{symbol}")
async def sentiment(symbol: str):
    return await ctrl.sentiment(symbol)


@router.get("/api/top_picks")
async def top_picks():
    return await ctrl.top_picks()


@router.post("/api/train_model/{symbol}")
async def train_model(symbol: str):
    return await ctrl.train_model(symbol)


@router.get("/api/ai/backtest/{symbol}")
async def backtest(symbol: str):
    return await ctrl.backtest(symbol)


@router.get("/api/bulk_predict")
async def bulk_predict(symbols: str = Query("AAPL,MSFT,GOOGL,AMZN,TSLA")):
    return await ctrl.bulk_predict(symbols)


@router.get("/api/model_info")
async def model_info():
    return ctrl.model_info()


@router.get("/api/ai/personalized-picks")
async def personalized_picks(user: dict = Depends(get_current_user)):
    return await ctrl.personalized_picks(str(user["_id"]))
