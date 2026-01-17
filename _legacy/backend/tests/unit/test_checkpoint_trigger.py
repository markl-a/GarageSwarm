"""
Unit tests for Checkpoint Trigger Service

Tests automatic checkpoint triggering based on:
- Low evaluation scores
- Errors during subtask execution
- Periodic subtask completion
- Correction cycle limits
- Timeout handling
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4, UUID

from src.services.checkpoint_trigger import (
    CheckpointTrigger,
    CheckpointTriggerConfig,
)
from src.services.checkpoint_service import CheckpointService
from src.services.redis_service import RedisService
from src.schemas.checkpoint import CheckpointTriggerReason
from src.models.task import Task
from src.models.subtask import Subtask
from src.models.checkpoint import Checkpoint
from src.models.evaluation import Evaluation
from src.models.correction import Correction


@pytest.fixture
def mock_redis_service():
    """Mock Redis service"""
    return AsyncMock(spec=RedisService)


@pytest.fixture
def mock_checkpoint_service():
    """Mock checkpoint service"""
    service = AsyncMock(spec=CheckpointService)
    service.should_trigger_checkpoint = AsyncMock(return_value=True)
    service.create_checkpoint = AsyncMock()
    return service


@pytest.fixture
def trigger_config():
    """Default trigger configuration"""
    return CheckpointTriggerConfig(
        evaluation_threshold=7.0,
        subtask_completion_interval=5,
        max_correction_cycles=3,
        timeout_hours=24,
        enable_error_trigger=True,
        enable_evaluation_trigger=True,
        enable_periodic_trigger=True,
        enable_timeout_trigger=True,
    )


@pytest_asyncio.fixture
async def checkpoint_trigger(
    db_session, mock_redis_service, mock_checkpoint_service, trigger_config
):
    """Create CheckpointTrigger instance with mocks"""
    trigger = CheckpointTrigger(
        db=db_session,
        redis_service=mock_redis_service,
        checkpoint_service=mock_checkpoint_service,
        config=trigger_config,
    )
    return trigger


@pytest_asyncio.fixture
async def sample_task(db_session):
    """Create a sample task for testing"""
    task = Task(
        description="Test task for checkpoint triggers",
        status="in_progress",
        progress=50,
        started_at=datetime.utcnow(),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


class TestCheckpointTriggerConfig:
    """Test CheckpointTriggerConfig"""

    def test_default_config(self):
        """Test default configuration values"""
        config = CheckpointTriggerConfig()

        assert config.evaluation_threshold == 7.0
        assert config.subtask_completion_interval == 5
        assert config.max_correction_cycles == 3
        assert config.timeout_hours == 24
        assert config.enable_error_trigger is True
        assert config.enable_evaluation_trigger is True
        assert config.enable_periodic_trigger is True
        assert config.enable_timeout_trigger is True

    def test_custom_config(self):
        """Test custom configuration values"""
        config = CheckpointTriggerConfig(
            evaluation_threshold=6.0,
            subtask_completion_interval=10,
            max_correction_cycles=5,
            timeout_hours=48,
            enable_error_trigger=False,
        )

        assert config.evaluation_threshold == 6.0
        assert config.subtask_completion_interval == 10
        assert config.max_correction_cycles == 5
        assert config.timeout_hours == 48
        assert config.enable_error_trigger is False


class TestErrorTrigger:
    """Test error-based checkpoint triggering"""

    async def test_error_trigger_activated(
        self, checkpoint_trigger, sample_task, mock_checkpoint_service
    ):
        """Test checkpoint triggered on error"""
        # Create mock checkpoint
        mock_checkpoint = Checkpoint(
            checkpoint_id=uuid4(),
            task_id=sample_task.task_id,
            trigger_reason=CheckpointTriggerReason.REVIEW_ISSUES_FOUND.value,
            status="pending_review",
        )
        mock_checkpoint_service.create_checkpoint.return_value = mock_checkpoint

        # Trigger with error
        result = await checkpoint_trigger.check_and_trigger(
            task_id=sample_task.task_id,
            error_occurred=True,
        )

        assert result is not None
        assert isinstance(result, Checkpoint)
        mock_checkpoint_service.create_checkpoint.assert_called_once()

    async def test_error_trigger_disabled(
        self, db_session, sample_task, mock_redis_service, mock_checkpoint_service
    ):
        """Test error trigger when disabled"""
        config = CheckpointTriggerConfig(enable_error_trigger=False)
        trigger = CheckpointTrigger(
            db=db_session,
            redis_service=mock_redis_service,
            checkpoint_service=mock_checkpoint_service,
            config=config,
        )

        result = await trigger.check_and_trigger(
            task_id=sample_task.task_id,
            error_occurred=True,
        )

        # Should not trigger checkpoint
        assert result is None


class TestEvaluationTrigger:
    """Test evaluation score-based checkpoint triggering"""

    async def test_low_evaluation_score_trigger(
        self, checkpoint_trigger, sample_task, mock_checkpoint_service
    ):
        """Test checkpoint triggered on low evaluation score"""
        mock_checkpoint = Checkpoint(
            checkpoint_id=uuid4(),
            task_id=sample_task.task_id,
            trigger_reason=CheckpointTriggerReason.LOW_EVALUATION_SCORE.value,
            status="pending_review",
        )
        mock_checkpoint_service.create_checkpoint.return_value = mock_checkpoint

        # Trigger with low score
        result = await checkpoint_trigger.check_and_trigger(
            task_id=sample_task.task_id,
            evaluation_score=5.5,  # Below threshold of 7.0
        )

        assert result is not None
        mock_checkpoint_service.create_checkpoint.assert_called_once()

    async def test_high_evaluation_score_no_trigger(
        self, checkpoint_trigger, sample_task
    ):
        """Test no checkpoint triggered on high evaluation score"""
        result = await checkpoint_trigger.check_and_trigger(
            task_id=sample_task.task_id,
            evaluation_score=8.5,  # Above threshold
        )

        # Should not trigger checkpoint
        assert result is None

    async def test_evaluation_trigger_disabled(
        self, db_session, sample_task, mock_redis_service, mock_checkpoint_service
    ):
        """Test evaluation trigger when disabled"""
        config = CheckpointTriggerConfig(enable_evaluation_trigger=False)
        trigger = CheckpointTrigger(
            db=db_session,
            redis_service=mock_redis_service,
            checkpoint_service=mock_checkpoint_service,
            config=config,
        )

        result = await trigger.check_and_trigger(
            task_id=sample_task.task_id,
            evaluation_score=5.0,
        )

        assert result is None


class TestPeriodicTrigger:
    """Test periodic checkpoint triggering based on subtask completion"""

    async def test_periodic_trigger_activated(
        self, checkpoint_trigger, sample_task, db_session, mock_checkpoint_service
    ):
        """Test checkpoint triggered after N subtasks completed"""
        # Create 5 completed subtasks (triggers at interval of 5)
        for i in range(5):
            subtask = Subtask(
                task_id=sample_task.task_id,
                name=f"Subtask {i+1}",
                description=f"Test subtask {i+1}",
                status="completed",
                progress=100,
            )
            db_session.add(subtask)
        await db_session.commit()

        mock_checkpoint = Checkpoint(
            checkpoint_id=uuid4(),
            task_id=sample_task.task_id,
            trigger_reason=CheckpointTriggerReason.CODE_GENERATION_COMPLETE.value,
            status="pending_review",
        )
        mock_checkpoint_service.create_checkpoint.return_value = mock_checkpoint

        # Create a subtask to trigger check
        subtask_id = uuid4()
        result = await checkpoint_trigger.check_and_trigger(
            task_id=sample_task.task_id,
            subtask_id=subtask_id,
        )

        assert result is not None

    async def test_periodic_trigger_not_reached(
        self, checkpoint_trigger, sample_task, db_session
    ):
        """Test no checkpoint triggered before interval reached"""
        # Create only 3 completed subtasks (interval is 5)
        for i in range(3):
            subtask = Subtask(
                task_id=sample_task.task_id,
                name=f"Subtask {i+1}",
                description=f"Test subtask {i+1}",
                status="completed",
                progress=100,
            )
            db_session.add(subtask)
        await db_session.commit()

        result = await checkpoint_trigger.check_and_trigger(
            task_id=sample_task.task_id,
            subtask_id=uuid4(),
        )

        assert result is None


class TestTimeoutTrigger:
    """Test timeout-based checkpoint triggering"""

    async def test_timeout_trigger_activated(
        self, checkpoint_trigger, db_session, mock_checkpoint_service
    ):
        """Test checkpoint triggered on timeout"""
        # Create task that started 25 hours ago (timeout is 24 hours)
        task = Task(
            description="Timed out task",
            status="in_progress",
            started_at=datetime.utcnow() - timedelta(hours=25),
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        mock_checkpoint = Checkpoint(
            checkpoint_id=uuid4(),
            task_id=task.task_id,
            trigger_reason=CheckpointTriggerReason.MANUAL_TRIGGER.value,
            status="pending_review",
        )
        mock_checkpoint_service.create_checkpoint.return_value = mock_checkpoint

        result = await checkpoint_trigger.check_and_trigger(task_id=task.task_id)

        assert result is not None

    async def test_timeout_not_reached(
        self, checkpoint_trigger, db_session
    ):
        """Test no timeout trigger when within time limit"""
        # Create task that started 10 hours ago
        task = Task(
            description="Recent task",
            status="in_progress",
            started_at=datetime.utcnow() - timedelta(hours=10),
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        result = await checkpoint_trigger.check_and_trigger(task_id=task.task_id)

        assert result is None


class TestCycleLimitTrigger:
    """Test correction cycle limit triggering"""

    async def test_get_cycle_count(
        self, checkpoint_trigger, sample_task, db_session
    ):
        """Test getting correction cycle count for a subtask"""
        # Create subtask
        subtask = Subtask(
            task_id=sample_task.task_id,
            name="Test subtask",
            description="Test",
            status="in_progress",
        )
        db_session.add(subtask)
        await db_session.flush()

        # Create checkpoint
        checkpoint = Checkpoint(
            task_id=sample_task.task_id,
            trigger_reason=CheckpointTriggerReason.REVIEW_ISSUES_FOUND.value,
            status="pending_review",
        )
        db_session.add(checkpoint)
        await db_session.flush()

        # Create 2 corrections
        for i in range(2):
            correction = Correction(
                checkpoint_id=checkpoint.checkpoint_id,
                subtask_id=subtask.subtask_id,
                correction_type="code_fix",
                description=f"Fix {i+1}",
                result="pending",
            )
            db_session.add(correction)
        await db_session.commit()

        # Get cycle count
        count = await checkpoint_trigger.get_cycle_count(
            task_id=sample_task.task_id,
            subtask_id=subtask.subtask_id,
        )

        assert count == 2

    async def test_is_at_cycle_limit(
        self, checkpoint_trigger, sample_task, db_session
    ):
        """Test checking if subtask is at cycle limit"""
        # Create subtask
        subtask = Subtask(
            task_id=sample_task.task_id,
            name="Test subtask",
            description="Test",
            status="in_progress",
        )
        db_session.add(subtask)
        await db_session.flush()

        # Create checkpoint
        checkpoint = Checkpoint(
            task_id=sample_task.task_id,
            trigger_reason=CheckpointTriggerReason.REVIEW_ISSUES_FOUND.value,
            status="pending_review",
        )
        db_session.add(checkpoint)
        await db_session.flush()

        # Create 3 corrections (at limit)
        for i in range(3):
            correction = Correction(
                checkpoint_id=checkpoint.checkpoint_id,
                subtask_id=subtask.subtask_id,
                correction_type="code_fix",
                description=f"Fix {i+1}",
                result="pending",
            )
            db_session.add(correction)
        await db_session.commit()

        # Check if at limit
        at_limit = await checkpoint_trigger.is_at_cycle_limit(
            task_id=sample_task.task_id,
            subtask_id=subtask.subtask_id,
        )

        assert at_limit is True


class TestTaskCheckpointStats:
    """Test checkpoint statistics retrieval"""

    async def test_get_task_checkpoint_stats(
        self, checkpoint_trigger, sample_task, db_session
    ):
        """Test getting checkpoint statistics for a task"""
        # Create checkpoint
        checkpoint = Checkpoint(
            task_id=sample_task.task_id,
            trigger_reason=CheckpointTriggerReason.CODE_GENERATION_COMPLETE.value,
            status="approved",
        )
        db_session.add(checkpoint)
        await db_session.commit()

        # Get stats
        stats = await checkpoint_trigger.get_task_checkpoint_stats(
            task_id=sample_task.task_id
        )

        assert "task_id" in stats
        assert stats["checkpoint_count"] == 1
        assert stats["elapsed_hours"] is not None
        assert stats["timeout_threshold_hours"] == 24
        assert "timeout_approaching" in stats
        assert "timeout_exceeded" in stats

    async def test_get_stats_nonexistent_task(self, checkpoint_trigger):
        """Test getting stats for non-existent task"""
        fake_task_id = uuid4()
        stats = await checkpoint_trigger.get_task_checkpoint_stats(
            task_id=fake_task_id
        )

        assert "error" in stats
        assert stats["error"] == "Task not found"


class TestTaskStatusChecks:
    """Test checkpoint triggering with different task statuses"""

    async def test_no_trigger_for_completed_task(
        self, checkpoint_trigger, db_session
    ):
        """Test no checkpoint triggered for completed task"""
        task = Task(
            description="Completed task",
            status="completed",
            progress=100,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        result = await checkpoint_trigger.check_and_trigger(
            task_id=task.task_id,
            error_occurred=True,
        )

        assert result is None

    async def test_no_trigger_for_failed_task(
        self, checkpoint_trigger, db_session
    ):
        """Test no checkpoint triggered for failed task"""
        task = Task(
            description="Failed task",
            status="failed",
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        result = await checkpoint_trigger.check_and_trigger(
            task_id=task.task_id,
            error_occurred=True,
        )

        assert result is None

    async def test_no_trigger_for_checkpoint_status(
        self, checkpoint_trigger, db_session
    ):
        """Test no checkpoint triggered for task already at checkpoint"""
        task = Task(
            description="Task at checkpoint",
            status="checkpoint",
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        result = await checkpoint_trigger.check_and_trigger(
            task_id=task.task_id,
            error_occurred=True,
        )

        assert result is None


class TestTriggerWithNonexistentTask:
    """Test checkpoint triggering with non-existent task"""

    async def test_trigger_nonexistent_task(self, checkpoint_trigger):
        """Test checkpoint trigger with non-existent task returns None"""
        fake_task_id = uuid4()

        result = await checkpoint_trigger.check_and_trigger(
            task_id=fake_task_id,
            error_occurred=True,
        )

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
