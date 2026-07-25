import logging
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession


class BaseCollector:
    """
    Abstract base class for all market data and FII/DII collectors.
    """
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"collectors.{name}")

    async def collect_daily(self, db: AsyncSession) -> None:
        """
        Fetches today's daily data and stores/updates it in the database.
        """
        raise NotImplementedError("Collectors must implement collect_daily.")

    async def collect_historical(self, db: AsyncSession, start_date: date, end_date: date) -> None:
        """
        Fetches historical data for a given range and stores/updates it in the database.
        """
        raise NotImplementedError("Collectors must implement collect_historical.")
