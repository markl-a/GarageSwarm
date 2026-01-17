"""
Diagnostics API

Developer tools for debugging and troubleshooting.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import redis.asyncio as redis
from sqlalchemy import select, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.dependencies import get_db, get_redis_client
from src.config import get_settings, Settings
from src.logging_config import get_logger
from src.auth.dependencies import require_auth
from src.models.user import User
from src.models.task import Task
from src.models.subtask import Subtask
from src.models.worker import Worker
from src.schemas.task import TaskStatus
from src.schemas.subtask import SubtaskStatus

logger = get_logger(__name__)

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])


# Response schemas
class ErrorLogEntry(BaseModel):
    """Error log entry"""
    timestamp: datetime
    level: str
    message: str
    error_code: Optional[str] = None
    request_id: Optional[str] = None
    path: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class TaskDebugInfo(BaseModel):
    """Task debugging information"""
    task_id: UUID
    status: str
    progress: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    subtasks_summary: Dict[str, int] = Field(default_factory=dict)
    assigned_workers: List[str] = Field(default_factory=list)
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list)
    potential_issues: List[str] = Field(default_factory=list)


class WorkerDebugInfo(BaseModel):
    """Worker debugging information"""
    worker_id: UUID
    machine_name: str
    status: str
    last_heartbeat: Optional[datetime] = None
    current_task: Optional[str] = None
    active_subtasks: int = 0
    completed_subtasks: int = 0
    failed_subtasks: int = 0
    potential_issues: List[str] = Field(default_factory=list)


class SystemDiagnostics(BaseModel):
    """System-wide diagnostics"""
    timestamp: datetime
    stuck_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    offline_workers: List[Dict[str, Any]] = Field(default_factory=list)
    orphaned_subtasks: List[Dict[str, Any]] = Field(default_factory=list)
    queue_issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# In-memory error log storage (for development/debugging)
# In production, use proper log aggregation
_recent_errors: List[Dict[str, Any]] = []
MAX_ERROR_LOG_SIZE = 100


def log_error_for_diagnostics(
    message: str,
    error_code: Optional[str] = None,
    request_id: Optional[str] = None,
    path: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """Log an error for diagnostics retrieval"""
    global _recent_errors

    entry = {
        "timestamp": datetime.utcnow(),
        "level": "ERROR",
        "message": message,
        "error_code": error_code,
        "request_id": request_id,
        "path": path,
        "details": details or {}
    }

    _recent_errors.append(entry)

    # Keep only recent errors
    if len(_recent_errors) > MAX_ERROR_LOG_SIZE:
        _recent_errors = _recent_errors[-MAX_ERROR_LOG_SIZE:]


@router.get("/errors", response_model=List[ErrorLogEntry])
async def get_recent_errors(
    limit: int = Query(default=50, ge=1, le=100, description="Number of errors to return"),
    error_code: Optional[str] = Query(default=None, description="Filter by error code"),
    since_minutes: Optional[int] = Query(default=None, description="Errors from last N minutes"),
    current_user: User = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    """
    Get recent error logs

    Retrieves recent errors for debugging. Useful for identifying
    patterns and troubleshooting issues.

    Note: Only available in DEBUG mode.
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=403,
            detail="Diagnostics only available in DEBUG mode"
        )

    errors = _recent_errors.copy()

    # Filter by error code
    if error_code:
        errors = [e for e in errors if e.get("error_code") == error_code]

    # Filter by time
    if since_minutes:
        cutoff = datetime.utcnow() - timedelta(minutes=since_minutes)
        errors = [e for e in errors if e.get("timestamp", datetime.min) >= cutoff]

    # Return most recent first
    errors = sorted(errors, key=lambda x: x.get("timestamp", datetime.min), reverse=True)

    return errors[:limit]


