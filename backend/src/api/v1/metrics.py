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
from src.services.circuit_breaker import get_circuit_registry
from src.dependencies import get_redis_service
from src.services.redis_service import RedisService


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


@router.get(
    "/circuits",
    summary="Circuit Breaker Status",
    description="Get status of all circuit breakers for fault tolerance monitoring",
    tags=["Metrics"],
)
async def get_circuit_breaker_status(
    redis_service: RedisService = Depends(get_redis_service)
) -> dict:
    """
    Get circuit breaker status for all services.

    Returns the state and statistics for each circuit breaker including:
    - Current state (closed, open, half_open)
    - Failure and success counts
    - Time until recovery (if open)
    - Configuration details

    Returns:
        dict: Circuit breaker status for all services
    """
    try:
        # Get global registry stats
        registry = get_circuit_registry()
        all_stats = registry.get_all_stats()

        # Add Redis circuit breaker stats directly from service
        redis_stats = redis_service.get_circuit_stats()
        if "redis" not in all_stats:
            all_stats["redis"] = redis_stats

        # Determine overall health
        all_closed = all(
            stats.get("state") == "closed"
            for stats in all_stats.values()
        )

        return {
            "healthy": all_closed,
            "circuits": all_stats,
            "summary": {
                "total": len(all_stats),
                "closed": sum(1 for s in all_stats.values() if s.get("state") == "closed"),
                "open": sum(1 for s in all_stats.values() if s.get("state") == "open"),
                "half_open": sum(1 for s in all_stats.values() if s.get("state") == "half_open"),
            }
        }

    except Exception as e:
        logger.error("Failed to get circuit breaker status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get circuit breaker status: {str(e)}",
        )


@router.post(
    "/circuits/{circuit_name}/reset",
    summary="Reset Circuit Breaker",
    description="Reset a specific circuit breaker to closed state",
    tags=["Metrics"],
)
async def reset_circuit_breaker(
    circuit_name: str,
    redis_service: RedisService = Depends(get_redis_service)
) -> dict:
    """
    Reset a specific circuit breaker.

    This forcibly closes the circuit, allowing requests to pass through again.
    Use with caution - the underlying service may still be unhealthy.

    Args:
        circuit_name: Name of the circuit breaker to reset

    Returns:
        dict: Result of the reset operation
    """
    try:
        # Handle Redis circuit breaker specially
        if circuit_name == "redis":
            await redis_service.circuit_breaker.reset()
            return {
                "success": True,
                "circuit": circuit_name,
                "message": "Circuit breaker reset successfully"
            }

        # Check global registry
        registry = get_circuit_registry()
        breaker = registry.get(circuit_name)

        if not breaker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Circuit breaker '{circuit_name}' not found"
            )

        await breaker.reset()

        return {
            "success": True,
            "circuit": circuit_name,
            "message": "Circuit breaker reset successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to reset circuit breaker", circuit=circuit_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset circuit breaker: {str(e)}",
        )
