import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from httpx import AsyncClient, ASGITransport
from app.core.auth import verify_api_key
from app.config.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_verify_api_key_no_key_dev_bypass() -> None:
    """
    Ensure authentication is bypassed when settings.API_KEY is not configured.
    """
    original_key = settings.API_KEY
    try:
        settings.API_KEY = None
        res = await verify_api_key(None)
        assert res is None
    finally:
        settings.API_KEY = original_key


@pytest.mark.asyncio
async def test_verify_api_key_valid_credentials() -> None:
    """
    Ensure the dependency returns the key when correct Bearer credentials are provided.
    """
    original_key = settings.API_KEY
    try:
        settings.API_KEY = "test-secret-key"
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-secret-key")
        res = await verify_api_key(creds)
        assert res == "test-secret-key"
    finally:
        settings.API_KEY = original_key


@pytest.mark.asyncio
async def test_verify_api_key_missing_credentials() -> None:
    """
    Ensure a 401 is raised when settings.API_KEY is set but credentials are omitted.
    """
    original_key = settings.API_KEY
    try:
        settings.API_KEY = "test-secret-key"
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(None)
        assert exc_info.value.status_code == 401
        assert "Missing Authorization header" in exc_info.value.detail
    finally:
        settings.API_KEY = original_key


@pytest.mark.asyncio
async def test_verify_api_key_invalid_credentials() -> None:
    """
    Ensure a 401 is raised when settings.API_KEY is set but incorrect credentials are provided.
    """
    original_key = settings.API_KEY
    try:
        settings.API_KEY = "test-secret-key"
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong-key")
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(creds)
        assert exc_info.value.status_code == 401
        assert "Invalid or incorrect API key" in exc_info.value.detail
    finally:
        settings.API_KEY = original_key


@pytest.mark.asyncio
async def test_app_endpoint_routing_auth_protection() -> None:
    """
    Ensure /health remains public, while protected routes like /decision block unauthenticated traffic.
    """
    original_key = settings.API_KEY
    try:
        settings.API_KEY = "router-protection-key"
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Health check endpoint MUST remain public (unauthenticated)
            res_health = await ac.get("/health")
            assert res_health.status_code == 200
            
            # 2. Decision endpoint MUST return 401 if token is missing
            res_decision_missing = await ac.get("/decision?symbol=NIFTY50&remaining_days=5")
            assert res_decision_missing.status_code == 401
            assert "Missing Authorization header" in res_decision_missing.json()["detail"]
            
            # 3. Decision endpoint MUST return 401 if token is incorrect
            res_decision_incorrect = await ac.get(
                "/decision?symbol=NIFTY50&remaining_days=5",
                headers={"Authorization": "Bearer incorrect-token"}
            )
            assert res_decision_incorrect.status_code == 401
            assert "Invalid or incorrect API key" in res_decision_incorrect.json()["detail"]
    finally:
        settings.API_KEY = original_key
