"""
WebSocket API

Real-time log streaming and task status updates via WebSocket.
Supports multi-instance deployment via Redis Pub/Sub.
Includes JWT token authentication for secure connections.
"""

import asyncio
import json
from datetime import datetime
from functools import lru_cache
from typing import Dict, Set, Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query
from jose import JWTError
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.auth.jwt_handler import verify_token, TokenType
from src.dependencies import get_db, get_redis_service
from src.models.subtask import Subtask
from src.models.task import Task
from src.models.user import User
from src.schemas.log import (
    LogMessage,
    LogRequest,
    LogResponse
)
from src.services.redis_service import RedisService
from src.config import get_settings

router = APIRouter()
settings = get_settings()
logger = structlog.get_logger()


@lru_cache(maxsize=1)
def get_connection_manager() -> 'ConnectionManager':
    """
    Dependency injection for ConnectionManager (singleton pattern).

    Uses lru_cache to ensure only one instance is created and reused.
    This is thread-safe and avoids global mutable state.
    """
    return ConnectionManager()


class RedisPubSubManager:
    """
    Redis Pub/Sub manager for WebSocket cross-instance broadcasting

    Handles Redis Pub/Sub subscriptions and message routing from Redis to WebSocket clients.
    """

    def __init__(self, redis_service: RedisService):
        """
        Initialize Redis Pub/Sub manager

        Args:
            redis_service: RedisService instance for pub/sub operations
        """
        self.redis_service = redis_service
        # PubSub instance for receiving messages
        self.pubsub: Optional[redis.client.PubSub] = None
        # Background task for listening to Redis messages
        self.listener_task: Optional[asyncio.Task] = None
        # Track active subscriptions: {task_id: subscription_count}
        self.active_subscriptions: Dict[UUID, int] = {}
        # Reference to the connection manager for routing messages
        self.connection_manager: Optional['ConnectionManager'] = None

    async def start(self, connection_manager: 'ConnectionManager') -> None:
        """
        Start Redis Pub/Sub listener

        Args:
            connection_manager: ConnectionManager instance for routing messages
        """
        self.connection_manager = connection_manager
        self.pubsub = self.redis_service.redis.pubsub()

        # Start background listener task
        self.listener_task = asyncio.create_task(self._listen_to_redis())
        logger.info("Redis Pub/Sub manager started")

    async def stop(self) -> None:
        """Stop Redis Pub/Sub listener"""
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass

        if self.pubsub:
            await self.pubsub.close()

        logger.info("Redis Pub/Sub manager stopped")

    async def subscribe_to_task(self, task_id: UUID) -> None:
        """
        Subscribe to task channel

        Args:
            task_id: Task UUID to subscribe to
        """
        if task_id not in self.active_subscriptions:
            # First subscription to this task - subscribe to Redis channel
            await self.redis_service.subscribe_to_task_channel(task_id, self.pubsub)
            self.active_subscriptions[task_id] = 1
            logger.info("Subscribed to Redis channel for task", task_id=str(task_id))
        else:
            # Increment subscription count
            self.active_subscriptions[task_id] += 1

    async def unsubscribe_from_task(self, task_id: UUID) -> None:
        """
        Unsubscribe from task channel

        Args:
            task_id: Task UUID to unsubscribe from
        """
        if task_id in self.active_subscriptions:
            self.active_subscriptions[task_id] -= 1

            if self.active_subscriptions[task_id] <= 0:
                # Last subscription removed - unsubscribe from Redis channel
                await self.redis_service.unsubscribe_from_task_channel(task_id, self.pubsub)
                del self.active_subscriptions[task_id]
                logger.info("Unsubscribed from Redis channel for task", task_id=str(task_id))

    async def _listen_to_redis(self) -> None:
        """Background task to listen for Redis Pub/Sub messages"""
        try:
            while True:
                try:
                    message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

                    if message and message['type'] == 'message':
                        channel = message['channel']
                        data = message['data']

                        # Parse channel to extract task_id
                        # Channel format: websocket:task:{task_id}
                        if channel.startswith('websocket:task:'):
                            task_id_str = channel.split(':', 2)[2]
                            try:
                                task_id = UUID(task_id_str)

                                # Parse message JSON
                                ws_message = json.loads(data)

                                # Route message to local WebSocket clients
                                if self.connection_manager:
                                    await self.connection_manager.broadcast_to_local_subscribers(
                                        task_id, ws_message
                                    )

                            except (ValueError, json.JSONDecodeError) as e:
                                logger.error("Failed to parse Redis message", channel=channel, error=str(e))

                except Exception as e:
                    logger.error("Error in Redis listener", error=str(e), exc_info=True)
                    # Continue listening even if there's an error
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Redis listener task cancelled")
            raise


