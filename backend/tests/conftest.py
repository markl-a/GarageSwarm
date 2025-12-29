"""Pytest configuration and fixtures for backend tests"""

import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool, NullPool
from httpx import AsyncClient, ASGITransport

from src.models.base import Base
from src.main import app
from src.dependencies import get_db, get_redis_service


# ==================== Database Fixtures ====================


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a PostgreSQL database engine for testing"""
    # Use the same database URL as the application
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@postgres:5432/multi_agent_test"
    )

    engine = create_async_engine(
        database_url,
        poolclass=NullPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create a database session for testing"""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session


# ==================== Mock Redis Service ====================


@pytest.fixture
def mock_redis_service():
    """Create a mock Redis service for testing"""
    redis_service = AsyncMock()
    redis_service.set_worker_status = AsyncMock()
    redis_service.set_worker_current_task = AsyncMock()
    redis_service.get_worker_status = AsyncMock(return_value=None)
    redis_service.get_online_workers = AsyncMock(return_value=[])
    redis_service.check_rate_limit = AsyncMock(return_value=True)
    return redis_service


# ==================== Test Client Fixtures ====================


@pytest_asyncio.fixture
async def test_client(db_session, mock_redis_service):
    """Create an async test client with dependency overrides"""

    async def override_get_db():
        yield db_session

    async def override_get_redis_service():
        return mock_redis_service

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_service] = override_get_redis_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()


# ==================== Sample Data Fixtures ====================


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": "hashed_password_123"
    }


@pytest.fixture
def sample_worker_data():
    """Sample worker data for testing"""
    return {
        "machine_id": "test-machine-001",
        "machine_name": "Test Machine",
        "system_info": {
            "os": "Linux",
            "cpu_count": 8,
            "memory_total": 16000000000
        },
        "tools": ["claude_code", "gemini_cli"]
    }


@pytest.fixture
def sample_task_data():
    """Sample task data for testing"""
    return {
        "description": "Test task description",
        "requirements": {
            "complexity": "medium",
            "estimated_time": "30m"
        },
        "checkpoint_frequency": "medium",
        "privacy_level": "normal"
    }
