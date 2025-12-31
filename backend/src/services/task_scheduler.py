"""Task Scheduler Service - Parallel scheduling engine for subtask execution"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
import structlog

from src.models.task import Task
from src.models.subtask import Subtask
from src.models.worker import Worker
from src.services.redis_service import RedisService
from src.services.task_allocator import TaskAllocator
from src.services.task_decomposer import TaskDecomposer
from src.config import get_settings

logger = structlog.get_logger()

# Get settings for concurrency limits
_settings = get_settings()
MAX_CONCURRENT_SUBTASKS = _settings.MAX_CONCURRENT_SUBTASKS
MAX_SUBTASKS_PER_WORKER = _settings.MAX_SUBTASKS_PER_WORKER
SCHEDULER_INTERVAL_SECONDS = _settings.SCHEDULER_INTERVAL_SECONDS


class TaskScheduler:
    """
    Parallel scheduling engine for subtask execution.

    The scheduler:
    - Identifies ready subtasks (dependencies satisfied)
    - Allocates them to available workers in parallel
    - Respects concurrency limits (system-wide and per-worker)
    - Tracks DAG dependencies
    - Triggers on subtask completion to check for new ready subtasks
    """

    def __init__(
        self,
        db: AsyncSession,
        redis_service: RedisService,
        allocator: Optional[TaskAllocator] = None,
        decomposer: Optional[TaskDecomposer] = None
    ):
        """Initialize TaskScheduler

        Args:
            db: Database session
            redis_service: Redis service instance
            allocator: Task allocator (created if not provided)
            decomposer: Task decomposer (created if not provided)
        """
        self.db = db
        self.redis = redis_service
        self.allocator = allocator or TaskAllocator(db, redis_service)
        self.decomposer = decomposer or TaskDecomposer(db, redis_service)
        self._running = False

    async def run_scheduling_cycle(self) -> Dict[str, Any]:
        """
        Run a single scheduling cycle.

        This is the main entry point for scheduled execution.

        Returns:
            Dict with scheduling results
        """
        logger.info("Starting scheduling cycle")

        results = {
            "cycle_start": datetime.utcnow().isoformat(),
            "tasks_processed": 0,
            "subtasks_allocated": 0,
            "subtasks_queued": 0,
            "errors": []
        }

        try:
            # Get current system state
            in_progress_count = await self._get_in_progress_count()

            if in_progress_count >= MAX_CONCURRENT_SUBTASKS:
                logger.info(
                    "System at max capacity",
                    in_progress=in_progress_count,
                    max=MAX_CONCURRENT_SUBTASKS
                )
                results["message"] = "System at max capacity"
                return results

            # Get all active tasks (initializing or in_progress)
            active_tasks = await self._get_active_tasks()
            results["tasks_processed"] = len(active_tasks)

            # Process each task
            for task in active_tasks:
                try:
                    allocated, queued = await self._schedule_task(task, in_progress_count)
                    results["subtasks_allocated"] += allocated
                    results["subtasks_queued"] += queued
                    in_progress_count += allocated
                except Exception as e:
                    logger.error(
                        "Error scheduling task",
                        task_id=str(task.task_id),
                        error=str(e)
                    )
                    results["errors"].append({
                        "task_id": str(task.task_id),
                        "error": str(e)
                    })

            # Also try to reallocate queued subtasks
            try:
                reallocated = await self._reallocate_queued()
                results["subtasks_allocated"] += reallocated
            except Exception as e:
                logger.error("Error reallocating queued subtasks", error=str(e))
                results["errors"].append({"phase": "reallocation", "error": str(e)})

            results["cycle_end"] = datetime.utcnow().isoformat()
            logger.info(
                "Scheduling cycle complete",
                allocated=results["subtasks_allocated"],
                queued=results["subtasks_queued"]
            )

        except Exception as e:
            logger.error("Scheduling cycle failed", error=str(e))
            results["errors"].append({"phase": "cycle", "error": str(e)})

        return results

    async def on_subtask_complete(self, subtask_id: UUID) -> Dict[str, Any]:
        """
        Handle subtask completion event.

        Called when a subtask finishes to check for newly ready subtasks.

        Args:
            subtask_id: Completed subtask UUID

        Returns:
            Dict with results
        """
        logger.info("Handling subtask completion", subtask_id=str(subtask_id))

        results = {
            "subtask_id": str(subtask_id),
            "newly_allocated": 0,
            "task_completed": False
        }

        try:
            # Get the subtask to find its parent task
            result = await self.db.execute(
                select(Subtask)
                .where(Subtask.subtask_id == subtask_id)
                .options(selectinload(Subtask.task))
            )
            subtask = result.scalar_one_or_none()

            if not subtask:
                logger.warning("Subtask not found", subtask_id=str(subtask_id))
                return results

            task_id = subtask.task_id

            # Check if task is complete
            is_complete = await self.decomposer.check_task_completion(task_id)
            results["task_completed"] = is_complete

            if is_complete:
                logger.info(
                    "Task completed",
                    task_id=str(task_id),
                    status=subtask.task.status
                )
                return results

            # Get ready subtasks for this task
            ready = await self.decomposer.get_ready_subtasks(task_id)

            # Allocate ready subtasks
            for ready_subtask in ready:
                try:
                    worker = await self.allocator.allocate_subtask(ready_subtask.subtask_id)
                    if worker:
                        results["newly_allocated"] += 1
                except ValueError as e:
                    logger.debug(
                        "Could not allocate subtask",
                        subtask_id=str(ready_subtask.subtask_id),
                        reason=str(e)
                    )

            logger.info(
                "Subtask completion handled",
                subtask_id=str(subtask_id),
                newly_allocated=results["newly_allocated"]
            )

        except Exception as e:
            logger.error(
                "Error handling subtask completion",
                subtask_id=str(subtask_id),
                error=str(e)
            )
            results["error"] = str(e)

        return results

    async def schedule_task(self, task_id: UUID) -> Dict[str, Any]:
        """
        Schedule a specific task's subtasks.

        Args:
            task_id: Task UUID to schedule

        Returns:
            Dict with scheduling results
        """
        logger.info("Scheduling task", task_id=str(task_id))

        results = {
            "task_id": str(task_id),
            "subtasks_allocated": 0,
            "subtasks_queued": 0
        }

        try:
            # Get task
            result = await self.db.execute(
                select(Task).where(Task.task_id == task_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                raise ValueError(f"Task {task_id} not found")

            # Check if task needs decomposition
            if task.status == "pending":
                await self.decomposer.decompose_task(task_id)
                await self.db.refresh(task)

            # Schedule the task
            allocated, queued = await self._schedule_task(task)
            results["subtasks_allocated"] = allocated
            results["subtasks_queued"] = queued

        except Exception as e:
            logger.error("Error scheduling task", task_id=str(task_id), error=str(e))
            results["error"] = str(e)

        return results

    async def _schedule_task(
        self,
        task: Task,
        current_in_progress: int = 0
    ) -> Tuple[int, int]:
        """
        Schedule subtasks for a single task.

        Args:
            task: Task to schedule
            current_in_progress: Current system-wide in-progress count

        Returns:
            Tuple of (allocated_count, queued_count)
        """
        # Get ready subtasks
        ready = await self.decomposer.get_ready_subtasks(task.task_id)

        if not ready:
            return 0, 0

        allocated = 0
        queued = 0

        # Check capacity
        remaining_capacity = MAX_CONCURRENT_SUBTASKS - current_in_progress

        for subtask in ready:
            if allocated >= remaining_capacity:
                # System at capacity, queue remaining
                if subtask.status == "pending":
                    subtask.status = "queued"
                    await self.redis.push_to_queue(subtask.subtask_id)
                queued += 1
                continue

            try:
                worker = await self.allocator.allocate_subtask(subtask.subtask_id)
                if worker:
                    allocated += 1
                else:
                    queued += 1
            except ValueError:
                queued += 1

        # Update task status if it was initializing
        if task.status == "initializing" and allocated > 0:
            task.status = "in_progress"
            task.started_at = datetime.utcnow()
            await self.db.commit()
            await self.redis.set_task_status(task.task_id, "in_progress")

        return allocated, queued

    async def _get_active_tasks(self) -> List[Task]:
        """Get all tasks that need scheduling"""
        # Use eager loading to avoid N+1 when accessing subtasks
        result = await self.db.execute(
            select(Task)
            .options(selectinload(Task.subtasks))  # Eager load subtasks
            .where(Task.status.in_(["initializing", "in_progress"]))
            .order_by(Task.created_at.asc())
        )
        return list(result.scalars().all())

    async def _get_in_progress_count(self) -> int:
        """Get current number of in-progress subtasks system-wide"""
        # Try Redis first
        count = await self.redis.get_in_progress_count()
        if count > 0:
            return count

        # Fall back to database
        result = await self.db.execute(
            select(func.count())
            .select_from(Subtask)
            .where(Subtask.status == "in_progress")
        )
        return result.scalar() or 0

    async def _reallocate_queued(self) -> int:
        """
        Try to reallocate queued subtasks.

        Returns:
            Number of successfully allocated subtasks
        """
        try:
            # Get queued subtasks ordered by priority
            result = await self.db.execute(
                select(Subtask)
                .where(Subtask.status == "queued")
                .where(Subtask.assigned_worker.is_(None))
                .order_by(Subtask.priority.desc(), Subtask.created_at.asc())
                .limit(MAX_CONCURRENT_SUBTASKS)
            )
            queued = result.scalars().all()

            allocated = 0
            for subtask in queued:
                try:
                    worker = await self.allocator.allocate_subtask(subtask.subtask_id)
                    if worker:
                        allocated += 1
                except ValueError as e:
                    logger.debug(
                        "Could not allocate queued subtask",
                        subtask_id=str(subtask.subtask_id),
                        error=str(e)
                    )
                    continue
                except Exception as e:
                    logger.error(
                        "Error allocating queued subtask",
                        subtask_id=str(subtask.subtask_id),
                        error=str(e)
                    )
                    continue

            return allocated

        except Exception as e:
            logger.error("Error in reallocate_queued", error=str(e))
            return 0

    async def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        # Use parallel queries with asyncio.gather for better performance
        import asyncio

        # Execute database queries in parallel
        subtask_stats, active_tasks_count, available_workers_count = await asyncio.gather(
            self.db.execute(
                select(Subtask.status, func.count())
                .group_by(Subtask.status)
            ),
            self.db.execute(
                select(func.count())
                .select_from(Task)
                .where(Task.status.in_(["initializing", "in_progress"]))
            ),
            self.db.execute(
                select(func.count())
                .select_from(Worker)
                .where(Worker.status.in_(["online", "idle"]))
            )
        )

        status_counts = dict(subtask_stats.fetchall())
        active_tasks = active_tasks_count.scalar() or 0
        available_workers = available_workers_count.scalar() or 0

        # Get Redis queue info in parallel
        queue_length, in_progress_redis = await asyncio.gather(
            self.redis.get_queue_length(),
            self.redis.get_in_progress_count()
        )

        return {
            "active_tasks": active_tasks,
            "available_workers": available_workers,
            "subtask_status_counts": status_counts,
            "queue_length": queue_length,
            "in_progress_count": in_progress_redis,
            "max_concurrent_subtasks": MAX_CONCURRENT_SUBTASKS,
            "max_subtasks_per_worker": MAX_SUBTASKS_PER_WORKER,
            "scheduler_interval_seconds": SCHEDULER_INTERVAL_SECONDS
        }

    def get_concurrency_limits(self) -> Dict[str, int]:
        """Get current concurrency limits"""
        return {
            "max_concurrent_subtasks": MAX_CONCURRENT_SUBTASKS,
            "max_subtasks_per_worker": MAX_SUBTASKS_PER_WORKER
        }

    async def identify_parallelizable_subtasks(
        self,
        task_id: UUID
    ) -> List[List[Subtask]]:
        """
        Identify all parallelizable subtasks for a task.

        Returns subtasks grouped by dependency level (parallelizable within each level).
        For example:
        - Level 0: All subtasks with no dependencies (can run in parallel)
        - Level 1: All subtasks that only depend on Level 0 (can run in parallel after Level 0)
        - Level 2: All subtasks that depend on Level 0 or 1 (can run in parallel after Level 1)
        - etc.

        Args:
            task_id: Task UUID

        Returns:
            List of lists, where each inner list contains subtasks that can run in parallel
        """
        logger.info("Identifying parallelizable subtasks", task_id=str(task_id))

        # Get all subtasks for the task
        result = await self.db.execute(
            select(Subtask)
            .where(Subtask.task_id == task_id)
            .order_by(Subtask.created_at.asc())
        )
        all_subtasks = list(result.scalars().all())

        if not all_subtasks:
            return []

        # Build dependency graph
        subtask_map = {str(s.subtask_id): s for s in all_subtasks}

        # Calculate dependency levels
        levels: List[List[Subtask]] = []
        assigned_subtasks = set()

        while len(assigned_subtasks) < len(all_subtasks):
            current_level = []

            for subtask in all_subtasks:
                if str(subtask.subtask_id) in assigned_subtasks:
                    continue

                # Check if all dependencies are in assigned_subtasks
                deps = subtask.dependencies or []
                if all(dep_id in assigned_subtasks for dep_id in deps):
                    current_level.append(subtask)

            if not current_level:
                # Circular dependency or orphaned subtasks
                logger.warning(
                    "Could not assign all subtasks to levels",
                    task_id=str(task_id),
                    unassigned=len(all_subtasks) - len(assigned_subtasks)
                )
                break

            levels.append(current_level)
            assigned_subtasks.update(str(s.subtask_id) for s in current_level)

        logger.info(
            "Parallelizable subtasks identified",
            task_id=str(task_id),
            levels=len(levels),
            subtasks_per_level=[len(level) for level in levels]
        )

        return levels

    async def coordinate_parallel_execution(
        self,
        task_id: UUID
    ) -> Dict[str, Any]:
        """
        Coordinate parallel execution of a task's subtasks.

        This method:
        1. Identifies parallelizable subtasks (grouped by dependency level)
        2. Distributes subtasks to different workers
        3. Tracks status of all parallel tasks
        4. Aggregates results when level completes
        5. Updates parent task status

        Args:
            task_id: Task UUID to coordinate

        Returns:
            Dict with execution results and statistics
        """
        logger.info("Coordinating parallel execution", task_id=str(task_id))

        results = {
            "task_id": str(task_id),
            "levels_executed": 0,
            "total_subtasks_allocated": 0,
            "total_subtasks_completed": 0,
            "total_subtasks_failed": 0,
            "execution_start": datetime.utcnow().isoformat(),
            "level_results": []
        }

        try:
            # Get parallelizable subtasks grouped by level
            levels = await self.identify_parallelizable_subtasks(task_id)

            if not levels:
                logger.info("No parallelizable subtasks found", task_id=str(task_id))
                return results

            # Execute each level in sequence (but subtasks within level in parallel)
            for level_idx, level_subtasks in enumerate(levels):
                logger.info(
                    "Executing parallel level",
                    task_id=str(task_id),
                    level=level_idx,
                    subtasks_count=len(level_subtasks)
                )

                level_result = await self._execute_parallel_level(
                    task_id=task_id,
                    level_idx=level_idx,
                    subtasks=level_subtasks
                )

                results["level_results"].append(level_result)
                results["levels_executed"] += 1
                results["total_subtasks_allocated"] += level_result["allocated"]
                results["total_subtasks_completed"] += level_result["completed"]
                results["total_subtasks_failed"] += level_result["failed"]

                # If level has failures, decide whether to continue
                if level_result["failed"] > 0:
                    logger.warning(
                        "Level has failures",
                        task_id=str(task_id),
                        level=level_idx,
                        failed=level_result["failed"]
                    )
                    # For now, continue to next level
                    # Future: Add failure handling strategy

            results["execution_end"] = datetime.utcnow().isoformat()

            # Update task progress
            await self._update_task_progress_from_coordination(task_id)

            logger.info(
                "Parallel execution coordination complete",
                task_id=str(task_id),
                levels=results["levels_executed"],
                total_allocated=results["total_subtasks_allocated"]
            )

        except Exception as e:
            logger.error(
                "Error coordinating parallel execution",
                task_id=str(task_id),
                error=str(e)
            )
            results["error"] = str(e)

        return results

    async def _execute_parallel_level(
        self,
        task_id: UUID,
        level_idx: int,
        subtasks: List[Subtask]
    ) -> Dict[str, Any]:
        """
        Execute all subtasks in a parallel level.

        Args:
            task_id: Parent task UUID
            level_idx: Level index
            subtasks: Subtasks to execute in parallel

        Returns:
            Dict with level execution results
        """
        level_result = {
            "level": level_idx,
            "total_subtasks": len(subtasks),
            "allocated": 0,
            "queued": 0,
            "completed": 0,
            "failed": 0,
            "start_time": datetime.utcnow().isoformat()
        }

        # Filter to only pending/ready subtasks
        ready_subtasks = [
            s for s in subtasks
            if s.status in ("pending", "queued")
        ]

        if not ready_subtasks:
            logger.info(
                "No ready subtasks in level",
                task_id=str(task_id),
                level=level_idx
            )
            level_result["end_time"] = datetime.utcnow().isoformat()
            return level_result

        # Allocate all ready subtasks to workers
        for subtask in ready_subtasks:
            try:
                worker = await self.allocator.allocate_subtask(subtask.subtask_id)
                if worker:
                    level_result["allocated"] += 1
                    logger.debug(
                        "Subtask allocated in parallel level",
                        subtask_id=str(subtask.subtask_id),
                        level=level_idx,
                        worker_id=str(worker.worker_id)
                    )
                else:
                    level_result["queued"] += 1
            except ValueError as e:
                logger.warning(
                    "Failed to allocate subtask in level",
                    subtask_id=str(subtask.subtask_id),
                    level=level_idx,
                    error=str(e)
                )
                level_result["queued"] += 1

        # Wait for all subtasks in this level to complete
        # Note: This is a simplified version. In production, you might want:
        # - Timeout handling
        # - Periodic status checks
        # - Real-time event-driven updates
        await self._wait_for_level_completion(task_id, [s.subtask_id for s in ready_subtasks])

        # Get final status counts using aggregation (optimized)
        from sqlalchemy import case

        result = await self.db.execute(
            select(
                func.sum(case((Subtask.status == "completed", 1), else_=0)).label('completed'),
                func.sum(case((Subtask.status == "failed", 1), else_=0)).label('failed')
            )
            .where(Subtask.subtask_id.in_([s.subtask_id for s in ready_subtasks]))
        )
        row = result.one()

        level_result["completed"] = int(row.completed or 0)
        level_result["failed"] = int(row.failed or 0)
        level_result["end_time"] = datetime.utcnow().isoformat()

        return level_result

    async def _wait_for_level_completion(
        self,
        task_id: UUID,
        subtask_ids: List[UUID],
        timeout_seconds: int = 3600
    ) -> None:
        """
        Wait for all subtasks in a level to complete.

        This is a simplified polling implementation. In production,
        you would use event-driven architecture with Redis pub/sub or WebSockets.

        Args:
            task_id: Parent task UUID
            subtask_ids: List of subtask UUIDs to wait for
            timeout_seconds: Maximum wait time in seconds
        """
        start_time = datetime.utcnow()
        poll_interval = 5  # Check every 5 seconds
        consecutive_errors = 0
        max_consecutive_errors = 3

        while True:
            try:
                # Check if timeout reached
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > timeout_seconds:
                    logger.warning(
                        "Level completion timeout",
                        task_id=str(task_id),
                        elapsed_seconds=elapsed
                    )
                    break

                # Get current status of all subtasks
                result = await self.db.execute(
                    select(Subtask)
                    .where(Subtask.subtask_id.in_(subtask_ids))
                )
                subtasks = list(result.scalars().all())

                # Reset error counter on successful query
                consecutive_errors = 0

                # Check if all are completed or failed
                terminal_statuses = {"completed", "failed"}
                all_done = all(s.status in terminal_statuses for s in subtasks)

                if all_done:
                    logger.info(
                        "Level completed",
                        task_id=str(task_id),
                        elapsed_seconds=elapsed
                    )
                    break

                # Wait before next poll
                await asyncio.sleep(poll_interval)

            except Exception as e:
                consecutive_errors += 1
                logger.error(
                    "Error checking level completion",
                    task_id=str(task_id),
                    error=str(e),
                    consecutive_errors=consecutive_errors
                )

                if consecutive_errors >= max_consecutive_errors:
                    logger.error(
                        "Too many consecutive errors, aborting wait",
                        task_id=str(task_id)
                    )
                    break

                # Wait before retry
                await asyncio.sleep(poll_interval)

    async def _update_task_progress_from_coordination(self, task_id: UUID) -> None:
        """
        Update task progress after parallel coordination.

        Args:
            task_id: Task UUID
        """
        # Get task with subtasks
        result = await self.db.execute(
            select(Task)
            .options(selectinload(Task.subtasks))
            .where(Task.task_id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task or not task.subtasks:
            return

        # Calculate progress
        total = len(task.subtasks)
        completed = sum(1 for s in task.subtasks if s.status == "completed")
        failed = sum(1 for s in task.subtasks if s.status == "failed")

        progress = int((completed / total) * 100) if total > 0 else 0

        # Update task
        task.progress = progress

        # Update status if needed
        if completed == total:
            task.status = "completed"
            task.completed_at = datetime.utcnow()
        elif failed > 0 and (completed + failed) == total:
            task.status = "failed"
            task.completed_at = datetime.utcnow()
        elif task.status != "in_progress":
            task.status = "in_progress"

        await self.db.commit()

        # Update Redis
        await self.redis.set_task_progress(task_id, progress)
        await self.redis.set_task_status(task_id, task.status)

    async def get_parallel_execution_stats(self, task_id: UUID) -> Dict[str, Any]:
        """
        Get statistics about parallel execution for a task.

        Args:
            task_id: Task UUID

        Returns:
            Dict with parallel execution statistics
        """
        # Get parallelizable levels
        levels = await self.identify_parallelizable_subtasks(task_id)

        # Get subtask status counts
        result = await self.db.execute(
            select(Subtask.status, func.count())
            .where(Subtask.task_id == task_id)
            .group_by(Subtask.status)
        )
        status_counts = dict(result.fetchall())

        return {
            "task_id": str(task_id),
            "parallel_levels": len(levels),
            "subtasks_per_level": [len(level) for level in levels],
            "max_parallelism": max([len(level) for level in levels]) if levels else 0,
            "status_counts": status_counts,
            "total_subtasks": sum(status_counts.values())
        }


class SchedulerRunner:
    """
    Background scheduler runner using APScheduler.

    Manages the periodic execution of scheduling cycles.
    """

    def __init__(
        self,
        db_session_factory,
        redis_service: RedisService,
        interval_seconds: int = SCHEDULER_INTERVAL_SECONDS
    ):
        """Initialize SchedulerRunner

        Args:
            db_session_factory: Async session factory for database connections
            redis_service: Redis service instance
            interval_seconds: Scheduling interval in seconds
        """
        self.db_session_factory = db_session_factory
        self.redis = redis_service
        self.interval = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the scheduler"""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Scheduler started",
            interval_seconds=self.interval
        )

    async def stop(self) -> None:
        """Stop the scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop"""
        while self._running:
            try:
                # Create a new session for each cycle
                async with self.db_session_factory() as db:
                    scheduler = TaskScheduler(db, self.redis)
                    await scheduler.run_scheduling_cycle()
            except Exception as e:
                logger.error("Scheduler cycle error", error=str(e))

            # Wait for next cycle
            await asyncio.sleep(self.interval)

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._running


async def run_single_cycle(
    db: AsyncSession,
    redis_service: RedisService
) -> Dict[str, Any]:
    """
    Convenience function to run a single scheduling cycle.

    Args:
        db: Database session
        redis_service: Redis service

    Returns:
        Scheduling results
    """
    scheduler = TaskScheduler(db, redis_service)
    return await scheduler.run_scheduling_cycle()
