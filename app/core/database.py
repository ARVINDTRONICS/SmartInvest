import logging
import time
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.sql import text
from app.config.config import settings

logger = logging.getLogger(__name__)

# Create Async Engine for PostgreSQL
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

# Async Session Factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection generator for FastAPI endpoints to retrieve database session.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_db_health() -> tuple[bool, float]:
    """
    Checks database connectivity and returns a tuple (is_healthy, latency_ms).
    """
    start_time = time.perf_counter()
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        latency_ms = (time.perf_counter() - start_time) * 1000
        return True, round(latency_ms, 2)
    except Exception as e:
        logger.error("Database connectivity check failed", extra={"error": str(e)})
        latency_ms = (time.perf_counter() - start_time) * 1000
        return False, round(latency_ms, 2)
