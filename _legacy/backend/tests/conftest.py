"""Pytest configuration and fixtures for backend tests"""

import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool, NullPool
from httpx import AsyncClient, ASGITransport

from src.models.base import Base
from src.main import app
from src.dependencies import get_db, get_redis_service, get_redis_client


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
    # Worker-related methods
    redis_service.set_worker_status = AsyncMock()
    redis_service.set_worker_current_task = AsyncMock()
    redis_service.get_worker_status = AsyncMock(return_value=None)
    redis_service.get_online_workers = AsyncMock(return_value=[])
    redis_service.check_rate_limit = AsyncMock(return_value=True)
    # Task-related methods
    redis_service.set_task_status = AsyncMock()
    redis_service.set_task_progress = AsyncMock()
    redis_service.get_task_status = AsyncMock(return_value=None)  # Return None to use DB value
    redis_service.get_task_progress = AsyncMock(return_value=None)  # Return None to use DB value
    redis_service.add_task_to_queue = AsyncMock()
    redis_service.remove_task_from_queue = AsyncMock()
    # Subtask-related methods (Story 3.5)
    redis_service.get_multiple_subtask_statuses = AsyncMock(return_value={})  # Empty dict to use DB values
    redis_service.set_subtask_status = AsyncMock()
    redis_service.set_subtask_progress = AsyncMock()
    redis_service.get_subtask_status = AsyncMock(return_value=None)
    redis_service.get_subtask_progress = AsyncMock(return_value=None)
    # Queue-related methods
    redis_service.push_to_queue = AsyncMock()
    redis_service.get_queue_length = AsyncMock(return_value=0)
    redis_service.get_in_progress_count = AsyncMock(return_value=0)
    redis_service.mark_in_progress = AsyncMock()
    redis_service.clear_worker_current_task = AsyncMock()
    redis_service.get_worker_current_task = AsyncMock(return_value=None)
    return redis_service


# ==================== Fake Redis Fixtures for Redis Tests ====================


class FakeRedis:
    """
    In-memory fake Redis implementation for testing without a real Redis server.
    Implements the minimal Redis commands needed by RedisService.
    """

    def __init__(self):
        self._data = {}
        self._sets = {}
        self._lists = {}
        self._hashes = {}
        self._expiry = {}

    async def ping(self):
        """Ping command"""
        return True

    async def set(self, key: str, value: str, nx=False, ex=None):
        """SET command"""
        if nx and key in self._data:
            return None
        self._data[key] = str(value)
        if ex:
            self._expiry[key] = ex
        return True

    async def setex(self, key: str, time: int, value: str):
        """SETEX command"""
        self._data[key] = str(value)
        self._expiry[key] = time
        return True

    async def get(self, key: str):
        """GET command"""
        return self._data.get(key)

    async def delete(self, *keys):
        """DELETE command"""
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                count += 1
            if key in self._sets:
                del self._sets[key]
                count += 1
            if key in self._lists:
                del self._lists[key]
                count += 1
            if key in self._hashes:
                del self._hashes[key]
                count += 1
        return count

    async def sadd(self, key: str, *values):
        """SADD command"""
        if key not in self._sets:
            self._sets[key] = set()
        before = len(self._sets[key])
        self._sets[key].update(str(v) for v in values)
        return len(self._sets[key]) - before

    async def srem(self, key: str, *values):
        """SREM command"""
        if key not in self._sets:
            return 0
        before = len(self._sets[key])
        self._sets[key].difference_update(str(v) for v in values)
        return before - len(self._sets[key])

    async def smembers(self, key: str):
        """SMEMBERS command"""
        return self._sets.get(key, set())

    async def scard(self, key: str):
        """SCARD command"""
        return len(self._sets.get(key, set()))

    async def rpush(self, key: str, *values):
        """RPUSH command"""
        if key not in self._lists:
            self._lists[key] = []
        self._lists[key].extend(str(v) for v in values)
        return len(self._lists[key])

    async def lpop(self, key: str):
        """LPOP command"""
        if key not in self._lists or not self._lists[key]:
            return None
        return self._lists[key].pop(0)

    async def llen(self, key: str):
        """LLEN command"""
        return len(self._lists.get(key, []))

    async def lindex(self, key: str, index: int):
        """LINDEX command"""
        lst = self._lists.get(key, [])
        if 0 <= index < len(lst):
            return lst[index]
        return None

    async def lrem(self, key: str, count: int, value: str):
        """LREM command"""
        if key not in self._lists:
            return 0
        value = str(value)
        # count=0 means remove all occurrences
        if count == 0:
            before_len = len(self._lists[key])
            self._lists[key] = [v for v in self._lists[key] if v != value]
            removed = before_len - len(self._lists[key])
        return removed

    async def hset(self, key: str, mapping=None, **kwargs):
        """HSET command"""
        if key not in self._hashes:
            self._hashes[key] = {}
        if mapping:
            self._hashes[key].update({k: str(v) for k, v in mapping.items()})
        if kwargs:
            self._hashes[key].update({k: str(v) for k, v in kwargs.items()})
        return len(self._hashes[key])

    async def hgetall(self, key: str):
        """HGETALL command"""
        return self._hashes.get(key, {})

    async def incr(self, key: str):
        """INCR command"""
        current = int(self._data.get(key, 0))
        current += 1
        self._data[key] = str(current)
        return current

    async def expire(self, key: str, time: int):
        """EXPIRE command"""
        self._expiry[key] = time
        return True

    async def publish(self, channel: str, message: str):
        """PUBLISH command (returns 0 as no subscribers in tests)"""
        return 0

    async def flushdb(self):
        """FLUSHDB command"""
        self._data.clear()
        self._sets.clear()
        self._lists.clear()
        self._hashes.clear()
        self._expiry.clear()
        return True

    def pipeline(self):
        """Return a pipeline mock"""
        return FakeRedisPipeline(self)


class FakeRedisPipeline:
    """Fake Redis pipeline for batch operations"""

    def __init__(self, redis_instance):
        self._redis = redis_instance
        self._commands = []

    def get(self, key: str):
        """Queue GET command"""
        self._commands.append(("get", key))
        return self

    async def execute(self):
        """Execute queued commands"""
        results = []
        for cmd, key in self._commands:
            if cmd == "get":
                results.append(await self._redis.get(key))
        self._commands.clear()
        return results


@pytest_asyncio.fixture
async def fake_redis_client():
    """Create a fake Redis client for testing"""
    return FakeRedis()


# ==================== Test Client Fixtures ====================


@pytest_asyncio.fixture
async def test_client(db_session, mock_redis_service, fake_redis_client):
    """Create an async test client with dependency overrides"""

    async def override_get_db():
        yield db_session

    async def override_get_redis_service():
        return mock_redis_service

    async def override_get_redis_client():
        return fake_redis_client

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_service] = override_get_redis_service
    app.dependency_overrides[get_redis_client] = override_get_redis_client

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
    """Sample task data for testing (for model tests)"""
    return {
        "description": "Test task description for model testing",
        "task_metadata": {
            "task_type": "develop_feature",
            "requirements": {
                "complexity": "medium",
                "estimated_time": "30m"
            }
        },
        "checkpoint_frequency": "medium",
        "privacy_level": "normal"
    }
