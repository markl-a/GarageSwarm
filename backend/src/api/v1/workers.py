"""
Workers API

Worker Agent management endpoints for registration, heartbeat, and monitoring.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.dependencies import get_db, get_redis_service
from src.auth.dependencies import require_auth
from src.models.user import User
from src.services.worker_service import WorkerService
from src.services.redis_service import RedisService
from src.schemas.worker import (
    WorkerRegisterRequest,
    WorkerRegisterResponse,
    WorkerHeartbeatRequest,
    WorkerHeartbeatResponse,
    WorkerListResponse,
    WorkerDetailResponse,
    WorkerSummary,
    WorkerStatus
)

router = APIRouter()
logger = structlog.get_logger()


async def get_worker_service(
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service)
) -> WorkerService:
    """Dependency to get WorkerService instance"""
    return WorkerService(db, redis_service)


@router.post(
    "/workers/register",
    response_model=WorkerRegisterResponse,
    status_code=status.HTTP_200_OK,
    summary="Register Worker Agent",
    description="Register a new worker agent or update an existing one (idempotent operation)"
)
async def register_worker(
    request: WorkerRegisterRequest,
    worker_service: WorkerService = Depends(get_worker_service)
):
    """
    Register a worker agent with the backend.

    This endpoint is idempotent - calling it multiple times with the same
    machine_id will update the existing worker instead of creating a duplicate.

    **Required fields:**
    - machine_id: Unique machine identifier (UUID format recommended)
    - machine_name: Human-readable name for the machine
    - system_info: System information (OS, CPU, memory, etc.)
    - tools: List of available AI tools

    **Response:**
    - status: "registered" or "updated"
    - worker_id: UUID of the registered worker
    - message: Additional information
    """
    try:
        worker = await worker_service.register_worker(
            machine_id=request.machine_id,
            machine_name=request.machine_name,
            system_info=request.system_info,
            tools=request.tools
        )

        # Determine if this was a new registration or update
        # If last_heartbeat is None, it's a new registration; otherwise check timestamps
        if worker.last_heartbeat is None:
            status_msg = "registered"
        else:
            status_msg = "updated" if worker.registered_at < worker.last_heartbeat else "registered"

        return WorkerRegisterResponse(
            status=status_msg,
            worker_id=worker.worker_id,
            message=f"Worker {status_msg} successfully"
        )

    except Exception as e:
        logger.error("Worker registration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Worker registration failed: {str(e)}"
        )


@router.post(
    "/workers/{worker_id}/heartbeat",
    response_model=WorkerHeartbeatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send Worker Heartbeat",
    description="Update worker status and resource usage via heartbeat"
)
async def worker_heartbeat(
    worker_id: UUID,
    request: WorkerHeartbeatRequest,
    worker_service: WorkerService = Depends(get_worker_service)
):
    """
    Send heartbeat from worker to backend.

    Workers should send heartbeat every 30 seconds to maintain their online status.
    Workers that haven't sent heartbeat for 90+ seconds will be marked as offline.

    **Required fields:**
    - status: Current worker status (online, busy, idle)
    - resources: Current resource usage (cpu_percent, memory_percent, disk_percent)
    - current_task: Currently executing task ID (optional)
    """
    try:
        await worker_service.update_heartbeat(
            worker_id=worker_id,
            status=request.status.value,
            resources=request.resources,
            current_task=request.current_task
        )

        return WorkerHeartbeatResponse(
            acknowledged=True,
            message="Heartbeat received"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Heartbeat update failed", worker_id=str(worker_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Heartbeat update failed: {str(e)}"
        )


@router.get(
    "/workers",
    response_model=WorkerListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Workers",
    description="Get list of all registered workers with optional filtering"
)
async def list_workers(
    status_filter: Optional[WorkerStatus] = Query(None, alias="status", description="Filter by worker status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    worker_service: WorkerService = Depends(get_worker_service),
    current_user: User = Depends(require_auth)
):
    """
    List all registered workers with optional filtering.

    **Query parameters:**
    - status: Filter by worker status (online, offline, busy, idle)
    - limit: Maximum number of results (1-100, default 50)
    - offset: Offset for pagination (default 0)

    **Response:**
    - workers: List of worker summaries
    - total: Total number of workers matching the filter
    - limit: Applied limit
    - offset: Applied offset
    """
    try:
        status_str = status_filter.value if status_filter else None
        workers, total = await worker_service.list_workers(
            status=status_str,
            limit=limit,
            offset=offset
        )

        worker_summaries = [
            WorkerSummary.model_validate(worker)
            for worker in workers
        ]

        return WorkerListResponse(
            workers=worker_summaries,
            total=total,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error("List workers failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workers: {str(e)}"
        )


@router.get(
    "/workers/{worker_id}",
    response_model=WorkerDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Worker Details",
    description="Get detailed information about a specific worker"
)
async def get_worker(
    worker_id: UUID,
    worker_service: WorkerService = Depends(get_worker_service),
    current_user: User = Depends(require_auth)
):
    """
    Get detailed information about a specific worker.

    **Path parameters:**
    - worker_id: UUID of the worker

    **Response:**
    - Complete worker information including system_info and current status
    - Returns 404 if worker not found
    """
    try:
        worker = await worker_service.get_worker(worker_id)

        if not worker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Worker {worker_id} not found"
            )

        return WorkerDetailResponse.model_validate(worker)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get worker failed", worker_id=str(worker_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get worker: {str(e)}"
        )


@router.post(
    "/workers/{worker_id}/unregister",
    status_code=status.HTTP_200_OK,
    summary="Unregister Worker",
    description="Mark worker as offline (graceful shutdown)"
)
async def unregister_worker(
    worker_id: UUID,
    worker_service: WorkerService = Depends(get_worker_service)
):
    """
    Unregister a worker (mark as offline).

    This endpoint should be called when a worker is gracefully shutting down.

    **Path parameters:**
    - worker_id: UUID of the worker to unregister

    **Response:**
    - Returns 200 if successful
    - Returns 404 if worker not found
    """
    try:
        success = await worker_service.unregister_worker(worker_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Worker {worker_id} not found"
            )

        return {"status": "unregistered", "worker_id": str(worker_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unregister worker failed", worker_id=str(worker_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unregister worker: {str(e)}"
        )
