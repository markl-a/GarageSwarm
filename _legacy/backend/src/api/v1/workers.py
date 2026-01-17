"""
Workers API

Worker Agent management endpoints for registration, heartbeat, and monitoring.
Includes WebSocket endpoint for real-time task push.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from src.dependencies import get_db, get_redis_service
from src.auth.dependencies import require_auth
from src.auth.worker_auth import require_worker_auth, validate_worker_websocket
from src.models.user import User
from src.models.worker import Worker
from src.services.worker_service import WorkerService
from src.services.worker_api_key_service import WorkerAPIKeyService
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
from src.schemas.worker_api_key import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeySummary,
    APIKeyRevokeResponse,
)

router = APIRouter()
logger = structlog.get_logger()


async def get_worker_service(
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service)
) -> WorkerService:
    """Dependency to get WorkerService instance"""
    return WorkerService(db, redis_service)


async def get_api_key_service(
    db: AsyncSession = Depends(get_db),
) -> WorkerAPIKeyService:
    """Dependency to get WorkerAPIKeyService instance"""
    return WorkerAPIKeyService(db)


@router.post(
    "/workers/register",
    response_model=WorkerRegisterResponse,
    status_code=status.HTTP_200_OK,
    summary="Register Worker Agent",
    description="Register a new worker agent or update an existing one (no auth required for bootstrap)"
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
    description="Update worker status and resource usage via heartbeat (requires API key)"
)
async def worker_heartbeat(
    worker_id: UUID,
    request: WorkerHeartbeatRequest,
    authenticated_worker_id: UUID = Depends(require_worker_auth),
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
    # Verify the authenticated worker matches the path parameter
    if authenticated_worker_id != worker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not match worker ID"
        )

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
    description="Mark worker as offline (graceful shutdown, requires API key)"
)
async def unregister_worker(
    worker_id: UUID,
    authenticated_worker_id: UUID = Depends(require_worker_auth),
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
    # Verify the authenticated worker matches the path parameter
    if authenticated_worker_id != worker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not match worker ID"
        )

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


# ==================== API Key Management Endpoints ====================


@router.post(
    "/workers/api-keys",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Worker API Key",
    description="Generate a new API key for a worker. The plain key is returned ONCE."
)
async def create_worker_api_key(
    request: APIKeyCreateRequest,
    current_user: User = Depends(require_auth),
    api_key_service: WorkerAPIKeyService = Depends(get_api_key_service)
):
    """
    Generate a new API key for a worker.

    **IMPORTANT**: The plain API key is returned only once. Save it securely!

    Requires user authentication (JWT).

    **Request body:**
    - worker_id: UUID of the worker to create key for
    - description: Optional description for the key
    - expires_in_days: Optional expiration (1-365 days, null = never expires)
    """
    try:
        api_key, plain_key = await api_key_service.create_api_key(
            worker_id=request.worker_id,
            created_by=current_user.user_id,
            description=request.description,
            expires_in_days=request.expires_in_days
        )

        return APIKeyCreateResponse(
            key_id=api_key.key_id,
            worker_id=api_key.worker_id,
            api_key=plain_key,
            key_prefix=api_key.key_prefix,
            description=api_key.description,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to create API key", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@router.get(
    "/workers/{worker_id}/api-keys",
    response_model=APIKeyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Worker API Keys",
    description="List all API keys for a worker (without the actual key values)"
)
async def list_worker_api_keys(
    worker_id: UUID,
    current_user: User = Depends(require_auth),
    api_key_service: WorkerAPIKeyService = Depends(get_api_key_service)
):
    """
    List all API keys for a specific worker.

    Only returns metadata (not the actual keys).
    Requires user authentication (JWT).
    """
    keys = await api_key_service.list_api_keys(worker_id)

    return APIKeyListResponse(
        keys=[APIKeySummary.model_validate(k) for k in keys],
        total=len(keys)
    )


@router.delete(
    "/workers/api-keys/{key_id}",
    response_model=APIKeyRevokeResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke Worker API Key",
    description="Revoke an API key, making it invalid for authentication"
)
async def revoke_worker_api_key(
    key_id: UUID,
    current_user: User = Depends(require_auth),
    api_key_service: WorkerAPIKeyService = Depends(get_api_key_service)
):
    """
    Revoke a worker API key.

    The key will immediately become invalid.
    Requires user authentication (JWT).
    """
    api_key = await api_key_service.revoke_api_key(key_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found"
        )

    return APIKeyRevokeResponse(
        key_id=api_key.key_id,
        revoked_at=api_key.revoked_at
    )


# ==================== Worker WebSocket Endpoint ====================


# Store active worker connections
_worker_connections: dict[UUID, WebSocket] = {}


def get_worker_connections() -> dict[UUID, WebSocket]:
    """Get active worker WebSocket connections"""
    return _worker_connections


@router.websocket("/workers/{worker_id}/ws")
async def worker_websocket_endpoint(
    websocket: WebSocket,
    worker_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service)
):
    """
    WebSocket endpoint for worker agents to receive real-time task assignments.

    Workers connect to this endpoint after registration to receive:
    - Task assignments pushed from the scheduler
    - Heartbeat acknowledgments
    - System notifications

    **Path parameters:**
    - worker_id: UUID of the registered worker

    **WebSocket Protocol:**

    Server sends task assignments:
    ```json
    {
        "type": "task_assignment",
        "data": {
            "subtask_id": "uuid",
            "task_id": "uuid",
            "description": "...",
            "assigned_tool": "claude_code",
            "input_data": {...}
        },
        "timestamp": "2025-12-08T10:30:00Z"
    }
    ```

    Client can send:
    ```json
    {"type": "ping"}
    {"type": "status", "data": {"status": "busy", "current_task": "uuid"}}
    ```

    **Authentication:**
    - Requires API key via X-Worker-API-Key header or api_key query parameter
    """
    # Validate API key before accepting connection
    authenticated_worker_id = await validate_worker_websocket(websocket, db)

    if not authenticated_worker_id:
        await websocket.close(code=1008, reason="Invalid or missing API key")
        logger.warning("Worker WebSocket rejected - invalid API key", worker_id=str(worker_id))
        return

    if authenticated_worker_id != worker_id:
        await websocket.close(code=1008, reason="API key does not match worker ID")
        logger.warning(
            "Worker WebSocket rejected - worker ID mismatch",
            path_worker_id=str(worker_id),
            auth_worker_id=str(authenticated_worker_id)
        )
        return

    # Verify worker exists
    result = await db.execute(select(Worker).where(Worker.worker_id == worker_id))
    worker = result.scalar_one_or_none()

    if not worker:
        await websocket.close(code=1008, reason=f"Worker {worker_id} not found")
        logger.warning("Worker WebSocket rejected - worker not found", worker_id=str(worker_id))
        return

    # Accept connection
    await websocket.accept()
    _worker_connections[worker_id] = websocket

    logger.info(
        "Worker WebSocket connected",
        worker_id=str(worker_id),
        machine_name=worker.machine_name,
        total_connections=len(_worker_connections)
    )

    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "data": {
            "worker_id": str(worker_id),
            "machine_name": worker.machine_name
        },
        "timestamp": datetime.utcnow().isoformat()
    })

    # Subscribe to worker-specific Redis channel for task assignments
    pubsub = redis_service.redis.pubsub()
    channel = f"worker:{worker_id}:tasks"

    try:
        await pubsub.subscribe(channel)
        logger.debug("Subscribed to worker channel", channel=channel)

        # Start background task to listen for Redis messages
        async def redis_listener():
            try:
                while True:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            await websocket.send_json(data)
                        except (json.JSONDecodeError, Exception) as e:
                            logger.error("Failed to forward Redis message", error=str(e))
            except asyncio.CancelledError:
                pass

        listener_task = asyncio.create_task(redis_listener())

        try:
            while True:
                # Receive messages from worker
                data = await websocket.receive_json()

                if isinstance(data, dict):
                    msg_type = data.get("type")

                    if msg_type == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        })

                    elif msg_type == "status":
                        # Update worker status in Redis
                        status_data = data.get("data", {})
                        await redis_service.set_worker_status(
                            worker_id,
                            status_data.get("status", "online")
                        )
                        logger.debug(
                            "Worker status updated via WebSocket",
                            worker_id=str(worker_id),
                            status=status_data.get("status")
                        )

                    elif msg_type == "task_complete":
                        # Worker finished a task
                        task_data = data.get("data", {})
                        logger.info(
                            "Worker reported task completion",
                            worker_id=str(worker_id),
                            subtask_id=task_data.get("subtask_id")
                        )

        except WebSocketDisconnect:
            logger.info("Worker WebSocket disconnected gracefully", worker_id=str(worker_id))
        finally:
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logger.error("Worker WebSocket error", worker_id=str(worker_id), error=str(e))
    finally:
        # Cleanup
        await pubsub.unsubscribe(channel)
        await pubsub.close()

        if worker_id in _worker_connections:
            del _worker_connections[worker_id]

        logger.info(
            "Worker WebSocket cleaned up",
            worker_id=str(worker_id),
            total_connections=len(_worker_connections)
        )


async def push_task_to_worker(
    worker_id: UUID,
    subtask_data: dict,
    redis_service: RedisService
) -> bool:
    """
    Push a task assignment to a worker via WebSocket.

    Args:
        worker_id: Target worker UUID
        subtask_data: Subtask data to send
        redis_service: Redis service for pub/sub

    Returns:
        True if message was published, False otherwise
    """
    message = {
        "type": "task_assignment",
        "data": subtask_data,
        "timestamp": datetime.utcnow().isoformat()
    }

    channel = f"worker:{worker_id}:tasks"

    try:
        await redis_service.redis.publish(channel, json.dumps(message))
        logger.debug("Task pushed to worker", worker_id=str(worker_id))
        return True
    except Exception as e:
        logger.error("Failed to push task to worker", worker_id=str(worker_id), error=str(e))
        return False
