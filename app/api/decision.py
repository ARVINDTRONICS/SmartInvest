import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from database.models import Recommendation
from decision_engine.execution import DecisionEngine

logger = logging.getLogger(__name__)
router = APIRouter()


class DecisionResponse(BaseModel):
    symbol: str
    date: date
    decision: str
    confidence: int
    reasons: list[str]
    triggered_rules: list[str]
    remaining_window_days: int


@router.get("/decision", response_model=DecisionResponse)
async def get_decision(
    symbol: str = Query(..., description="Target investment symbol (e.g. NIFTY50)"),
    remaining_days: int = Query(..., ge=1, description="Remaining days inside the current SIP window"),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Evaluates buy signals and confidence scores on-the-fly, saves the result as a recommendation,
    and returns decision engine outputs.
    """
    try:
        engine = DecisionEngine()
        result = await engine.evaluate(db, symbol=symbol, remaining_days=remaining_days)
        return result
    except ValueError as ve:
        logger.warning(f"Invalid request parameters for decision evaluation: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to evaluate decision for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error executing decision logic.")


@router.get("/recommendation/latest", response_model=DecisionResponse)
async def get_latest_recommendation(
    symbol: str = Query(..., description="Symbol to fetch recommendation for"),
    db: AsyncSession = Depends(get_db)
) -> Recommendation:
    """
    Retrieves the latest processed recommendation from the database for the given symbol.
    """
    try:
        stmt = (
            select(Recommendation)
            .where(Recommendation.symbol == symbol)
            .order_by(Recommendation.date.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        rec = res.scalar_one_or_none()
        if not rec:
            raise HTTPException(
                status_code=404, 
                detail=f"No recommendations found for symbol: {symbol}"
            )
        return rec
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch latest recommendation for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error fetching recommendation.")
