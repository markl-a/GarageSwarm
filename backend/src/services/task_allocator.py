"""Task Allocator Service - Smart task allocation using weighted scoring algorithm"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import structlog

from src.models.task import Task
from src.models.subtask import Subtask
from src.models.worker import Worker
from src.services.redis_service import RedisService
from src.config import get_settings
from src.schemas.subtask import SubtaskStatus
from src.schemas.worker import WorkerStatus

logger = structlog.get_logger()
settings = get_settings()


# Scoring weights for worker selection (from config)
SCORING_WEIGHTS = {
    "tool_matching": settings.ALLOCATOR_WEIGHT_TOOL_MATCH,
    "resource_score": settings.ALLOCATOR_WEIGHT_RESOURCES,
    "privacy_score": settings.ALLOCATOR_WEIGHT_PRIVACY,
}

# Resource thresholds (from config)
RESOURCE_THRESHOLDS = {
    "cpu_high": settings.RESOURCE_THRESHOLD_CPU_HIGH,
    "memory_high": settings.RESOURCE_THRESHOLD_MEMORY_HIGH,
    "disk_high": settings.RESOURCE_THRESHOLD_DISK_HIGH,
}

# Resource scoring weights (CPU, Memory, Disk)
RESOURCE_SCORING_WEIGHTS = {
    "cpu": 0.4,
    "memory": 0.4,
    "disk": 0.2,
}

# Tool matching scores
TOOL_SCORE_PERFECT_MATCH = 1.0      # Worker has the recommended tool
TOOL_SCORE_PARTIAL_MATCH = 0.5     # Worker has other tools but not recommended
TOOL_SCORE_NO_TOOLS = 0.0          # Worker has no tools
TOOL_SCORE_UNKNOWN_RESOURCE = 0.5  # Default when resource usage unknown

# Privacy compatibility scores
PRIVACY_SCORE_NORMAL = 1.0         # Normal privacy - all workers compatible
PRIVACY_SCORE_LOCAL_ONLY = 1.0     # Sensitive + local tools only
PRIVACY_SCORE_LOCAL_WITH_CLOUD = 0.8  # Sensitive + has local option
PRIVACY_SCORE_CLOUD_ONLY = 0.5     # Sensitive + cloud tools only
PRIVACY_SCORE_NO_TOOLS = 0.0       # No tools available


class TaskAllocator:
    """
    Service for smart task allocation using a weighted scoring algorithm.

    The allocation algorithm considers:
    - Tool matching (50%): Whether the worker has the subtask's recommended tool
    - Resource availability (30%): Current CPU, memory, and disk usage
    - Privacy compatibility (20%): Whether the worker can handle the task's privacy level

    Workers are scored and the best available worker is selected.
    If no suitable worker is found, the subtask remains in the queue.
    """

    def __init__(self, db: AsyncSession, redis_service: RedisService):
        """Initialize TaskAllocator

        Args:
            db: Database session
            redis_service: Redis service instance
        """
        self.db = db
        self.redis = redis_service

    async def allocate_subtask(self, subtask_id: UUID) -> Optional[Worker]:
        """
        Allocate a subtask to the best available worker.

        Args:
            subtask_id: Subtask UUID to allocate

        Returns:
            Worker if allocation successful, None if no suitable worker found

        Raises:
            ValueError: If subtask not found or already assigned
        """
        logger.info("Allocating subtask", subtask_id=str(subtask_id))

        # Get subtask with task relationship
        result = await self.db.execute(
            select(Subtask)
            .where(Subtask.subtask_id == subtask_id)
            .options(selectinload(Subtask.task))
        )
        subtask = result.scalar_one_or_none()

        if not subtask:
            raise ValueError(f"Subtask {subtask_id} not found")

        if subtask.assigned_worker:
            raise ValueError(f"Subtask {subtask_id} is already assigned")

        if subtask.status not in (SubtaskStatus.PENDING.value, SubtaskStatus.QUEUED.value):
            raise ValueError(f"Subtask {subtask_id} is not in allocatable state: {subtask.status}")

        # Get all available workers
        available_workers = await self._get_available_workers()

        if not available_workers:
            logger.info("No available workers for subtask", subtask_id=str(subtask_id))
            # Push to queue if not already queued
            if subtask.status != SubtaskStatus.QUEUED.value:
                subtask.status = SubtaskStatus.QUEUED.value
                await self.redis.push_to_queue(subtask_id)
                await self.db.commit()
            return None

        # Score each worker
        worker_scores = []
        for worker in available_workers:
            score = await self._calculate_worker_score(worker, subtask)
            worker_scores.append((worker, score))

        # Sort by score descending
        worker_scores.sort(key=lambda x: x[1], reverse=True)

        # Select best worker (score > 0)
        best_worker, best_score = worker_scores[0]

        if best_score <= 0:
            logger.info(
                "No suitable worker found",
                subtask_id=str(subtask_id),
                best_score=best_score
            )
            if subtask.status != SubtaskStatus.QUEUED.value:
                subtask.status = SubtaskStatus.QUEUED.value
                await self.redis.push_to_queue(subtask_id)
                await self.db.commit()
            return None

        # Assign subtask to worker
        await self._assign_subtask_to_worker(subtask, best_worker)

        logger.info(
            "Subtask allocated successfully",
            subtask_id=str(subtask_id),
            worker_id=str(best_worker.worker_id),
            score=best_score
        )

        return best_worker

    async def allocate_ready_subtasks(self, task_id: UUID) -> List[Tuple[Subtask, Optional[Worker]]]:
        """
        Allocate all ready subtasks for a task.

        Args:
            task_id: Parent task UUID

        Returns:
            List of (subtask, assigned_worker) tuples
        """
        logger.info("Allocating ready subtasks for task", task_id=str(task_id))

        # Get ready subtasks (pending with satisfied dependencies)
        ready_subtasks = await self._get_ready_subtasks(task_id)

        allocations = []
        for subtask in ready_subtasks:
            try:
                worker = await self.allocate_subtask(subtask.subtask_id)
                allocations.append((subtask, worker))
            except ValueError as e:
                logger.warning(
                    "Failed to allocate subtask",
                    subtask_id=str(subtask.subtask_id),
                    error=str(e)
                )
                allocations.append((subtask, None))

        return allocations

    async def reallocate_queued_subtasks(self) -> List[Tuple[Subtask, Worker]]:
        """
        Attempt to reallocate queued subtasks.
        Called periodically (e.g., every 30 seconds) by scheduler.

        Returns:
            List of (subtask, worker) tuples for successful allocations
        """
        logger.info("Reallocating queued subtasks")

        allocations = []

        # Process queue one by one until empty or no more can be allocated
        max_attempts = settings.MAX_QUEUE_ALLOCATION_ATTEMPTS
        attempts = 0

        while attempts < max_attempts:
            attempts += 1

            # Peek at next item in queue
            next_subtask_id_str = await self.redis.peek_queue()
            if not next_subtask_id_str:
                # Queue is empty
                break

            try:
                next_subtask_id = UUID(next_subtask_id_str)

                # Try to allocate
                worker = await self.allocate_subtask(next_subtask_id)

                if worker:
                    # Successfully allocated, remove from queue
                    popped = await self.redis.pop_from_queue()
                    if popped != next_subtask_id_str:
                        logger.warning(
                            "Queue mismatch during reallocation",
                            expected=next_subtask_id_str,
                            got=popped
                        )

                    # Get subtask for return value
                    result = await self.db.execute(
                        select(Subtask).where(Subtask.subtask_id == next_subtask_id)
                    )
                    subtask = result.scalar_one_or_none()
                    if subtask:
                        allocations.append((subtask, worker))
                else:
                    # No worker available, stop trying for now
                    logger.debug(
                        "No workers available for reallocation",
                        queued_subtask=next_subtask_id_str
                    )
                    break

            except ValueError as e:
                # Subtask not in allocatable state, remove from queue
                logger.warning(
                    "Removing non-allocatable subtask from queue",
                    subtask_id=next_subtask_id_str,
                    error=str(e)
                )
                await self.redis.pop_from_queue()
            except Exception as e:
                # Unexpected error, log and skip this item
                logger.error(
                    "Error during reallocation",
                    subtask_id=next_subtask_id_str,
                    error=str(e)
                )
                # Pop to prevent getting stuck on this item
                await self.redis.pop_from_queue()

        logger.info(
            "Reallocation complete",
            attempts=attempts,
            successful=len(allocations)
        )

        return allocations

    async def _get_available_workers(self) -> List[Worker]:
        """Get all workers that are available for task assignment

        Uses batch Redis query (pipeline) to check all workers at once,
        reducing N Redis round-trips to just 1.
        """
        # Get workers with status 'online' or 'idle'
        result = await self.db.execute(
            select(Worker)
            .where(Worker.status.in_([WorkerStatus.ONLINE.value, WorkerStatus.IDLE.value]))
        )
        workers = list(result.scalars().all())

        if not workers:
            return []

        # Batch query: Get current tasks for ALL workers in single Redis call
        worker_ids = [w.worker_id for w in workers]
        current_tasks = await self.redis.get_multiple_worker_current_tasks(worker_ids)

        # Filter out workers with current tasks
        available = [
            worker for worker in workers
            if not current_tasks.get(str(worker.worker_id))
        ]

        logger.debug(
            "Available workers check",
            total_online=len(workers),
            available=len(available)
        )

        return available

    async def _calculate_worker_score(
        self,
        worker: Worker,
        subtask: Subtask
    ) -> float:
        """
        Calculate worker score for a subtask using weighted algorithm.

        Score = (tool_matching * 0.5) + (resource_score * 0.3) + (privacy_score * 0.2)

        Args:
            worker: Worker to score
            subtask: Subtask to allocate

        Returns:
            Score between 0.0 and 1.0
        """
        # Tool matching score (0 or 1)
        tool_score = self._calculate_tool_score(worker, subtask)

        # Resource availability score (0 to 1)
        resource_score = self._calculate_resource_score(worker)

        # Privacy compatibility score (0 or 1)
        privacy_score = await self._calculate_privacy_score(worker, subtask)

        # Calculate weighted total
        total_score = (
            tool_score * SCORING_WEIGHTS["tool_matching"] +
            resource_score * SCORING_WEIGHTS["resource_score"] +
            privacy_score * SCORING_WEIGHTS["privacy_score"]
        )

        logger.debug(
            "Worker score calculated",
            worker_id=str(worker.worker_id),
            tool_score=tool_score,
            resource_score=resource_score,
            privacy_score=privacy_score,
            total_score=total_score
        )

        return total_score

    def _calculate_tool_score(self, worker: Worker, subtask: Subtask) -> float:
        """
        Calculate tool matching score.

        Returns TOOL_SCORE_PERFECT_MATCH if worker has the recommended tool.
        Returns TOOL_SCORE_PARTIAL_MATCH if worker has other tools.
        Returns TOOL_SCORE_NO_TOOLS if worker has no tools.
        """
        recommended_tool = subtask.recommended_tool

        if not recommended_tool:
            # No specific tool recommended, any worker with tools is fine
            return TOOL_SCORE_PERFECT_MATCH if worker.tools else TOOL_SCORE_NO_TOOLS

        if not worker.tools:
            return TOOL_SCORE_NO_TOOLS

        if recommended_tool in worker.tools:
            return TOOL_SCORE_PERFECT_MATCH

        # Worker has tools but not the recommended one
        return TOOL_SCORE_PARTIAL_MATCH

    def _calculate_resource_score(self, worker: Worker) -> float:
        """
        Calculate resource availability score based on CPU, memory, and disk usage.

        Lower usage = higher score.
        Score is average of (100 - usage) / 100 for each resource.
        """
        scores = []

        # CPU score
        if worker.cpu_percent is not None:
            cpu_available = max(0, 100 - worker.cpu_percent)
            scores.append(cpu_available / 100)
        else:
            scores.append(TOOL_SCORE_UNKNOWN_RESOURCE)  # Unknown, assume moderate

        # Memory score
        if worker.memory_percent is not None:
            mem_available = max(0, 100 - worker.memory_percent)
            scores.append(mem_available / 100)
        else:
            scores.append(TOOL_SCORE_UNKNOWN_RESOURCE)

        # Disk score (less important, lower weight)
        if worker.disk_percent is not None:
            disk_available = max(0, 100 - worker.disk_percent)
            scores.append(disk_available / 100)
        else:
            scores.append(TOOL_SCORE_UNKNOWN_RESOURCE)

        # Weight: CPU and memory more important than disk
        weighted_score = (
            scores[0] * RESOURCE_SCORING_WEIGHTS["cpu"] +
            scores[1] * RESOURCE_SCORING_WEIGHTS["memory"] +
            scores[2] * RESOURCE_SCORING_WEIGHTS["disk"]
        )

        return weighted_score

    async def _calculate_privacy_score(
        self,
        worker: Worker,
        subtask: Subtask
    ) -> float:
        """
        Calculate privacy compatibility score.

        For 'sensitive' tasks, prefer workers that:
        - Have local tools (ollama) rather than cloud-based
        - Have lower resource usage (less chance of data leakage)

        For 'normal' tasks, all workers score equally.
        """
        task = subtask.task
        privacy_level = task.privacy_level if task else "normal"

        if privacy_level == "normal":
            return PRIVACY_SCORE_NORMAL  # All workers are compatible

        # Sensitive task - prefer local processing
        if worker.tools:
            has_local = "ollama" in worker.tools
            has_cloud = any(t in worker.tools for t in ["claude_code", "gemini_cli"])

            if has_local and not has_cloud:
                return PRIVACY_SCORE_LOCAL_ONLY  # Perfect for sensitive tasks
            elif has_local:
                return PRIVACY_SCORE_LOCAL_WITH_CLOUD  # Has local option
            else:
                return PRIVACY_SCORE_CLOUD_ONLY  # Only cloud options
        else:
            return PRIVACY_SCORE_NO_TOOLS  # No tools

    async def _assign_subtask_to_worker(
        self,
        subtask: Subtask,
        worker: Worker
    ) -> None:
        """
        Assign subtask to worker and update all relevant states.

        Args:
            subtask: Subtask to assign
            worker: Worker to assign to
        """
        # Update subtask
        subtask.assigned_worker = worker.worker_id
        subtask.assigned_tool = subtask.recommended_tool or (
            worker.tools[0] if worker.tools else None
        )
        subtask.status = SubtaskStatus.QUEUED.value  # Will become in_progress when worker starts

        # Update worker status
        worker.status = "busy"

        # Commit database changes
        await self.db.commit()

        # Update Redis
        await self.redis.set_worker_current_task(
            worker_id=worker.worker_id,
            task_id=subtask.task_id
        )
        await self.redis.set_worker_status(
            worker_id=worker.worker_id,
            status="busy"
        )

        # Mark subtask as in progress in Redis
        await self.redis.mark_in_progress(subtask.subtask_id)

    async def _get_ready_subtasks(self, task_id: UUID) -> List[Subtask]:
        """Get subtasks that are ready for execution (dependencies satisfied)"""
        # Get all pending subtasks
        result = await self.db.execute(
            select(Subtask)
            .where(Subtask.task_id == task_id)
            .where(Subtask.status == SubtaskStatus.PENDING.value)
        )
        pending_subtasks = result.scalars().all()

        # Get completed subtask IDs
        completed_result = await self.db.execute(
            select(Subtask.subtask_id)
            .where(Subtask.task_id == task_id)
            .where(Subtask.status == SubtaskStatus.COMPLETED.value)
        )
        completed_ids = {str(row[0]) for row in completed_result.fetchall()}

        # Filter subtasks with all dependencies satisfied
        ready = []
        for subtask in pending_subtasks:
            deps = subtask.dependencies or []
            if all(dep_id in completed_ids for dep_id in deps):
                ready.append(subtask)

        return ready

    async def release_worker(self, worker_id: UUID) -> None:
        """
        Release a worker after task completion.

        Args:
            worker_id: Worker UUID to release
        """
        logger.info("Releasing worker", worker_id=str(worker_id))

        # Get worker
        result = await self.db.execute(
            select(Worker).where(Worker.worker_id == worker_id)
        )
        worker = result.scalar_one_or_none()

        if worker:
            worker.status = WorkerStatus.ONLINE.value
            await self.db.commit()

        # Clear Redis current task
        await self.redis.clear_worker_current_task(worker_id)
        await self.redis.set_worker_status(worker_id, WorkerStatus.ONLINE.value)

    def get_scoring_weights(self) -> Dict[str, float]:
        """Get current scoring weights"""
        return SCORING_WEIGHTS.copy()

    async def get_allocation_stats(self) -> Dict[str, Any]:
        """Get allocation statistics"""
        # Get queue length
        queue_length = await self.redis.get_queue_length()
        in_progress_count = await self.redis.get_in_progress_count()

        # Get worker counts by status
        online_workers = await self.redis.get_online_workers()

        # Get queued subtask count from DB
        result = await self.db.execute(
            select(Subtask).where(Subtask.status == SubtaskStatus.QUEUED.value)
        )
        queued_subtasks = len(result.scalars().all())

        return {
            "queue_length": queue_length,
            "in_progress_count": in_progress_count,
            "online_workers": len(online_workers),
            "queued_subtasks": queued_subtasks
        }
