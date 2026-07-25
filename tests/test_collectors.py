import pytest
import pandas as pd
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock
from collectors.india_market.index_collector import IndiaIndexCollector
from collectors.india_market.fii_dii_collector import FIIDIICollector
from collectors.us_market.index_collector import USIndexCollector
from collectors.commodities.commodity_collector import CommodityCollector
from collectors.forex.forex_collector import ForexCollector


@pytest.mark.asyncio
async def test_yfinance_collector_success() -> None:
    """
    Verifies that the yfinance-based collectors query correct symbols
    and perform database updates.
    """
    db_mock = AsyncMock()
    collector = IndiaIndexCollector()

    # Create mock dataframe matching expected yfinance output
    df_mock = pd.DataFrame(
        [
            {"Open": 22000.0, "High": 22100.0, "Low": 21900.0, "Close": 22050.0, "Volume": 1000}
        ],
        index=[pd.Timestamp("2026-07-24")]
    )

    with patch.object(collector, "_fetch_data", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = df_mock
        await collector.collect_historical(db_mock, date(2026, 7, 24), date(2026, 7, 24))

        # IndiaIndexCollector has 11 symbols defined
        assert mock_fetch.call_count == 11
        assert db_mock.execute.call_count == 11
        assert db_mock.commit.call_count == 11


@pytest.mark.asyncio
async def test_fii_dii_collector_daily_success() -> None:
    """
    Verifies that the FII/DII daily collector fetches latest data,
    parses it cleanly, and performs database upsert.
    """
    db_mock = AsyncMock()
    collector = FIIDIICollector()

    mock_response = {
        "date": "24-Jul-2026",
        "fii_buy": 10000.00,
        "fii_sell": 12000.00,
        "fii_net": -2000.00,
        "dii_buy": 15000.00,
        "dii_sell": 11000.00,
        "dii_net": 4000.00
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
        
        await collector.collect_daily(db_mock)

        assert db_mock.execute.call_count == 1
        db_mock.commit.assert_called_once()


@pytest.mark.asyncio
async def test_fii_dii_collector_historical_success() -> None:
    """
    Verifies that the FII/DII historical collector fetches, parses,
    and filters records inside the date range.
    """
    db_mock = AsyncMock()
    collector = FIIDIICollector()

    mock_response = [
        {
            "date": "24-Jul-2026",
            "fii_buy": 10000.00,
            "fii_sell": 12000.00,
            "fii_net": -2000.00,
            "dii_buy": 15000.00,
            "dii_sell": 11000.00,
            "dii_net": 4000.00
        },
        {
            "date": "23-Jul-2026",
            "fii_buy": 9000.00,
            "fii_sell": 9500.00,
            "fii_net": -500.00,
            "dii_buy": 11000.00,
            "dii_sell": 10000.00,
            "dii_net": 1000.00
        }
    ]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
        
        # Querying for July 24 specifically, should filter out July 23
        await collector.collect_historical(db_mock, date(2026, 7, 24), date(2026, 7, 24))

        assert db_mock.execute.call_count == 1
        db_mock.commit.assert_called_once()
