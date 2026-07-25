import logging
from datetime import date, timedelta
import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from collectors.base import BaseCollector
from collectors.utils import retry_async
from database.models import MarketData


class YFinanceBaseCollector(BaseCollector):
    """
    Base collector class for all yfinance-based market data sources.
    Handles fetching data, retry logic, cleaning, and upserting records.
    """
    def __init__(self, name: str, symbols: dict[str, str]):
        super().__init__(name)
        # Mapping from DB symbol string to Yahoo Finance ticker string
        self.symbols = symbols

    async def _fetch_data(self, yf_symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Invokes yfinance to retrieve history for the symbol.
        """
        def fetch() -> pd.DataFrame:
            ticker = yf.Ticker(yf_symbol)
            # yfinance end date is exclusive, so we add 1 day
            adjusted_end = end_date + timedelta(days=1)
            df = ticker.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=adjusted_end.strftime("%Y-%m-%d"),
                raise_errors=True
            )
            return df
        
        return await retry_async(fetch)

    async def _save_to_db(self, db: AsyncSession, db_symbol: str, df: pd.DataFrame) -> None:
        """
        Performs upsert operations for each row of the fetched data.
        """
        if df.empty:
            self.logger.warning(f"Empty data received for symbol: {db_symbol}")
            return

        # Clean NaN close prices
        df = df.dropna(subset=["Close"])

        count = 0
        for index_val, row in df.iterrows():
            # Date timezone handling: extract the date component
            row_date = index_val.date() if hasattr(index_val, "date") else index_val

            # PostgreSQL upsert (insert ... on conflict do update)
            stmt = insert(MarketData).values(
                symbol=db_symbol,
                date=row_date,
                open=float(row["Open"]) if not pd.isna(row.get("Open")) else None,
                high=float(row["High"]) if not pd.isna(row.get("High")) else None,
                low=float(row["Low"]) if not pd.isna(row.get("Low")) else None,
                close=float(row["Close"]),
                volume=int(row["Volume"]) if not pd.isna(row.get("Volume")) else None
            )

            stmt = stmt.on_conflict_do_update(
                constraint="uq_symbol_date",
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                }
            )
            await db.execute(stmt)
            count += 1

        await db.commit()
        self.logger.info(f"Upserted {count} records for symbol: {db_symbol}")

    async def collect_daily(self, db: AsyncSession) -> None:
        """
        Default daily collector fetches last 5 calendar days to cover weekends/holidays.
        """
        today = date.today()
        await self.collect_historical(db, today - timedelta(days=5), today)

    async def collect_historical(self, db: AsyncSession, start_date: date, end_date: date) -> None:
        """
        Collects data for all symbols sequentially in the specified date range.
        """
        for db_symbol, yf_symbol in self.symbols.items():
            self.logger.info(f"Starting collection: {db_symbol} ({yf_symbol})")
            try:
                df = await self._fetch_data(yf_symbol, start_date, end_date)
                await self._save_to_db(db, db_symbol, df)
            except Exception as e:
                self.logger.error(
                    f"Failed to collect symbol {db_symbol} ({yf_symbol}): {e}",
                    exc_info=True
                )
