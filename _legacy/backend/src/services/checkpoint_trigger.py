"""
Checkpoint Trigger Service

Automatic checkpoint triggering based on configurable rules:
- Low evaluation scores
- Errors/exceptions during subtask execution
- Periodic N subtasks completion
- Cycle count tracking and limits
- Timeout handling
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import structlog

from src.models.task import Task
from src.models.subtask import Subtask
from src.models.evaluation import Evaluation
from src.models.checkpoint import Checkpoint
from src.models.correction import Correction
from src.schemas.checkpoint import CheckpointTriggerReason
from src.schemas.subtask import SubtaskStatus
from src.services.checkpoint_service import CheckpointService
from src.services.redis_service import RedisService
from src.config import settings

logger = structlog.get_logger()


class CheckpointTriggerConfig:
    """Configuration for checkpoint trigger rules"""

    def __init__(
        self,
        evaluation_threshold: float = 7.0,
        subtask_completion_interval: int = 5,
        max_correction_cycles: int = 3,
        timeout_hours: int = 24,
        enable_error_trigger: bool = True,
        enable_evaluation_trigger: bool = True,
        enable_periodic_trigger: bool = True,
        enable_timeout_trigger: bool = True
    ):
        """
        Initialize checkpoint trigger configuration

        Args:
            evaluation_threshold: Trigger checkpoint if evaluation score < this (default: 7.0)
            subtask_completion_interval: Trigger after N subtasks complete (default: 5)
            max_correction_cycles: Maximum correction cycles before escalation (default: 3)
            timeout_hours: Hours before timeout triggers escalation (default: 24)
            enable_error_trigger: Enable auto-trigger on errors (default: True)
            enable_evaluation_trigger: Enable auto-trigger on low scores (default: True)
            enable_periodic_trigger: Enable periodic triggers (default: True)
            enable_timeout_trigger: Enable timeout triggers (default: True)
        """
        self.evaluation_threshold = evaluation_threshold
        self.subtask_completion_interval = subtask_completion_interval
        self.max_correction_cycles = max_correction_cycles
        self.timeout_hours = timeout_hours
        self.enable_error_trigger = enable_error_trigger
        self.enable_evaluation_trigger = enable_evaluation_trigger
        self.enable_periodic_trigger = enable_periodic_trigger
        self.enable_timeout_trigger = enable_timeout_trigger


class CheckpointTrigger:
    """Service for automatic checkpoint triggering"""

    def __init__(
        self,
        db: AsyncSession,
        redis_service: RedisService,
        checkpoint_service: CheckpointService,
        config: Optional[CheckpointTriggerConfig] = None
    ):
        """
        Initialize CheckpointTrigger

        Args:
            db: Database session
            redis_service: Redis service instance
            checkpoint_service: Checkpoint service instance
            config: Trigger configuration (uses defaults from settings if None)
        """
        self.db = db
        self.redis = redis_service
        self.checkpoint_service = checkpoint_service
        self.config = config or CheckpointTriggerConfig(
            evaluation_threshold=settings.EVALUATION_SCORE_THRESHOLD,
            subtask_completion_interval=settings.CHECKPOINT_SUBTASK_INTERVAL,
            max_correction_cycles=settings.CHECKPOINT_MAX_CORRECTION_CYCLES,
            timeout_hours=settings.CHECKPOINT_TIMEOUT_HOURS,
            enable_error_trigger=settings.CHECKPOINT_ENABLE_ERROR_TRIGGER,
            enable_evaluation_trigger=settings.CHECKPOINT_ENABLE_EVALUATION_TRIGGER,
            enable_periodic_trigger=settings.CHECKPOINT_ENABLE_PERIODIC_TRIGGER,
            enable_timeout_trigger=settings.CHECKPOINT_ENABLE_TIMEOUT_TRIGGER
        )

    async def check_and_trigger(
        self,
        task_id: UUID,
        subtask_id: Optional[UUID] = None,
        evaluation_score: Optional[float] = None,
        error_occurred: bool = False
    ) -> Optional[Checkpoint]:
        """
        Check if checkpoint should be triggered and create if needed

        Args:
            task_id: Task UUID
            subtask_id: Subtask UUID (if checking after subtask completion)
            evaluation_score: Evaluation score if available
            error_occurred: Whether an error occurred during execution

        Returns:
            Checkpoint if triggered, None otherwise
        """
        logger.info(
            "Checking checkpoint trigger",
            task_id=str(task_id),
            subtask_id=str(subtask_id) if subtask_id else None,
            evaluation_score=evaluation_score,
            error_occurred=error_occurred
        )

        try:
            # Get task
            result = await self.db.execute(
                select(Task).where(Task.task_id == task_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                logger.warning("Task not found for checkpoint check", task_id=str(task_id))
                return None

            # Skip if task is already at checkpoint or completed
            if task.status in ("checkpoint", "completed", "failed", "cancelled"):
                logger.info(
                    "Task not eligible for checkpoint",
                    task_id=str(task_id),
                    status=task.status
                )
                return None

            # Check for timeout (24 hours by default)
            if self.config.enable_timeout_trigger:
                timeout_checkpoint = await self._check_timeout_trigger(task)
                if timeout_checkpoint:
                    return timeout_checkpoint

            # Check for error trigger
            if self.config.enable_error_trigger and error_occurred:
                logger.info("Error trigger activated", task_id=str(task_id))
                return await self._trigger_checkpoint(
                    task_id,
                    CheckpointTriggerReason.REVIEW_ISSUES_FOUND,
                    {
                        "reason": "error_during_execution",
                        "subtask_id": str(subtask_id) if subtask_id else None,
                        "auto_triggered": True
                    }
                )

            # Check for low evaluation score trigger
            if self.config.enable_evaluation_trigger and evaluation_score is not None:
                if evaluation_score < self.config.evaluation_threshold:
                    logger.info(
                        "Low evaluation score trigger activated",
                        task_id=str(task_id),
                        score=evaluation_score,
                        threshold=self.config.evaluation_threshold
                    )
                    return await self._trigger_checkpoint(
                        task_id,
                        CheckpointTriggerReason.LOW_EVALUATION_SCORE,
                        {
                            "reason": "low_evaluation_score",
                            "score": evaluation_score,
                            "threshold": self.config.evaluation_threshold,
                            "subtask_id": str(subtask_id) if subtask_id else None,
                            "auto_triggered": True
                        }
                    )

            # Check for periodic trigger (every N subtasks)
            if self.config.enable_periodic_trigger and subtask_id:
                periodic_checkpoint = await self._check_periodic_trigger(task)
                if periodic_checkpoint:
                    return periodic_checkpoint

            # Check for excessive correction cycles
            cycle_checkpoint = await self._check_correction_cycle_limit(task)
            if cycle_checkpoint:
                return cycle_checkpoint

            logger.info("No checkpoint trigger activated", task_id=str(task_id))
            return None

        except Exception as e:
            logger.error(
                "Checkpoint trigger check failed",
                task_id=str(task_id),
                error=str(e)
            )
            return None

    async def _check_periodic_trigger(self, task: Task) -> Optional[Checkpoint]:
        """
        Check if periodic checkpoint should be triggered

        Triggers after every N completed subtasks based on configuration

        Args:
            task: Task instance

        Returns:
            Checkpoint if triggered, None otherwise
        """
        # Count completed subtasks
        result = await self.db.execute(
            select(func.count(Subtask.subtask_id))
            .where(Subtask.task_id == task.task_id)
            .where(Subtask.status == SubtaskStatus.COMPLETED.value)
        )
        completed_count = result.scalar() or 0

        # Get count of completed subtasks at last checkpoint
        last_checkpoint_result = await self.db.execute(
            select(Checkpoint)
            .where(Checkpoint.task_id == task.task_id)
            .order_by(Checkpoint.triggered_at.desc())
            .limit(1)
        )
        last_checkpoint = last_checkpoint_result.scalar_one_or_none()

        last_checkpoint_count = 0
        if last_checkpoint and last_checkpoint.subtasks_completed:
            last_checkpoint_count = len(last_checkpoint.subtasks_completed)

        # Check if we've completed N more subtasks since last checkpoint
        subtasks_since_last = completed_count - last_checkpoint_count

        if subtasks_since_last >= self.config.subtask_completion_interval:
            logger.info(
                "Periodic trigger activated",
                task_id=str(task.task_id),
                completed_since_last=subtasks_since_last,
                interval=self.config.subtask_completion_interval
            )
            return await self._trigger_checkpoint(
                task.task_id,
                CheckpointTriggerReason.CODE_GENERATION_COMPLETE,
                {
                    "reason": "periodic_completion",
                    "completed_count": completed_count,
                    "subtasks_since_last": subtasks_since_last,
                    "interval": self.config.subtask_completion_interval,
                    "auto_triggered": True
                }
            )

        return None

    async def _check_timeout_trigger(self, task: Task) -> Optional[Checkpoint]:
        """
        Check if timeout checkpoint should be triggered

        Triggers if task has been in progress for more than configured hours

        Args:
            task: Task instance

        Returns:
            Checkpoint if triggered, None otherwise
        """
        if not task.started_at:
            return None

        elapsed = datetime.utcnow() - task.started_at
        timeout_threshold = timedelta(hours=self.config.timeout_hours)

        if elapsed > timeout_threshold:
            logger.warning(
                "Timeout trigger activated",
                task_id=str(task.task_id),
                elapsed_hours=elapsed.total_seconds() / 3600,
                threshold_hours=self.config.timeout_hours
            )
            return await self._trigger_checkpoint(
                task.task_id,
                CheckpointTriggerReason.MANUAL_TRIGGER,
                {
                    "reason": "timeout_escalation",
                    "elapsed_hours": elapsed.total_seconds() / 3600,
                    "threshold_hours": self.config.timeout_hours,
                    "auto_triggered": True,
                    "requires_attention": True
                }
            )

        return None

    async def _check_correction_cycle_limit(self, task: Task) -> Optional[Checkpoint]:
        """
        Check if correction cycle limit has been reached

        Triggers if a subtask has exceeded max correction cycles

        Args:
            task: Task instance

        Returns:
            Checkpoint if triggered, None otherwise
        """
        # Get all corrections for this task through checkpoints
        result = await self.db.execute(
            select(Correction, func.count(Correction.correction_id).label('retry_count'))
            .join(Checkpoint, Correction.checkpoint_id == Checkpoint.checkpoint_id)
            .where(Checkpoint.task_id == task.task_id)
            .where(Correction.result.in_(["pending", "failed"]))
            .group_by(Correction.subtask_id, Correction.correction_id)
            .having(func.count(Correction.correction_id) >= self.config.max_correction_cycles)
        )
        excessive_corrections = result.all()

        if excessive_corrections:
            subtask_ids = [str(corr[0].subtask_id) for corr in excessive_corrections]
            logger.warning(
                "Correction cycle limit exceeded",
                task_id=str(task.task_id),
                subtask_ids=subtask_ids,
                max_cycles=self.config.max_correction_cycles
            )
            return await self._trigger_checkpoint(
                task.task_id,
                CheckpointTriggerReason.REVIEW_ISSUES_FOUND,
                {
                    "reason": "excessive_correction_cycles",
                    "subtasks_with_issues": subtask_ids,
                    "max_cycles": self.config.max_correction_cycles,
                    "auto_triggered": True,
                    "requires_attention": True
                }
            )

        return None

    async def _trigger_checkpoint(
        self,
        task_id: UUID,
        trigger_reason: CheckpointTriggerReason,
        context_info: Dict[str, Any]
    ) -> Optional[Checkpoint]:
        """
        Trigger checkpoint creation

        Args:
            task_id: Task UUID
            trigger_reason: Reason for checkpoint trigger
            context_info: Context information about the trigger

        Returns:
            Created checkpoint or None if creation failed
        """
        try:
            # Check if checkpoint should actually be triggered
            should_trigger = await self.checkpoint_service.should_trigger_checkpoint(
                task_id,
                trigger_reason,
                context_info.get("score")
            )

            if not should_trigger:
                logger.info(
                    "Checkpoint trigger declined by service",
                    task_id=str(task_id),
                    trigger_reason=trigger_reason.value
                )
                return None

            # Create checkpoint
            checkpoint = await self.checkpoint_service.create_checkpoint(
                task_id,
                trigger_reason,
                context_info
            )

            logger.info(
                "Checkpoint auto-triggered successfully",
                checkpoint_id=str(checkpoint.checkpoint_id),
                task_id=str(task_id),
                trigger_reason=trigger_reason.value
            )

            return checkpoint

        except Exception as e:
            logger.error(
                "Failed to trigger checkpoint",
                task_id=str(task_id),
                trigger_reason=trigger_reason.value,
                error=str(e)
            )
            return None

    async def get_cycle_count(self, task_id: UUID, subtask_id: UUID) -> int:
        """
        Get correction cycle count for a subtask

        Args:
            task_id: Task UUID
            subtask_id: Subtask UUID

        Returns:
            Number of correction cycles for the subtask
        """
        result = await self.db.execute(
            select(func.count(Correction.correction_id))
            .join(Checkpoint, Correction.checkpoint_id == Checkpoint.checkpoint_id)
            .where(Checkpoint.task_id == task_id)
            .where(Correction.subtask_id == subtask_id)
        )
        return result.scalar() or 0

    async def is_at_cycle_limit(self, task_id: UUID, subtask_id: UUID) -> bool:
        """
        Check if subtask is at correction cycle limit

        Args:
            task_id: Task UUID
            subtask_id: Subtask UUID

        Returns:
            True if at or above cycle limit, False otherwise
        """
        cycle_count = await self.get_cycle_count(task_id, subtask_id)
        return cycle_count >= self.config.max_correction_cycles

    async def get_task_checkpoint_stats(self, task_id: UUID) -> Dict[str, Any]:
        """
        Get checkpoint statistics for a task

        Args:
            task_id: Task UUID

        Returns:
            Dict with checkpoint statistics
        """
        # Get task
        task_result = await self.db.execute(
            select(Task).where(Task.task_id == task_id)
        )
        task = task_result.scalar_one_or_none()

        if not task:
            return {"error": "Task not found"}

        # Get checkpoint count
        checkpoint_result = await self.db.execute(
            select(func.count(Checkpoint.checkpoint_id))
            .where(Checkpoint.task_id == task_id)
        )
        checkpoint_count = checkpoint_result.scalar() or 0

        # Get correction count
        correction_result = await self.db.execute(
            select(func.count(Correction.correction_id))
            .join(Checkpoint, Correction.checkpoint_id == Checkpoint.checkpoint_id)
            .where(Checkpoint.task_id == task_id)
        )
        correction_count = correction_result.scalar() or 0

        # Get time elapsed
        elapsed_hours = None
        if task.started_at:
            elapsed = datetime.utcnow() - task.started_at
            elapsed_hours = elapsed.total_seconds() / 3600

        # Get timeout status
        timeout_approaching = False
        timeout_exceeded = False
        if elapsed_hours:
            timeout_approaching = elapsed_hours > (self.config.timeout_hours * 0.8)
            timeout_exceeded = elapsed_hours > self.config.timeout_hours

        return {
            "task_id": str(task_id),
            "checkpoint_count": checkpoint_count,
            "correction_count": correction_count,
            "elapsed_hours": elapsed_hours,
            "timeout_threshold_hours": self.config.timeout_hours,
            "timeout_approaching": timeout_approaching,
            "timeout_exceeded": timeout_exceeded,
            "max_correction_cycles": self.config.max_correction_cycles,
            "evaluation_threshold": self.config.evaluation_threshold,
            "subtask_completion_interval": self.config.subtask_completion_interval
        }
