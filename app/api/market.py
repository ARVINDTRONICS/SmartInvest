import json
import logging
from datetime import date
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.core.database import get_db
from app.core.redis import get_redis
from database.models import FIIDIIFlow, MarketData

logger = logging.getLogger(__name__)
router = APIRouter()

CACHE_KEY = "market:today"
CACHE_TTL = 14400  # 4 hours in seconds


class MarketDataResponse(BaseModel):
    symbol: str
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: int | None


class FIIDIIFlowResponse(BaseModel):
    date: date
    fii_buy: float | None
    fii_sell: float | None
    fii_net: float
    dii_buy: float | None
    dii_sell: float | None
    dii_net: float


class MarketTodayResponse(BaseModel):
    date: date
    market_data: list[MarketDataResponse]
    fii_dii: FIIDIIFlowResponse | None


@router.get("/market/today", response_model=MarketTodayResponse)
async def get_market_today(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict:
    """
    Retrieves the latest available daily prices for all symbols and FII/DII flows.
    Checks Redis cache first. On cache miss, queries Postgres and caches response.
    """
    # 1. Check Redis Cache
    try:
        cached_val = await redis_client.get(CACHE_KEY)
        if cached_val:
            logger.info("Serving /market/today from Redis cache.")
            return json.loads(cached_val)
    except Exception as e:
        logger.warning(f"Redis cache lookup failed: {e}")

    # 2. Cache Miss - Query Postgres Database
    logger.info("Cache miss. Querying database for latest market data.")
    
    # Subquery: get the maximum date for each distinct symbol
    subq = (
        select(MarketData.symbol, func.max(MarketData.date).label("max_date"))
        .group_by(MarketData.symbol)
        .subquery()
    )

    # Main query: join MarketData with the subquery on symbol and max_date
    stmt = select(MarketData).join(
        subq,
        (MarketData.symbol == subq.c.symbol) & (MarketData.date == subq.c.max_date)
    )
    result = await db.execute(stmt)
    db_market_data = result.scalars().all()

    # Get the single latest FII/DII flow record
    stmt_fii = select(FIIDIIFlow).order_by(FIIDIIFlow.date.desc()).limit(1)
    result_fii = await db.execute(stmt_fii)
    db_fii_dii = result_fii.scalar_one_or_none()

    # 3. Format Response Data
    response_data = {
        "date": date.today().isoformat(),
        "market_data": [
            {
                "symbol": md.symbol,
                "date": md.date.isoformat(),
                "open": float(md.open) if md.open is not None else None,
                "high": float(md.high) if md.high is not None else None,
                "low": float(md.low) if md.low is not None else None,
                "close": float(md.close),
                "volume": md.volume,
            }
            for md in db_market_data
        ],
        "fii_dii": {
            "date": db_fii_dii.date.isoformat(),
            "fii_buy": float(db_fii_dii.fii_buy) if db_fii_dii.fii_buy is not None else None,
            "fii_sell": float(db_fii_dii.fii_sell) if db_fii_dii.fii_sell is not None else None,
            "fii_net": float(db_fii_dii.fii_net),
            "dii_buy": float(db_fii_dii.dii_buy) if db_fii_dii.dii_buy is not None else None,
            "dii_sell": float(db_fii_dii.dii_sell) if db_fii_dii.dii_sell is not None else None,
            "dii_net": float(db_fii_dii.dii_net),
        } if db_fii_dii else None
    }

    # 4. Write back to Redis cache
    try:
        await redis_client.setex(CACHE_KEY, CACHE_TTL, json.dumps(response_data))
        logger.info("Successfully updated /market/today Redis cache.")
    except Exception as e:
        logger.warning(f"Updating Redis cache failed: {e}")

    return response_data
