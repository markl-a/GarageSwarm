"""Unit tests for TaskAllocator"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from src.services.task_allocator import (
    TaskAllocator,
    SCORING_WEIGHTS,
    RESOURCE_THRESHOLDS
)
from src.models.task import Task
from src.models.subtask import Subtask
from src.models.worker import Worker


def create_mock_result(return_value):
    """Helper to create a mock execute result"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = return_value
    mock_result.scalars.return_value.all.return_value = [return_value] if return_value else []
    mock_result.scalars.return_value.first.return_value = return_value
    mock_result.scalar.return_value = 1
    mock_result.fetchall.return_value = []
    return mock_result


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_redis_service():
    """Mock Redis service"""
    redis = AsyncMock()
    redis.get_worker_current_task = AsyncMock(return_value=None)
    redis.set_worker_current_task = AsyncMock()
    redis.clear_worker_current_task = AsyncMock()
    redis.set_worker_status = AsyncMock()
    redis.push_to_queue = AsyncMock()
    redis.pop_from_queue = AsyncMock()
    redis.mark_in_progress = AsyncMock()
    redis.get_queue_length = AsyncMock(return_value=0)
    redis.get_in_progress_count = AsyncMock(return_value=0)
    redis.get_online_workers = AsyncMock(return_value=[])
    return redis


@pytest.fixture
def task_allocator(mock_db_session, mock_redis_service):
    """Create TaskAllocator instance with mocks"""
    return TaskAllocator(mock_db_session, mock_redis_service)


@pytest.fixture
def sample_task():
    """Sample task instance"""
    task = MagicMock(spec=Task)
    task.task_id = uuid4()
    task.description = "Create a Python function"
    task.status = "initializing"
    task.progress = 0
    task.privacy_level = "normal"
    task.tool_preferences = ["claude_code"]
    return task


@pytest.fixture
def sample_subtask(sample_task):
    """Sample subtask instance"""
    subtask = MagicMock(spec=Subtask)
    subtask.subtask_id = uuid4()
    subtask.task_id = sample_task.task_id
    subtask.task = sample_task
    subtask.name = "Code Generation"
    subtask.description = "Generate the main code"
    subtask.status = "pending"
    subtask.progress = 0
    subtask.recommended_tool = "claude_code"
    subtask.assigned_worker = None
    subtask.assigned_tool = None
    subtask.complexity = 3
    subtask.priority = 100
    subtask.dependencies = []
    return subtask


@pytest.fixture
def sample_worker():
    """Sample worker instance"""
    worker = MagicMock(spec=Worker)
    worker.worker_id = uuid4()
    worker.machine_id = "test-machine-001"
    worker.machine_name = "Test Machine"
    worker.status = "online"
    worker.tools = ["claude_code", "gemini_cli"]
    worker.cpu_percent = 30.0
    worker.memory_percent = 40.0
    worker.disk_percent = 50.0
    worker.system_info = {"os": "linux"}
    return worker


# ==================== Scoring Algorithm Tests ====================


