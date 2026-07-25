import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint_healthy() -> None:
    """
    Test /health endpoint when both PostgreSQL and Redis connections are healthy.
    """
    with patch("app.api.health.check_db_health", new_callable=AsyncMock) as mock_db, \
         patch("app.api.health.check_redis_health", new_callable=AsyncMock) as mock_redis:
        
        mock_db.return_value = (True, 1.5)
        mock_redis.return_value = (True, 0.8)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health")
            
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"]["connected"] is True
        assert data["database"]["latency_ms"] == 1.5
        assert data["redis"]["connected"] is True
        assert data["redis"]["latency_ms"] == 0.8
        assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_health_endpoint_unhealthy() -> None:
    """
    Test /health endpoint when one or both of PostgreSQL or Redis connections fail.
    """
    with patch("app.api.health.check_db_health", new_callable=AsyncMock) as mock_db, \
         patch("app.api.health.check_redis_health", new_callable=AsyncMock) as mock_redis:
        
        mock_db.return_value = (False, 0.0)
        mock_redis.return_value = (True, 1.2)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health")
            
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"]["connected"] is False
        assert data["redis"]["connected"] is True
        assert "uptime_seconds" in data
