"""Unit tests for WorkerService"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from src.services.worker_service import WorkerService
from src.models.worker import Worker
from src.schemas.worker import WorkerStatus


def create_mock_result(return_value):
    """Helper to create a mock execute result"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = return_value
    mock_result.scalars.return_value.all.return_value = [return_value] if return_value else []
    mock_result.scalar.return_value = 1
    return mock_result


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_redis_service():
    """Mock Redis service"""
    redis = AsyncMock()
    redis.set_worker_status = AsyncMock()
    redis.set_worker_current_task = AsyncMock()
    return redis


@pytest.fixture
def worker_service(mock_db_session, mock_redis_service):
    """Create WorkerService instance with mocks"""
    return WorkerService(mock_db_session, mock_redis_service)


@pytest.fixture
def sample_worker():
    """Sample worker instance"""
    worker = MagicMock(spec=Worker)
    worker.worker_id = uuid4()
    worker.machine_id = "test-machine-001"
    worker.machine_name = "Test Machine"
    worker.system_info = {"os": "Linux", "cpu_count": 8}
    worker.tools = ["claude_code"]
    worker.status = WorkerStatus.ONLINE.value
    return worker


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_new_worker(worker_service, mock_db_session, mock_redis_service):
    """Test registering a new worker"""
    # Arrange
    machine_id = "test-machine-001"
    machine_name = "Test Machine"
    system_info = {"os": "Linux", "cpu_count": 8}
    tools = ["claude_code"]

    # Mock database to return None (no existing worker)
    mock_db_session.execute.return_value = create_mock_result(None)

    # Act
    worker = await worker_service.register_worker(
        machine_id=machine_id,
        machine_name=machine_name,
        system_info=system_info,
        tools=tools
    )

    # Assert
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_redis_service.set_worker_status.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_existing_worker_updates(
    worker_service, mock_db_session, mock_redis_service, sample_worker
):
    """Test that registering an existing worker updates it (idempotency)"""
    # Arrange
    machine_id = sample_worker.machine_id
    new_machine_name = "Updated Machine Name"
    new_tools = ["claude_code", "gemini_cli"]

    # Mock database to return existing worker
    mock_db_session.execute.return_value = create_mock_result(sample_worker)

    # Act
    worker = await worker_service.register_worker(
        machine_id=machine_id,
        machine_name=new_machine_name,
        system_info=sample_worker.system_info,
        tools=new_tools
    )

    # Assert
    assert worker.machine_name == new_machine_name
    assert worker.tools == new_tools
    mock_db_session.add.assert_not_called()  # Should NOT add, only update
    mock_db_session.commit.assert_called_once()
    mock_redis_service.set_worker_status.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_heartbeat(
    worker_service, mock_db_session, mock_redis_service, sample_worker
):
    """Test updating worker heartbeat"""
    # Arrange
    worker_id = sample_worker.worker_id
    status = WorkerStatus.IDLE.value
    resources = {
        "cpu_percent": 25.5,
        "memory_percent": 60.2,
        "disk_percent": 45.0
    }

    # Mock database to return worker
    mock_db_session.execute.return_value = create_mock_result(sample_worker)

    # Act
    result = await worker_service.update_heartbeat(
        worker_id=worker_id,
        status=status,
        resources=resources
    )

    # Assert
    assert result is True
    assert sample_worker.status == status
    assert sample_worker.cpu_percent == 25.5
    assert sample_worker.memory_percent == 60.2
    assert sample_worker.disk_percent == 45.0
    mock_db_session.commit.assert_called_once()
    mock_redis_service.set_worker_status.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_heartbeat_worker_not_found(
    worker_service, mock_db_session, mock_redis_service
):
    """Test heartbeat update with non-existent worker"""
    # Arrange
    worker_id = uuid4()

    # Mock database to return None
    mock_db_session.execute.return_value = create_mock_result(None)

    # Act & Assert
    with pytest.raises(ValueError, match="Worker .* not found"):
        await worker_service.update_heartbeat(
            worker_id=worker_id,
            status=WorkerStatus.ONLINE.value,
            resources={"cpu_percent": 0}
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_worker(worker_service, mock_db_session, sample_worker):
    """Test getting worker by ID"""
    # Arrange
    worker_id = sample_worker.worker_id

    # Mock database
    mock_db_session.execute.return_value = create_mock_result(sample_worker)

    # Act
    worker = await worker_service.get_worker(worker_id)

    # Assert
    assert worker == sample_worker
    assert worker.worker_id == worker_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_worker_not_found(worker_service, mock_db_session):
    """Test getting non-existent worker"""
    # Arrange
    worker_id = uuid4()

    # Mock database to return None
    mock_db_session.execute.return_value = create_mock_result(None)

    # Act
    worker = await worker_service.get_worker(worker_id)

    # Assert
    assert worker is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unregister_worker(
    worker_service, mock_db_session, mock_redis_service, sample_worker
):
    """Test unregistering worker"""
    # Arrange
    worker_id = sample_worker.worker_id

    # Mock database
    mock_db_session.execute.return_value = create_mock_result(sample_worker)

    # Act
    result = await worker_service.unregister_worker(worker_id)

    # Assert
    assert result is True
    assert sample_worker.status == WorkerStatus.OFFLINE.value
    mock_db_session.commit.assert_called_once()
    mock_redis_service.set_worker_status.assert_called_once_with(
        worker_id=worker_id,
        status=WorkerStatus.OFFLINE.value
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unregister_worker_not_found(
    worker_service, mock_db_session, mock_redis_service
):
    """Test unregistering non-existent worker"""
    # Arrange
    worker_id = uuid4()

    # Mock database to return None
    mock_db_session.execute.return_value = create_mock_result(None)

    # Act
    result = await worker_service.unregister_worker(worker_id)

    # Assert
    assert result is False
    mock_db_session.commit.assert_not_called()
    mock_redis_service.set_worker_status.assert_not_called()
