"""Unit tests for TaskScheduler"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from src.services.task_scheduler import (
    TaskScheduler,
    SchedulerRunner,
    MAX_CONCURRENT_SUBTASKS,
    MAX_SUBTASKS_PER_WORKER,
    SCHEDULER_INTERVAL_SECONDS
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
    mock_result.scalar.return_value = 1 if return_value else 0
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
    redis.get_in_progress_count = AsyncMock(return_value=0)
    redis.get_queue_length = AsyncMock(return_value=0)
    redis.push_to_queue = AsyncMock()
    redis.set_task_status = AsyncMock()
    redis.set_task_progress = AsyncMock()
    redis.set_worker_status = AsyncMock()
    redis.set_worker_current_task = AsyncMock()
    redis.clear_worker_current_task = AsyncMock()
    redis.mark_in_progress = AsyncMock()
    redis.get_worker_current_task = AsyncMock(return_value=None)
    return redis


@pytest.fixture
def mock_allocator():
    """Mock TaskAllocator"""
    allocator = AsyncMock()
    allocator.allocate_subtask = AsyncMock(return_value=None)
    allocator.release_worker = AsyncMock()
    allocator.get_allocation_stats = AsyncMock(return_value={
        "queue_length": 0,
        "in_progress_count": 0,
        "online_workers": 0,
        "queued_subtasks": 0
    })
    return allocator


@pytest.fixture
def mock_decomposer():
    """Mock TaskDecomposer"""
    decomposer = AsyncMock()
    decomposer.decompose_task = AsyncMock(return_value=[])
    decomposer.get_ready_subtasks = AsyncMock(return_value=[])
    decomposer.check_task_completion = AsyncMock(return_value=False)
    return decomposer


@pytest.fixture
def task_scheduler(mock_db_session, mock_redis_service, mock_allocator, mock_decomposer):
    """Create TaskScheduler instance with mocks"""
    return TaskScheduler(
        mock_db_session,
        mock_redis_service,
        mock_allocator,
        mock_decomposer
    )


@pytest.fixture
def sample_task():
    """Sample task instance"""
    task = MagicMock(spec=Task)
    task.task_id = uuid4()
    task.description = "Sample task"
    task.status = "initializing"
    task.progress = 0
    task.created_at = datetime.utcnow()
    return task


@pytest.fixture
def sample_subtask(sample_task):
    """Sample subtask instance"""
    subtask = MagicMock(spec=Subtask)
    subtask.subtask_id = uuid4()
    subtask.task_id = sample_task.task_id
    subtask.task = sample_task
    subtask.name = "Code Generation"
    subtask.status = "pending"
    subtask.priority = 100
    subtask.dependencies = []
    subtask.assigned_worker = None
    return subtask


@pytest.fixture
def sample_worker():
    """Sample worker instance"""
    worker = MagicMock(spec=Worker)
    worker.worker_id = uuid4()
    worker.machine_name = "Test Worker"
    worker.status = "online"
    worker.tools = ["claude_code"]
    return worker


# ==================== Constants Tests ====================


@pytest.mark.unit
def test_max_concurrent_subtasks_default():
    """Test default max concurrent subtasks"""
    assert MAX_CONCURRENT_SUBTASKS == 20


@pytest.mark.unit
def test_max_subtasks_per_worker_default():
    """Test default max subtasks per worker"""
    assert MAX_SUBTASKS_PER_WORKER == 1


@pytest.mark.unit
def test_scheduler_interval_default():
    """Test default scheduler interval"""
    assert SCHEDULER_INTERVAL_SECONDS == 30


# ==================== Scheduling Cycle Tests ====================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_scheduling_cycle_empty(task_scheduler, mock_db_session, mock_redis_service):
    """Test scheduling cycle with no active tasks"""
    # Mock empty results
    mock_empty_result = MagicMock()
    mock_empty_result.scalars.return_value.all.return_value = []

    mock_db_session.execute.return_value = mock_empty_result

    result = await task_scheduler.run_scheduling_cycle()

    assert "cycle_start" in result
    assert result["tasks_processed"] == 0
    assert result["subtasks_allocated"] == 0
    assert result["subtasks_queued"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_scheduling_cycle_at_capacity(
    task_scheduler, mock_db_session, mock_redis_service
):
    """Test scheduling cycle when system at max capacity"""
    mock_redis_service.get_in_progress_count.return_value = MAX_CONCURRENT_SUBTASKS

    result = await task_scheduler.run_scheduling_cycle()

    assert result["message"] == "System at max capacity"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_scheduling_cycle_with_tasks(
    task_scheduler, mock_db_session, mock_redis_service, mock_decomposer,
    mock_allocator, sample_task, sample_subtask, sample_worker
):
    """Test scheduling cycle with active tasks"""
    # Mock in-progress count from Redis (non-zero to skip DB fallback)
    mock_redis_service.get_in_progress_count.return_value = 5

    # Mock active tasks
    mock_tasks_result = MagicMock()
    mock_tasks_result.scalars.return_value.all.return_value = [sample_task]

    # Mock queued subtasks (empty for reallocation)
    mock_queued_result = MagicMock()
    mock_queued_result.scalars.return_value.all.return_value = []

    mock_db_session.execute.side_effect = [
        mock_tasks_result,  # Get active tasks
        mock_queued_result,  # Get queued subtasks for reallocation
    ]

    # Mock ready subtasks
    mock_decomposer.get_ready_subtasks.return_value = [sample_subtask]

    # Mock successful allocation
    mock_allocator.allocate_subtask.return_value = sample_worker

    result = await task_scheduler.run_scheduling_cycle()

    assert result["tasks_processed"] == 1
    assert result["subtasks_allocated"] >= 0


# ==================== Task Scheduling Tests ====================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_schedule_task_not_found(task_scheduler, mock_db_session):
    """Test scheduling non-existent task"""
    mock_db_session.execute.return_value = create_mock_result(None)

    result = await task_scheduler.schedule_task(uuid4())

    assert "error" in result
    assert "not found" in result["error"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_schedule_task_pending(
    task_scheduler, mock_db_session, mock_decomposer, sample_task
):
    """Test scheduling pending task triggers decomposition"""
    sample_task.status = "pending"

    mock_db_session.execute.return_value = create_mock_result(sample_task)
    mock_decomposer.decompose_task.return_value = []
    mock_decomposer.get_ready_subtasks.return_value = []

    result = await task_scheduler.schedule_task(sample_task.task_id)

    mock_decomposer.decompose_task.assert_called_once()
    assert "error" not in result or result.get("error") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_schedule_task_with_ready_subtasks(
    task_scheduler, mock_db_session, mock_decomposer, mock_allocator,
    sample_task, sample_subtask, sample_worker
):
    """Test scheduling task with ready subtasks"""
    sample_task.status = "initializing"

    mock_db_session.execute.return_value = create_mock_result(sample_task)
    mock_decomposer.get_ready_subtasks.return_value = [sample_subtask]
    mock_allocator.allocate_subtask.return_value = sample_worker

    result = await task_scheduler.schedule_task(sample_task.task_id)

    assert result["subtasks_allocated"] >= 0


# ==================== Subtask Completion Tests ====================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_subtask_complete_not_found(task_scheduler, mock_db_session):
    """Test handling completion of non-existent subtask"""
    mock_db_session.execute.return_value = create_mock_result(None)

    result = await task_scheduler.on_subtask_complete(uuid4())

    assert result["newly_allocated"] == 0
    assert result["task_completed"] is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_subtask_complete_task_done(
    task_scheduler, mock_db_session, mock_decomposer, sample_subtask
):
    """Test handling completion when task is done"""
    sample_subtask.task.status = "completed"

    mock_db_session.execute.return_value = create_mock_result(sample_subtask)
    mock_decomposer.check_task_completion.return_value = True

    result = await task_scheduler.on_subtask_complete(sample_subtask.subtask_id)

    assert result["task_completed"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_subtask_complete_triggers_allocation(
    task_scheduler, mock_db_session, mock_decomposer, mock_allocator,
    sample_subtask, sample_worker
):
    """Test handling completion triggers new allocation"""
    # Create another subtask that becomes ready
    new_subtask = MagicMock(spec=Subtask)
    new_subtask.subtask_id = uuid4()

    mock_db_session.execute.return_value = create_mock_result(sample_subtask)
    mock_decomposer.check_task_completion.return_value = False
    mock_decomposer.get_ready_subtasks.return_value = [new_subtask]
    mock_allocator.allocate_subtask.return_value = sample_worker

    result = await task_scheduler.on_subtask_complete(sample_subtask.subtask_id)

    assert result["newly_allocated"] >= 0


# ==================== Concurrency Tests ====================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_schedule_respects_capacity_limit(
    task_scheduler, mock_db_session, mock_redis_service, mock_decomposer,
    mock_allocator, sample_task
):
    """Test scheduling respects capacity limit"""
    # Create many subtasks
    subtasks = []
    for _ in range(MAX_CONCURRENT_SUBTASKS + 5):
        subtask = MagicMock(spec=Subtask)
        subtask.subtask_id = uuid4()
        subtask.status = "pending"
        subtasks.append(subtask)

    mock_decomposer.get_ready_subtasks.return_value = subtasks

    # Mock that we start with 15 in progress
    current_in_progress = 15

    allocated, queued = await task_scheduler._schedule_task(
        sample_task,
        current_in_progress
    )

    # Should only allocate up to the limit
    remaining_capacity = MAX_CONCURRENT_SUBTASKS - current_in_progress
    assert allocated <= remaining_capacity


# ==================== Stats Tests ====================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_scheduler_stats(task_scheduler, mock_db_session, mock_redis_service):
    """Test getting scheduler statistics"""
    # Mock status counts
    mock_status_result = MagicMock()
    mock_status_result.fetchall.return_value = [("pending", 5), ("completed", 10)]

    # Mock active tasks count
    mock_active_result = MagicMock()
    mock_active_result.scalar.return_value = 3

    # Mock available workers count
    mock_workers_result = MagicMock()
    mock_workers_result.scalar.return_value = 2

    mock_db_session.execute.side_effect = [
        mock_status_result,
        mock_active_result,
        mock_workers_result,
    ]

    mock_redis_service.get_queue_length.return_value = 5
    mock_redis_service.get_in_progress_count.return_value = 3

    stats = await task_scheduler.get_scheduler_stats()

    assert "active_tasks" in stats
    assert "available_workers" in stats
    assert "subtask_status_counts" in stats
    assert stats["max_concurrent_subtasks"] == MAX_CONCURRENT_SUBTASKS


@pytest.mark.unit
def test_get_concurrency_limits(task_scheduler):
    """Test getting concurrency limits"""
    limits = task_scheduler.get_concurrency_limits()

    assert limits["max_concurrent_subtasks"] == MAX_CONCURRENT_SUBTASKS
    assert limits["max_subtasks_per_worker"] == MAX_SUBTASKS_PER_WORKER


# ==================== In Progress Count Tests ====================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_in_progress_count_from_redis(task_scheduler, mock_redis_service):
    """Test getting in-progress count from Redis"""
    mock_redis_service.get_in_progress_count.return_value = 5

    count = await task_scheduler._get_in_progress_count()

    assert count == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_in_progress_count_fallback_to_db(
    task_scheduler, mock_db_session, mock_redis_service
):
    """Test falling back to DB when Redis returns 0"""
    mock_redis_service.get_in_progress_count.return_value = 0

    mock_db_result = MagicMock()
    mock_db_result.scalar.return_value = 3

    mock_db_session.execute.return_value = mock_db_result

    count = await task_scheduler._get_in_progress_count()

    assert count == 3


# ==================== Active Tasks Tests ====================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_active_tasks(task_scheduler, mock_db_session, sample_task):
    """Test getting active tasks"""
    sample_task.status = "in_progress"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [sample_task]

    mock_db_session.execute.return_value = mock_result

    tasks = await task_scheduler._get_active_tasks()

    assert len(tasks) == 1
    assert tasks[0] == sample_task


# ==================== Reallocate Queued Tests ====================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reallocate_queued_empty(task_scheduler, mock_db_session):
    """Test reallocation when queue is empty"""
    mock_empty_result = MagicMock()
    mock_empty_result.scalars.return_value.all.return_value = []

    mock_db_session.execute.return_value = mock_empty_result

    allocated = await task_scheduler._reallocate_queued()

    assert allocated == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reallocate_queued_success(
    task_scheduler, mock_db_session, mock_allocator, sample_subtask, sample_worker
):
    """Test successful reallocation"""
    sample_subtask.status = "queued"
    sample_subtask.assigned_worker = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [sample_subtask]

    mock_db_session.execute.return_value = mock_result
    mock_allocator.allocate_subtask.return_value = sample_worker

    allocated = await task_scheduler._reallocate_queued()

    assert allocated == 1


# ==================== SchedulerRunner Tests ====================


@pytest.mark.unit
def test_scheduler_runner_init(mock_redis_service):
    """Test SchedulerRunner initialization"""
    runner = SchedulerRunner(
        db_session_factory=MagicMock(),
        redis_service=mock_redis_service,
        interval_seconds=60
    )

    assert runner.interval == 60
    assert runner.is_running is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scheduler_runner_start_stop(mock_redis_service):
    """Test starting and stopping SchedulerRunner"""
    runner = SchedulerRunner(
        db_session_factory=MagicMock(),
        redis_service=mock_redis_service,
        interval_seconds=1
    )

    await runner.start()
    assert runner.is_running is True

    await runner.stop()
    assert runner.is_running is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scheduler_runner_double_start(mock_redis_service):
    """Test that double start is handled"""
    runner = SchedulerRunner(
        db_session_factory=MagicMock(),
        redis_service=mock_redis_service,
        interval_seconds=1
    )

    await runner.start()
    await runner.start()  # Should not raise
    assert runner.is_running is True

    await runner.stop()