@router.get("/tasks/{task_id}", response_model=TaskDebugInfo)
async def debug_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    """
    Get detailed debugging information for a task

    Provides comprehensive task state including:
    - Current status and progress
    - Subtask breakdown
    - Assigned workers
    - Potential issues and recommendations

    Note: Only available in DEBUG mode.
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=403,
            detail="Diagnostics only available in DEBUG mode"
        )

    # Get task with subtasks
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.subtasks))
        .where(Task.task_id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Summarize subtasks by status
    subtask_summary: Dict[str, int] = {}
    assigned_workers: set = set()
    recent_activity: List[Dict[str, Any]] = []

    for subtask in task.subtasks:
        status = subtask.status
        subtask_summary[status] = subtask_summary.get(status, 0) + 1

        if subtask.assigned_worker:
            assigned_workers.add(str(subtask.assigned_worker))

        # Track recent activity
        if subtask.updated_at and subtask.updated_at > datetime.utcnow() - timedelta(hours=1):
            recent_activity.append({
                "subtask_id": str(subtask.subtask_id),
                "name": subtask.name,
                "status": subtask.status,
                "updated_at": subtask.updated_at.isoformat()
            })

    # Sort recent activity
    recent_activity = sorted(
        recent_activity,
        key=lambda x: x.get("updated_at", ""),
        reverse=True
    )[:10]

    # Identify potential issues
    issues: List[str] = []

    # Task stuck in progress too long
    if task.status == TaskStatus.IN_PROGRESS.value and task.started_at:
        hours_running = (datetime.utcnow() - task.started_at).total_seconds() / 3600
        if hours_running > 24:
            issues.append(f"Task running for {hours_running:.1f} hours - may be stuck")

    # No progress on active task
    if task.status == TaskStatus.IN_PROGRESS.value and task.progress == 0:
        if task.started_at and (datetime.utcnow() - task.started_at).total_seconds() > 300:
            issues.append("Task in progress but no progress recorded")

    # Failed subtasks
    failed_count = subtask_summary.get("failed", 0)
    if failed_count > 0:
        issues.append(f"{failed_count} subtask(s) failed")

    # Subtasks without workers
    pending_count = subtask_summary.get("pending", 0)
    if pending_count > len(assigned_workers) and task.status == TaskStatus.IN_PROGRESS.value:
        issues.append(f"{pending_count} pending subtasks - may need more workers")

    return TaskDebugInfo(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        subtasks_summary=subtask_summary,
        assigned_workers=list(assigned_workers),
        recent_activity=recent_activity,
        potential_issues=issues
    )


@router.get("/workers/{worker_id}", response_model=WorkerDebugInfo)
async def debug_worker(
    worker_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    """
    Get detailed debugging information for a worker

    Provides worker state including:
    - Connection status
    - Current assignments
    - Task history
    - Potential issues

    Note: Only available in DEBUG mode.
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=403,
            detail="Diagnostics only available in DEBUG mode"
        )

    # Get worker
    result = await db.execute(
        select(Worker).where(Worker.worker_id == worker_id)
    )
    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Get subtask stats
    subtask_stats = await db.execute(
        select(Subtask.status, func.count())
        .where(Subtask.assigned_worker == worker_id)
        .group_by(Subtask.status)
    )
    stats = dict(subtask_stats.fetchall())

    # Get current active subtask
    active_subtask = await db.execute(
        select(Subtask)
        .where(Subtask.assigned_worker == worker_id)
        .where(Subtask.status == SubtaskStatus.IN_PROGRESS.value)
        .limit(1)
    )
    current = active_subtask.scalar_one_or_none()

    # Identify issues
    issues: List[str] = []

    # Stale heartbeat
    if worker.last_heartbeat:
        seconds_since_heartbeat = (datetime.utcnow() - worker.last_heartbeat).total_seconds()
        if seconds_since_heartbeat > 120:
            issues.append(f"No heartbeat for {seconds_since_heartbeat:.0f}s - worker may be offline")
        elif seconds_since_heartbeat > 60:
            issues.append(f"Heartbeat delayed: {seconds_since_heartbeat:.0f}s ago")
    else:
        issues.append("Worker has never sent a heartbeat")

    # High failure rate
    total = sum(stats.values())
    failed = stats.get("failed", 0)
    if total > 5 and failed / total > 0.3:
        issues.append(f"High failure rate: {failed}/{total} ({failed/total*100:.0f}%)")

    # Worker marked online but no recent activity
    if worker.status in ["online", "idle"]:
        if not current and total == 0:
            issues.append("Worker online but has never completed any work")

    return WorkerDebugInfo(
        worker_id=worker.worker_id,
        machine_name=worker.machine_name,
        status=worker.status,
        last_heartbeat=worker.last_heartbeat,
        current_task=str(current.subtask_id) if current else None,
        active_subtasks=stats.get("in_progress", 0),
        completed_subtasks=stats.get("completed", 0),
        failed_subtasks=stats.get("failed", 0),
        potential_issues=issues
    )


