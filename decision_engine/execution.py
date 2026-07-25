import logging
from datetime import datetime, time
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MarketData, TechnicalIndicator, News, Recommendation
from decision_engine.scoring import calculate_decision_score

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Main Orchestrator for evaluating buy rules and confidence scores.
    """
    def __init__(self) -> None:
        self.logger = logging.getLogger("decision_engine.execution")

    async def evaluate(self, db: AsyncSession, symbol: str, remaining_days: int) -> dict:
        """
        Evaluates decision rules and confidence based on the latest market indicators and news.
        Persists the result as a Recommendation.
        """
        self.logger.info(f"Evaluating decision for symbol: {symbol} (Remaining Window Days: {remaining_days})")

        # 1. Retrieve latest pricing data
        stmt_m = (
            select(MarketData)
            .where(MarketData.symbol == symbol)
            .order_by(MarketData.date.desc())
            .limit(1)
        )
        res_m = await db.execute(stmt_m)
        m_rec = res_m.scalar_one_or_none()

        if not m_rec:
            raise ValueError(f"No market pricing data found for symbol: {symbol}. Cannot evaluate decision.")

        eval_date = m_rec.date

        # 2. Retrieve latest technical indicators
        stmt_t = (
            select(TechnicalIndicator)
            .where(TechnicalIndicator.symbol == symbol)
            .where(TechnicalIndicator.date <= eval_date)
            .order_by(TechnicalIndicator.date.desc())
            .limit(1)
        )
        res_t = await db.execute(stmt_t)
        t_rec = res_t.scalar_one_or_none()

        # 3. Retrieve news headlines published on target evaluation date
        start_dt = datetime.combine(eval_date, time.min)
        end_dt = datetime.combine(eval_date, time.max)
        stmt_n = (
            select(News.headline)
            .where(News.published_date.between(start_dt, end_dt))
        )
        res_n = await db.execute(stmt_n)
        headlines = list(res_n.scalars().all())

        # 4. Extract indicator variables
        close = float(m_rec.close)
        sma_50 = float(t_rec.sma_50) if t_rec and t_rec.sma_50 is not None else None
        sma_200 = float(t_rec.sma_200) if t_rec and t_rec.sma_200 is not None else None
        rsi = float(t_rec.rsi) if t_rec and t_rec.rsi is not None else None
        macd_hist = float(t_rec.macd_hist) if t_rec and t_rec.macd_hist is not None else None
        trend_str = float(t_rec.trend_strength) if t_rec and t_rec.trend_strength is not None else None
        vix_val = float(t_rec.fear_index) if t_rec and t_rec.fear_index is not None else None
        liq_score = float(t_rec.liquidity_score) if t_rec and t_rec.liquidity_score is not None else None

        # 5. Evaluate scoring matrix
        decision, confidence, reasons, triggered_rules = calculate_decision_score(
            close=close,
            sma_50=sma_50,
            sma_200=sma_200,
            rsi=rsi,
            macd_hist=macd_hist,
            trend_strength=trend_str,
            headlines=headlines,
            vix_value=vix_val,
            liq_score=liq_score,
            remaining_days=remaining_days
        )

        # 6. Persist Recommendation to Postgres
        stmt_upsert = insert(Recommendation).values(
            symbol=symbol,
            date=eval_date,
            decision=decision,
            confidence=confidence,
            reasons=reasons,
            triggered_rules=triggered_rules,
            remaining_window_days=remaining_days
        )

        stmt_upsert = stmt_upsert.on_conflict_do_update(
            constraint="uq_rec_symbol_date",
            set_={
                "decision": stmt_upsert.excluded.decision,
                "confidence": stmt_upsert.excluded.confidence,
                "reasons": stmt_upsert.excluded.reasons,
                "triggered_rules": stmt_upsert.excluded.triggered_rules,
                "remaining_window_days": stmt_upsert.excluded.remaining_window_days,
            }
        )
        await db.execute(stmt_upsert)
        await db.commit()

        self.logger.info(f"Decision engine outcome for {symbol}: {decision} ({confidence}% Confidence)")

        return {
            "symbol": symbol,
            "date": eval_date.isoformat(),
            "decision": decision,
            "confidence": confidence,
            "reasons": reasons,
            "triggered_rules": triggered_rules,
            "remaining_window_days": remaining_days
        }
