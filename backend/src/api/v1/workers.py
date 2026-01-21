"""
Worker Endpoints

Worker registration, heartbeat, and management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.database import get_db
from src.models.worker import Worker
from src.models.task import Task
from src.models.user import User
from src.models.user_worker import UserWorker, WorkerRole
from src.schemas.worker import (
    WorkerRegister,
    WorkerHeartbeat,
    WorkerResponse,
    WorkerListResponse,
    WorkerTaskAssignment,
    TaskCompleteRequest,
    TaskFailedRequest,
    TaskResultReport,
    TaskResultResponse,
)
from src.auth.dependencies import get_current_active_user, get_optional_user
from src.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=WorkerListResponse)
async def list_workers(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List workers accessible to the current user.
    """
    # Get worker IDs user has access to
    user_worker_query = select(UserWorker.worker_id).where(
        UserWorker.user_id == current_user.user_id,
        UserWorker.is_active == True,
    )

    query = select(Worker).where(Worker.worker_id.in_(user_worker_query))

    if status:
        query = query.where(Worker.status == status)

    query = query.order_by(Worker.registered_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    workers = result.scalars().all()

    # Get total count
    count_query = select(func.count()).select_from(Worker).where(
        Worker.worker_id.in_(user_worker_query)
    )
    if status:
        count_query = count_query.where(Worker.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return WorkerListResponse(
        workers=[WorkerResponse.model_validate(w) for w in workers],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/register", response_model=WorkerResponse, status_code=status.HTTP_201_CREATED)
async def register_worker(
    data: WorkerRegister,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new worker or update existing one.
    """
    # Check if worker exists
    result = await db.execute(
        select(Worker).where(Worker.machine_id == data.machine_id)
    )
    worker = result.scalar_one_or_none()

    if worker:
        # Update existing worker
        worker.machine_name = data.machine_name
        worker.tools = data.tools
        worker.system_info = data.system_info
        worker.status = "idle"
        worker.last_heartbeat = datetime.utcnow()

        logger.info("Worker updated", worker_id=str(worker.worker_id))
    else:
        # Create new worker
        worker = Worker(
            machine_id=data.machine_id,
            machine_name=data.machine_name,
            tools=data.tools,
            system_info=data.system_info,
            status="idle",
            last_heartbeat=datetime.utcnow(),
        )
        db.add(worker)
        await db.flush()

        # If user is authenticated, create ownership association
        if current_user:
            user_worker = UserWorker(
                user_id=current_user.user_id,
                worker_id=worker.worker_id,
                role=WorkerRole.OWNER.value,
            )
            db.add(user_worker)

        logger.info("Worker registered", worker_id=str(worker.worker_id))

    await db.commit()
    await db.refresh(worker)

    return worker


@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(
    worker_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific worker.
    """
    # Check user has access
    result = await db.execute(
        select(UserWorker).where(
            UserWorker.worker_id == worker_id,
            UserWorker.user_id == current_user.user_id,
            UserWorker.is_active == True,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    result = await db.execute(
        select(Worker).where(Worker.worker_id == worker_id)
    )
    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    return worker


@router.post("/{worker_id}/heartbeat", response_model=WorkerResponse)
async def worker_heartbeat(
    worker_id: UUID,
    data: WorkerHeartbeat,
    db: AsyncSession = Depends(get_db),
):
    """
    Update worker heartbeat and status.
    """
    result = await db.execute(
        select(Worker).where(Worker.worker_id == worker_id)
    )
    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    worker.status = data.status
    worker.cpu_percent = data.cpu_percent
    worker.memory_percent = data.memory_percent
    worker.disk_percent = data.disk_percent
    worker.last_heartbeat = datetime.utcnow()

    if data.tools:
        worker.tools = data.tools

    await db.commit()
    await db.refresh(worker)

    return worker


@router.get("/{worker_id}/pull-task", response_model=Optional[WorkerTaskAssignment])
async def pull_task(
    worker_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Pull a pending task for the worker (Pull mode).
    """
    result = await db.execute(
        select(Worker).where(Worker.worker_id == worker_id)
    )
    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    if not worker.is_available():
        return None

    # Find a pending task that matches worker's tools
    query = select(Task).where(
        Task.status == "pending",
        Task.worker_id.is_(None),
    )

    # Filter by tool preference if worker has tools
    if worker.tools:
        query = query.where(
            (Task.tool_preference.is_(None)) |
            (Task.tool_preference.in_(worker.tools))
        )

    query = query.order_by(Task.priority.desc(), Task.created_at.asc()).limit(1)

    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        return None

    # Assign task to worker
    task.worker_id = worker_id
    task.status = "assigned"
    worker.status = "busy"

    await db.commit()
    await db.refresh(task)

    logger.info(
        "Task pulled",
        task_id=str(task.task_id),
        worker_id=str(worker_id),
    )

    return WorkerTaskAssignment(
        task_id=task.task_id,
        description=task.description,
        tool_preference=task.tool_preference,
        priority=task.priority,
        workflow_id=task.workflow_id,
        metadata=task.task_metadata,
    )


@router.post("/{worker_id}/task-complete")
async def complete_task(
    worker_id: UUID,
    data: TaskCompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Report task completion from worker.
    """
    # Verify worker
    result_worker = await db.execute(
        select(Worker).where(Worker.worker_id == worker_id)
    )
    worker = result_worker.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    # Find and update task
    result_task = await db.execute(
        select(Task).where(
            Task.task_id == data.task_id,
            Task.worker_id == worker_id,
        )
    )
    task = result_task.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    task.status = "completed"
    task.result = data.result
    task.progress = 100
    task.completed_at = datetime.utcnow()
    task.version += 1

    worker.status = "idle"

    await db.commit()

    logger.info(
        "Task completed",
        task_id=str(data.task_id),
        worker_id=str(worker_id),
    )

    return {"status": "success"}


@router.post("/{worker_id}/task-failed")
async def fail_task(
    worker_id: UUID,
    data: TaskFailedRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Report task failure from worker.
    """
    # Verify worker
    result_worker = await db.execute(
        select(Worker).where(Worker.worker_id == worker_id)
    )
    worker = result_worker.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    # Find and update task
    result_task = await db.execute(
        select(Task).where(
            Task.task_id == data.task_id,
            Task.worker_id == worker_id,
        )
    )
    task = result_task.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    task.status = "failed"
    task.error = data.error
    task.completed_at = datetime.utcnow()
    task.version += 1

    worker.status = "idle"

    await db.commit()

    logger.info(
        "Task failed",
        task_id=str(data.task_id),
        worker_id=str(worker_id),
        error=data.error,
    )

    return {"status": "success"}


@router.post("/{worker_id}/report-result", response_model=TaskResultResponse)
async def report_task_result(
    worker_id: UUID,
    data: TaskResultReport,
    db: AsyncSession = Depends(get_db),
):
    """
    Report task result from worker with execution metrics.

    This is a unified endpoint for reporting task completion, failure, or cancellation.
    It provides more detailed metrics than the separate task-complete/task-failed endpoints.
    """
    # Verify worker exists
    result_worker = await db.execute(
        select(Worker).where(Worker.worker_id == worker_id)
    )
    worker = result_worker.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )

    # Find task and validate it belongs to this worker
    result_task = await db.execute(
        select(Task).where(Task.task_id == data.task_id)
    )
    task = result_task.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Validate task belongs to this worker
    if task.worker_id != worker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Task is not assigned to this worker",
        )

    # Validate task is in a state that can be updated
    if task.status in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task is already in terminal state: {task.status}",
        )

    # Update task status
    task.status = data.status
    task.completed_at = datetime.utcnow()
    task.version += 1

    # Set result or error based on status
    if data.status == "completed":
        task.result = data.result or {}
        task.progress = 100
        message = "Task completed successfully"
    elif data.status == "failed":
        task.error = data.error
        task.result = data.result  # May contain partial results
        message = f"Task failed: {data.error}" if data.error else "Task failed"
    else:  # cancelled
        task.error = data.error or "Task was cancelled"
        message = "Task was cancelled"

    # Store execution metrics in task metadata
    if task.task_metadata is None:
        task.task_metadata = {}

    task.task_metadata["execution_time_ms"] = data.execution_time_ms
    if data.metrics:
        task.task_metadata["metrics"] = data.metrics

    # Set worker back to idle
    worker.status = "idle"

    await db.commit()

    logger.info(
        "Task result reported",
        task_id=str(data.task_id),
        worker_id=str(worker_id),
        status=data.status,
        execution_time_ms=data.execution_time_ms,
        metrics=data.metrics,
    )

    return TaskResultResponse(
        status="success",
        task_id=data.task_id,
        task_status=data.status,
        message=message,
    )
