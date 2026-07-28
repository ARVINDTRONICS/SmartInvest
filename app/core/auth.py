import logging
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config.config import settings

logger = logging.getLogger(__name__)

# Use auto_error=False so that we can check if credentials are None.
# If API_KEY is not set, we can allow the request to bypass auth gracefully.
security = HTTPBearer(auto_error=False)

async def verify_api_key(credentials: HTTPAuthorizationCredentials | None = Security(security)) -> str | None:
    """
    Dependency that validates the incoming request's Bearer token against settings.API_KEY.
    If settings.API_KEY is not configured, it logs a warning and allows the request (local dev bypass).
    """
    # 1. Check if API_KEY is set in configuration
    if not settings.API_KEY:
        logger.warning("API_KEY is not configured. API endpoints are running in UNAUTHENTICATED mode!")
        return None

    # 2. Check if credentials were provided
    if credentials is None:
        logger.warning("Unauthorized access attempt: Missing Bearer Token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header with Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Verify Bearer token credentials
    if credentials.credentials != settings.API_KEY:
        logger.warning("Unauthorized access attempt: Invalid Bearer Token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or incorrect API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
