import logging
from datetime import date, timedelta
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MarketData, TechnicalIndicator
from indicators.trend.ma import calculate_sma, calculate_ema, calculate_trend_strength
from indicators.volatility.indicators import calculate_drawdown, calculate_volatility
from indicators.momentum.indicators import calculate_rsi, calculate_macd, calculate_momentum
from indicators.valuation.indicators import calculate_liquidity_score

logger = logging.getLogger(__name__)

SECTOR_SYMBOLS = [
    "NIFTY_IT", "NIFTY_PHARMA", "NIFTY_FMCG", "NIFTY_METAL",
    "NIFTY_AUTO", "NIFTY_REALTY", "NIFTY_FIN"
]


class IndicatorsEngine:
    """
    Orchestrator to retrieve market data, compute all technical indicators, 
    and store them back to the database.
    """
    def __init__(self) -> None:
        self.logger = logging.getLogger("indicators.engine")

    def _get_vix_symbol(self, symbol: str) -> str:
        """
        Maps the target asset symbol to its corresponding Fear Index.
        """
        if symbol in ["NASDAQ", "DOW", "SP500"]:
            return "USVIX"
        return "INDIAVIX"

    async def _calculate_market_breadth(self, db: AsyncSession, dates: list[date]) -> pd.Series:
        """
        Computes Market Breadth as the fraction of Indian sector indices trading above their 50-day SMA.
        """
        if not dates:
            return pd.Series(dtype=float)

        # Build clean target calendar index
        target_index = pd.to_datetime(dates)
        breadth_df = pd.DataFrame(index=target_index)

        for sec_sym in SECTOR_SYMBOLS:
            stmt = (
                select(MarketData.date, MarketData.close)
                .where(MarketData.symbol == sec_sym)
                .order_by(MarketData.date.asc())
            )
            res = await db.execute(stmt)
            rows = res.all()
            if not rows:
                continue

            sec_data = pd.DataFrame(rows, columns=["date", "close"])
            sec_data["date"] = pd.to_datetime(sec_data["date"])
            sec_data.set_index("date", inplace=True)

            # Compute SMA 50
            sma_50 = calculate_sma(sec_data["close"], 50)
            above_sma = (sec_data["close"] > sma_50).astype(float)

            # Reindex to align with target dates
            breadth_df[sec_sym] = above_sma.reindex(target_index).ffill()

        if breadth_df.empty:
            return pd.Series(0.0, index=target_index)

        # Average across columns for daily breadth score
        return breadth_df.mean(axis=1)

    async def _fetch_fear_index(self, db: AsyncSession, vix_symbol: str, dates: list[date]) -> pd.Series:
        """
        Retrieves historical VIX values for the target dates.
        """
        if not dates:
            return pd.Series(dtype=float)

        target_index = pd.to_datetime(dates)
        stmt = (
            select(MarketData.date, MarketData.close)
            .where(MarketData.symbol == vix_symbol)
            .order_by(MarketData.date.asc())
        )
        res = await db.execute(stmt)
        rows = res.all()
        
        if not rows:
            return pd.Series(None, index=target_index, dtype=float)

        vix_data = pd.DataFrame(rows, columns=["date", "close"])
        vix_data["date"] = pd.to_datetime(vix_data["date"])
        vix_data.set_index("date", inplace=True)

        return vix_data["close"].reindex(target_index).ffill()

    async def calculate_for_symbol(self, db: AsyncSession, symbol: str, lookback_days: int = 365) -> None:
        """
        Calculates all indicators for a symbol and stores/updates them in the database.
        """
        self.logger.info(f"Calculating technical indicators for: {symbol}")

        # 1. Fetch MarketData historical records
        start_date = date.today() - timedelta(days=lookback_days)
        stmt = (
            select(MarketData)
            .where(MarketData.symbol == symbol)
            .where(MarketData.date >= start_date)
            .order_by(MarketData.date.asc())
        )
        res = await db.execute(stmt)
        records = res.scalars().all()

        if len(records) < 15:
            self.logger.warning(f"Insufficient market data for {symbol} to calculate features.")
            return

        # 2. Convert to pandas DataFrame
        df = pd.DataFrame([
            {
                "date": r.date,
                "open": float(r.open) if r.open is not None else None,
                "high": float(r.high) if r.high is not None else None,
                "low": float(r.low) if r.low is not None else None,
                "close": float(r.close),
                "volume": r.volume
            }
            for r in records
        ])
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)

        # 3. Calculate Core Indicators
        close_series = df["close"]
        vol_series = df["volume"]

        # Trend
        sma_50 = calculate_sma(close_series, 50)
        sma_200 = calculate_sma(close_series, 200)
        ema_20 = calculate_ema(close_series, 20)
        trend_str = calculate_trend_strength(ema_20, sma_50)

        # Volatility & Drawdown
        dd = calculate_drawdown(close_series, window=252)
        vol = calculate_volatility(close_series, period=20)

        # Momentum
        rsi = calculate_rsi(close_series, period=14)
        macd, macd_sig, macd_hist = calculate_macd(close_series)
        mom = calculate_momentum(close_series, period=14)

        # Valuation
        liq = calculate_liquidity_score(vol_series, period=20) if vol_series.notna().any() else pd.Series(None, index=df.index)

        # 4. Fetch Global Market Breadth & VIX
        dates_list = [d.date() for d in df.index]
        breadth = await self._calculate_market_breadth(db, dates_list)
        
        vix_sym = self._get_vix_symbol(symbol)
        vix_series = await self._fetch_fear_index(db, vix_sym, dates_list)

        # 5. Save/Upsert into Database
        count = 0
        for dt_idx, row in df.iterrows():
            row_date = dt_idx.date()

            # Skip writing if not enough lookback elements are present to make values valid (e.g. SMA 50 requires 50 values)
            # However, we still write rows that have valid Close. The indicators themselves will write as NULL/None if they are NaN.
            
            def sanitize(val) -> float | None:
                return float(val) if pd.notna(val) else None

            stmt_upsert = insert(TechnicalIndicator).values(
                symbol=symbol,
                date=row_date,
                rsi=sanitize(rsi.loc[dt_idx]),
                macd=sanitize(macd.loc[dt_idx]),
                macd_signal=sanitize(macd_sig.loc[dt_idx]),
                macd_hist=sanitize(macd_hist.loc[dt_idx]),
                sma_50=sanitize(sma_50.loc[dt_idx]),
                sma_200=sanitize(sma_200.loc[dt_idx]),
                ema_20=sanitize(ema_20.loc[dt_idx]),
                drawdown=sanitize(dd.loc[dt_idx]),
                momentum=sanitize(mom.loc[dt_idx]),
                volatility=sanitize(vol.loc[dt_idx]),
                market_breadth=sanitize(breadth.loc[dt_idx]),
                trend_strength=sanitize(trend_str.loc[dt_idx]),
                fear_index=sanitize(vix_series.loc[dt_idx]),
                liquidity_score=sanitize(liq.loc[dt_idx])
            )

            stmt_upsert = stmt_upsert.on_conflict_do_update(
                constraint="uq_indicator_symbol_date",
                set_={
                    "rsi": stmt_upsert.excluded.rsi,
                    "macd": stmt_upsert.excluded.macd,
                    "macd_signal": stmt_upsert.excluded.macd_signal,
                    "macd_hist": stmt_upsert.excluded.macd_hist,
                    "sma_50": stmt_upsert.excluded.sma_50,
                    "sma_200": stmt_upsert.excluded.sma_200,
                    "ema_20": stmt_upsert.excluded.ema_20,
                    "drawdown": stmt_upsert.excluded.drawdown,
                    "momentum": stmt_upsert.excluded.momentum,
                    "volatility": stmt_upsert.excluded.volatility,
                    "market_breadth": stmt_upsert.excluded.market_breadth,
                    "trend_strength": stmt_upsert.excluded.trend_strength,
                    "fear_index": stmt_upsert.excluded.fear_index,
                    "liquidity_score": stmt_upsert.excluded.liquidity_score,
                }
            )
            await db.execute(stmt_upsert)
            count += 1

        await db.commit()
        self.logger.info(f"Upserted {count} indicator records for: {symbol}")
