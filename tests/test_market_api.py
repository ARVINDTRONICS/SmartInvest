import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import get_db
from app.core.redis import get_redis


@pytest.mark.asyncio
async def test_market_today_cache_hit() -> None:
    """
    Verifies that the /market/today endpoint returns cached JSON from Redis
    if it is available, avoiding database queries.
    """
    mock_cache = {
        "date": "2026-07-25",
        "market_data": [
            {
                "symbol": "NIFTY50",
                "date": "2026-07-24",
                "open": 22000.0,
                "high": 22100.0,
                "low": 21900.0,
                "close": 22050.0,
                "volume": 1000,
            }
        ],
        "fii_dii": {
            "date": "2026-07-24",
            "fii_buy": 10000.0,
            "fii_sell": 12000.0,
            "fii_net": -2000.0,
            "dii_buy": 15000.0,
            "dii_sell": 11000.0,
            "dii_net": 4000.0,
        }
    }

    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps(mock_cache)

    # Register dependency overrides
    app.dependency_overrides[get_redis] = lambda: mock_redis

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/market/today")

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-07-25"
        assert len(data["market_data"]) == 1
        assert data["market_data"][0]["symbol"] == "NIFTY50"
        assert data["fii_dii"]["fii_net"] == -2000.0
        mock_redis.get.assert_called_once_with("market:today")
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_market_today_cache_miss() -> None:
    """
    Verifies that /market/today fetches from database and writes back to Redis cache
    when cache is empty.
    """
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Force cache miss

    class MockMarketData:
        symbol = "NIFTY50"
        date = date(2026, 7, 24)
        open = 22000.0
        high = 22100.0
        low = 21900.0
        close = 22050.0
        volume = 1000

    class MockFIIDII:
        date = date(2026, 7, 24)
        fii_buy = 10000.0
        fii_sell = 12000.0
        fii_net = -2000.0
        dii_buy = 15000.0
        dii_sell = 11000.0
        dii_net = 4000.0

    mock_db = AsyncMock()
    
    # Mocking SQLAlchemy results: first call returns market data, second returns FII/DII
    execute_mock = AsyncMock()
    result_market = MagicMock()
    result_market.scalars.return_value.all.return_value = [MockMarketData()]
    
    result_fii = MagicMock()
    result_fii.scalar_one_or_none.return_value = MockFIIDII()
    
    execute_mock.side_effect = [result_market, result_fii]
    mock_db.execute = execute_mock

    # Register dependency overrides
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/market/today")

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == date.today().isoformat()
        assert len(data["market_data"]) == 1
        assert data["market_data"][0]["symbol"] == "NIFTY50"
        assert data["fii_dii"]["fii_net"] == -2000.0
        
        # Verify writing to Redis cache
        mock_redis.setex.assert_called_once()
    finally:
        app.dependency_overrides.clear()
