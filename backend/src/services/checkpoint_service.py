"""
Checkpoint Service

Business logic for checkpoint management, including checkpoint trigger logic,
decision processing, and WebSocket notifications.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
import structlog

from src.models.checkpoint import Checkpoint
from src.models.correction import Correction
from src.models.task import Task
from src.models.subtask import Subtask
from src.models.evaluation import Evaluation
from src.services.redis_service import RedisService
from src.schemas.checkpoint import CheckpointTriggerReason

logger = structlog.get_logger()


# Maximum correction cycles before requiring human intervention
MAX_CORRECTION_CYCLES = 3


class CheckpointService:
    """Service for managing checkpoint operations"""

    def __init__(self, db: AsyncSession, redis_service: RedisService):
        """Initialize CheckpointService

        Args:
            db: Database session
            redis_service: Redis service instance
        """
        self.db = db
        self.redis = redis_service

    async def should_trigger_checkpoint(
        self,
        task_id: UUID,
        trigger_reason: CheckpointTriggerReason,
        evaluation_score: Optional[float] = None
    ) -> bool:
        """Determine if checkpoint should be triggered

        Args:
            task_id: Task UUID
            trigger_reason: Reason for potential checkpoint
            evaluation_score: Evaluation score if applicable

        Returns:
            bool: True if checkpoint should be triggered
        """
        # Get task
        result = await self.db.execute(
            select(Task).where(Task.task_id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            logger.warning("Task not found for checkpoint check", task_id=str(task_id))
            return False

        # Always trigger on manual request
        if trigger_reason == CheckpointTriggerReason.MANUAL_TRIGGER:
            return True

        # Always trigger on review issues
        if trigger_reason == CheckpointTriggerReason.REVIEW_ISSUES_FOUND:
            return True

        # Trigger on low evaluation score (< 7)
        if trigger_reason == CheckpointTriggerReason.LOW_EVALUATION_SCORE:
            if evaluation_score is not None and evaluation_score < 7.0:
                return True
            return False

        # Trigger based on checkpoint frequency and completed subtasks
        if trigger_reason == CheckpointTriggerReason.CODE_GENERATION_COMPLETE:
            # Count completed subtasks
            subtask_result = await self.db.execute(
                select(func.count(Subtask.subtask_id))
                .where(Subtask.task_id == task_id)
                .where(Subtask.status == "completed")
            )
            completed_count = subtask_result.scalar()

            # Count total subtasks
            total_result = await self.db.execute(
                select(func.count(Subtask.subtask_id))
                .where(Subtask.task_id == task_id)
            )
            total_count = total_result.scalar()

            if total_count == 0:
                return False

            # Calculate checkpoint frequency based on setting
            checkpoint_freq = task.checkpoint_frequency
            if checkpoint_freq == "high":
                # Trigger after every subtask
                return True
            elif checkpoint_freq == "medium":
                # Trigger after 25%, 50%, 75%, 100%
                progress_percentage = (completed_count / total_count) * 100
                milestone = int(progress_percentage // 25) * 25
                previous_milestone = int(((completed_count - 1) / total_count) * 100 // 25) * 25
                return milestone > previous_milestone
            elif checkpoint_freq == "low":
                # Trigger at 50% and 100%
                progress_percentage = (completed_count / total_count) * 100
                milestone = int(progress_percentage // 50) * 50
                previous_milestone = int(((completed_count - 1) / total_count) * 100 // 50) * 50
                return milestone > previous_milestone

        return False

    async def create_checkpoint(
        self,
        task_id: UUID,
        trigger_reason: CheckpointTriggerReason,
        context_info: Optional[Dict[str, Any]] = None
    ) -> Checkpoint:
        """Create a new checkpoint

        Args:
            task_id: Task UUID
            trigger_reason: Reason for checkpoint trigger
            context_info: Additional context information

        Returns:
            Checkpoint: Created checkpoint instance

        Raises:
            ValueError: If task not found
        """
        logger.info(
            "Creating checkpoint",
            task_id=str(task_id),
            trigger_reason=trigger_reason.value
        )

        try:
            # Get task
            result = await self.db.execute(
                select(Task).where(Task.task_id == task_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                raise ValueError(f"Task {task_id} not found")

            # Get completed subtasks
            subtasks_result = await self.db.execute(
                select(Subtask.subtask_id)
                .where(Subtask.task_id == task_id)
                .where(Subtask.status == "completed")
            )
            completed_subtask_ids = [str(row[0]) for row in subtasks_result.all()]

            # Add trigger reason to context
            if context_info is None:
                context_info = {}
            context_info["trigger_reason"] = trigger_reason.value

            # Create checkpoint record
            checkpoint = Checkpoint(
                task_id=task_id,
                status="pending_review",
                subtasks_completed=completed_subtask_ids
            )

            self.db.add(checkpoint)
            await self.db.commit()
            await self.db.refresh(checkpoint)

            # Update task status to "checkpoint"
            task.status = "checkpoint"
            await self.db.commit()

            # Update Redis
            await self.redis.set_task_status(task_id, "checkpoint")

            # Notify frontend via WebSocket
            await self._notify_checkpoint_reached(
                checkpoint_id=checkpoint.checkpoint_id,
                task_id=task_id,
                trigger_reason=trigger_reason.value,
                context_info=context_info
            )

            logger.info(
                "Checkpoint created successfully",
                checkpoint_id=str(checkpoint.checkpoint_id),
                task_id=str(task_id)
            )

            return checkpoint

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Checkpoint creation failed",
                task_id=str(task_id),
                error=str(e)
            )
            raise

    async def get_checkpoint(self, checkpoint_id: UUID) -> Optional[Checkpoint]:
        """Get checkpoint by ID with related data

        Args:
            checkpoint_id: Checkpoint UUID

        Returns:
            Optional[Checkpoint]: Checkpoint instance with related data or None
        """
        result = await self.db.execute(
            select(Checkpoint)
            .options(
                selectinload(Checkpoint.task).selectinload(Task.subtasks).selectinload(Subtask.evaluations)
            )
            .where(Checkpoint.checkpoint_id == checkpoint_id)
        )
        return result.scalar_one_or_none()

    async def list_task_checkpoints(
        self,
        task_id: UUID,
        include_details: bool = False
    ) -> List[Checkpoint]:
        """List all checkpoints for a task

        Args:
            task_id: Task UUID
            include_details: Whether to include subtask and evaluation details

        Returns:
            List[Checkpoint]: List of checkpoints ordered by triggered_at desc
        """
        query = select(Checkpoint).where(Checkpoint.task_id == task_id)

        if include_details:
            query = query.options(
                selectinload(Checkpoint.task).selectinload(Task.subtasks).selectinload(Subtask.evaluations)
            )

        query = query.order_by(Checkpoint.triggered_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def process_decision(
        self,
        checkpoint_id: UUID,
        decision: str,
        feedback: Optional[str] = None,
        correction_type: Optional[str] = None,
        reference_files: Optional[List[str]] = None,
        apply_to_future: bool = False
    ) -> Dict[str, Any]:
        """Process user decision on checkpoint

        Args:
            checkpoint_id: Checkpoint UUID
            decision: User decision (accept, correct, reject)
            feedback: User feedback or correction instructions
            correction_type: Type of correction if decision is correct
            reference_files: Reference files for correction
            apply_to_future: Apply correction pattern to future tasks

        Returns:
            Dict with result information

        Raises:
            ValueError: If checkpoint not found or invalid state
        """
        logger.info(
            "Processing checkpoint decision",
            checkpoint_id=str(checkpoint_id),
            decision=decision
        )

        try:
            # Get checkpoint with task
            result = await self.db.execute(
                select(Checkpoint)
                .options(selectinload(Checkpoint.task).selectinload(Task.subtasks))
                .where(Checkpoint.checkpoint_id == checkpoint_id)
            )
            checkpoint = result.scalar_one_or_none()

            if not checkpoint:
                raise ValueError(f"Checkpoint {checkpoint_id} not found")

            if checkpoint.status != "pending_review":
                raise ValueError(f"Checkpoint {checkpoint_id} is not pending review")

            # Update checkpoint with decision
            checkpoint.user_decision = decision
            checkpoint.decision_notes = feedback
            checkpoint.reviewed_at = datetime.utcnow()

            corrections_created = 0
            next_action = ""
            task_status = ""

            if decision == "accept":
                # Accept: Continue to next subtask
                checkpoint.status = "approved"
                checkpoint.task.status = "in_progress"
                task_status = "in_progress"
                next_action = "Task continues with next subtask"

            elif decision == "correct":
                # Correct: Create correction records for completed subtasks
                checkpoint.status = "corrected"
                checkpoint.task.status = "in_progress"
                task_status = "in_progress"

                # Create corrections for subtasks in this checkpoint
                for subtask_id_str in checkpoint.subtasks_completed:
                    try:
                        subtask_id = UUID(subtask_id_str)
                        correction = Correction(
                            checkpoint_id=checkpoint_id,
                            subtask_id=subtask_id,
                            correction_type=correction_type or "other",
                            guidance=feedback or "Please review and correct the output",
                            reference_files=reference_files or [],
                            result="pending",
                            retry_count=0,
                            apply_to_future=apply_to_future
                        )
                        self.db.add(correction)
                        corrections_created += 1

                        # Update subtask status to "correcting"
                        subtask_result = await self.db.execute(
                            select(Subtask).where(Subtask.subtask_id == subtask_id)
                        )
                        subtask = subtask_result.scalar_one_or_none()
                        if subtask:
                            subtask.status = "correcting"
                            await self.redis.set_subtask_status(subtask_id, "correcting")

                    except ValueError:
                        logger.warning("Invalid subtask UUID in checkpoint", subtask_id=subtask_id_str)

                next_action = f"Corrections created for {corrections_created} subtask(s). Task will continue after corrections are applied."

            elif decision == "reject":
                # Reject: Mark task as cancelled
                checkpoint.status = "rejected"
                checkpoint.task.status = "cancelled"
                checkpoint.task.completed_at = datetime.utcnow()
                task_status = "cancelled"
                next_action = "Task cancelled by user"

                # Cancel all pending subtasks
                for subtask in checkpoint.task.subtasks:
                    if subtask.status in ["pending", "queued"]:
                        subtask.status = "cancelled"

            await self.db.commit()

            # Update Redis
            await self.redis.set_task_status(checkpoint.task_id, task_status)

            # Notify via WebSocket
            await self._notify_checkpoint_decision(
                checkpoint_id=checkpoint_id,
                task_id=checkpoint.task_id,
                decision=decision,
                task_status=task_status,
                corrections_created=corrections_created
            )

            logger.info(
                "Checkpoint decision processed",
                checkpoint_id=str(checkpoint_id),
                decision=decision,
                corrections_created=corrections_created
            )

            return {
                "checkpoint_id": checkpoint_id,
                "status": checkpoint.status,
                "task_status": task_status,
                "corrections_created": corrections_created,
                "next_action": next_action
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Checkpoint decision processing failed",
                checkpoint_id=str(checkpoint_id),
                error=str(e)
            )
            raise

    async def get_checkpoint_history(self, task_id: UUID) -> Dict[str, Any]:
        """Get checkpoint history for a task

        Args:
            task_id: Task UUID

        Returns:
            Dict with checkpoints and statistics
        """
        # Get all checkpoints for task
        checkpoints = await self.list_task_checkpoints(task_id, include_details=False)

        # Calculate statistics
        stats = {
            "total": len(checkpoints),
            "approved": sum(1 for c in checkpoints if c.status == "approved"),
            "corrected": sum(1 for c in checkpoints if c.status == "corrected"),
            "rejected": sum(1 for c in checkpoints if c.status == "rejected"),
            "pending": sum(1 for c in checkpoints if c.status == "pending_review")
        }

        return {
            "task_id": task_id,
            "checkpoints": checkpoints,
            "total": len(checkpoints),
            "statistics": stats
        }

    async def get_checkpoint_details(self, checkpoint_id: UUID) -> Optional[Dict[str, Any]]:
        """Get detailed checkpoint information including subtasks and evaluations

        Args:
            checkpoint_id: Checkpoint UUID

        Returns:
            Dict with checkpoint details or None
        """
        checkpoint = await self.get_checkpoint(checkpoint_id)

        if not checkpoint:
            return None

        # Build subtask details
        subtask_details = []
        evaluations = []

        for subtask_id_str in checkpoint.subtasks_completed:
            try:
                subtask_id = UUID(subtask_id_str)
                subtask_result = await self.db.execute(
                    select(Subtask)
                    .options(selectinload(Subtask.evaluations))
                    .where(Subtask.subtask_id == subtask_id)
                )
                subtask = subtask_result.scalar_one_or_none()

                if subtask:
                    subtask_details.append({
                        "subtask_id": subtask.subtask_id,
                        "name": subtask.name,
                        "status": subtask.status,
                        "output": subtask.output,
                        "error": subtask.error
                    })

                    # Add evaluations
                    for evaluation in subtask.evaluations:
                        evaluations.append({
                            "evaluation_id": evaluation.evaluation_id,
                            "subtask_id": evaluation.subtask_id,
                            "overall_score": float(evaluation.overall_score) if evaluation.overall_score else None,
                            "code_quality": float(evaluation.code_quality) if evaluation.code_quality else None,
                            "completeness": float(evaluation.completeness) if evaluation.completeness else None,
                            "security": float(evaluation.security) if evaluation.security else None,
                            "architecture": float(evaluation.architecture) if evaluation.architecture else None,
                            "testability": float(evaluation.testability) if evaluation.testability else None,
                            "details": evaluation.details
                        })

            except ValueError:
                logger.warning("Invalid subtask UUID in checkpoint", subtask_id=subtask_id_str)

        return {
            "checkpoint_id": checkpoint.checkpoint_id,
            "task_id": checkpoint.task_id,
            "status": checkpoint.status,
            "subtasks_completed": checkpoint.subtasks_completed,
            "user_decision": checkpoint.user_decision,
            "decision_notes": checkpoint.decision_notes,
            "triggered_at": checkpoint.triggered_at,
            "reviewed_at": checkpoint.reviewed_at,
            "subtask_details": subtask_details,
            "evaluations": evaluations
        }

    async def _notify_checkpoint_reached(
        self,
        checkpoint_id: UUID,
        task_id: UUID,
        trigger_reason: str,
        context_info: Dict[str, Any]
    ) -> None:
        """Send WebSocket notification when checkpoint is reached

        Args:
            checkpoint_id: Checkpoint UUID
            task_id: Task UUID
            trigger_reason: Reason for checkpoint trigger
            context_info: Additional context
        """
        try:
            event = {
                "type": "checkpoint_reached",
                "checkpoint_id": str(checkpoint_id),
                "task_id": str(task_id),
                "trigger_reason": trigger_reason,
                "context": context_info,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Publish to Redis for WebSocket broadcasting
            await self.redis.publish_event("events:checkpoint", event)

            logger.debug(
                "Checkpoint notification sent",
                checkpoint_id=str(checkpoint_id),
                task_id=str(task_id)
            )

        except Exception as e:
            logger.error(
                "Failed to send checkpoint notification",
                checkpoint_id=str(checkpoint_id),
                error=str(e)
            )

    async def _notify_checkpoint_decision(
        self,
        checkpoint_id: UUID,
        task_id: UUID,
        decision: str,
        task_status: str,
        corrections_created: int
    ) -> None:
        """Send WebSocket notification when checkpoint decision is made

        Args:
            checkpoint_id: Checkpoint UUID
            task_id: Task UUID
            decision: User decision
            task_status: Updated task status
            corrections_created: Number of corrections created
        """
        try:
            event = {
                "type": "checkpoint_decision",
                "checkpoint_id": str(checkpoint_id),
                "task_id": str(task_id),
                "decision": decision,
                "task_status": task_status,
                "corrections_created": corrections_created,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Publish to Redis for WebSocket broadcasting
            await self.redis.publish_event("events:checkpoint", event)

            logger.debug(
                "Checkpoint decision notification sent",
                checkpoint_id=str(checkpoint_id),
                task_id=str(task_id),
                decision=decision
            )

        except Exception as e:
            logger.error(
                "Failed to send checkpoint decision notification",
                checkpoint_id=str(checkpoint_id),
                error=str(e)
            )

    async def get_subtask_correction_count(
        self,
        task_id: UUID,
        subtask_id: UUID
    ) -> int:
        """
        Get the number of corrections for a specific subtask

        Args:
            task_id: Task UUID
            subtask_id: Subtask UUID

        Returns:
            Number of corrections for the subtask
        """
        result = await self.db.execute(
            select(func.count(Correction.correction_id))
            .join(Checkpoint, Correction.checkpoint_id == Checkpoint.checkpoint_id)
            .where(Checkpoint.task_id == task_id)
            .where(Correction.subtask_id == subtask_id)
        )
        return result.scalar() or 0

    async def is_at_correction_limit(
        self,
        task_id: UUID,
        subtask_id: UUID,
        limit: int = MAX_CORRECTION_CYCLES
    ) -> bool:
        """
        Check if a subtask has reached the correction limit

        Args:
            task_id: Task UUID
            subtask_id: Subtask UUID
            limit: Correction limit (default: MAX_CORRECTION_CYCLES)

        Returns:
            True if at or above limit, False otherwise
        """
        count = await self.get_subtask_correction_count(task_id, subtask_id)
        return count >= limit

    async def get_task_elapsed_time(self, task_id: UUID) -> Optional[float]:
        """
        Get elapsed time for a task in hours

        Args:
            task_id: Task UUID

        Returns:
            Elapsed hours or None if task not started
        """
        result = await self.db.execute(
            select(Task).where(Task.task_id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task or not task.started_at:
            return None

        elapsed = datetime.utcnow() - task.started_at
        return elapsed.total_seconds() / 3600

    async def validate_checkpoint_eligibility(
        self,
        task_id: UUID
    ) -> Dict[str, Any]:
        """
        Validate if task is eligible for checkpoint

        Args:
            task_id: Task UUID

        Returns:
            Dict with eligibility status and reasons
        """
        result = await self.db.execute(
            select(Task).where(Task.task_id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            return {
                "eligible": False,
                "reason": "task_not_found"
            }

        # Check if task is in a state that allows checkpoints
        ineligible_statuses = ["checkpoint", "completed", "failed", "cancelled"]
        if task.status in ineligible_statuses:
            return {
                "eligible": False,
                "reason": f"task_status_{task.status}",
                "current_status": task.status
            }

        return {
            "eligible": True,
            "reason": "task_eligible"
        }
