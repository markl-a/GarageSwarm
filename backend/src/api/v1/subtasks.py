"""
Subtasks API

Subtask management and allocation endpoints.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.dependencies import get_db, get_redis_service
from src.auth.dependencies import require_auth
from src.models.user import User
from src.services.task_allocator import TaskAllocator
from src.services.task_scheduler import TaskScheduler
from src.services.redis_service import RedisService
from src.services.checkpoint_service import CheckpointService
from src.services.checkpoint_trigger import CheckpointTrigger, CheckpointTriggerConfig
from src.schemas.subtask import (
    SubtaskResponse,
    SubtaskListResponse,
    SubtaskStatus,
    SubtaskResultRequest,
    SubtaskResultResponse
)
from src.schemas.allocation import (
    AllocationRequest,
    AllocationResponse,
    BatchAllocationResponse,
    AllocationStatsResponse,
    WorkerScoreDetail
)
from src.schemas.scheduler import (
    SchedulingCycleResult,
    SubtaskCompletionResult,
    TaskScheduleResult,
    SchedulerStatsResponse
)
from src.models.subtask import Subtask
from sqlalchemy import select
from sqlalchemy.orm import selectinload

router = APIRouter()
logger = structlog.get_logger()


async def get_task_allocator(
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service)
) -> TaskAllocator:
    """Dependency to get TaskAllocator instance"""
    return TaskAllocator(db, redis_service)


async def get_task_scheduler(
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service)
) -> TaskScheduler:
    """Dependency to get TaskScheduler instance"""
    return TaskScheduler(db, redis_service)


async def get_checkpoint_service(
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service)
) -> CheckpointService:
    """Dependency to get CheckpointService instance"""
    return CheckpointService(db, redis_service)


async def get_checkpoint_trigger(
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service),
    checkpoint_service: CheckpointService = Depends(get_checkpoint_service)
) -> CheckpointTrigger:
    """Dependency to get CheckpointTrigger instance"""
    return CheckpointTrigger(db, redis_service, checkpoint_service)


@router.get(
    "/subtasks/{subtask_id}",
    response_model=SubtaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Subtask Details",
    description="Get detailed information about a specific subtask"
)
async def get_subtask(
    subtask_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Get detailed information about a specific subtask.

    **Path parameters:**
    - subtask_id: UUID of the subtask

    **Response:**
    - Complete subtask information
    - Returns 404 if subtask not found
    """
    try:
        result = await db.execute(
            select(Subtask).where(Subtask.subtask_id == subtask_id)
        )
        subtask = result.scalar_one_or_none()

        if not subtask:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subtask {subtask_id} not found"
            )

        return SubtaskResponse(
            subtask_id=subtask.subtask_id,
            task_id=subtask.task_id,
            name=subtask.name,
            description=subtask.description,
            status=SubtaskStatus(subtask.status),
            progress=subtask.progress,
            recommended_tool=subtask.recommended_tool,
            assigned_worker=subtask.assigned_worker,
            assigned_tool=subtask.assigned_tool,
            complexity=subtask.complexity,
            priority=subtask.priority,
            dependencies=subtask.dependencies or [],
            output=subtask.output,
            error=subtask.error,
            created_at=subtask.created_at,
            started_at=subtask.started_at,
            completed_at=subtask.completed_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get subtask failed", subtask_id=str(subtask_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subtask: {str(e)}"
        )


