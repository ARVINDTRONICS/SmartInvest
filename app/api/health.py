import time
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.database import check_db_health
from app.core.redis import check_redis_health

router = APIRouter()

# Track start time for uptime calculation
APP_START_TIME = time.time()


class ServiceHealth(BaseModel):
    connected: bool
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    database: ServiceHealth
    redis: ServiceHealth


@router.get("/health", response_model=HealthResponse)
async def health_check() -> dict:
    """
    Checks connection status and latency for PostgreSQL and Redis.
    Returns general app status and uptime.
    """
    db_ok, db_latency = await check_db_health()
    redis_ok, redis_latency = await check_redis_health()

    uptime = time.time() - APP_START_TIME
    status = "healthy" if (db_ok and redis_ok) else "unhealthy"

    return {
        "status": status,
        "uptime_seconds": round(uptime, 2),
        "database": {
            "connected": db_ok,
            "latency_ms": db_latency,
        },
        "redis": {
            "connected": redis_ok,
            "latency_ms": redis_latency,
        },
    }