class ConnectionManager:
    """
    WebSocket connection manager

    Manages active WebSocket connections and message broadcasting.
    Uses Redis Pub/Sub for cross-instance communication.
    """

    def __init__(self, redis_service: Optional[RedisService] = None):
        """
        Initialize connection manager

        Args:
            redis_service: Optional RedisService for pub/sub operations
        """
        # Active connections: {client_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Task subscriptions: {task_id: Set[client_id]}
        self.task_subscriptions: Dict[UUID, Set[str]] = {}
        # Client subscriptions: {client_id: Set[task_id]}
        self.client_subscriptions: Dict[str, Set[UUID]] = {}
        # Redis service for pub/sub
        self.redis_service = redis_service
        # Redis Pub/Sub manager
        self.pubsub_manager: Optional[RedisPubSubManager] = None

    async def initialize(self) -> None:
        """Initialize Redis Pub/Sub manager if Redis service is available"""
        if self.redis_service and not self.pubsub_manager:
            self.pubsub_manager = RedisPubSubManager(self.redis_service)
            await self.pubsub_manager.start(self)
            logger.info("ConnectionManager initialized with Redis Pub/Sub support")

    async def shutdown(self) -> None:
        """Shutdown Redis Pub/Sub manager"""
        if self.pubsub_manager:
            await self.pubsub_manager.stop()
            logger.info("ConnectionManager shutdown complete")

    async def connect(self, client_id: str, websocket: WebSocket, redis_service: Optional[RedisService] = None) -> None:
        """
        Register a new WebSocket connection

        Args:
            client_id: Unique client identifier
            websocket: WebSocket connection instance
            redis_service: Optional RedisService for this connection
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.client_subscriptions[client_id] = set()

        # Set redis_service if not already set
        if redis_service and not self.redis_service:
            self.redis_service = redis_service

        # Initialize pub/sub manager if needed
        if self.redis_service and not self.pubsub_manager:
            await self.initialize()

        # Retrieve and send any queued messages
        if self.redis_service:
            queued_messages = await self.redis_service.get_queued_messages(client_id)
            for msg in queued_messages:
                try:
                    await websocket.send_json(msg)
                except Exception as e:
                    logger.error("Failed to send queued message", client_id=client_id, error=str(e))

        logger.info("WebSocket client connected", client_id=client_id, total_connections=len(self.active_connections))

    async def disconnect(self, client_id: str) -> None:
        """
        Remove a WebSocket connection and cleanup all subscriptions

        Args:
            client_id: Client identifier to disconnect
        """
        # Remove from active connections
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        # Clean up subscriptions (including Redis Pub/Sub)
        if client_id in self.client_subscriptions:
            task_ids_to_cleanup = list(self.client_subscriptions[client_id])

            for task_id in task_ids_to_cleanup:
                if task_id in self.task_subscriptions:
                    self.task_subscriptions[task_id].discard(client_id)

                    # If no more local subscribers, cleanup Redis Pub/Sub
                    if not self.task_subscriptions[task_id]:
                        del self.task_subscriptions[task_id]
                        # Unsubscribe from Redis channel to prevent memory leak
                        if self.pubsub_manager:
                            try:
                                await self.pubsub_manager.unsubscribe_from_task(task_id)
                            except Exception as e:
                                logger.warning(
                                    "Failed to unsubscribe from Redis channel during disconnect",
                                    task_id=str(task_id),
                                    error=str(e)
                                )

            del self.client_subscriptions[client_id]

        logger.info("WebSocket client disconnected", client_id=client_id, total_connections=len(self.active_connections))

    async def subscribe_to_task(self, client_id: str, task_id: UUID) -> None:
        """
        Subscribe a client to task logs

        Args:
            client_id: Client identifier
            task_id: Task ID to subscribe to
        """
        if client_id not in self.client_subscriptions:
            logger.warning("Cannot subscribe unknown client", client_id=client_id)
            return

        # Add to local subscriptions
        self.client_subscriptions[client_id].add(task_id)

        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
            # First local subscriber - subscribe to Redis channel
            if self.pubsub_manager:
                await self.pubsub_manager.subscribe_to_task(task_id)

        self.task_subscriptions[task_id].add(client_id)

        logger.info("Client subscribed to task", client_id=client_id, task_id=str(task_id))

    async def unsubscribe_from_task(self, client_id: str, task_id: UUID) -> None:
        """
        Unsubscribe a client from task logs

        Args:
            client_id: Client identifier
            task_id: Task ID to unsubscribe from
        """
        if client_id in self.client_subscriptions:
            self.client_subscriptions[client_id].discard(task_id)

        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(client_id)
            if not self.task_subscriptions[task_id]:
                # Last local subscriber - unsubscribe from Redis channel
                if self.pubsub_manager:
                    await self.pubsub_manager.unsubscribe_from_task(task_id)
                del self.task_subscriptions[task_id]

        logger.info("Client unsubscribed from task", client_id=client_id, task_id=str(task_id))

    async def send_personal_message(self, message: dict, client_id: str) -> None:
        """
        Send message to specific client

        Args:
            message: Message dict to send
            client_id: Target client identifier
        """
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error("Failed to send personal message", client_id=client_id, error=str(e))
                await self.disconnect(client_id)

    async def broadcast_to_local_subscribers(self, task_id: UUID, message: dict) -> int:
        """
        Broadcast message to local WebSocket clients subscribed to a task

        This is called when receiving messages from Redis Pub/Sub.

        Args:
            task_id: Task ID
            message: Message dict to broadcast

        Returns:
            Number of local clients that received the message
        """
        if task_id not in self.task_subscriptions:
            return 0

        subscribers = self.task_subscriptions[task_id].copy()
        success_count = 0

        for client_id in subscribers:
            if client_id in self.active_connections:
                websocket = self.active_connections[client_id]
                try:
                    await websocket.send_json(message)
                    success_count += 1
                except Exception as e:
                    logger.error("Failed to broadcast to client", client_id=client_id, task_id=str(task_id), error=str(e))
                    # Queue the message for later delivery
                    if self.redis_service:
                        try:
                            await self.redis_service.queue_message_for_client(client_id, message)
                        except Exception as queue_error:
                            logger.error("Failed to queue message", client_id=client_id, error=str(queue_error))
                    await self.disconnect(client_id)

        logger.debug("Broadcasted message to local task subscribers", task_id=str(task_id), recipients=success_count)
        return success_count

    async def broadcast_to_task_subscribers(self, task_id: UUID, message: dict) -> int:
        """
        Broadcast message to all clients subscribed to a task (across all instances)

        Publishes message to Redis Pub/Sub for cross-instance delivery.

        Args:
            task_id: Task ID
            message: Message dict to broadcast

        Returns:
            Number of backend instances that received the message
        """
        # Publish to Redis for cross-instance broadcasting
        if self.redis_service:
            try:
                num_instances = await self.redis_service.publish_websocket_message(task_id, message)
                logger.debug("Published message to Redis", task_id=str(task_id), instances=num_instances)
                return num_instances
            except Exception as e:
                logger.error("Failed to publish to Redis", task_id=str(task_id), error=str(e))
                # Fallback to local broadcasting if Redis fails
                return await self.broadcast_to_local_subscribers(task_id, message)
        else:
            # No Redis service - broadcast locally only
            return await self.broadcast_to_local_subscribers(task_id, message)

    async def broadcast_to_all(self, message: dict) -> None:
        """
        Broadcast message to all connected clients

        Args:
            message: Message dict to broadcast
        """
        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error("Failed to broadcast to client", client_id=client_id, error=str(e))
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)

        logger.debug("Broadcasted message to all clients", total=len(self.active_connections))


# Connection manager singleton (use get_connection_manager() for dependency injection)
# Note: The global reference is kept for backward compatibility with existing code
connection_manager = get_connection_manager()


# ==================== WebSocket Endpoint ====================


@router.websocket("/ws/tasks/{task_id}/logs")
async def websocket_endpoint(
    websocket: WebSocket,
    task_id: UUID,
    token: Optional[str] = Query(None, description="JWT access token for authentication"),
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service)
):
    """
    WebSocket endpoint for real-time log streaming

    **Authentication:**
    Requires JWT access token passed as query parameter:
    `ws://host/api/v1/ws/tasks/{task_id}/logs?token=<jwt_access_token>`

    **Path parameters:**
    - task_id: Task ID to subscribe to logs

    **Query parameters:**
    - token: JWT access token (required)

    **WebSocket Protocol:**

    Client can send messages to subscribe/unsubscribe:
    ```json
    {
        "action": "subscribe",
        "task_id": "550e8400-e29b-41d4-a716-446655440000"
    }
    ```

    Server sends log messages:
    ```json
    {
        "type": "log",
        "data": {
            "subtask_id": "...",
            "task_id": "...",
            "level": "info",
            "message": "Log message",
            "worker_id": "...",
            "timestamp": "2025-12-08T10:30:00Z"
        },
        "timestamp": "2025-12-08T10:30:00Z"
    }
    ```

    Server sends ping/pong for heartbeat:
    ```json
    {"type": "ping", "timestamp": "2025-12-08T10:30:00Z"}
    ```

    **Error codes:**
    - 4001: Missing authentication token
    - 4003: Invalid or expired token
    - 4004: User not found
    - 1008: Task not found
    """
    # --- Authentication Check ---
    if not token:
        await websocket.close(code=4001, reason="Authentication required: missing token")
        logger.warning("WebSocket connection rejected - no token provided", task_id=str(task_id))
        return

    # Verify JWT token
    try:
        payload = verify_token(token, expected_type=TokenType.ACCESS)
        user_id_str = payload.get("sub")
        if not user_id_str:
            await websocket.close(code=4003, reason="Invalid token: missing user identifier")
            logger.warning("WebSocket connection rejected - invalid token", task_id=str(task_id))
            return

        user_id = UUID(user_id_str)

        # Verify user exists and is active
        user_result = await db.execute(select(User).where(User.user_id == user_id))
        user = user_result.scalar_one_or_none()

        if not user:
            await websocket.close(code=4004, reason="User not found")
            logger.warning("WebSocket connection rejected - user not found", user_id=str(user_id))
            return

        if hasattr(user, "is_active") and not user.is_active:
            await websocket.close(code=4003, reason="User account is inactive")
            logger.warning("WebSocket connection rejected - user inactive", user_id=str(user_id))
            return

        logger.info("WebSocket authenticated", user_id=str(user_id), username=user.username)

    except (JWTError, ValueError) as e:
        await websocket.close(code=4003, reason=f"Authentication failed: {str(e)}")
        logger.warning("WebSocket connection rejected - token verification failed", error=str(e))
        return

    # Generate client ID from connection (include user_id for tracking)
    client_id = f"{user_id}_{websocket.client.host}:{websocket.client.port}_{id(websocket)}"

    # Verify task exists
    result = await db.execute(select(Task).where(Task.task_id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        await websocket.close(code=1008, reason=f"Task {task_id} not found")
        logger.warning("WebSocket connection rejected - task not found", task_id=str(task_id))
        return

    # Accept connection and subscribe to task
    await connection_manager.connect(client_id, websocket, redis_service)
    await connection_manager.subscribe_to_task(client_id, task_id)

    # Send confirmation message
    await connection_manager.send_personal_message(
        {
            "type": "subscribed",
            "data": {"task_id": str(task_id)},
            "timestamp": datetime.utcnow().isoformat()
        },
        client_id
    )

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()

            # Handle subscription actions
            if isinstance(data, dict):
                action = data.get("action")
                new_task_id = data.get("task_id")

                if action == "subscribe" and new_task_id:
                    try:
                        task_uuid = UUID(new_task_id)
                        await connection_manager.subscribe_to_task(client_id, task_uuid)
                        await connection_manager.send_personal_message(
                            {
                                "type": "subscribed",
                                "data": {"task_id": new_task_id},
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            client_id
                        )
                    except ValueError:
                        await connection_manager.send_personal_message(
                            {
                                "type": "error",
                                "data": {"message": "Invalid task_id format"},
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            client_id
                        )

                elif action == "unsubscribe" and new_task_id:
                    try:
                        task_uuid = UUID(new_task_id)
                        await connection_manager.unsubscribe_from_task(client_id, task_uuid)
                        await connection_manager.send_personal_message(
                            {
                                "type": "unsubscribed",
                                "data": {"task_id": new_task_id},
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            client_id
                        )
                    except ValueError:
                        await connection_manager.send_personal_message(
                            {
                                "type": "error",
                                "data": {"message": "Invalid task_id format"},
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            client_id
                        )

                elif action == "ping":
                    # Respond to ping with pong
                    await connection_manager.send_personal_message(
                        {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        client_id
                    )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected gracefully", client_id=client_id)
    except Exception as e:
        logger.error("WebSocket error", client_id=client_id, error=str(e), exc_info=True)
    finally:
        # Always cleanup on disconnect - this prevents memory leaks
        await connection_manager.disconnect(client_id)


# ==================== General WebSocket Endpoint ====================


@router.websocket("/ws")
async def general_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT access token for authentication"),
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service)
):
    """
    General WebSocket endpoint for real-time updates

    Supports dynamic subscription/unsubscription to tasks and workers.

    **Authentication:**
    Requires JWT access token passed as query parameter:
    `ws://host/api/v1/ws?token=<jwt_access_token>`

    **Query parameters:**
    - token: JWT access token (required)

    **WebSocket Protocol:**

    Subscribe to task updates:
    ```json
    {"action": "subscribe", "type": "task", "task_id": "uuid"}
    ```

    Subscribe to worker updates:
    ```json
    {"action": "subscribe", "type": "worker", "worker_id": "uuid"}
    ```

    Subscribe to all workers:
    ```json
    {"action": "subscribe", "type": "workers"}
    ```

    Unsubscribe:
    ```json
    {"action": "unsubscribe", "type": "task", "task_id": "uuid"}
    ```

    Ping/pong heartbeat:
    ```json
    {"action": "ping"}
    ```
    Response:
    ```json
    {"type": "heartbeat", "timestamp": "..."}
    ```

    Server broadcasts status updates:
    ```json
    {
        "type": "task_status",
        "data": {"task_id": "...", "status": "...", "progress": 50},
        "timestamp": "..."
    }
    ```
    """
    # --- Mandatory Authentication Check ---
    if not token:
        await websocket.close(code=4001, reason="Authentication required: missing token")
        logger.warning("General WebSocket connection rejected - no token provided")
        return

    # Verify JWT token
    try:
        payload = verify_token(token, expected_type=TokenType.ACCESS)
        user_id_str = payload.get("sub")
        if not user_id_str:
            await websocket.close(code=4003, reason="Invalid token: missing user identifier")
            logger.warning("General WebSocket connection rejected - invalid token")
            return

        user_id = UUID(user_id_str)

        # Verify user exists and is active
        user_result = await db.execute(select(User).where(User.user_id == user_id))
        user = user_result.scalar_one_or_none()

        if not user:
            await websocket.close(code=4004, reason="User not found")
            logger.warning("General WebSocket connection rejected - user not found", user_id=str(user_id))
            return

        if hasattr(user, "is_active") and not user.is_active:
            await websocket.close(code=4003, reason="User account is inactive")
            logger.warning("General WebSocket connection rejected - user inactive", user_id=str(user_id))
            return

        logger.info("General WebSocket authenticated", user_id=str(user_id), username=user.username)

    except (JWTError, ValueError) as e:
        await websocket.close(code=4003, reason=f"Authentication failed: {str(e)}")
        logger.warning("General WebSocket connection rejected - token verification failed", error=str(e))
        return

    # Generate unique client ID and accept WebSocket connection
    import uuid as uuid_module
    client_id = f"{user_id}_{uuid_module.uuid4()}"
    await connection_manager.connect(client_id, websocket, redis_service)
    logger.info("General WebSocket client connected", client_id=client_id, user_id=str(user_id))

    # Track subscriptions for this client
    task_subscriptions: Set[UUID] = set()
    worker_subscriptions: Set[UUID] = set()
    all_workers_subscribed = False

    try:
        # Start Redis Pub/Sub if not started
        if connection_manager.pubsub_manager and not connection_manager.pubsub_manager.pubsub:
            await connection_manager.pubsub_manager.start(connection_manager)

        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action", "")

                if action == "ping":
                    # Respond to ping
                    await connection_manager.send_personal_message(
                        {"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()},
                        client_id
                    )

                elif action == "subscribe":
                    msg_type = message.get("type", "")

                    if msg_type == "task" and "task_id" in message:
                        task_id = UUID(message["task_id"])
                        task_subscriptions.add(task_id)
                        # Use connection_manager for proper tracking
                        await connection_manager.subscribe_to_task(client_id, task_id)
                        logger.debug("Client subscribed to task", client_id=client_id, task_id=str(task_id))

                    elif msg_type == "worker" and "worker_id" in message:
                        worker_id = UUID(message["worker_id"])
                        worker_subscriptions.add(worker_id)
                        logger.debug("Client subscribed to worker", client_id=client_id, worker_id=str(worker_id))

                    elif msg_type == "workers":
                        all_workers_subscribed = True
                        logger.debug("Client subscribed to all workers", client_id=client_id)

                elif action == "unsubscribe":
                    msg_type = message.get("type", "")

                    if msg_type == "task" and "task_id" in message:
                        task_id = UUID(message["task_id"])
                        task_subscriptions.discard(task_id)
                        # Use connection_manager for proper cleanup
                        await connection_manager.unsubscribe_from_task(client_id, task_id)
                        logger.debug("Client unsubscribed from task", client_id=client_id, task_id=str(task_id))

                    elif msg_type == "worker" and "worker_id" in message:
                        worker_id = UUID(message["worker_id"])
                        worker_subscriptions.discard(worker_id)
                        logger.debug("Client unsubscribed from worker", client_id=client_id, worker_id=str(worker_id))

                    elif msg_type == "workers":
                        all_workers_subscribed = False
                        logger.debug("Client unsubscribed from all workers", client_id=client_id)

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Invalid WebSocket message", client_id=client_id, error=str(e))
                await connection_manager.send_personal_message(
                    {"type": "error", "message": f"Invalid message: {str(e)}"},
                    client_id
                )

    except WebSocketDisconnect:
        logger.info("General WebSocket client disconnected", client_id=client_id)
    except Exception as e:
        logger.error("General WebSocket error", client_id=client_id, error=str(e), exc_info=True)
    finally:
        # Always cleanup on disconnect - this prevents memory leaks
        await connection_manager.disconnect(client_id)


# ==================== Log POST Endpoint ====================


@router.post(
    "/subtasks/{subtask_id}/log",
    response_model=LogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send Log Message",
    description="Workers send log messages during subtask execution"
)
async def send_log(
    subtask_id: UUID,
    log_request: LogRequest,
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service)
):
    """
    Send a log message from a worker during subtask execution.

    The log message will be:
    1. Stored in Redis with 1-hour TTL
    2. Broadcast to all WebSocket clients subscribed to the parent task

    **Path parameters:**
    - subtask_id: UUID of the subtask generating the log

    **Request body:**
    - level: Log level (debug | info | warning | error)
    - message: Log message content
    - metadata: Optional additional metadata

    **Response:**
    - success: Whether log was stored successfully
    - message: Response message
    - broadcasted: Number of WebSocket clients that received the log
    """
    try:
        # Get subtask and verify it exists
        result = await db.execute(
            select(Subtask).where(Subtask.subtask_id == subtask_id)
        )
        subtask = result.scalar_one_or_none()

        if not subtask:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subtask {subtask_id} not found"
            )

        # Get worker info if assigned
        worker_id = subtask.assigned_worker
        worker_name = None
        if worker_id:
            from src.models.worker import Worker
            worker_result = await db.execute(
                select(Worker).where(Worker.worker_id == worker_id)
            )
            worker = worker_result.scalar_one_or_none()
            if worker:
                worker_name = worker.machine_name

        # Create log message
        log_message = LogMessage(
            subtask_id=subtask_id,
            task_id=subtask.task_id,
            level=log_request.level,
            message=log_request.message,
            worker_id=worker_id,
            worker_name=worker_name,
            timestamp=datetime.utcnow(),
            metadata=log_request.metadata
        )

        # Store log in Redis with configurable TTL
        log_key = f"logs:{subtask.task_id}:{subtask_id}:{datetime.utcnow().timestamp()}"
        await redis_service.redis.setex(
            log_key,
            settings.LOG_TTL_SECONDS,
            log_message.model_dump_json()
        )

        # Also add to a sorted set for ordered retrieval
        logs_set_key = f"logs:task:{subtask.task_id}"
        await redis_service.redis.zadd(
            logs_set_key,
            {log_key: datetime.utcnow().timestamp()}
        )
        # Set TTL on the sorted set too
        await redis_service.redis.expire(logs_set_key, settings.LOG_TTL_SECONDS)

        # Broadcast to WebSocket clients subscribed to the task
        ws_message = {
            "type": "log",
            "data": log_message.model_dump(mode='json'),
            "timestamp": datetime.utcnow().isoformat()
        }

        broadcasted = await connection_manager.broadcast_to_task_subscribers(
            subtask.task_id,
            ws_message
        )

        logger.info(
            "Log message sent",
            subtask_id=str(subtask_id),
            task_id=str(subtask.task_id),
            level=log_request.level,
            broadcasted=broadcasted
        )

        return LogResponse(
            success=True,
            message="Log stored and broadcast successfully",
            broadcasted=broadcasted
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to send log", subtask_id=str(subtask_id), error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send log: {str(e)}"
        )


# ==================== Log Retrieval Endpoint ====================


@router.get(
    "/tasks/{task_id}/logs",
    summary="Get Task Logs",
    description="Retrieve stored logs for a task"
)
async def get_task_logs(
    task_id: UUID,
    limit: int = Query(100, ge=1, le=1000, description="Maximum logs to return (1-1000)"),
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service)
):
    """
    Retrieve stored logs for a task from Redis.

    **Path parameters:**
    - task_id: UUID of the task

    **Query parameters:**
    - limit: Maximum number of logs to return (1-1000, default: 100)

    **Response:**
    - List of log messages ordered by timestamp (newest first)
    """
    try:
        # Verify task exists
        result = await db.execute(select(Task).where(Task.task_id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )

        # Get logs from Redis sorted set (newest first)
        logs_set_key = f"logs:task:{task_id}"
        log_keys = await redis_service.redis.zrevrange(logs_set_key, 0, limit - 1)

        # Retrieve log messages
        logs = []
        if log_keys:
            pipeline = redis_service.redis.pipeline()
            for log_key in log_keys:
                pipeline.get(log_key)
            log_data = await pipeline.execute()

            for data in log_data:
                if data:
                    try:
                        log_dict = json.loads(data)
                        logs.append(log_dict)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse log data", data=data)

        return {
            "task_id": str(task_id),
            "logs": logs,
            "count": len(logs)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get task logs", task_id=str(task_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task logs: {str(e)}"
        )