@router.post(
    "/subtasks/{subtask_id}/result",
    response_model=SubtaskResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload Subtask Result",
    description="Upload execution result for a subtask from worker"
)
async def upload_subtask_result(
    subtask_id: UUID,
    request: SubtaskResultRequest,
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service),
    scheduler: TaskScheduler = Depends(get_task_scheduler),
    allocator: TaskAllocator = Depends(get_task_allocator),
    checkpoint_trigger: CheckpointTrigger = Depends(get_checkpoint_trigger)
):
    """
    Upload subtask execution result from worker.

    This endpoint is called by workers when they complete a subtask execution.
    It updates the subtask status, stores the result, and triggers scheduling
    of newly ready subtasks.

    **Path parameters:**
    - subtask_id: UUID of the completed subtask

    **Request body:**
    - status: Execution status ("completed" or "failed")
    - result: Dict containing output data, files, metrics, etc.
    - execution_time: Execution duration in seconds
    - error: Optional error message if failed

    **Response:**
    - subtask_id: UUID of the updated subtask
    - status: New subtask status
    - progress: Subtask progress (100 if completed)
    - message: Result message
    - newly_allocated: Number of newly allocated subtasks

    **Process:**
    1. Validates subtask exists and is in progress
    2. Updates subtask record in PostgreSQL
    3. Updates Redis status cache
    4. Releases worker for new assignments
    5. Triggers scheduler to allocate newly ready subtasks
    """
    try:
        from datetime import datetime

        # Get the subtask
        result_query = await db.execute(
            select(Subtask)
            .where(Subtask.subtask_id == subtask_id)
            .options(selectinload(Subtask.task))
        )
        subtask = result_query.scalar_one_or_none()

        if not subtask:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subtask {subtask_id} not found"
            )

        if subtask.status not in ("in_progress", "queued"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subtask is not in progress. Current status: {subtask.status}"
            )

        # Validate status value
        if request.status not in (SubtaskStatus.COMPLETED, SubtaskStatus.FAILED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be 'completed' or 'failed', got: {request.status}"
            )

        # Update subtask record
        subtask.status = request.status.value
        subtask.output = request.result
        subtask.error = request.error
        subtask.completed_at = datetime.utcnow()

        if request.status == SubtaskStatus.COMPLETED:
            subtask.progress = 100
        elif request.status == SubtaskStatus.FAILED:
            subtask.progress = 0  # Reset progress on failure

        # Store execution time in output metadata
        if subtask.output:
            subtask.output["execution_time"] = request.execution_time
        else:
            subtask.output = {"execution_time": request.execution_time}

        await db.commit()
        await db.refresh(subtask)

        # Update Redis status cache
        await redis_service.set_subtask_status(
            subtask_id,
            request.status.value,
            ttl=3600
        )
        await redis_service.set_subtask_progress(
            subtask_id,
            subtask.progress,
            ttl=3600
        )

        # Remove from in-progress set in Redis
        await redis_service.remove_from_in_progress(subtask_id)

        # Release worker if assigned
        newly_allocated = 0
        if subtask.assigned_worker:
            try:
                await allocator.release_worker(subtask.assigned_worker)
                logger.info(
                    "Worker released",
                    worker_id=str(subtask.assigned_worker),
                    subtask_id=str(subtask_id)
                )
            except Exception as e:
                logger.warning(
                    "Failed to release worker",
                    worker_id=str(subtask.assigned_worker),
                    error=str(e)
                )

        # Trigger scheduler to check for newly ready subtasks (only on completion)
        if request.status == SubtaskStatus.COMPLETED:
            try:
                completion_result = await scheduler.on_subtask_complete(subtask_id)
                newly_allocated = completion_result.get("newly_allocated", 0)
                logger.info(
                    "Scheduling triggered",
                    subtask_id=str(subtask_id),
                    newly_allocated=newly_allocated
                )
            except Exception as e:
                logger.warning(
                    "Scheduler trigger failed",
                    subtask_id=str(subtask_id),
                    error=str(e)
                )

        # Check for automatic checkpoint triggers
        checkpoint_triggered = False
        checkpoint_id = None
        try:
            # Get evaluation score if available
            from src.models.evaluation import Evaluation
            eval_result = await db.execute(
                select(Evaluation)
                .where(Evaluation.subtask_id == subtask_id)
                .order_by(Evaluation.evaluated_at.desc())
                .limit(1)
            )
            latest_evaluation = eval_result.scalar_one_or_none()
            evaluation_score = None
            if latest_evaluation and latest_evaluation.overall_score:
                evaluation_score = float(latest_evaluation.overall_score)

            # Determine if error occurred
            error_occurred = (
                request.status == SubtaskStatus.FAILED or
                (request.error is not None and len(request.error.strip()) > 0)
            )

            # Check and trigger checkpoint if needed
            checkpoint = await checkpoint_trigger.check_and_trigger(
                task_id=subtask.task_id,
                subtask_id=subtask_id,
                evaluation_score=evaluation_score,
                error_occurred=error_occurred
            )

            if checkpoint:
                checkpoint_triggered = True
                checkpoint_id = checkpoint.checkpoint_id
                logger.info(
                    "Automatic checkpoint triggered",
                    checkpoint_id=str(checkpoint_id),
                    task_id=str(subtask.task_id),
                    subtask_id=str(subtask_id)
                )

        except Exception as e:
            logger.warning(
                "Checkpoint trigger check failed",
                subtask_id=str(subtask_id),
                error=str(e)
            )

        logger.info(
            "Subtask result uploaded",
            subtask_id=str(subtask_id),
            status=request.status.value,
            execution_time=request.execution_time,
            newly_allocated=newly_allocated,
            checkpoint_triggered=checkpoint_triggered
        )

        return SubtaskResultResponse(
            subtask_id=subtask_id,
            status=SubtaskStatus(subtask.status),
            progress=subtask.progress,
            message=f"Subtask result uploaded successfully. Status: {subtask.status}",
            newly_allocated=newly_allocated
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Upload subtask result failed",
            subtask_id=str(subtask_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload subtask result: {str(e)}"
        )


@router.post(
    "/subtasks/{subtask_id}/allocate",
    response_model=AllocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Allocate Subtask",
    description="Allocate a subtask to the best available worker"
)
async def allocate_subtask(
    subtask_id: UUID,
    allocator: TaskAllocator = Depends(get_task_allocator),
    current_user: User = Depends(require_auth)
):
    """
    Allocate a subtask to the best available worker using weighted scoring.

    The allocation algorithm considers:
    - Tool matching (50%): Whether the worker has the recommended tool
    - Resource availability (30%): Current CPU, memory, and disk usage
    - Privacy compatibility (20%): Task privacy level compatibility

    **Path parameters:**
    - subtask_id: UUID of the subtask to allocate

    **Response:**
    - subtask_id: UUID of the allocated subtask
    - worker_id: UUID of the assigned worker (null if no worker available)
    - status: Allocation status
    - message: Result message
    """
    try:
        worker = await allocator.allocate_subtask(subtask_id)

        if worker:
            return AllocationResponse(
                subtask_id=subtask_id,
                worker_id=worker.worker_id,
                assigned_tool=worker.tools[0] if worker.tools else None,
                status="allocated",
                message=f"Subtask allocated to worker {worker.machine_name}"
            )
        else:
            return AllocationResponse(
                subtask_id=subtask_id,
                worker_id=None,
                assigned_tool=None,
                status="queued",
                message="No available workers, subtask added to queue"
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Allocate subtask failed", subtask_id=str(subtask_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to allocate subtask: {str(e)}"
        )


@router.post(
    "/tasks/{task_id}/allocate",
    response_model=BatchAllocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Allocate Task Subtasks",
    description="Allocate all ready subtasks for a task"
)
async def allocate_task_subtasks(
    task_id: UUID,
    allocator: TaskAllocator = Depends(get_task_allocator),
    current_user: User = Depends(require_auth)
):
    """
    Allocate all ready subtasks for a task to available workers.

    A subtask is ready when all its dependencies are completed.

    **Path parameters:**
    - task_id: UUID of the parent task

    **Response:**
    - task_id: UUID of the task
    - allocations: List of allocation results
    - total_allocated: Number of subtasks successfully allocated
    - total_queued: Number of subtasks added to queue
    """
    try:
        allocations = await allocator.allocate_ready_subtasks(task_id)

        results = []
        allocated = 0
        queued = 0

        for subtask, worker in allocations:
            if worker:
                results.append(AllocationResponse(
                    subtask_id=subtask.subtask_id,
                    worker_id=worker.worker_id,
                    assigned_tool=worker.tools[0] if worker.tools else None,
                    status="allocated",
                    message=f"Allocated to {worker.machine_name}"
                ))
                allocated += 1
            else:
                results.append(AllocationResponse(
                    subtask_id=subtask.subtask_id,
                    worker_id=None,
                    assigned_tool=None,
                    status="queued",
                    message="No available workers"
                ))
                queued += 1

        return BatchAllocationResponse(
            task_id=task_id,
            allocations=results,
            total_allocated=allocated,
            total_queued=queued
        )

    except Exception as e:
        logger.error("Allocate task subtasks failed", task_id=str(task_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to allocate subtasks: {str(e)}"
        )


@router.post(
    "/subtasks/reallocate-queued",
    response_model=BatchAllocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Reallocate Queued Subtasks",
    description="Attempt to reallocate all queued subtasks"
)
async def reallocate_queued_subtasks(
    allocator: TaskAllocator = Depends(get_task_allocator),
    current_user: User = Depends(require_auth)
):
    """
    Attempt to reallocate all queued subtasks to available workers.

    This endpoint is typically called periodically by a scheduler.

    **Response:**
    - task_id: null (batch operation across tasks)
    - allocations: List of successful allocations
    - total_allocated: Number of subtasks allocated
    - total_queued: Remaining queued subtasks
    """
    try:
        allocations = await allocator.reallocate_queued_subtasks()

        results = [
            AllocationResponse(
                subtask_id=subtask.subtask_id,
                worker_id=worker.worker_id,
                assigned_tool=worker.tools[0] if worker.tools else None,
                status="allocated",
                message=f"Allocated to {worker.machine_name}"
            )
            for subtask, worker in allocations
        ]

        # Get remaining queued count
        stats = await allocator.get_allocation_stats()

        return BatchAllocationResponse(
            task_id=None,
            allocations=results,
            total_allocated=len(allocations),
            total_queued=stats["queued_subtasks"]
        )

    except Exception as e:
        logger.error("Reallocate queued subtasks failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reallocate subtasks: {str(e)}"
        )


@router.post(
    "/workers/{worker_id}/release",
    status_code=status.HTTP_200_OK,
    summary="Release Worker",
    description="Release a worker after task completion"
)
async def release_worker(
    worker_id: UUID,
    allocator: TaskAllocator = Depends(get_task_allocator),
    current_user: User = Depends(require_auth)
):
    """
    Release a worker so it can accept new tasks.

    Called when a worker completes its assigned subtask.

    **Path parameters:**
    - worker_id: UUID of the worker to release

    **Response:**
    - worker_id: UUID of the released worker
    - status: New status (online)
    - message: Confirmation message
    """
    try:
        await allocator.release_worker(worker_id)

        return {
            "worker_id": str(worker_id),
            "status": "online",
            "message": "Worker released successfully"
        }

    except Exception as e:
        logger.error("Release worker failed", worker_id=str(worker_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to release worker: {str(e)}"
        )


@router.get(
    "/allocation/stats",
    response_model=AllocationStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Allocation Stats",
    description="Get current allocation statistics"
)
async def get_allocation_stats(
    allocator: TaskAllocator = Depends(get_task_allocator),
    current_user: User = Depends(require_auth)
):
    """
    Get current allocation statistics.

    **Response:**
    - queue_length: Number of subtasks in Redis queue
    - in_progress_count: Number of subtasks being executed
    - online_workers: Number of online workers
    - queued_subtasks: Number of subtasks in queued status
    - scoring_weights: Current scoring algorithm weights
    """
    try:
        stats = await allocator.get_allocation_stats()
        weights = allocator.get_scoring_weights()

        return AllocationStatsResponse(
            queue_length=stats["queue_length"],
            in_progress_count=stats["in_progress_count"],
            online_workers=stats["online_workers"],
            queued_subtasks=stats["queued_subtasks"],
            scoring_weights=weights
        )

    except Exception as e:
        logger.error("Get allocation stats failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get allocation stats: {str(e)}"
        )


# ==================== Scheduler Endpoints ====================


@router.post(
    "/scheduler/run",
    response_model=SchedulingCycleResult,
    status_code=status.HTTP_200_OK,
    summary="Run Scheduling Cycle",
    description="Manually trigger a scheduling cycle"
)
async def run_scheduling_cycle(
    scheduler: TaskScheduler = Depends(get_task_scheduler),
    current_user: User = Depends(require_auth)
):
    """
    Manually trigger a scheduling cycle.

    This endpoint runs a single scheduling cycle to:
    - Find all active tasks (initializing or in_progress)
    - Identify ready subtasks (dependencies satisfied)
    - Allocate them to available workers
    - Respect concurrency limits

    **Response:**
    - cycle_start: Start timestamp
    - cycle_end: End timestamp
    - tasks_processed: Number of tasks processed
    - subtasks_allocated: Number of subtasks allocated
    - subtasks_queued: Number of subtasks queued
    - errors: List of any errors encountered
    """
    try:
        result = await scheduler.run_scheduling_cycle()

        return SchedulingCycleResult(
            cycle_start=result.get("cycle_start", ""),
            cycle_end=result.get("cycle_end"),
            tasks_processed=result.get("tasks_processed", 0),
            subtasks_allocated=result.get("subtasks_allocated", 0),
            subtasks_queued=result.get("subtasks_queued", 0),
            errors=result.get("errors", []),
            message=result.get("message")
        )

    except Exception as e:
        logger.error("Scheduling cycle failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scheduling cycle failed: {str(e)}"
        )


@router.post(
    "/subtasks/{subtask_id}/complete",
    response_model=SubtaskCompletionResult,
    status_code=status.HTTP_200_OK,
    summary="Handle Subtask Completion",
    description="Notify scheduler that a subtask has completed"
)
async def handle_subtask_completion(
    subtask_id: UUID,
    scheduler: TaskScheduler = Depends(get_task_scheduler)
):
    """
    Handle subtask completion event.

    Called when a subtask finishes to:
    - Check if the parent task is complete
    - Identify newly ready subtasks
    - Allocate them to available workers

    **Path parameters:**
    - subtask_id: UUID of the completed subtask

    **Response:**
    - subtask_id: UUID of the completed subtask
    - newly_allocated: Number of newly allocated subtasks
    - task_completed: Whether the parent task is now complete
    """
    try:
        result = await scheduler.on_subtask_complete(subtask_id)

        return SubtaskCompletionResult(
            subtask_id=result.get("subtask_id", str(subtask_id)),
            newly_allocated=result.get("newly_allocated", 0),
            task_completed=result.get("task_completed", False),
            error=result.get("error")
        )

    except Exception as e:
        logger.error("Handle subtask completion failed", subtask_id=str(subtask_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle subtask completion: {str(e)}"
        )


@router.post(
    "/tasks/{task_id}/schedule",
    response_model=TaskScheduleResult,
    status_code=status.HTTP_200_OK,
    summary="Schedule Task",
    description="Schedule a specific task's subtasks"
)
async def schedule_task(
    task_id: UUID,
    scheduler: TaskScheduler = Depends(get_task_scheduler),
    current_user: User = Depends(require_auth)
):
    """
    Schedule a specific task's subtasks.

    If the task is pending, it will be decomposed first.
    Then ready subtasks will be allocated to available workers.

    **Path parameters:**
    - task_id: UUID of the task to schedule

    **Response:**
    - task_id: UUID of the task
    - subtasks_allocated: Number of subtasks allocated
    - subtasks_queued: Number of subtasks queued
    """
    try:
        result = await scheduler.schedule_task(task_id)

        return TaskScheduleResult(
            task_id=result.get("task_id", str(task_id)),
            subtasks_allocated=result.get("subtasks_allocated", 0),
            subtasks_queued=result.get("subtasks_queued", 0),
            error=result.get("error")
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Schedule task failed", task_id=str(task_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule task: {str(e)}"
        )


@router.get(
    "/scheduler/stats",
    response_model=SchedulerStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Scheduler Stats",
    description="Get current scheduler statistics"
)
async def get_scheduler_stats(
    scheduler: TaskScheduler = Depends(get_task_scheduler),
    current_user: User = Depends(require_auth)
):
    """
    Get current scheduler statistics.

    **Response:**
    - active_tasks: Number of active tasks
    - available_workers: Number of available workers
    - subtask_status_counts: Subtask counts by status
    - queue_length: Number of subtasks in Redis queue
    - in_progress_count: Number of in-progress subtasks
    - max_concurrent_subtasks: System-wide concurrency limit
    - max_subtasks_per_worker: Per-worker concurrency limit
    - scheduler_interval_seconds: Scheduling interval
    """
    try:
        stats = await scheduler.get_scheduler_stats()

        return SchedulerStatsResponse(
            active_tasks=stats.get("active_tasks", 0),
            available_workers=stats.get("available_workers", 0),
            subtask_status_counts=stats.get("subtask_status_counts", {}),
            queue_length=stats.get("queue_length", 0),
            in_progress_count=stats.get("in_progress_count", 0),
            max_concurrent_subtasks=stats.get("max_concurrent_subtasks", 20),
            max_subtasks_per_worker=stats.get("max_subtasks_per_worker", 1),
            scheduler_interval_seconds=stats.get("scheduler_interval_seconds", 30)
        )

    except Exception as e:
        logger.error("Get scheduler stats failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler stats: {str(e)}"
        )
