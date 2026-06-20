"""Public market-data routes, incl. an SSE price stream."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from controllers import market_controller as ctrl

router = APIRouter(tags=["market"])


@router.get("/get_live_data")
async def get_live_data():
    return await ctrl.get_live_data()


@router.get("/api/market-analysis")
async def market_analysis():
    return await ctrl.market_analysis()


@router.get("/api/stock/{symbol}")
async def stock_detail(symbol: str):
    return await ctrl.stock_detail(symbol)


@router.get("/api/stock/{symbol}/history")
async def stock_history(symbol: str, range: str = Query("1mo")):
    return await ctrl.stock_history(symbol, range)


@router.get("/api/search")
async def search(q: str = Query("")):
    return ctrl.search_symbols(q)


@router.get("/stream/prices")
async def stream_prices():
    """Server-Sent Events: push a fresh dashboard snapshot every ~20s."""

    async def gen():
        while True:
            try:
                data = await ctrl.get_live_data()
                yield {"event": "snapshot", "data": json.dumps(data)}
            except Exception:
                yield {"event": "error", "data": json.dumps({"message": "snapshot failed"})}
            await asyncio.sleep(20)

    return EventSourceResponse(gen())