@router.get("/system", response_model=SystemDiagnostics)
async def system_diagnostics(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
    current_user: User = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    """
    Run system-wide diagnostics

    Identifies potential issues across the system:
    - Tasks stuck in progress
    - Workers that went offline
    - Orphaned subtasks (assigned to offline workers)
    - Queue health issues

    Note: Only available in DEBUG mode.
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=403,
            detail="Diagnostics only available in DEBUG mode"
        )

    stuck_tasks: List[Dict[str, Any]] = []
    offline_workers: List[Dict[str, Any]] = []
    orphaned_subtasks: List[Dict[str, Any]] = []
    queue_issues: List[str] = []
    recommendations: List[str] = []

    # Find stuck tasks (in_progress for > 24 hours)
    stuck_cutoff = datetime.utcnow() - timedelta(hours=24)
    stuck_result = await db.execute(
        select(Task)
        .where(Task.status == TaskStatus.IN_PROGRESS.value)
        .where(Task.started_at < stuck_cutoff)
    )
    for task in stuck_result.scalars():
        hours = (datetime.utcnow() - task.started_at).total_seconds() / 3600
        stuck_tasks.append({
            "task_id": str(task.task_id),
            "description": task.description[:100],
            "hours_running": round(hours, 1),
            "progress": task.progress
        })

    if stuck_tasks:
        recommendations.append(f"Consider cancelling {len(stuck_tasks)} stuck task(s)")

    # Find offline workers (no heartbeat > 5 minutes)
    heartbeat_cutoff = datetime.utcnow() - timedelta(minutes=5)
    offline_result = await db.execute(
        select(Worker)
        .where(Worker.status.in_(["online", "busy", "idle"]))
        .where(or_(
            Worker.last_heartbeat < heartbeat_cutoff,
            Worker.last_heartbeat.is_(None)
        ))
    )
    for worker in offline_result.scalars():
        minutes_offline = None
        if worker.last_heartbeat:
            minutes_offline = (datetime.utcnow() - worker.last_heartbeat).total_seconds() / 60

        offline_workers.append({
            "worker_id": str(worker.worker_id),
            "machine_name": worker.machine_name,
            "last_status": worker.status,
            "minutes_since_heartbeat": round(minutes_offline, 1) if minutes_offline else None
        })

    if offline_workers:
        recommendations.append(f"Mark {len(offline_workers)} unresponsive worker(s) as offline")

    # Find orphaned subtasks (assigned to offline workers)
    if offline_workers:
        offline_ids = [UUID(w["worker_id"]) for w in offline_workers]
        orphan_result = await db.execute(
            select(Subtask)
            .where(Subtask.status == SubtaskStatus.IN_PROGRESS.value)
            .where(Subtask.assigned_worker.in_(offline_ids))
        )
        for subtask in orphan_result.scalars():
            orphaned_subtasks.append({
                "subtask_id": str(subtask.subtask_id),
                "name": subtask.name,
                "assigned_worker": str(subtask.assigned_worker),
                "task_id": str(subtask.task_id)
            })

        if orphaned_subtasks:
            recommendations.append(
                f"Reassign {len(orphaned_subtasks)} orphaned subtask(s) to active workers"
            )

    # Check queue health
    try:
        queue_len = await redis_client.llen("task_queue")

        # Get online worker count
        online_count = await db.execute(
            select(func.count())
            .select_from(Worker)
            .where(Worker.status.in_(["online", "idle"]))
        )
        online = online_count.scalar() or 0

        if queue_len > 100:
            queue_issues.append(f"Queue backlog: {queue_len} items")
            if online < 3:
                recommendations.append("Consider adding more workers to handle queue backlog")

        if online == 0 and queue_len > 0:
            queue_issues.append("No online workers to process queue")
            recommendations.append("Start worker agents to process pending tasks")

    except Exception as e:
        queue_issues.append(f"Could not check queue: {str(e)}")

    return SystemDiagnostics(
        timestamp=datetime.utcnow(),
        stuck_tasks=stuck_tasks,
        offline_workers=offline_workers,
        orphaned_subtasks=orphaned_subtasks,
        queue_issues=queue_issues,
        recommendations=recommendations
    )


@router.post("/cleanup/offline-workers")
async def cleanup_offline_workers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
    settings: Settings = Depends(get_settings),
):
    """
    Mark unresponsive workers as offline

    Workers with no heartbeat in the last 5 minutes will be
    marked as offline. Their in-progress subtasks will be
    reset to pending for reassignment.

    Note: Only available in DEBUG mode.
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=403,
            detail="Diagnostics only available in DEBUG mode"
        )

    heartbeat_cutoff = datetime.utcnow() - timedelta(minutes=5)

    # Find and update offline workers
    result = await db.execute(
        select(Worker)
        .where(Worker.status.in_(["online", "busy", "idle"]))
        .where(or_(
            Worker.last_heartbeat < heartbeat_cutoff,
            Worker.last_heartbeat.is_(None)
        ))
    )
    workers = result.scalars().all()

    workers_updated = 0
    subtasks_reset = 0

    for worker in workers:
        worker.status = "offline"
        workers_updated += 1

        # Reset in-progress subtasks
        subtask_result = await db.execute(
            select(Subtask)
            .where(Subtask.assigned_worker == worker.worker_id)
            .where(Subtask.status == SubtaskStatus.IN_PROGRESS.value)
        )
        for subtask in subtask_result.scalars():
            subtask.status = "pending"
            subtask.assigned_worker = None
            subtasks_reset += 1

    await db.commit()

    return {
        "workers_marked_offline": workers_updated,
        "subtasks_reset": subtasks_reset,
        "message": f"Cleaned up {workers_updated} offline workers"
    }
