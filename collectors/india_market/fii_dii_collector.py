import logging
from datetime import date, datetime
import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from collectors.base import BaseCollector
from collectors.utils import retry_async
from database.models import FIIDIIFlow


class FIIDIICollector(BaseCollector):
    """
    Collector for daily FII and DII trading flows, sourcing from Mr. Chartist API.
    """
    def __init__(self) -> None:
        super().__init__(name="fii_dii")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Referer": "https://fii-diidata.mrchartist.com/",
        }

    def _parse_record(self, record: dict) -> dict:
        """
        Parses a single JSON FII/DII record and returns a dictionary matching database model.
        """
        date_str = record.get("date", "")
        try:
            flow_date = datetime.strptime(date_str.strip(), "%d-%b-%Y").date()
        except ValueError as e:
            self.logger.error(f"Failed parsing FII/DII date string: '{date_str}'")
            raise e

        return {
            "date": flow_date,
            "fii_buy": float(record["fii_buy"]) if record.get("fii_buy") is not None else None,
            "fii_sell": float(record["fii_sell"]) if record.get("fii_sell") is not None else None,
            "fii_net": float(record.get("fii_net", 0.0)),
            "dii_buy": float(record["dii_buy"]) if record.get("dii_buy") is not None else None,
            "dii_sell": float(record["dii_sell"]) if record.get("dii_sell") is not None else None,
            "dii_net": float(record.get("dii_net", 0.0)),
        }

    async def _upsert_records(self, db: AsyncSession, records: list[dict]) -> None:
        """
        Executes database upserts for list of FII/DII records.
        """
        if not records:
            return

        count = 0
        for rec in records:
            stmt = insert(FIIDIIFlow).values(**rec)
            stmt = stmt.on_conflict_do_update(
                index_elements=["date"],
                set_={
                    "fii_buy": stmt.excluded.fii_buy,
                    "fii_sell": stmt.excluded.fii_sell,
                    "fii_net": stmt.excluded.fii_net,
                    "dii_buy": stmt.excluded.dii_buy,
                    "dii_sell": stmt.excluded.dii_sell,
                    "dii_net": stmt.excluded.dii_net,
                }
            )
            await db.execute(stmt)
            count += 1

        await db.commit()
        self.logger.info(f"Upserted {count} FII/DII flow records.")

    async def collect_daily(self, db: AsyncSession) -> None:
        """
        Fetches the latest FII/DII data session.
        """
        async def fetch() -> dict:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=10.0) as client:
                response = await client.get("https://fii-diidata.mrchartist.com/api/data")
                response.raise_for_status()
                return response.json()

        try:
            data = await retry_async(fetch)
            parsed = self._parse_record(data)
            await self._upsert_records(db, [parsed])
        except Exception as e:
            self.logger.error(f"FII/DII daily collection failed: {e}", exc_info=True)

    async def collect_historical(self, db: AsyncSession, start_date: date, end_date: date) -> None:
        """
        Fetches FII/DII data history and filters it within the specified date range.
        """
        async def fetch() -> list[dict]:
            # Determine history endpoint based on target date span
            days_diff = (date.today() - start_date).days
            endpoint = "https://fii-diidata.mrchartist.com/api/history"
            if days_diff > 60:
                endpoint = "https://fii-diidata.mrchartist.com/api/history-full"
            
            self.logger.info(f"Fetching FII/DII history from: {endpoint}")
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=15.0) as client:
                response = await client.get(endpoint)
                response.raise_for_status()
                return response.json()

        try:
            data = await retry_async(fetch)
            parsed_records = []
            for record in data:
                try:
                    parsed = self._parse_record(record)
                    if start_date <= parsed["date"] <= end_date:
                        parsed_records.append(parsed)
                except Exception as e:
                    self.logger.warning(
                        f"Skipping invalid historical FII/DII record: {record}, error: {e}"
                    )
            
            await self._upsert_records(db, parsed_records)
        except Exception as e:
            self.logger.error(f"FII/DII historical collection failed: {e}", exc_info=True)