@pytest.mark.unit
def test_scoring_weights_sum_to_one():
    """Test that scoring weights sum to 1.0"""
    total = sum(SCORING_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, should be 1.0"


@pytest.mark.unit
def test_calculate_tool_score_perfect_match(task_allocator, sample_worker, sample_subtask):
    """Test tool score when worker has recommended tool"""
    sample_subtask.recommended_tool = "claude_code"
    sample_worker.tools = ["claude_code", "gemini_cli"]

    score = task_allocator._calculate_tool_score(sample_worker, sample_subtask)

    assert score == 1.0


@pytest.mark.unit
def test_calculate_tool_score_partial_match(task_allocator, sample_worker, sample_subtask):
    """Test tool score when worker has tools but not the recommended one"""
    sample_subtask.recommended_tool = "ollama"
    sample_worker.tools = ["claude_code", "gemini_cli"]

    score = task_allocator._calculate_tool_score(sample_worker, sample_subtask)

    assert score == 0.5


@pytest.mark.unit
def test_calculate_tool_score_no_tools(task_allocator, sample_worker, sample_subtask):
    """Test tool score when worker has no tools"""
    sample_subtask.recommended_tool = "claude_code"
    sample_worker.tools = []

    score = task_allocator._calculate_tool_score(sample_worker, sample_subtask)

    assert score == 0.0


@pytest.mark.unit
def test_calculate_tool_score_no_recommendation(task_allocator, sample_worker, sample_subtask):
    """Test tool score when no tool is recommended"""
    sample_subtask.recommended_tool = None
    sample_worker.tools = ["claude_code"]

    score = task_allocator._calculate_tool_score(sample_worker, sample_subtask)

    assert score == 1.0  # Any tool is fine


@pytest.mark.unit
def test_calculate_resource_score_low_usage(task_allocator, sample_worker):
    """Test resource score with low resource usage"""
    sample_worker.cpu_percent = 10.0
    sample_worker.memory_percent = 20.0
    sample_worker.disk_percent = 30.0

    score = task_allocator._calculate_resource_score(sample_worker)

    # Expected: (0.9 * 0.4) + (0.8 * 0.4) + (0.7 * 0.2) = 0.36 + 0.32 + 0.14 = 0.82
    assert 0.80 <= score <= 0.84


@pytest.mark.unit
def test_calculate_resource_score_high_usage(task_allocator, sample_worker):
    """Test resource score with high resource usage"""
    sample_worker.cpu_percent = 90.0
    sample_worker.memory_percent = 85.0
    sample_worker.disk_percent = 80.0

    score = task_allocator._calculate_resource_score(sample_worker)

    # Low resource availability means low score
    assert score < 0.3


@pytest.mark.unit
def test_calculate_resource_score_unknown_values(task_allocator, sample_worker):
    """Test resource score when values are unknown"""
    sample_worker.cpu_percent = None
    sample_worker.memory_percent = None
    sample_worker.disk_percent = None

    score = task_allocator._calculate_resource_score(sample_worker)

    # Unknown values should return moderate score (0.5)
    assert score == 0.5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_privacy_score_normal(task_allocator, sample_worker, sample_subtask):
    """Test privacy score for normal privacy level"""
    sample_subtask.task.privacy_level = "normal"

    score = await task_allocator._calculate_privacy_score(sample_worker, sample_subtask)

    assert score == 1.0  # All workers compatible with normal tasks


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_privacy_score_sensitive_local(task_allocator, sample_worker, sample_subtask):
    """Test privacy score for sensitive task with local tool"""
    sample_subtask.task.privacy_level = "sensitive"
    sample_worker.tools = ["ollama"]  # Local only

    score = await task_allocator._calculate_privacy_score(sample_worker, sample_subtask)

    assert score == 1.0  # Perfect for sensitive tasks


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_privacy_score_sensitive_mixed(task_allocator, sample_worker, sample_subtask):
    """Test privacy score for sensitive task with mixed tools"""
    sample_subtask.task.privacy_level = "sensitive"
    sample_worker.tools = ["ollama", "claude_code"]  # Has local option

    score = await task_allocator._calculate_privacy_score(sample_worker, sample_subtask)

    assert score == 0.8  # Has local option


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_privacy_score_sensitive_cloud_only(task_allocator, sample_worker, sample_subtask):
    """Test privacy score for sensitive task with cloud-only tools"""
    sample_subtask.task.privacy_level = "sensitive"
    sample_worker.tools = ["claude_code", "gemini_cli"]  # Cloud only

    score = await task_allocator._calculate_privacy_score(sample_worker, sample_subtask)

    assert score == 0.5  # Less suitable for sensitive tasks


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_worker_score_combined(
    task_allocator, mock_db_session, sample_worker, sample_subtask
):
    """Test combined worker scoring"""
    sample_subtask.recommended_tool = "claude_code"
    sample_subtask.task.privacy_level = "normal"
    sample_worker.tools = ["claude_code"]
    sample_worker.cpu_percent = 20.0
    sample_worker.memory_percent = 30.0
    sample_worker.disk_percent = 40.0

    score = await task_allocator._calculate_worker_score(sample_worker, sample_subtask)

    # tool_score = 1.0 (perfect match)
    # resource_score ≈ 0.74
    # privacy_score = 1.0 (normal)
    # total = (1.0 * 0.5) + (0.74 * 0.3) + (1.0 * 0.2) = 0.5 + 0.222 + 0.2 = 0.922
    assert 0.85 <= score <= 0.95


# ==================== Allocation Tests ====================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_allocate_subtask_not_found(task_allocator, mock_db_session):
    """Test allocating non-existent subtask"""
    subtask_id = uuid4()
    mock_db_session.execute.return_value = create_mock_result(None)

    with pytest.raises(ValueError, match="not found"):
        await task_allocator.allocate_subtask(subtask_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_allocate_subtask_already_assigned(task_allocator, mock_db_session, sample_subtask):
    """Test allocating already assigned subtask"""
    sample_subtask.assigned_worker = uuid4()
    mock_db_session.execute.return_value = create_mock_result(sample_subtask)

    with pytest.raises(ValueError, match="already assigned"):
        await task_allocator.allocate_subtask(sample_subtask.subtask_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_allocate_subtask_wrong_status(task_allocator, mock_db_session, sample_subtask):
    """Test allocating subtask in wrong status"""
    sample_subtask.status = "in_progress"
    mock_db_session.execute.return_value = create_mock_result(sample_subtask)

    with pytest.raises(ValueError, match="not in allocatable state"):
        await task_allocator.allocate_subtask(sample_subtask.subtask_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_allocate_subtask_no_workers(
    task_allocator, mock_db_session, mock_redis_service, sample_subtask
):
    """Test allocation when no workers available"""
    # First call returns subtask, second returns empty workers list
    mock_empty_result = MagicMock()
    mock_empty_result.scalars.return_value.all.return_value = []

    mock_db_session.execute.side_effect = [
        create_mock_result(sample_subtask),  # Get subtask
        mock_empty_result,  # Get available workers
    ]

    result = await task_allocator.allocate_subtask(sample_subtask.subtask_id)

    assert result is None
    mock_redis_service.push_to_queue.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_allocate_subtask_success(
    task_allocator, mock_db_session, mock_redis_service, sample_subtask, sample_worker
):
    """Test successful subtask allocation"""
    # Mock worker has no current task
    mock_redis_service.get_worker_current_task.return_value = None

    # First call returns subtask, second returns workers list
    mock_workers_result = MagicMock()
    mock_workers_result.scalars.return_value.all.return_value = [sample_worker]

    mock_db_session.execute.side_effect = [
        create_mock_result(sample_subtask),  # Get subtask
        mock_workers_result,  # Get available workers
    ]

    result = await task_allocator.allocate_subtask(sample_subtask.subtask_id)

    assert result == sample_worker
    assert sample_subtask.assigned_worker == sample_worker.worker_id
    mock_redis_service.set_worker_current_task.assert_called_once()
    mock_redis_service.mark_in_progress.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_allocate_subtask_selects_best_worker(
    task_allocator, mock_db_session, mock_redis_service, sample_subtask
):
    """Test that allocation selects the best scoring worker"""
    # Create two workers with different scores
    worker1 = MagicMock(spec=Worker)
    worker1.worker_id = uuid4()
    worker1.machine_name = "Worker 1"
    worker1.tools = ["gemini_cli"]  # Not recommended
    worker1.cpu_percent = 50.0
    worker1.memory_percent = 50.0
    worker1.disk_percent = 50.0

    worker2 = MagicMock(spec=Worker)
    worker2.worker_id = uuid4()
    worker2.machine_name = "Worker 2"
    worker2.tools = ["claude_code"]  # Recommended tool
    worker2.cpu_percent = 20.0
    worker2.memory_percent = 20.0
    worker2.disk_percent = 20.0

    sample_subtask.recommended_tool = "claude_code"
    sample_subtask.task.privacy_level = "normal"

    mock_redis_service.get_worker_current_task.return_value = None

    mock_workers_result = MagicMock()
    mock_workers_result.scalars.return_value.all.return_value = [worker1, worker2]

    mock_db_session.execute.side_effect = [
        create_mock_result(sample_subtask),
        mock_workers_result,
    ]

    result = await task_allocator.allocate_subtask(sample_subtask.subtask_id)

    # Worker 2 should be selected (better tool match and resource availability)
    assert result == worker2


# ==================== Release Worker Tests ====================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_release_worker(task_allocator, mock_db_session, mock_redis_service, sample_worker):
    """Test releasing a worker"""
    mock_db_session.execute.return_value = create_mock_result(sample_worker)

    await task_allocator.release_worker(sample_worker.worker_id)

    assert sample_worker.status == "online"
    mock_db_session.commit.assert_called_once()
    mock_redis_service.clear_worker_current_task.assert_called_once()
    mock_redis_service.set_worker_status.assert_called_with(
        sample_worker.worker_id, "online"
    )


# ==================== Helper Method Tests ====================


@pytest.mark.unit
def test_get_scoring_weights(task_allocator):
    """Test getting scoring weights"""
    weights = task_allocator.get_scoring_weights()

    assert "tool_matching" in weights
    assert "resource_score" in weights
    assert "privacy_score" in weights
    assert weights["tool_matching"] == 0.5
    assert weights["resource_score"] == 0.3
    assert weights["privacy_score"] == 0.2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_allocation_stats(task_allocator, mock_db_session, mock_redis_service):
    """Test getting allocation statistics"""
    mock_redis_service.get_queue_length.return_value = 5
    mock_redis_service.get_in_progress_count.return_value = 3
    mock_redis_service.get_online_workers.return_value = ["w1", "w2"]

    mock_queued_result = MagicMock()
    mock_queued_result.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]

    mock_db_session.execute.return_value = mock_queued_result

    stats = await task_allocator.get_allocation_stats()

    assert stats["queue_length"] == 5
    assert stats["in_progress_count"] == 3
    assert stats["online_workers"] == 2
    assert stats["queued_subtasks"] == 2


# ==================== Get Ready Subtasks Tests ====================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ready_subtasks_no_dependencies(task_allocator, mock_db_session):
    """Test getting ready subtasks when no dependencies"""
    task_id = uuid4()

    subtask = MagicMock(spec=Subtask)
    subtask.subtask_id = uuid4()
    subtask.dependencies = []

    mock_pending_result = MagicMock()
    mock_pending_result.scalars.return_value.all.return_value = [subtask]

    mock_completed_result = MagicMock()
    mock_completed_result.fetchall.return_value = []

    mock_db_session.execute.side_effect = [
        mock_pending_result,
        mock_completed_result,
    ]

    ready = await task_allocator._get_ready_subtasks(task_id)

    assert len(ready) == 1
    assert ready[0] == subtask


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ready_subtasks_with_met_dependencies(task_allocator, mock_db_session):
    """Test getting ready subtasks when dependencies are met"""
    task_id = uuid4()
    dep_id = uuid4()

    subtask = MagicMock(spec=Subtask)
    subtask.subtask_id = uuid4()
    subtask.dependencies = [str(dep_id)]

    mock_pending_result = MagicMock()
    mock_pending_result.scalars.return_value.all.return_value = [subtask]

    mock_completed_result = MagicMock()
    mock_completed_result.fetchall.return_value = [(dep_id,)]  # Dependency completed

    mock_db_session.execute.side_effect = [
        mock_pending_result,
        mock_completed_result,
    ]

    ready = await task_allocator._get_ready_subtasks(task_id)

    assert len(ready) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ready_subtasks_with_unmet_dependencies(task_allocator, mock_db_session):
    """Test getting ready subtasks when dependencies not met"""
    task_id = uuid4()
    dep_id = uuid4()

    subtask = MagicMock(spec=Subtask)
    subtask.subtask_id = uuid4()
    subtask.dependencies = [str(dep_id)]

    mock_pending_result = MagicMock()
    mock_pending_result.scalars.return_value.all.return_value = [subtask]

    mock_completed_result = MagicMock()
    mock_completed_result.fetchall.return_value = []  # No completed dependencies

    mock_db_session.execute.side_effect = [
        mock_pending_result,
        mock_completed_result,
    ]

    ready = await task_allocator._get_ready_subtasks(task_id)

    assert len(ready) == 0  # Subtask not ready


# ==================== Get Available Workers Tests ====================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_available_workers_filters_busy(
    task_allocator, mock_db_session, mock_redis_service
):
    """Test that workers with current tasks are filtered out"""
    worker1 = MagicMock(spec=Worker)
    worker1.worker_id = uuid4()
    worker1.status = "online"

    worker2 = MagicMock(spec=Worker)
    worker2.worker_id = uuid4()
    worker2.status = "online"

    mock_workers_result = MagicMock()
    mock_workers_result.scalars.return_value.all.return_value = [worker1, worker2]

    mock_db_session.execute.return_value = mock_workers_result

    # Worker1 has a current task, worker2 doesn't
    mock_redis_service.get_worker_current_task.side_effect = [
        "some-task-id",  # worker1 is busy
        None,  # worker2 is available
    ]

    available = await task_allocator._get_available_workers()

    assert len(available) == 1
    assert available[0] == worker2
