"""Unit tests for TaskDecomposer"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from src.services.task_decomposer import TaskDecomposer, SUBTASK_DEFINITIONS
from src.models.task import Task
from src.models.subtask import Subtask


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
    redis.set_task_status = AsyncMock()
    redis.set_task_progress = AsyncMock()
    return redis


@pytest.fixture
def task_decomposer(mock_db_session, mock_redis_service):
    """Create TaskDecomposer instance with mocks"""
    return TaskDecomposer(mock_db_session, mock_redis_service)


@pytest.fixture
def sample_task():
    """Sample task instance"""
    task = MagicMock(spec=Task)
    task.task_id = uuid4()
    task.description = "Create a Python function that calculates fibonacci numbers"
    task.status = "pending"
    task.progress = 0
    task.task_metadata = {"task_type": "develop_feature"}
    task.created_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()
    return task


@pytest.mark.unit
def test_get_supported_task_types(task_decomposer):
    """Test getting supported task types"""
    types = task_decomposer.get_supported_task_types()

    assert "develop_feature" in types
    assert "bug_fix" in types
    assert "refactor" in types
    assert "code_review" in types
    assert "documentation" in types
    assert "testing" in types


@pytest.mark.unit
def test_get_subtask_template_develop_feature(task_decomposer):
    """Test getting subtask template for develop_feature"""
    template = task_decomposer.get_subtask_template("develop_feature")

    assert len(template) == 4
    assert template[0]["name"] == "Code Generation"
    assert template[1]["name"] == "Code Review"
    assert template[2]["name"] == "Test Generation"
    assert template[3]["name"] == "Documentation"


@pytest.mark.unit
def test_get_subtask_template_bug_fix(task_decomposer):
    """Test getting subtask template for bug_fix"""
    template = task_decomposer.get_subtask_template("bug_fix")

    assert len(template) == 3
    assert template[0]["name"] == "Bug Analysis"
    assert template[1]["name"] == "Fix Implementation"
    assert template[2]["name"] == "Regression Testing"


@pytest.mark.unit
def test_get_subtask_template_unknown_type(task_decomposer):
    """Test that unknown task type falls back to develop_feature"""
    template = task_decomposer.get_subtask_template("unknown_type")

    # Should return develop_feature template as fallback
    assert len(template) == 4
    assert template[0]["name"] == "Code Generation"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decompose_task_not_found(task_decomposer, mock_db_session):
    """Test decomposing non-existent task"""
    task_id = uuid4()
    mock_db_session.execute.return_value = create_mock_result(None)

    with pytest.raises(ValueError, match="not found"):
        await task_decomposer.decompose_task(task_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decompose_task_already_decomposed(task_decomposer, mock_db_session, sample_task):
    """Test that already decomposed task raises error"""
    task_id = sample_task.task_id

    # First call returns task, second call returns existing subtask
    mock_db_session.execute.side_effect = [
        create_mock_result(sample_task),
        create_mock_result(MagicMock(spec=Subtask))  # Existing subtask
    ]

    with pytest.raises(ValueError, match="already has subtasks"):
        await task_decomposer.decompose_task(task_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decompose_task_success(task_decomposer, mock_db_session, mock_redis_service, sample_task):
    """Test successful task decomposition"""
    task_id = sample_task.task_id

    # First call returns task, second call returns no existing subtasks
    mock_empty_result = MagicMock()
    mock_empty_result.scalars.return_value.first.return_value = None

    mock_db_session.execute.side_effect = [
        create_mock_result(sample_task),  # Get task
        mock_empty_result,  # Check existing subtasks
    ]

    subtasks = await task_decomposer.decompose_task(task_id)

    # Should create 4 subtasks for develop_feature
    assert mock_db_session.add.call_count == 4
    mock_db_session.flush.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_redis_service.set_task_status.assert_called_once_with(task_id, "initializing")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ready_subtasks_no_dependencies(task_decomposer, mock_db_session):
    """Test getting ready subtasks when no dependencies"""
    task_id = uuid4()

    # Create mock subtask with no dependencies
    mock_subtask = MagicMock(spec=Subtask)
    mock_subtask.subtask_id = uuid4()
    mock_subtask.task_id = task_id
    mock_subtask.status = "pending"
    mock_subtask.dependencies = []

    mock_pending_result = MagicMock()
    mock_pending_result.scalars.return_value.all.return_value = [mock_subtask]

    mock_completed_result = MagicMock()
    mock_completed_result.fetchall.return_value = []

    mock_db_session.execute.side_effect = [
        mock_pending_result,  # Pending subtasks
        mock_completed_result,  # Completed subtasks
    ]

    ready = await task_decomposer.get_ready_subtasks(task_id)

    assert len(ready) == 1
    assert ready[0] == mock_subtask


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ready_subtasks_with_unmet_dependencies(task_decomposer, mock_db_session):
    """Test getting ready subtasks when dependencies not met"""
    task_id = uuid4()
    dep_id = uuid4()

    # Create mock subtask with unmet dependency
    mock_subtask = MagicMock(spec=Subtask)
    mock_subtask.subtask_id = uuid4()
    mock_subtask.task_id = task_id
    mock_subtask.status = "pending"
    mock_subtask.dependencies = [str(dep_id)]  # Dependency not completed

    mock_pending_result = MagicMock()
    mock_pending_result.scalars.return_value.all.return_value = [mock_subtask]

    mock_completed_result = MagicMock()
    mock_completed_result.fetchall.return_value = []  # No completed subtasks

    mock_db_session.execute.side_effect = [
        mock_pending_result,
        mock_completed_result,
    ]

    ready = await task_decomposer.get_ready_subtasks(task_id)

    assert len(ready) == 0  # Subtask not ready due to unmet dependency


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ready_subtasks_with_met_dependencies(task_decomposer, mock_db_session):
    """Test getting ready subtasks when dependencies are met"""
    task_id = uuid4()
    dep_id = uuid4()

    # Create mock subtask with met dependency
    mock_subtask = MagicMock(spec=Subtask)
    mock_subtask.subtask_id = uuid4()
    mock_subtask.task_id = task_id
    mock_subtask.status = "pending"
    mock_subtask.dependencies = [str(dep_id)]

    mock_pending_result = MagicMock()
    mock_pending_result.scalars.return_value.all.return_value = [mock_subtask]

    mock_completed_result = MagicMock()
    mock_completed_result.fetchall.return_value = [(dep_id,)]  # Dependency completed

    mock_db_session.execute.side_effect = [
        mock_pending_result,
        mock_completed_result,
    ]

    ready = await task_decomposer.get_ready_subtasks(task_id)

    assert len(ready) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_task_completion_all_completed(task_decomposer, mock_db_session, mock_redis_service, sample_task):
    """Test task completion check when all subtasks completed"""
    task_id = sample_task.task_id

    # Create mock completed subtasks
    mock_subtask1 = MagicMock()
    mock_subtask1.status = "completed"
    mock_subtask2 = MagicMock()
    mock_subtask2.status = "completed"

    mock_subtasks_result = MagicMock()
    mock_subtasks_result.scalars.return_value.all.return_value = [mock_subtask1, mock_subtask2]

    mock_db_session.execute.side_effect = [
        mock_subtasks_result,  # Get all subtasks
        create_mock_result(sample_task),  # Get task
    ]

    is_complete = await task_decomposer.check_task_completion(task_id)

    assert is_complete is True
    assert sample_task.status == "completed"
    mock_redis_service.set_task_status.assert_called_with(task_id, "completed")
    mock_redis_service.set_task_progress.assert_called_with(task_id, 100)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_task_completion_has_failed(task_decomposer, mock_db_session, mock_redis_service, sample_task):
    """Test task completion check when some subtasks failed"""
    task_id = sample_task.task_id

    mock_subtask1 = MagicMock()
    mock_subtask1.status = "completed"
    mock_subtask2 = MagicMock()
    mock_subtask2.status = "failed"

    mock_subtasks_result = MagicMock()
    mock_subtasks_result.scalars.return_value.all.return_value = [mock_subtask1, mock_subtask2]

    mock_db_session.execute.side_effect = [
        mock_subtasks_result,
        create_mock_result(sample_task),
    ]

    is_complete = await task_decomposer.check_task_completion(task_id)

    assert is_complete is True
    assert sample_task.status == "failed"
    mock_redis_service.set_task_status.assert_called_with(task_id, "failed")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_task_completion_still_in_progress(task_decomposer, mock_db_session, mock_redis_service, sample_task):
    """Test task completion check when subtasks still in progress"""
    task_id = sample_task.task_id

    mock_subtask1 = MagicMock()
    mock_subtask1.status = "completed"
    mock_subtask2 = MagicMock()
    mock_subtask2.status = "in_progress"

    mock_subtasks_result = MagicMock()
    mock_subtasks_result.scalars.return_value.all.return_value = [mock_subtask1, mock_subtask2]

    mock_db_session.execute.side_effect = [
        mock_subtasks_result,
        create_mock_result(sample_task),
    ]

    is_complete = await task_decomposer.check_task_completion(task_id)

    assert is_complete is False
    assert sample_task.progress == 50  # 1 of 2 completed


@pytest.mark.unit
def test_enhance_description(task_decomposer):
    """Test description enhancement"""
    base = "Generate code based on requirements"
    task_desc = "Create a function to calculate fibonacci"

    enhanced = task_decomposer._enhance_description(base, task_desc)

    assert base in enhanced
    assert task_desc in enhanced
    assert "Task Context" in enhanced


@pytest.mark.unit
def test_enhance_description_long_context(task_decomposer):
    """Test description enhancement with long context truncation"""
    base = "Generate code"
    task_desc = "x" * 1000  # Long description

    enhanced = task_decomposer._enhance_description(base, task_desc)

    # Should truncate to 500 chars
    assert len(enhanced) < 1100


@pytest.mark.unit
def test_get_task_type_from_metadata(task_decomposer, sample_task):
    """Test extracting task type from metadata"""
    sample_task.task_metadata = {"task_type": "bug_fix"}

    task_type = task_decomposer._get_task_type(sample_task)

    assert task_type == "bug_fix"


@pytest.mark.unit
def test_get_task_type_default(task_decomposer, sample_task):
    """Test default task type when not in metadata"""
    sample_task.task_metadata = None

    task_type = task_decomposer._get_task_type(sample_task)

    assert task_type == "develop_feature"


@pytest.mark.unit
def test_subtask_definitions_have_dependencies():
    """Test that subtask definitions have proper dependency structure"""
    for task_type, subtasks in SUBTASK_DEFINITIONS.items():
        for subtask in subtasks:
            assert "name" in subtask
            assert "description" in subtask
            assert "dependencies" in subtask
            assert isinstance(subtask["dependencies"], list)


@pytest.mark.unit
def test_subtask_definitions_dag_valid():
    """Test that subtask definitions form valid DAGs (no circular dependencies)"""
    for task_type, subtasks in SUBTASK_DEFINITIONS.items():
        names = {s["name"] for s in subtasks}

        for subtask in subtasks:
            for dep in subtask["dependencies"]:
                # All dependencies should reference existing subtasks
                assert dep in names, f"Invalid dependency {dep} in {task_type}"

                # Dependency should come before the subtask in the list
                dep_idx = next(i for i, s in enumerate(subtasks) if s["name"] == dep)
                curr_idx = next(i for i, s in enumerate(subtasks) if s["name"] == subtask["name"])
                assert dep_idx < curr_idx, f"Dependency {dep} should come before {subtask['name']}"
