import logging
import time
import redis.asyncio as aioredis
from app.config.config import settings

logger = logging.getLogger(__name__)

# Single Redis client reference
redis_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    """
    Retrieves or initializes the global async Redis client.
    """
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5.0,
        )
    return redis_client


async def get_redis() -> aioredis.Redis:
    """
    Dependency injection helper to get Redis client.
    """
    return get_redis_client()


async def close_redis() -> None:
    """
    Gracefully closes the global Redis client connection.
    """
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed gracefully.")


async def check_redis_health() -> tuple[bool, float]:
    """
    Checks Redis connectivity (PING) and returns a tuple (is_healthy, latency_ms).
    """
    start_time = time.perf_counter()
    try:
        client = get_redis_client()
        await client.ping()
        latency_ms = (time.perf_counter() - start_time) * 1000
        return True, round(latency_ms, 2)
    except Exception as e:
        logger.error("Redis connectivity check failed", extra={"error": str(e)})
        latency_ms = (time.perf_counter() - start_time) * 1000
        return False, round(latency_ms, 2)
