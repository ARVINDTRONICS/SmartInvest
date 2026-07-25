import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config.config import settings
from app.core.database import engine
from app.core.logging import setup_logging
from app.core.redis import close_redis, get_redis_client
from app.api import health, market, decision
from database.models import Base
from scheduler.main import start_scheduler, shutdown_scheduler

# Setup logging immediately on file load
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Life-cycle manager for database, redis, and scheduler services.
    """
    logger.info("Starting up SmartInvest AI Engine app...")

    # Initialize Database Tables
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Safe schema migration: upgrade volume column to BIGINT if it's currently INTEGER
            await conn.execute(text("ALTER TABLE market_data ALTER COLUMN volume TYPE BIGINT;"))
        logger.info("Database tables initialized successfully and volume column upgraded to BIGINT.")
    except Exception as e:
        logger.error("Failed to initialize database tables.", extra={"error": str(e)})
    
    # Pre-warm Redis connection
    try:
        client = get_redis_client()
        await client.ping()
        logger.info("Successfully pre-warmed Redis connection at startup.")
    except Exception as e:
        logger.error("Failed to connect to Redis during startup.", extra={"error": str(e)})

    # Start scheduled collection jobs
    try:
        start_scheduler()
    except Exception as e:
        logger.error("Failed to start daily scheduler.", extra={"error": str(e)})

    yield

    logger.info("Shutting down SmartInvest AI Engine app...")
    
    # Shut down scheduler
    try:
        shutdown_scheduler()
    except Exception as e:
        logger.error("Failed to shutdown daily scheduler.", extra={"error": str(e)})

    await close_redis()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# Include API routers
app.include_router(health.router)
app.include_router(market.router)
app.include_router(decision.router)

