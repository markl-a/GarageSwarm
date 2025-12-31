"""Task Service - Business logic for task management"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
import structlog

from src.models.task import Task
from src.models.subtask import Subtask
from src.services.redis_service import RedisService
from src.schemas.task import TaskStatus, CheckpointFrequency, PrivacyLevel

logger = structlog.get_logger()


class TaskService:
    """Service for managing task operations"""

    def __init__(self, db: AsyncSession, redis_service: RedisService):
        """Initialize TaskService

        Args:
            db: Database session
            redis_service: Redis service instance
        """
        self.db = db
        self.redis = redis_service

    async def create_task(
        self,
        description: str,
        task_type: str = "develop_feature",
        requirements: Optional[Dict[str, Any]] = None,
        checkpoint_frequency: str = "medium",
        privacy_level: str = "normal",
        tool_preferences: Optional[List[str]] = None,
        user_id: Optional[UUID] = None
    ) -> Task:
        """Create a new task

        Args:
            description: Task description (supports Markdown)
            task_type: Type of task (develop_feature, bug_fix, etc.)
            requirements: Additional requirements
            checkpoint_frequency: Checkpoint frequency (low, medium, high)
            privacy_level: Privacy level (normal, sensitive)
            tool_preferences: Preferred AI tools
            user_id: Optional user ID (for future auth)

        Returns:
            Task: Created task instance

        Raises:
            Exception: If task creation fails
        """
        logger.info(
            "Creating task",
            task_type=task_type,
            checkpoint_frequency=checkpoint_frequency,
            privacy_level=privacy_level
        )

        try:
            # Create task record
            task = Task(
                description=description,
                status=TaskStatus.PENDING.value,
                progress=0,
                checkpoint_frequency=checkpoint_frequency,
                privacy_level=privacy_level,
                tool_preferences=tool_preferences,
                task_metadata={
                    "task_type": task_type,
                    "requirements": requirements
                },
                user_id=user_id
            )

            self.db.add(task)
            await self.db.commit()
            await self.db.refresh(task)

            # Set task status in Redis
            await self.redis.set_task_status(
                task_id=task.task_id,
                status=TaskStatus.PENDING.value
            )

            # Add task to queue
            await self.redis.add_task_to_queue(task.task_id)

            logger.info(
                "Task created successfully",
                task_id=str(task.task_id)
            )

            return task

        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Task creation failed",
                error=str(e)
            )
            raise

    async def get_task(self, task_id: UUID) -> Optional[Task]:
        """Get task by ID

        Args:
            task_id: Task UUID

        Returns:
            Optional[Task]: Task instance or None
        """
        result = await self.db.execute(
            select(Task)
            .options(selectinload(Task.subtasks))
            .where(Task.task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Task], int]:
        """List tasks with optional filtering

        Args:
            status: Filter by status (optional)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            tuple: (list of tasks, total count)
        """
        # Build query with eager loading to avoid N+1
        query = select(Task).options(
            selectinload(Task.subtasks)  # Eager load subtasks to avoid N+1
        )

        if status:
            query = query.where(Task.status == status)

        # Order by created_at descending (newest first)
        query = query.order_by(Task.created_at.desc())

        # Get total count
        count_query = select(func.count()).select_from(Task)
        if status:
            count_query = count_query.where(Task.status == status)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get paginated results with eager loading
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        tasks = result.scalars().all()

        return list(tasks), total

    async def update_task_status(
        self,
        task_id: UUID,
        status: str,
        progress: Optional[int] = None
    ) -> bool:
        """Update task status

        Args:
            task_id: Task UUID
            status: New status
            progress: Optional progress percentage

        Returns:
            bool: True if successful

        Raises:
            ValueError: If task not found
        """
        logger.debug(
            "Updating task status",
            task_id=str(task_id),
            status=status,
            progress=progress
        )

        result = await self.db.execute(
            select(Task).where(Task.task_id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Update task record
        task.status = status
        if progress is not None:
            task.progress = progress

        # Update timestamps based on status
        now = datetime.utcnow()
        if status == TaskStatus.IN_PROGRESS.value and task.started_at is None:
            task.started_at = now
        elif status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
            task.completed_at = now

        await self.db.commit()

        # Update Redis
        await self.redis.set_task_status(
            task_id=task_id,
            status=status
        )

        if progress is not None:
            await self.redis.set_task_progress(
                task_id=task_id,
                progress=progress
            )

        # Invalidate task list cache when status changes
        await self.redis.invalidate_cache_pattern("tasks_list:*")

        return True

    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a task

        Args:
            task_id: Task UUID

        Returns:
            bool: True if cancelled successfully

        Raises:
            ValueError: If task not found or already completed
        """
        logger.info("Cancelling task", task_id=str(task_id))

        result = await self.db.execute(
            select(Task).where(Task.task_id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Check if task can be cancelled
        if task.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
            raise ValueError(f"Task {task_id} is already {task.status} and cannot be cancelled")

        # Update task status
        task.status = TaskStatus.CANCELLED.value
        task.completed_at = datetime.utcnow()

        # Cancel all pending subtasks
        await self.db.execute(
            update(Subtask)
            .where(Subtask.task_id == task_id)
            .where(Subtask.status.in_(["pending", "queued"]))
            .values(status="cancelled")
        )

        await self.db.commit()

        # Update Redis
        await self.redis.set_task_status(
            task_id=task_id,
            status=TaskStatus.CANCELLED.value
        )

        # Remove from queue
        await self.redis.remove_task_from_queue(task_id)

        logger.info("Task cancelled", task_id=str(task_id))
        return True

    async def get_task_progress(self, task_id: UUID) -> Dict[str, Any]:
        """Get task progress from Redis

        Args:
            task_id: Task UUID

        Returns:
            Dict with status and progress
        """
        status = await self.redis.get_task_status(task_id)
        progress = await self.redis.get_task_progress(task_id)

        return {
            "task_id": str(task_id),
            "status": status,
            "progress": progress
        }

    async def get_task_with_realtime_status(self, task_id: UUID) -> Optional[Dict[str, Any]]:
        """Get task with real-time status from Redis combined with DB data

        This method combines:
        - Static data from PostgreSQL (task details, subtasks)
        - Real-time data from Redis (current status, progress)
        - Evaluation scores from PostgreSQL

        Args:
            task_id: Task UUID

        Returns:
            Dict with combined task data, or None if not found
        """
        # Get task from database with subtasks and evaluations
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(Task)
            .options(
                selectinload(Task.subtasks).selectinload(Subtask.evaluations)
            )
            .where(Task.task_id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            return None

        # Get real-time task status from Redis
        redis_status = await self.redis.get_task_status(task_id)
        redis_progress = await self.redis.get_task_progress(task_id)

        # Decode bytes if needed
        if isinstance(redis_status, bytes):
            redis_status = redis_status.decode()

        # Use Redis data if available, otherwise use DB data
        current_status = redis_status if redis_status else task.status
        current_progress = redis_progress if redis_progress is not None else task.progress

        # Get real-time subtask statuses from Redis (batch query)
        subtask_ids = [s.subtask_id for s in task.subtasks]
        redis_subtask_statuses = await self.redis.get_multiple_subtask_statuses(subtask_ids)

        # Build subtask data with real-time status and evaluations
        subtasks_data = []
        for subtask in task.subtasks:
            # Get real-time status from Redis if available
            subtask_redis_status = redis_subtask_statuses.get(str(subtask.subtask_id))
            # Ensure status is a string, not bytes or None
            if subtask_redis_status and isinstance(subtask_redis_status, bytes):
                subtask_redis_status = subtask_redis_status.decode()
            subtask_status = subtask_redis_status if subtask_redis_status else subtask.status

            # Get latest evaluation if exists
            evaluation_data = None
            if subtask.evaluations:
                latest_eval = max(subtask.evaluations, key=lambda e: e.evaluated_at)
                evaluation_data = {
                    "overall_score": float(latest_eval.overall_score) if latest_eval.overall_score else None,
                    "code_quality": float(latest_eval.code_quality) if latest_eval.code_quality else None,
                    "completeness": float(latest_eval.completeness) if latest_eval.completeness else None,
                    "security": float(latest_eval.security) if latest_eval.security else None,
                    "architecture": float(latest_eval.architecture) if latest_eval.architecture else None,
                    "testability": float(latest_eval.testability) if latest_eval.testability else None,
                }

            subtasks_data.append({
                "subtask_id": subtask.subtask_id,
                "name": subtask.name,
                "status": subtask_status,
                "progress": subtask.progress,
                "assigned_worker": subtask.assigned_worker,
                "assigned_tool": subtask.assigned_tool,
                "evaluation": evaluation_data
            })

        return {
            "task_id": task.task_id,
            "description": task.description,
            "status": current_status,
            "progress": current_progress,
            "checkpoint_frequency": task.checkpoint_frequency,
            "privacy_level": task.privacy_level,
            "tool_preferences": task.tool_preferences,
            "task_metadata": task.task_metadata,
            "subtasks": subtasks_data,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at
        }

    async def update_subtask_status(
        self,
        subtask_id: UUID,
        status: str,
        progress: Optional[int] = None
    ) -> bool:
        """Update subtask status in both DB and Redis

        Args:
            subtask_id: Subtask UUID
            status: New status
            progress: Optional progress percentage

        Returns:
            bool: True if successful

        Raises:
            ValueError: If subtask not found
        """
        result = await self.db.execute(
            select(Subtask).where(Subtask.subtask_id == subtask_id)
        )
        subtask = result.scalar_one_or_none()

        if not subtask:
            raise ValueError(f"Subtask {subtask_id} not found")

        # Update subtask record
        subtask.status = status
        if progress is not None:
            subtask.progress = progress

        # Update timestamps
        now = datetime.utcnow()
        if status == "in_progress" and subtask.started_at is None:
            subtask.started_at = now
        elif status in ["completed", "failed"]:
            subtask.completed_at = now

        await self.db.commit()

        # Update Redis cache
        await self.redis.set_subtask_status(subtask_id, status)
        if progress is not None:
            await self.redis.set_subtask_progress(subtask_id, progress)

        # Update parent task progress
        await self._update_task_progress_from_subtasks(subtask.task_id)

        return True

    async def _update_task_progress_from_subtasks(self, task_id: UUID) -> None:
        """Update task progress based on subtask completion

        Args:
            task_id: Task UUID
        """
        # Use a single query with aggregation to avoid N+1
        from sqlalchemy import case

        result = await self.db.execute(
            select(
                func.count().label('total'),
                func.sum(
                    case((Subtask.status == "completed", 1), else_=0)
                ).label('completed')
            )
            .where(Subtask.task_id == task_id)
        )
        row = result.one()

        total_count = row.total or 0
        completed_count = row.completed or 0

        if total_count == 0:
            return

        # Calculate progress as percentage of completed subtasks
        progress = int((completed_count / total_count) * 100)

        # Update task progress with a single query
        task_result = await self.db.execute(
            select(Task).where(Task.task_id == task_id)
        )
        task = task_result.scalar_one_or_none()

        if task:
            task.progress = progress
            await self.db.commit()
            await self.redis.set_task_progress(task_id, progress)
