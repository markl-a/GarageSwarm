"""Unit tests for TaskService"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from src.services.task_service import TaskService
from src.models.task import Task
from src.models.subtask import Subtask
from src.schemas.task import TaskStatus


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
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_redis_service():
    """Mock Redis service"""
    redis = AsyncMock()
    redis.set_task_status = AsyncMock()
    redis.set_task_progress = AsyncMock()
    redis.add_task_to_queue = AsyncMock()
    redis.remove_task_from_queue = AsyncMock()
    redis.get_task_status = AsyncMock(return_value="pending")
    redis.get_task_progress = AsyncMock(return_value=0)
    return redis


@pytest.fixture
def task_service(mock_db_session, mock_redis_service):
    """Create TaskService instance with mocks"""
    return TaskService(mock_db_session, mock_redis_service)


@pytest.fixture
def sample_task():
    """Sample task instance"""
    task = MagicMock(spec=Task)
    task.task_id = uuid4()
    task.description = "Test task description for unit testing purposes"
    task.status = TaskStatus.PENDING.value
    task.progress = 0
    task.checkpoint_frequency = "medium"
    task.privacy_level = "normal"
    task.tool_preferences = ["claude_code"]
    task.task_metadata = {"task_type": "develop_feature", "requirements": None}
    task.created_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()
    task.started_at = None
    task.completed_at = None
    task.subtasks = []
    return task


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_task(task_service, mock_db_session, mock_redis_service):
    """Test creating a new task"""
    # Arrange
    description = "Create a Python function for testing"
    task_type = "develop_feature"
    checkpoint_frequency = "medium"
    privacy_level = "normal"

    # Act
    task = await task_service.create_task(
        description=description,
        task_type=task_type,
        checkpoint_frequency=checkpoint_frequency,
        privacy_level=privacy_level
    )

    # Assert
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()
    mock_redis_service.set_task_status.assert_called_once()
    mock_redis_service.add_task_to_queue.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_task_with_requirements(task_service, mock_db_session, mock_redis_service):
    """Test creating a task with requirements"""
    # Arrange
    description = "Create a function with specific requirements"
    requirements = {"language": "python", "include_tests": True}
    tool_preferences = ["claude_code", "gemini_cli"]

    # Act
    task = await task_service.create_task(
        description=description,
        requirements=requirements,
        tool_preferences=tool_preferences
    )

    # Assert
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_task_rollback_on_error(task_service, mock_db_session, mock_redis_service):
    """Test that task creation rolls back on error"""
    # Arrange
    mock_db_session.commit.side_effect = Exception("Database error")

    # Act & Assert
    with pytest.raises(Exception, match="Database error"):
        await task_service.create_task(
            description="This task should fail"
        )

    mock_db_session.rollback.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task(task_service, mock_db_session, sample_task):
    """Test getting task by ID"""
    # Arrange
    task_id = sample_task.task_id
    mock_db_session.execute.return_value = create_mock_result(sample_task)

    # Act
    task = await task_service.get_task(task_id)

    # Assert
    assert task == sample_task
    assert task.task_id == task_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_not_found(task_service, mock_db_session):
    """Test getting non-existent task"""
    # Arrange
    task_id = uuid4()
    mock_db_session.execute.return_value = create_mock_result(None)

    # Act
    task = await task_service.get_task(task_id)

    # Assert
    assert task is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tasks(task_service, mock_db_session, sample_task):
    """Test listing tasks"""
    # Arrange
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 5

    mock_tasks_result = MagicMock()
    mock_tasks_result.scalars.return_value.all.return_value = [sample_task]

    mock_db_session.execute.side_effect = [mock_count_result, mock_tasks_result]

    # Act
    tasks, total = await task_service.list_tasks(limit=50, offset=0)

    # Assert
    assert total == 5
    assert len(tasks) == 1
    assert tasks[0] == sample_task


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_tasks_with_status_filter(task_service, mock_db_session, sample_task):
    """Test listing tasks with status filter"""
    # Arrange
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 2

    mock_tasks_result = MagicMock()
    mock_tasks_result.scalars.return_value.all.return_value = [sample_task]

    mock_db_session.execute.side_effect = [mock_count_result, mock_tasks_result]

    # Act
    tasks, total = await task_service.list_tasks(
        status=TaskStatus.PENDING.value,
        limit=50,
        offset=0
    )

    # Assert
    assert total == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_task_status(task_service, mock_db_session, mock_redis_service, sample_task):
    """Test updating task status"""
    # Arrange
    task_id = sample_task.task_id
    new_status = TaskStatus.IN_PROGRESS.value
    progress = 25

    mock_db_session.execute.return_value = create_mock_result(sample_task)

    # Act
    result = await task_service.update_task_status(
        task_id=task_id,
        status=new_status,
        progress=progress
    )

    # Assert
    assert result is True
    assert sample_task.status == new_status
    assert sample_task.progress == progress
    mock_db_session.commit.assert_called_once()
    mock_redis_service.set_task_status.assert_called_once()
    mock_redis_service.set_task_progress.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_task_status_sets_started_at(task_service, mock_db_session, mock_redis_service, sample_task):
    """Test that started_at is set when status changes to in_progress"""
    # Arrange
    task_id = sample_task.task_id
    sample_task.started_at = None

    mock_db_session.execute.return_value = create_mock_result(sample_task)

    # Act
    await task_service.update_task_status(
        task_id=task_id,
        status=TaskStatus.IN_PROGRESS.value
    )

    # Assert
    assert sample_task.started_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_task_status_sets_completed_at(task_service, mock_db_session, mock_redis_service, sample_task):
    """Test that completed_at is set when status changes to completed"""
    # Arrange
    task_id = sample_task.task_id
    sample_task.completed_at = None

    mock_db_session.execute.return_value = create_mock_result(sample_task)

    # Act
    await task_service.update_task_status(
        task_id=task_id,
        status=TaskStatus.COMPLETED.value
    )

    # Assert
    assert sample_task.completed_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_task_status_not_found(task_service, mock_db_session):
    """Test updating non-existent task status"""
    # Arrange
    task_id = uuid4()
    mock_db_session.execute.return_value = create_mock_result(None)

    # Act & Assert
    with pytest.raises(ValueError, match="Task .* not found"):
        await task_service.update_task_status(
            task_id=task_id,
            status=TaskStatus.IN_PROGRESS.value
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_task(task_service, mock_db_session, mock_redis_service, sample_task):
    """Test cancelling a task"""
    # Arrange
    task_id = sample_task.task_id
    sample_task.status = TaskStatus.PENDING.value

    mock_db_session.execute.return_value = create_mock_result(sample_task)

    # Act
    result = await task_service.cancel_task(task_id)

    # Assert
    assert result is True
    assert sample_task.status == TaskStatus.CANCELLED.value
    assert sample_task.completed_at is not None
    mock_db_session.commit.assert_called_once()
    mock_redis_service.set_task_status.assert_called_once()
    mock_redis_service.remove_task_from_queue.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_task_not_found(task_service, mock_db_session):
    """Test cancelling non-existent task"""
    # Arrange
    task_id = uuid4()
    mock_db_session.execute.return_value = create_mock_result(None)

    # Act & Assert
    with pytest.raises(ValueError, match="Task .* not found"):
        await task_service.cancel_task(task_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_already_completed_task(task_service, mock_db_session, sample_task):
    """Test that already completed task cannot be cancelled"""
    # Arrange
    task_id = sample_task.task_id
    sample_task.status = TaskStatus.COMPLETED.value

    mock_db_session.execute.return_value = create_mock_result(sample_task)

    # Act & Assert
    with pytest.raises(ValueError, match="already completed"):
        await task_service.cancel_task(task_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_already_cancelled_task(task_service, mock_db_session, sample_task):
    """Test that already cancelled task cannot be cancelled again"""
    # Arrange
    task_id = sample_task.task_id
    sample_task.status = TaskStatus.CANCELLED.value

    mock_db_session.execute.return_value = create_mock_result(sample_task)

    # Act & Assert
    with pytest.raises(ValueError, match="already cancelled"):
        await task_service.cancel_task(task_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_progress(task_service, mock_redis_service):
    """Test getting task progress from Redis"""
    # Arrange
    task_id = uuid4()
    mock_redis_service.get_task_status.return_value = "in_progress"
    mock_redis_service.get_task_progress.return_value = 50

    # Act
    progress_data = await task_service.get_task_progress(task_id)

    # Assert
    assert progress_data["task_id"] == str(task_id)
    assert progress_data["status"] == "in_progress"
    assert progress_data["progress"] == 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_progress_no_data(task_service, mock_redis_service):
    """Test getting task progress when no data in Redis"""
    # Arrange
    task_id = uuid4()
    mock_redis_service.get_task_status.return_value = None
    mock_redis_service.get_task_progress.return_value = None

    # Act
    progress_data = await task_service.get_task_progress(task_id)

    # Assert
    assert progress_data["task_id"] == str(task_id)
    assert progress_data["status"] is None
    assert progress_data["progress"] is None


# ==================== Real-time Status Tests ====================


@pytest.fixture
def sample_evaluation():
    """Sample evaluation for testing"""
    from src.models.evaluation import Evaluation
    eval_mock = MagicMock(spec=Evaluation)
    eval_mock.evaluation_id = uuid4()
    eval_mock.overall_score = 8.5
    eval_mock.code_quality = 8.0
    eval_mock.completeness = 9.0
    eval_mock.security = 8.5
    eval_mock.architecture = 8.0
    eval_mock.testability = 8.5
    eval_mock.evaluated_at = datetime.utcnow()
    return eval_mock


@pytest.fixture
def sample_subtask_with_eval(sample_task, sample_evaluation):
    """Sample subtask with evaluation"""
    subtask = MagicMock(spec=Subtask)
    subtask.subtask_id = uuid4()
    subtask.task_id = sample_task.task_id
    subtask.name = "Code Generation"
    subtask.status = "completed"
    subtask.progress = 100
    subtask.assigned_worker = uuid4()
    subtask.assigned_tool = "claude_code"
    subtask.evaluations = [sample_evaluation]
    return subtask


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_with_realtime_status(
    task_service, mock_db_session, mock_redis_service, sample_task, sample_subtask_with_eval
):
    """Test getting task with real-time status from Redis"""
    # Arrange
    sample_task.subtasks = [sample_subtask_with_eval]

    mock_db_session.execute.return_value = create_mock_result(sample_task)
    mock_redis_service.get_task_status.return_value = "in_progress"
    mock_redis_service.get_task_progress.return_value = 50
    mock_redis_service.get_multiple_subtask_statuses = AsyncMock(return_value={
        str(sample_subtask_with_eval.subtask_id): "completed"
    })

    # Act
    result = await task_service.get_task_with_realtime_status(sample_task.task_id)

    # Assert
    assert result is not None
    assert result["task_id"] == sample_task.task_id
    assert result["status"] == "in_progress"  # From Redis
    assert result["progress"] == 50  # From Redis
    assert len(result["subtasks"]) == 1
    assert result["subtasks"][0]["evaluation"] is not None
    assert result["subtasks"][0]["evaluation"]["overall_score"] == 8.5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_with_realtime_status_not_found(task_service, mock_db_session):
    """Test getting non-existent task with real-time status"""
    # Arrange
    task_id = uuid4()
    mock_db_session.execute.return_value = create_mock_result(None)

    # Act
    result = await task_service.get_task_with_realtime_status(task_id)

    # Assert
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_with_realtime_status_uses_db_when_redis_empty(
    task_service, mock_db_session, mock_redis_service, sample_task
):
    """Test that DB data is used when Redis has no data"""
    # Arrange
    sample_task.subtasks = []
    sample_task.status = "pending"
    sample_task.progress = 0

    mock_db_session.execute.return_value = create_mock_result(sample_task)
    mock_redis_service.get_task_status.return_value = None  # No Redis data
    mock_redis_service.get_task_progress.return_value = None  # No Redis data
    mock_redis_service.get_multiple_subtask_statuses = AsyncMock(return_value={})

    # Act
    result = await task_service.get_task_with_realtime_status(sample_task.task_id)

    # Assert
    assert result is not None
    assert result["status"] == "pending"  # From DB
    assert result["progress"] == 0  # From DB


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_with_realtime_status_subtask_without_eval(
    task_service, mock_db_session, mock_redis_service, sample_task
):
    """Test task with subtask that has no evaluation"""
    # Arrange
    subtask_no_eval = MagicMock(spec=Subtask)
    subtask_no_eval.subtask_id = uuid4()
    subtask_no_eval.name = "Pending Task"
    subtask_no_eval.status = "pending"
    subtask_no_eval.progress = 0
    subtask_no_eval.assigned_worker = None
    subtask_no_eval.assigned_tool = None
    subtask_no_eval.evaluations = []

    sample_task.subtasks = [subtask_no_eval]

    mock_db_session.execute.return_value = create_mock_result(sample_task)
    mock_redis_service.get_task_status.return_value = "initializing"
    mock_redis_service.get_task_progress.return_value = 0
    mock_redis_service.get_multiple_subtask_statuses = AsyncMock(return_value={})

    # Act
    result = await task_service.get_task_with_realtime_status(sample_task.task_id)

    # Assert
    assert result is not None
    assert len(result["subtasks"]) == 1
    assert result["subtasks"][0]["evaluation"] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_subtask_status(
    task_service, mock_db_session, mock_redis_service
):
    """Test updating subtask status"""
    # Arrange
    subtask = MagicMock(spec=Subtask)
    subtask.subtask_id = uuid4()
    subtask.task_id = uuid4()
    subtask.started_at = None
    subtask.completed_at = None

    # Use PropertyMock for attributes that will be set
    type(subtask).status = "pending"
    type(subtask).progress = 0

    # Create mock for the _update_task_progress_from_subtasks call
    mock_subtasks_result = MagicMock()
    mock_subtasks_result.scalars.return_value.all.return_value = [subtask]

    mock_task = MagicMock()
    mock_task.progress = 0

    mock_task_result = MagicMock()
    mock_task_result.scalar_one_or_none.return_value = mock_task

    mock_db_session.execute.side_effect = [
        create_mock_result(subtask),  # First call for getting subtask
        mock_subtasks_result,  # For _update_task_progress_from_subtasks
        mock_task_result  # For getting task
    ]
    mock_redis_service.set_subtask_status = AsyncMock()
    mock_redis_service.set_subtask_progress = AsyncMock()
    mock_redis_service.set_task_progress = AsyncMock()

    # Act
    result = await task_service.update_subtask_status(
        subtask_id=subtask.subtask_id,
        status="in_progress",
        progress=25
    )

    # Assert
    assert result is True
    mock_redis_service.set_subtask_status.assert_called_once()
    mock_redis_service.set_subtask_progress.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_subtask_status_not_found(task_service, mock_db_session):
    """Test updating non-existent subtask status"""
    # Arrange
    subtask_id = uuid4()
    mock_db_session.execute.return_value = create_mock_result(None)

    # Act & Assert
    with pytest.raises(ValueError, match="Subtask .* not found"):
        await task_service.update_subtask_status(
            subtask_id=subtask_id,
            status="in_progress"
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_subtask_status_sets_completed_at(
    task_service, mock_db_session, mock_redis_service
):
    """Test that completed_at is set when subtask completes"""
    # Arrange
    subtask = MagicMock(spec=Subtask)
    subtask.subtask_id = uuid4()
    subtask.task_id = uuid4()
    subtask.started_at = datetime.utcnow()
    subtask.completed_at = None

    # Create mock for the _update_task_progress_from_subtasks call
    mock_subtasks_result = MagicMock()
    mock_subtasks_result.scalars.return_value.all.return_value = [subtask]

    mock_task = MagicMock()
    mock_task.progress = 0

    mock_task_result = MagicMock()
    mock_task_result.scalar_one_or_none.return_value = mock_task

    mock_db_session.execute.side_effect = [
        create_mock_result(subtask),  # First call for getting subtask
        mock_subtasks_result,  # For _update_task_progress_from_subtasks
        mock_task_result  # For getting task
    ]
    mock_redis_service.set_subtask_status = AsyncMock()
    mock_redis_service.set_subtask_progress = AsyncMock()
    mock_redis_service.set_task_progress = AsyncMock()

    # Act
    await task_service.update_subtask_status(
        subtask_id=subtask.subtask_id,
        status="completed",
        progress=100
    )

    # Assert
    assert subtask.completed_at is not None
