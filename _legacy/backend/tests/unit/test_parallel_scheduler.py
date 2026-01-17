"""
Unit tests for TaskScheduler parallel execution features

Tests the parallel execution coordinator including:
- Identifying parallelizable subtasks
- Coordinating parallel execution by levels
- Tracking parallel task status
- Aggregating results
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime

from src.services.task_scheduler import TaskScheduler
from src.models.task import Task
from src.models.subtask import Subtask


@pytest_asyncio.fixture
async def sample_task_with_dag(db_session):
    """
    Create a task with DAG subtasks for parallel testing.

    DAG structure:
    Level 0: [A, B] - No dependencies, can run in parallel
    Level 1: [C] - Depends on A
    Level 2: [D] - Depends on B and C
    Level 3: [E, F] - E depends on D, F depends on D, can run in parallel
    """
    task = Task(
        description="Test parallel execution",
        status="in_progress",
        progress=0,
        checkpoint_frequency="medium",
        privacy_level="normal"
    )
    db_session.add(task)
    await db_session.flush()

    # Level 0: No dependencies
    subtask_a = Subtask(
        task_id=task.task_id,
        name="Subtask A",
        description="First independent task",
        status="pending",
        subtask_type="code_generation",
        dependencies=[],
        complexity=2,
        priority=5
    )
    subtask_b = Subtask(
        task_id=task.task_id,
        name="Subtask B",
        description="Second independent task",
        status="pending",
        subtask_type="code_generation",
        dependencies=[],
        complexity=2,
        priority=5
    )
    db_session.add_all([subtask_a, subtask_b])
    await db_session.flush()

    # Level 1: Depends on A
    subtask_c = Subtask(
        task_id=task.task_id,
        name="Subtask C",
        description="Depends on A",
        status="pending",
        subtask_type="code_generation",
        dependencies=[str(subtask_a.subtask_id)],
        complexity=2,
        priority=5
    )
    db_session.add(subtask_c)
    await db_session.flush()

    # Level 2: Depends on B and C
    subtask_d = Subtask(
        task_id=task.task_id,
        name="Subtask D",
        description="Depends on B and C",
        status="pending",
        subtask_type="code_generation",
        dependencies=[str(subtask_b.subtask_id), str(subtask_c.subtask_id)],
        complexity=3,
        priority=5
    )
    db_session.add(subtask_d)
    await db_session.flush()

    # Level 3: Both depend on D, can run in parallel
    subtask_e = Subtask(
        task_id=task.task_id,
        name="Subtask E",
        description="Depends on D",
        status="pending",
        subtask_type="code_generation",
        dependencies=[str(subtask_d.subtask_id)],
        complexity=2,
        priority=5
    )
    subtask_f = Subtask(
        task_id=task.task_id,
        name="Subtask F",
        description="Depends on D",
        status="pending",
        subtask_type="code_generation",
        dependencies=[str(subtask_d.subtask_id)],
        complexity=2,
        priority=5
    )
    db_session.add_all([subtask_e, subtask_f])
    await db_session.commit()

    return task, {
        "a": subtask_a,
        "b": subtask_b,
        "c": subtask_c,
        "d": subtask_d,
        "e": subtask_e,
        "f": subtask_f
    }


@pytest.mark.asyncio
class TestParallelizableSubtasks:
    """Test identification of parallelizable subtasks"""

    async def test_identify_parallelizable_subtasks(
        self,
        db_session,
        mock_redis_service,
        sample_task_with_dag
    ):
        """Test identifying parallelizable subtasks grouped by level"""
        task, subtasks = sample_task_with_dag

        scheduler = TaskScheduler(db_session, mock_redis_service)

        levels = await scheduler.identify_parallelizable_subtasks(task.task_id)

        # Should have 4 levels
        assert len(levels) == 4

        # Level 0: A and B (no dependencies)
        assert len(levels[0]) == 2
        level0_names = {s.name for s in levels[0]}
        assert level0_names == {"Subtask A", "Subtask B"}

        # Level 1: C (depends on A)
        assert len(levels[1]) == 1
        assert levels[1][0].name == "Subtask C"

        # Level 2: D (depends on B and C)
        assert len(levels[2]) == 1
        assert levels[2][0].name == "Subtask D"

        # Level 3: E and F (both depend on D, can run in parallel)
        assert len(levels[3]) == 2
        level3_names = {s.name for s in levels[3]}
        assert level3_names == {"Subtask E", "Subtask F"}

    async def test_identify_parallelizable_empty_task(self, db_session, mock_redis_service):
        """Test with task that has no subtasks"""
        task = Task(
            description="Empty task",
            status="in_progress"
        )
        db_session.add(task)
        await db_session.commit()

        scheduler = TaskScheduler(db_session, mock_redis_service)

        levels = await scheduler.identify_parallelizable_subtasks(task.task_id)

        assert len(levels) == 0

    async def test_identify_parallelizable_all_independent(self, db_session, mock_redis_service):
        """Test with all independent subtasks (max parallelism)"""
        task = Task(
            description="All parallel task",
            status="in_progress"
        )
        db_session.add(task)
        await db_session.flush()

        # Create 5 independent subtasks
        for i in range(5):
            subtask = Subtask(
                task_id=task.task_id,
                name=f"Subtask {i}",
                description=f"Independent task {i}",
                status="pending",
                subtask_type="code_generation",
                dependencies=[]
            )
            db_session.add(subtask)

        await db_session.commit()

        scheduler = TaskScheduler(db_session, mock_redis_service)

        levels = await scheduler.identify_parallelizable_subtasks(task.task_id)

        # All subtasks should be in level 0
        assert len(levels) == 1
        assert len(levels[0]) == 5


@pytest.mark.asyncio
class TestParallelExecutionStats:
    """Test parallel execution statistics"""

    async def test_get_parallel_execution_stats(
        self,
        db_session,
        mock_redis_service,
        sample_task_with_dag
    ):
        """Test getting parallel execution statistics"""
        task, subtasks = sample_task_with_dag

        scheduler = TaskScheduler(db_session, mock_redis_service)

        stats = await scheduler.get_parallel_execution_stats(task.task_id)

        assert stats["task_id"] == str(task.task_id)
        assert stats["parallel_levels"] == 4
        assert len(stats["subtasks_per_level"]) == 4
        assert stats["max_parallelism"] == 2  # Max 2 subtasks in level 0 and level 3
        assert stats["total_subtasks"] == 6

    async def test_parallel_stats_linear_dag(self, db_session, mock_redis_service):
        """Test stats for linear DAG (no parallelism)"""
        task = Task(
            description="Linear task",
            status="in_progress"
        )
        db_session.add(task)
        await db_session.flush()

        # Create linear chain: A -> B -> C
        prev_id = None
        for i in range(3):
            subtask = Subtask(
                task_id=task.task_id,
                name=f"Subtask {i}",
                description=f"Task {i}",
                status="pending",
                subtask_type="code_generation",
                dependencies=[prev_id] if prev_id else []
            )
            db_session.add(subtask)
            await db_session.flush()
            prev_id = str(subtask.subtask_id)

        await db_session.commit()

        scheduler = TaskScheduler(db_session, mock_redis_service)

        stats = await scheduler.get_parallel_execution_stats(task.task_id)

        assert stats["parallel_levels"] == 3
        assert stats["max_parallelism"] == 1  # No parallelism
        assert stats["total_subtasks"] == 3


@pytest.mark.asyncio
class TestParallelCoordination:
    """Test parallel execution coordination"""

    async def test_coordinate_parallel_execution_structure(
        self,
        db_session,
        mock_redis_service,
        sample_task_with_dag
    ):
        """Test that coordination creates proper structure (without actual execution)"""
        task, subtasks = sample_task_with_dag

        scheduler = TaskScheduler(db_session, mock_redis_service)

        # Just test the levels are identified correctly
        # Actual allocation would require workers
        levels = await scheduler.identify_parallelizable_subtasks(task.task_id)

        assert len(levels) == 4

        # Verify that subtasks in each level have correct dependencies
        # Level 0 should have no dependencies
        for subtask in levels[0]:
            assert len(subtask.dependencies or []) == 0

        # Level 1 subtasks should only depend on level 0
        level0_ids = {str(s.subtask_id) for s in levels[0]}
        for subtask in levels[1]:
            deps = set(subtask.dependencies or [])
            assert deps.issubset(level0_ids)

    async def test_parallel_level_execution_ready_only(self, db_session, mock_redis_service):
        """Test that parallel level only processes ready subtasks"""
        task = Task(
            description="Test task",
            status="in_progress"
        )
        db_session.add(task)
        await db_session.flush()

        # Create subtasks with different statuses
        pending = Subtask(
            task_id=task.task_id,
            name="Pending",
            description="Ready",
            status="pending",
            subtask_type="code_generation"
        )
        completed = Subtask(
            task_id=task.task_id,
            name="Completed",
            description="Already done",
            status="completed",
            subtask_type="code_generation"
        )
        db_session.add_all([pending, completed])
        await db_session.commit()

        scheduler = TaskScheduler(db_session, mock_redis_service)

        # Get levels
        levels = await scheduler.identify_parallelizable_subtasks(task.task_id)

        # Both should be in level 0, but only pending should be processed
        assert len(levels[0]) == 2
        ready_subtasks = [s for s in levels[0] if s.status == "pending"]
        assert len(ready_subtasks) == 1


@pytest.mark.asyncio
class TestUpdateTaskProgress:
    """Test task progress updates during parallel execution"""

    async def test_update_task_progress_all_completed(self, db_session, mock_redis_service):
        """Test task progress when all subtasks completed"""
        task = Task(
            description="Test task",
            status="in_progress",
            progress=0
        )
        db_session.add(task)
        await db_session.flush()

        # Create completed subtasks
        for i in range(5):
            subtask = Subtask(
                task_id=task.task_id,
                name=f"Subtask {i}",
                description=f"Task {i}",
                status="completed",
                subtask_type="code_generation"
            )
            db_session.add(subtask)

        await db_session.commit()
        await db_session.refresh(task)

        scheduler = TaskScheduler(db_session, mock_redis_service)

        await scheduler._update_task_progress_from_coordination(task.task_id)

        await db_session.refresh(task)
        assert task.progress == 100
        assert task.status == "completed"
        assert task.completed_at is not None

    async def test_update_task_progress_partial(self, db_session, mock_redis_service):
        """Test task progress with partial completion"""
        task = Task(
            description="Test task",
            status="in_progress",
            progress=0
        )
        db_session.add(task)
        await db_session.flush()

        # Create mix of completed and pending
        for i in range(3):
            subtask = Subtask(
                task_id=task.task_id,
                name=f"Completed {i}",
                description="Done",
                status="completed",
                subtask_type="code_generation"
            )
            db_session.add(subtask)

        for i in range(2):
            subtask = Subtask(
                task_id=task.task_id,
                name=f"Pending {i}",
                description="Not done",
                status="pending",
                subtask_type="code_generation"
            )
            db_session.add(subtask)

        await db_session.commit()

        scheduler = TaskScheduler(db_session, mock_redis_service)

        await scheduler._update_task_progress_from_coordination(task.task_id)

        await db_session.refresh(task)
        assert task.progress == 60  # 3/5 = 60%
        assert task.status == "in_progress"

    async def test_update_task_progress_all_failed(self, db_session, mock_redis_service):
        """Test task status when all subtasks failed"""
        task = Task(
            description="Test task",
            status="in_progress",
            progress=0
        )
        db_session.add(task)
        await db_session.flush()

        # Create failed subtasks
        for i in range(3):
            subtask = Subtask(
                task_id=task.task_id,
                name=f"Subtask {i}",
                description="Failed",
                status="failed",
                subtask_type="code_generation"
            )
            db_session.add(subtask)

        await db_session.commit()

        scheduler = TaskScheduler(db_session, mock_redis_service)

        await scheduler._update_task_progress_from_coordination(task.task_id)

        await db_session.refresh(task)
        assert task.status == "failed"
        assert task.completed_at is not None
