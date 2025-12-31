"""
Metrics API Endpoint

Exposes Prometheus metrics for scraping
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import structlog

from src.database import get_db
from src.models.worker import Worker
from src.models.task import Task
from src.models.subtask import Subtask
from src.middleware.metrics import (
    update_worker_metrics,
    update_task_metrics,
    update_subtask_metrics,
)


logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus Metrics",
    description="Exposes application metrics in Prometheus format for scraping",
    tags=["Metrics"],
)
async def metrics(db: AsyncSession = Depends(get_db)) -> PlainTextResponse:
    """
    Prometheus metrics endpoint

    Returns metrics in Prometheus text format for scraping by Prometheus server.
    This endpoint is called periodically by Prometheus to collect metrics.

    Metrics include:
    - HTTP request count, latency, and error rates
    - Active workers by status
    - Worker resource usage (CPU, memory, disk)
    - Tasks by status
    - Subtasks by status and tool
    - Checkpoint and evaluation metrics
    - WebSocket connection metrics
    - Database and Redis metrics

    Returns:
        PlainTextResponse: Metrics in Prometheus text format
    """
    try:
        # Update worker metrics from database
        await _update_worker_metrics_from_db(db)

        # Update task metrics from database
        await _update_task_metrics_from_db(db)

        # Update subtask metrics from database
        await _update_subtask_metrics_from_db(db)

        # Generate Prometheus metrics
        metrics_output = generate_latest()

        return PlainTextResponse(
            content=metrics_output,
            media_type=CONTENT_TYPE_LATEST,
        )

    except Exception as e:
        logger.error("Failed to generate metrics", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate metrics",
        )


async def _update_worker_metrics_from_db(db: AsyncSession) -> None:
    """
    Fetch current worker data from database and update metrics

    Args:
        db: Database session
    """
    try:
        # Query all workers
        result = await db.execute(
            select(
                Worker.worker_id,
                Worker.machine_name,
                Worker.status,
                Worker.cpu_percent,
                Worker.memory_percent,
                Worker.disk_percent,
            )
        )
        workers = result.all()

        # Convert to list of dicts
        workers_data = [
            {
                "worker_id": worker.worker_id,
                "machine_name": worker.machine_name,
                "status": worker.status,
                "cpu_percent": worker.cpu_percent,
                "memory_percent": worker.memory_percent,
                "disk_percent": worker.disk_percent,
            }
            for worker in workers
        ]

        # Update metrics
        update_worker_metrics(workers_data)

    except Exception as e:
        logger.error("Failed to update worker metrics", error=str(e))


async def _update_task_metrics_from_db(db: AsyncSession) -> None:
    """
    Fetch current task data from database and update metrics

    Args:
        db: Database session
    """
    try:
        # Query task counts by status
        result = await db.execute(
            select(Task.status, func.count(Task.task_id).label("count"))
            .group_by(Task.status)
        )
        task_counts = result.all()

        # Convert to list of dicts
        tasks_data = []
        for status, count in task_counts:
            # Create count entries for each status
            tasks_data.extend([{"status": status} for _ in range(count)])

        # Update metrics
        update_task_metrics(tasks_data)

    except Exception as e:
        logger.error("Failed to update task metrics", error=str(e))


async def _update_subtask_metrics_from_db(db: AsyncSession) -> None:
    """
    Fetch current subtask data from database and update metrics

    Args:
        db: Database session
    """
    try:
        # Query subtask counts by status and tool
        result = await db.execute(
            select(
                Subtask.status,
                Subtask.assigned_tool,
                func.count(Subtask.subtask_id).label("count"),
            )
            .group_by(Subtask.status, Subtask.assigned_tool)
        )
        subtask_counts = result.all()

        # Convert to list of dicts
        subtasks_data = []
        for status, tool, count in subtask_counts:
            # Create count entries for each status/tool combination
            subtasks_data.extend([
                {"status": status, "assigned_tool": tool}
                for _ in range(count)
            ])

        # Update metrics
        update_subtask_metrics(subtasks_data)

    except Exception as e:
        logger.error("Failed to update subtask metrics", error=str(e))


@router.get(
    "/health/metrics",
    summary="Metrics Health Check",
    description="Check if metrics collection is working",
    tags=["Metrics"],
)
async def metrics_health() -> dict:
    """
    Check metrics health

    Verifies that the metrics system is operational and can generate metrics.

    Returns:
        dict: Health status
    """
    try:
        # Try to generate metrics
        metrics_output = generate_latest()

        return {
            "status": "healthy",
            "metrics_enabled": True,
            "metrics_size_bytes": len(metrics_output),
        }

    except Exception as e:
        logger.error("Metrics health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "metrics_enabled": False,
            "error": str(e),
        }
