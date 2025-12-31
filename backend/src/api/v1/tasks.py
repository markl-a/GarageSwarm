"""
Tasks API

Task management endpoints for creating, listing, and managing tasks.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.dependencies import get_db, get_redis_service
from src.auth.dependencies import require_auth
from src.models.user import User
from src.services.task_service import TaskService
from src.services.task_decomposer import TaskDecomposer
from src.services.redis_service import RedisService
from src.exceptions import NotFoundError, ValidationError, create_http_exception
from src.schemas.task import (
    TaskCreateRequest,
    TaskCreateResponse,
    TaskDetailResponse,
    TaskListResponse,
    TaskCancelResponse,
    TaskProgressResponse,
    TaskSummary,
    TaskStatus,
    SubtaskSummary,
    EvaluationScores,
    TaskPriority,
    TaskPriorityUpdateRequest,
    BatchTaskRequest,
    BatchOperationResult,
    BatchOperationResponse,
    TaskAnalytics,
    WorkerAnalytics,
    SystemAnalytics
)
from src.services.analytics_service import AnalyticsService
from src.schemas.subtask import (
    TaskDecomposeResponse,
    ReadySubtasksResponse,
    SubtaskResponse,
    SubtaskStatus
)

router = APIRouter()
logger = structlog.get_logger()


async def get_task_service(
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service)
) -> TaskService:
    """Dependency to get TaskService instance"""
    return TaskService(db, redis_service)


async def get_task_decomposer(
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service)
) -> TaskDecomposer:
    """Dependency to get TaskDecomposer instance"""
    return TaskDecomposer(db, redis_service)


async def get_analytics_service(
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service)
) -> AnalyticsService:
    """Dependency to get AnalyticsService instance"""
    return AnalyticsService(db, redis_service)


@router.post(
    "/tasks",
    response_model=TaskCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Task",
    description="Submit a new task for processing by AI agents"
)
async def create_task(
    request: TaskCreateRequest,
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(require_auth)
):
    """
    Create a new task for AI agent processing.

    **Required fields:**
    - description: Task description (supports Markdown, 10-10000 chars)

    **Optional fields:**
    - task_type: Type of task (develop_feature, bug_fix, refactor, etc.)
    - requirements: Additional requirements as JSON object
    - checkpoint_frequency: How often to create checkpoints (low, medium, high)
    - privacy_level: Privacy level for the task (normal, sensitive)
    - tool_preferences: Preferred AI tools for task execution

    **Response:**
    - task_id: UUID of the created task
    - status: Initial task status (pending)
    - message: Confirmation message
    """
    try:
        logger.info("Creating task", user_id=str(current_user.user_id))
        task = await task_service.create_task(
            description=request.description,
            task_type=request.task_type.value,
            requirements=request.requirements,
            checkpoint_frequency=request.checkpoint_frequency.value,
            privacy_level=request.privacy_level.value,
            tool_preferences=request.tool_preferences
        )
        logger.info("Task created successfully", task_id=str(task.task_id))

        return TaskCreateResponse(
            task_id=task.task_id,
            status=TaskStatus(task.status),
            message="Task created successfully"
        )
    except ValidationError:
        raise
    except Exception as e:
        raise create_http_exception(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "create", e, logger
        )


@router.get(
    "/tasks",
    response_model=TaskListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Tasks",
    description="Get list of all tasks with optional filtering and pagination"
)
async def list_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status", description="Filter by task status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(require_auth)
):
    """
    List all tasks with optional filtering.

    **Query parameters:**
    - status: Filter by task status (pending, in_progress, completed, etc.)
    - limit: Maximum number of results (1-100, default 50)
    - offset: Offset for pagination (default 0)

    **Response:**
    - tasks: List of task summaries
    - total: Total number of tasks matching the filter
    - limit: Applied limit
    - offset: Applied offset
    """
    try:
        logger.debug("Listing tasks", status=status_filter, limit=limit, offset=offset)
        status_str = status_filter.value if status_filter else None
        tasks, total = await task_service.list_tasks(
            status=status_str,
            limit=limit,
            offset=offset
        )

        task_summaries = [
            TaskSummary(
                task_id=task.task_id,
                description=task.description[:200] if len(task.description) > 200 else task.description,
                status=TaskStatus(task.status),
                progress=task.progress,
                created_at=task.created_at,
                updated_at=task.updated_at
            )
            for task in tasks
        ]

        return TaskListResponse(
            tasks=task_summaries,
            total=total,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise create_http_exception(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "list", e, logger
        )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Task Details",
    description="Get detailed information about a specific task with real-time status"
)
async def get_task(
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(require_auth)
):
    """
    Get detailed information about a specific task.

    This endpoint combines:
    - Static data from PostgreSQL (task details, subtasks)
    - Real-time data from Redis (current status, progress)
    - Evaluation scores for each subtask

    **Path parameters:**
    - task_id: UUID of the task

    **Response:**
    - Complete task information including subtasks with real-time status
    - Evaluation scores for completed subtasks
    - Returns 404 if task not found
    """
    try:
        logger.debug("Getting task details", task_id=str(task_id))
        # Use the new method that combines Redis and DB data
        task_data = await task_service.get_task_with_realtime_status(task_id)

        if not task_data:
            raise NotFoundError("Task", str(task_id))

        # Build subtask summaries with evaluation scores
        subtask_summaries = [
            SubtaskSummary(
                subtask_id=subtask["subtask_id"],
                name=subtask["name"],
                status=subtask["status"],
                progress=subtask["progress"],
                assigned_worker=subtask["assigned_worker"],
                assigned_tool=subtask["assigned_tool"],
                evaluation=EvaluationScores(**subtask["evaluation"]) if subtask["evaluation"] else None
            )
            for subtask in task_data["subtasks"]
        ]

        return TaskDetailResponse(
            task_id=task_data["task_id"],
            description=task_data["description"],
            status=TaskStatus(task_data["status"]),
            progress=task_data["progress"],
            checkpoint_frequency=task_data["checkpoint_frequency"],
            privacy_level=task_data["privacy_level"],
            tool_preferences=task_data["tool_preferences"],
            task_metadata=task_data["task_metadata"],
            subtasks=subtask_summaries,
            created_at=task_data["created_at"],
            updated_at=task_data["updated_at"],
            started_at=task_data["started_at"],
            completed_at=task_data["completed_at"]
        )
    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to get task details", task_id=str(task_id), error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task details: {str(e)}"
        )


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=TaskCancelResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Task",
    description="Cancel a pending or in-progress task"
)
async def cancel_task(
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(require_auth)
):
    """
    Cancel a task.

    Can only cancel tasks that are pending or in progress.
    Completed, failed, or already cancelled tasks cannot be cancelled.

    **Path parameters:**
    - task_id: UUID of the task to cancel

    **Response:**
    - task_id: UUID of the cancelled task
    - status: New status (cancelled)
    - message: Confirmation message
    """
    try:
        logger.info("Cancelling task", task_id=str(task_id), user_id=str(current_user.user_id))
        await task_service.cancel_task(task_id)
        logger.info("Task cancelled successfully", task_id=str(task_id))

        return TaskCancelResponse(
            task_id=task_id,
            status=TaskStatus.CANCELLED,
            message="Task cancelled successfully"
        )
    except NotFoundError:
        raise
    except ValidationError:
        raise
    except Exception as e:
        logger.error("Failed to cancel task", task_id=str(task_id), error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {str(e)}"
        )


@router.get(
    "/tasks/{task_id}/progress",
    response_model=TaskProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Task Progress",
    description="Get real-time task progress from Redis cache"
)
async def get_task_progress(
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(require_auth)
):
    """
    Get real-time task progress from Redis.

    This endpoint returns the cached progress from Redis for faster access.
    Use this for frequent polling of task status.

    **Path parameters:**
    - task_id: UUID of the task

    **Response:**
    - task_id: UUID of the task
    - status: Current task status
    - progress: Current progress percentage (0-100)
    """
    try:
        logger.debug("Getting task progress", task_id=str(task_id))
        progress_data = await task_service.get_task_progress(task_id)

        if not progress_data:
            raise NotFoundError("Task", str(task_id))

        # Ensure proper types for response
        return TaskProgressResponse(
            task_id=str(progress_data["task_id"]),
            status=progress_data["status"].decode() if isinstance(progress_data["status"], bytes) else progress_data["status"],
            progress=int(progress_data["progress"]) if progress_data["progress"] is not None else None
        )
    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to get task progress", task_id=str(task_id), error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task progress: {str(e)}"
        )


@router.post(
    "/tasks/{task_id}/decompose",
    response_model=TaskDecomposeResponse,
    status_code=status.HTTP_200_OK,
    summary="Decompose Task",
    description="Decompose a task into subtasks based on its type"
)
async def decompose_task(
    task_id: UUID,
    decomposer: TaskDecomposer = Depends(get_task_decomposer),
    current_user: User = Depends(require_auth)
):
    """
    Decompose a task into subtasks using rule-based decomposition.

    The task type determines the decomposition strategy:
    - develop_feature: Code Generation → Code Review → Test Generation → Documentation
    - bug_fix: Bug Analysis → Fix Implementation → Regression Testing
    - refactor: Code Analysis → Refactoring → Test Verification
    - code_review: Static Analysis + Security Review → Review Report
    - documentation: API Documentation + User Guide → README Update
    - testing: Test Planning → Unit Tests + Integration Tests → Test Report

    **Path parameters:**
    - task_id: UUID of the task to decompose

    **Response:**
    - task_id: UUID of the task
    - subtask_count: Number of subtasks created
    - subtasks: List of created subtasks
    - message: Confirmation message
    """
    try:
        logger.info("Decomposing task", task_id=str(task_id), user_id=str(current_user.user_id))
        subtasks = await decomposer.decompose_task(task_id)

        subtask_responses = [
            SubtaskResponse(
                subtask_id=s.subtask_id,
                task_id=s.task_id,
                name=s.name,
                description=s.description,
                status=SubtaskStatus(s.status),
                progress=s.progress,
                recommended_tool=s.recommended_tool,
                assigned_worker=s.assigned_worker,
                assigned_tool=s.assigned_tool,
                complexity=s.complexity,
                priority=s.priority,
                dependencies=s.dependencies or [],
                output=s.output,
                error=s.error,
                created_at=s.created_at,
                started_at=s.started_at,
                completed_at=s.completed_at
            )
            for s in subtasks
        ]
        logger.info("Task decomposed successfully", task_id=str(task_id), subtask_count=len(subtasks))

        return TaskDecomposeResponse(
            task_id=task_id,
            subtask_count=len(subtasks),
            subtasks=subtask_responses,
            message=f"Task decomposed into {len(subtasks)} subtasks"
        )
    except NotFoundError:
        raise
    except ValidationError:
        raise
    except Exception as e:
        logger.error("Failed to decompose task", task_id=str(task_id), error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decompose task: {str(e)}"
        )


@router.get(
    "/tasks/{task_id}/ready-subtasks",
    response_model=ReadySubtasksResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Ready Subtasks",
    description="Get subtasks that are ready for execution (all dependencies satisfied)"
)
async def get_ready_subtasks(
    task_id: UUID,
    decomposer: TaskDecomposer = Depends(get_task_decomposer),
    current_user: User = Depends(require_auth)
):
    """
    Get subtasks that are ready for execution.

    A subtask is ready when:
    - Its status is "pending"
    - All its dependencies are "completed"

    **Path parameters:**
    - task_id: UUID of the task

    **Response:**
    - task_id: UUID of the task
    - ready_subtasks: List of subtasks ready for execution
    - total_ready: Number of ready subtasks
    """
    try:
        logger.debug("Getting ready subtasks", task_id=str(task_id))
        ready = await decomposer.get_ready_subtasks(task_id)

        subtask_responses = [
            SubtaskResponse(
                subtask_id=s.subtask_id,
                task_id=s.task_id,
                name=s.name,
                description=s.description,
                status=SubtaskStatus(s.status),
                progress=s.progress,
                recommended_tool=s.recommended_tool,
                assigned_worker=s.assigned_worker,
                assigned_tool=s.assigned_tool,
                complexity=s.complexity,
                priority=s.priority,
                dependencies=s.dependencies or [],
                output=s.output,
                error=s.error,
                created_at=s.created_at,
                started_at=s.started_at,
                completed_at=s.completed_at
            )
            for s in ready
        ]

        return ReadySubtasksResponse(
            task_id=task_id,
            ready_subtasks=subtask_responses,
            total_ready=len(ready)
        )
    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to get ready subtasks", task_id=str(task_id), error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ready subtasks: {str(e)}"
        )


# =============================================================================
# Priority Management
# =============================================================================

@router.patch(
    "/tasks/{task_id}/priority",
    status_code=status.HTTP_200_OK,
    summary="Update Task Priority",
    description="Update the priority level of a task"
)
async def update_task_priority(
    task_id: UUID,
    request: TaskPriorityUpdateRequest,
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(require_auth)
):
    """
    Update task priority level.

    Priority levels (affects scheduling order):
    - low: Background tasks
    - normal: Default priority (default)
    - high: Important tasks
    - urgent: Critical tasks (scheduled first)

    **Path parameters:**
    - task_id: UUID of the task

    **Request body:**
    - priority: New priority level
    """
    try:
        task = await task_service.get_task(task_id)
        if not task:
            raise NotFoundError("Task", str(task_id))

        # Update priority in task_metadata
        if task.task_metadata is None:
            task.task_metadata = {}
        task.task_metadata["priority"] = request.priority.value

        await task_service.db.commit()

        return {
            "task_id": str(task_id),
            "priority": request.priority.value,
            "message": "Priority updated successfully"
        }
    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to update priority", task_id=str(task_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update priority: {str(e)}"
        )


# =============================================================================
# Batch Operations
# =============================================================================

@router.post(
    "/tasks/batch/cancel",
    response_model=BatchOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch Cancel Tasks",
    description="Cancel multiple tasks at once"
)
async def batch_cancel_tasks(
    request: BatchTaskRequest,
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(require_auth)
):
    """
    Cancel multiple tasks in a single request.

    **Request body:**
    - task_ids: List of task UUIDs to cancel (max 100)

    **Response:**
    - operation: "cancel"
    - total: Total tasks in request
    - successful: Successfully cancelled tasks
    - failed: Failed tasks
    - results: Individual results for each task
    """
    logger.info("Batch cancel", task_count=len(request.task_ids), user_id=str(current_user.user_id))

    results = []
    successful = 0
    failed = 0

    for task_id in request.task_ids:
        try:
            await task_service.cancel_task(task_id)
            results.append(BatchOperationResult(
                task_id=task_id,
                success=True,
                message="Cancelled"
            ))
            successful += 1
        except ValueError as e:
            results.append(BatchOperationResult(
                task_id=task_id,
                success=False,
                error=str(e)
            ))
            failed += 1
        except Exception as e:
            results.append(BatchOperationResult(
                task_id=task_id,
                success=False,
                error=f"Unexpected error: {str(e)}"
            ))
            failed += 1

    return BatchOperationResponse(
        operation="cancel",
        total=len(request.task_ids),
        successful=successful,
        failed=failed,
        results=results
    )


@router.post(
    "/tasks/batch/priority",
    response_model=BatchOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch Update Priority",
    description="Update priority for multiple tasks"
)
async def batch_update_priority(
    request: BatchTaskRequest,
    priority: TaskPriority = Query(..., description="New priority level"),
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(require_auth)
):
    """
    Update priority for multiple tasks.

    **Query parameters:**
    - priority: New priority level for all tasks

    **Request body:**
    - task_ids: List of task UUIDs (max 100)
    """
    logger.info("Batch priority update", task_count=len(request.task_ids), priority=priority.value)

    results = []
    successful = 0
    failed = 0

    for task_id in request.task_ids:
        try:
            task = await task_service.get_task(task_id)
            if not task:
                results.append(BatchOperationResult(
                    task_id=task_id,
                    success=False,
                    error="Task not found"
                ))
                failed += 1
                continue

            if task.task_metadata is None:
                task.task_metadata = {}
            task.task_metadata["priority"] = priority.value

            results.append(BatchOperationResult(
                task_id=task_id,
                success=True,
                message=f"Priority set to {priority.value}"
            ))
            successful += 1
        except Exception as e:
            results.append(BatchOperationResult(
                task_id=task_id,
                success=False,
                error=str(e)
            ))
            failed += 1

    await task_service.db.commit()

    return BatchOperationResponse(
        operation="priority_update",
        total=len(request.task_ids),
        successful=successful,
        failed=failed,
        results=results
    )


# =============================================================================
# Analytics
# =============================================================================

@router.get(
    "/analytics/tasks",
    response_model=TaskAnalytics,
    status_code=status.HTTP_200_OK,
    summary="Get Task Analytics",
    description="Get comprehensive task analytics and statistics"
)
async def get_task_analytics(
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(require_auth)
):
    """
    Get task analytics including:
    - Total tasks count
    - Tasks by status
    - Tasks by priority
    - Average completion time
    - Completion and failure rates
    - Active and pending task counts
    """
    try:
        analytics = await analytics_service.get_task_analytics()
        return TaskAnalytics(**analytics)
    except Exception as e:
        logger.error("Failed to get task analytics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )


@router.get(
    "/analytics/workers",
    response_model=WorkerAnalytics,
    status_code=status.HTTP_200_OK,
    summary="Get Worker Analytics",
    description="Get worker performance analytics"
)
async def get_worker_analytics(
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(require_auth)
):
    """
    Get worker analytics including:
    - Total workers
    - Workers by status
    - Top performers
    - Average tasks per worker
    """
    try:
        analytics = await analytics_service.get_worker_analytics()
        return WorkerAnalytics(**analytics)
    except Exception as e:
        logger.error("Failed to get worker analytics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )


@router.get(
    "/analytics/system",
    response_model=SystemAnalytics,
    status_code=status.HTTP_200_OK,
    summary="Get System Analytics",
    description="Get comprehensive system-wide analytics"
)
async def get_system_analytics(
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(require_auth)
):
    """
    Get complete system analytics including:
    - Task analytics
    - Worker analytics
    - Subtask status distribution
    - Queue length
    - Throughput (tasks/hour)
    """
    try:
        analytics = await analytics_service.get_system_analytics()
        return SystemAnalytics(**analytics)
    except Exception as e:
        logger.error("Failed to get system analytics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )


@router.get(
    "/analytics/daily",
    status_code=status.HTTP_200_OK,
    summary="Get Daily Summary",
    description="Get daily task summary for the last N days"
)
async def get_daily_summary(
    days: int = Query(7, ge=1, le=30, description="Number of days"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(require_auth)
):
    """
    Get daily task summary including:
    - Tasks created per day
    - Tasks completed per day
    - Tasks failed per day
    """
    try:
        summary = await analytics_service.get_daily_summary(days=days)
        return {"days": days, "summary": summary}
    except Exception as e:
        logger.error("Failed to get daily summary", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get summary: {str(e)}"
        )


@router.get(
    "/tasks/{task_id}/timeline",
    status_code=status.HTTP_200_OK,
    summary="Get Task Timeline",
    description="Get detailed execution timeline for a task"
)
async def get_task_timeline(
    task_id: UUID,
    include_subtasks: bool = Query(True, description="Include subtask timelines"),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    current_user: User = Depends(require_auth)
):
    """
    Get task execution timeline including:
    - Task creation, start, and completion times
    - Duration
    - Subtask timelines (optional)
    """
    try:
        timeline = await analytics_service.get_task_timeline(
            task_id=task_id,
            include_subtasks=include_subtasks
        )
        if not timeline:
            raise NotFoundError("Task", str(task_id))
        return timeline
    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Failed to get task timeline", task_id=str(task_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get timeline: {str(e)}"
        )
