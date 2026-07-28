import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from app.core.database import async_session_factory
from database.models import MarketData
from collectors.india_market.index_collector import IndiaIndexCollector
from collectors.india_market.fii_dii_collector import FIIDIICollector
from collectors.us_market.index_collector import USIndexCollector
from collectors.commodities.commodity_collector import CommodityCollector
from collectors.forex.forex_collector import ForexCollector
from collectors.news.news_collector import NewsCollector

logger = logging.getLogger(__name__)

# Single instance of AsyncIOScheduler
scheduler = AsyncIOScheduler()


async def run_market_collection_job() -> None:
    """
    Core orchestration job to run all daily market data, FII/DII flow, and news collectors.
    """
    logger.info("Daily market data collection job started...")
    
    async with async_session_factory() as db:
        # Collect India Index Data
        try:
            await IndiaIndexCollector().collect_daily(db)
        except Exception as e:
            logger.error(f"IndiaIndexCollector daily run failed: {e}", exc_info=True)

        # Collect FII/DII Flow Data
        try:
            await FIIDIICollector().collect_daily(db)
        except Exception as e:
            logger.error(f"FIIDIICollector daily run failed: {e}", exc_info=True)

        # Collect US Index Data
        try:
            await USIndexCollector().collect_daily(db)
        except Exception as e:
            logger.error(f"USIndexCollector daily run failed: {e}", exc_info=True)

        # Collect Commodity Prices
        try:
            await CommodityCollector().collect_daily(db)
        except Exception as e:
            logger.error(f"CommodityCollector daily run failed: {e}", exc_info=True)

        # Collect Forex Rates
        try:
            await ForexCollector().collect_daily(db)
        except Exception as e:
            logger.error(f"ForexCollector daily run failed: {e}", exc_info=True)

        # Collect News Articles
        try:
            await NewsCollector().collect_daily(db)
        except Exception as e:
            logger.error(f"NewsCollector daily run failed: {e}", exc_info=True)

        # Compute Technical Indicators
        try:
            from indicators.engine import IndicatorsEngine
            # Fetch distinct symbols in the market data table
            stmt_syms = select(MarketData.symbol).distinct()
            res_syms = await db.execute(stmt_syms)
            distinct_symbols = res_syms.scalars().all()
            
            indicators_engine = IndicatorsEngine()
            for sym in distinct_symbols:
                # Skip computing indicators for the fear indexes themselves
                if sym not in ["INDIAVIX", "USVIX"]:
                    try:
                        await indicators_engine.calculate_for_symbol(db, sym)
                    except Exception as e:
                        logger.error(f"Technical indicators calculation failed for {sym}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"IndicatorsEngine daily run failed: {e}", exc_info=True)

        # Run Decision Engine, LangGraph AI, and Telegram dispatch
        try:
            from decision_engine.execution import DecisionEngine
            from ai.graph.workflow import app as ai_app
            from telegram.client import send_telegram_message
            from datetime import date
            
            decision_engine = DecisionEngine()
            
            for sym in distinct_symbols:
                if sym not in ["INDIAVIX", "USVIX"]:
                    try:
                        # 1. Resolve remaining days
                        remaining_days = 5
                        today_day = date.today().day
                        if 21 <= today_day <= 30:
                            remaining_days = 30 - today_day + 1

                        # 2. Run Decision Engine
                        rec = await decision_engine.evaluate(db, symbol=sym, remaining_days=remaining_days)

                        # 3. Invoke LangGraph AI Layer
                        eval_date = date.fromisoformat(rec["date"])
                        state_inputs = {
                            "symbol": sym,
                            "date": eval_date,
                            "remaining_days": remaining_days,
                            "recommendation": rec
                        }
                        final_state = await ai_app.ainvoke(state_inputs)

                        # 4. Send Telegram message
                        telegram_msg = final_state.get("telegram_text")
                        if telegram_msg:
                            from app.config.config import settings
                            alert_symbols = [
                                s.strip().upper() 
                                for s in (settings.TELEGRAM_ALERT_SYMBOLS or "").split(",") 
                                if s.strip()
                            ]
                            
                            # Allow matches (e.g. "NIFTY" in "NIFTY50" or exact match "DOW")
                            should_send = False
                            for allowed in alert_symbols:
                                if allowed in sym.upper() or sym.upper() in allowed:
                                    should_send = True
                                    break
                                    
                            if should_send:
                                await send_telegram_message(telegram_msg)
                            else:
                                logger.info(f"Skipping Telegram alert for {sym} as it is not allowed in TELEGRAM_ALERT_SYMBOLS.")


                    except Exception as e:
                        logger.error(f"Decision/AI/Telegram pipeline failed for {sym}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Decision/AI/Telegram daily execution pipeline failed: {e}", exc_info=True)

    logger.info("Daily market data collection job completed.")


def start_scheduler() -> None:
    """
    Registers the daily job and starts the scheduler on the running event loop.
    """
    # Runs at 18:30 IST / 13:00 UTC daily
    trigger = CronTrigger(hour=12, minute=56, timezone="Asia/Dubai")
    
    scheduler.add_job(
        run_market_collection_job,
        trigger=trigger,
        id="daily_market_data_collection",
        name="Daily collection of indices, commodities, forex, and FII/DII flows",
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("APScheduler started and daily market data collection job registered.")


def shutdown_scheduler() -> None:
    """
    Shuts down the scheduler gracefully.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler shutdown completed.")
