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
from src.exceptions import NotFoundError, ValidationError
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
    EvaluationScores
)
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
        logger.error("Failed to create task", error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
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
        logger.error("Failed to list tasks", error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}"
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
