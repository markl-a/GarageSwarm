"""
Database Connection Management

SQLAlchemy async session and connection management.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config import settings
from src.logging_config import get_logger
from src.models import Base

logger = get_logger(__name__)

# Create async engine
# When using NullPool, pool_size and max_overflow are not applicable
engine_kwargs = {
    "echo": settings.DEBUG,  # Log SQL queries in debug mode
    "pool_pre_ping": True,  # Verify connections before using
}

if settings.DEBUG:
    # Use NullPool for development/testing (no connection pooling)
    engine_kwargs["poolclass"] = NullPool
else:
    # Use connection pooling in production
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 40

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for database sessions

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database connection

    Called on application startup.
    """
    try:
        async with engine.begin() as conn:
            # Test connection
            await conn.run_sync(lambda _: None)
        logger.info("✓ Database connection established", url=settings.DATABASE_URL.split("@")[-1])
    except Exception as e:
        logger.error("✗ Failed to connect to database", error=str(e))
        raise


async def close_db() -> None:
    """
    Close database connection

    Called on application shutdown.
    """
    await engine.dispose()
    logger.info("Database connection closed")


async def create_tables() -> None:
    """
    Create all database tables

    WARNING: Only use this in development. Use Alembic migrations in production.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")
