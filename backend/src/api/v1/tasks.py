"""
Task Endpoints

Task CRUD operations and management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.database import get_db
from src.models.task import Task
from src.models.user import User
from src.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
from src.auth.dependencies import get_current_active_user
from src.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List tasks for the current user.
    """
    query = select(Task).where(Task.user_id == current_user.user_id)

    if status:
        query = query.where(Task.status == status)

    query = query.order_by(Task.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    tasks = result.scalars().all()

    # Get total count
    count_query = select(func.count()).select_from(Task).where(
        Task.user_id == current_user.user_id
    )
    if status:
        count_query = count_query.where(Task.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new task.
    """
    task = Task(
        user_id=current_user.user_id,
        description=data.description,
        tool_preference=data.tool_preference,
        priority=data.priority,
        workflow_id=data.workflow_id,
        task_metadata=data.metadata,
        status="pending",
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(
        "Task created",
        task_id=str(task.task_id),
        user_id=str(current_user.user_id),
    )

    return task


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific task.
    """
    result = await db.execute(
        select(Task).where(
            Task.task_id == task_id,
            Task.user_id == current_user.user_id,
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    data: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a task.
    """
    result = await db.execute(
        select(Task).where(
            Task.task_id == task_id,
            Task.user_id == current_user.user_id,
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    task.version += 1
    await db.commit()
    await db.refresh(task)

    logger.info("Task updated", task_id=str(task_id))

    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a task.
    """
    result = await db.execute(
        select(Task).where(
            Task.task_id == task_id,
            Task.user_id == current_user.user_id,
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    await db.delete(task)
    await db.commit()

    logger.info("Task deleted", task_id=str(task_id))

    return None


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a running task.
    """
    result = await db.execute(
        select(Task).where(
            Task.task_id == task_id,
            Task.user_id == current_user.user_id,
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    if task.status in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel task with status: {task.status}",
        )

    task.status = "cancelled"
    task.completed_at = datetime.utcnow()
    task.version += 1
    await db.commit()
    await db.refresh(task)

    logger.info("Task cancelled", task_id=str(task_id))

    return task
