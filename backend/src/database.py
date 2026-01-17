"""
Database Connection Management

SQLAlchemy async session and connection management.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config import settings
from src.logging_config import get_logger
from src.models.base import Base

logger = get_logger(__name__)

# Engine configuration
engine_kwargs = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
    "connect_args": {
        "timeout": settings.DB_QUERY_TIMEOUT_SECONDS,
        "command_timeout": settings.DB_QUERY_TIMEOUT_SECONDS,
    },
}

if settings.DEBUG:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 40
    engine_kwargs["pool_timeout"] = settings.DB_QUERY_TIMEOUT_SECONDS

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async_session_factory = AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: None)
        logger.info("Database connection established", url=settings.DATABASE_URL.split("@")[-1])
    except Exception as e:
        logger.error("Failed to connect to database", error=str(e))
        raise


async def close_db() -> None:
    """Close database connection."""
    await engine.dispose()
    logger.info("Database connection closed")


async def create_tables() -> None:
    """Create all database tables (development only)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")
