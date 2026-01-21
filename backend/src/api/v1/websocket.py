"""
WebSocket Endpoints for Worker Connections

Handles real-time communication between backend and workers.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Optional, Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db, AsyncSessionLocal
from src.models.worker import Worker
from src.models.task import Task
from src.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections for workers.

    Handles connection lifecycle, message routing, and broadcasting.
    """

    def __init__(self):
        # Active connections keyed by worker_id
        self.active_connections: Dict[str, WebSocket] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, worker_id: str, websocket: WebSocket) -> bool:
        """
        Accept a new WebSocket connection for a worker.

        Args:
            worker_id: The worker's UUID as string
            websocket: The WebSocket connection

        Returns:
            True if connection was successful, False otherwise
        """
        await websocket.accept()

        async with self._lock:
            # Close existing connection if any
            if worker_id in self.active_connections:
                old_ws = self.active_connections[worker_id]
                try:
                    await old_ws.close(code=1000, reason="New connection established")
                except Exception:
                    pass

            self.active_connections[worker_id] = websocket

        logger.info(
            "WebSocket connected",
            worker_id=worker_id,
            total_connections=len(self.active_connections),
        )
        return True

    async def disconnect(self, worker_id: str) -> None:
        """
        Remove a worker's WebSocket connection.

        Args:
            worker_id: The worker's UUID as string
        """
        async with self._lock:
            if worker_id in self.active_connections:
                del self.active_connections[worker_id]

        logger.info(
            "WebSocket disconnected",
            worker_id=worker_id,
            total_connections=len(self.active_connections),
        )

    async def send_to_worker(self, worker_id: str, message: dict) -> bool:
        """
        Send a message to a specific worker.

        Args:
            worker_id: The worker's UUID as string
            message: Dictionary to send as JSON

        Returns:
            True if message was sent, False if worker not connected
        """
        websocket = self.active_connections.get(worker_id)
        if websocket is None:
            logger.warning("Worker not connected", worker_id=worker_id)
            return False

        try:
            await websocket.send_json(message)
            logger.debug("Message sent to worker", worker_id=worker_id, message_type=message.get("type"))
            return True
        except Exception as e:
            logger.error("Failed to send message", worker_id=worker_id, error=str(e))
            await self.disconnect(worker_id)
            return False

    async def broadcast(self, message: dict, exclude: Optional[list] = None) -> int:
        """
        Broadcast a message to all connected workers.

        Args:
            message: Dictionary to send as JSON
            exclude: List of worker_ids to exclude from broadcast

        Returns:
            Number of workers message was sent to
        """
        exclude = exclude or []
        sent_count = 0
        disconnected = []

        for worker_id, websocket in list(self.active_connections.items()):
            if worker_id in exclude:
                continue

            try:
                await websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.error("Broadcast failed for worker", worker_id=worker_id, error=str(e))
                disconnected.append(worker_id)

        # Clean up disconnected workers
        for worker_id in disconnected:
            await self.disconnect(worker_id)

        logger.debug(
            "Broadcast complete",
            message_type=message.get("type"),
            sent_count=sent_count,
        )
        return sent_count

    def is_connected(self, worker_id: str) -> bool:
        """Check if a worker is currently connected."""
        return worker_id in self.active_connections

    def get_connected_workers(self) -> list:
        """Get list of all connected worker IDs."""
        return list(self.active_connections.keys())

    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)


# Global connection manager instance
manager = ConnectionManager()


async def get_connection_manager() -> ConnectionManager:
    """Dependency to get the connection manager."""
    return manager


@router.websocket("/ws/worker/{worker_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    worker_id: str,
):
    """
    WebSocket endpoint for worker connections.

    Protocol:
    - On connect: Worker sends authentication/registration message
    - Heartbeat: Worker sends periodic heartbeat, server responds with ack
    - Task assignment: Server pushes tasks to worker
    - Task updates: Worker sends progress/completion updates

    Message format:
    {
        "type": "heartbeat" | "task_result" | "task_progress" | "register" | ...,
        "data": { ... },
        "timestamp": "ISO8601"
    }
    """
    # Validate worker_id format
    try:
        worker_uuid = UUID(worker_id)
    except ValueError:
        await websocket.close(code=1008, reason="Invalid worker_id format")
        return

    # Accept connection
    await manager.connect(worker_id, websocket)

    # Update worker status in database
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Worker).where(Worker.worker_id == worker_uuid)
        )
        worker = result.scalar_one_or_none()

        if worker:
            worker.last_heartbeat = datetime.utcnow()
            worker.status = "idle"
            await db.commit()
        else:
            logger.warning("Unknown worker connected", worker_id=worker_id)

    # Send connection acknowledgment
    await websocket.send_json({
        "type": "connected",
        "data": {
            "worker_id": worker_id,
            "message": "Connection established",
        },
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Heartbeat task
    heartbeat_interval = 30  # seconds
    last_heartbeat = datetime.utcnow()

    try:
        while True:
            try:
                # Wait for message with timeout for heartbeat check
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=heartbeat_interval + 10
                )

                await handle_message(worker_id, message, websocket)
                last_heartbeat = datetime.utcnow()

            except asyncio.TimeoutError:
                # Check if we should send a ping
                elapsed = (datetime.utcnow() - last_heartbeat).total_seconds()
                if elapsed > heartbeat_interval * 2:
                    logger.warning("Worker heartbeat timeout", worker_id=worker_id)
                    break

                # Send ping to keep connection alive
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                except Exception:
                    break

    except WebSocketDisconnect as e:
        logger.info(
            "WebSocket disconnected by client",
            worker_id=worker_id,
            code=e.code,
        )
    except Exception as e:
        logger.error(
            "WebSocket error",
            worker_id=worker_id,
            error=str(e),
        )
    finally:
        await manager.disconnect(worker_id)

        # Update worker status in database
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Worker).where(Worker.worker_id == worker_uuid)
            )
            worker = result.scalar_one_or_none()
            if worker:
                worker.status = "offline"
                await db.commit()


async def handle_message(worker_id: str, message: dict, websocket: WebSocket) -> None:
    """
    Handle incoming messages from workers.

    Args:
        worker_id: The worker's UUID as string
        message: The received message dictionary
        websocket: The WebSocket connection
    """
    message_type = message.get("type", "unknown")
    data = message.get("data", {})

    logger.debug(
        "Message received",
        worker_id=worker_id,
        message_type=message_type,
    )

    if message_type == "heartbeat":
        await handle_heartbeat(worker_id, data, websocket)

    elif message_type == "pong":
        # Response to our ping, connection is alive
        pass

    elif message_type == "task_progress":
        await handle_task_progress(worker_id, data)

    elif message_type == "task_result":
        await handle_task_result(worker_id, data)

    elif message_type == "task_failed":
        await handle_task_failed(worker_id, data)

    elif message_type == "register":
        await handle_register(worker_id, data, websocket)

    else:
        logger.warning(
            "Unknown message type",
            worker_id=worker_id,
            message_type=message_type,
        )
        await websocket.send_json({
            "type": "error",
            "data": {"message": f"Unknown message type: {message_type}"},
            "timestamp": datetime.utcnow().isoformat(),
        })


async def handle_heartbeat(worker_id: str, data: dict, websocket: WebSocket) -> None:
    """Handle heartbeat message from worker."""
    worker_uuid = UUID(worker_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Worker).where(Worker.worker_id == worker_uuid)
        )
        worker = result.scalar_one_or_none()

        if worker:
            worker.last_heartbeat = datetime.utcnow()
            worker.status = data.get("status", worker.status)

            # Update resource metrics if provided
            if "cpu_percent" in data:
                worker.cpu_percent = data["cpu_percent"]
            if "memory_percent" in data:
                worker.memory_percent = data["memory_percent"]
            if "disk_percent" in data:
                worker.disk_percent = data["disk_percent"]

            await db.commit()

    # Send heartbeat acknowledgment
    await websocket.send_json({
        "type": "heartbeat_ack",
        "data": {"status": "ok"},
        "timestamp": datetime.utcnow().isoformat(),
    })


async def handle_task_progress(worker_id: str, data: dict) -> None:
    """Handle task progress update from worker."""
    task_id = data.get("task_id")
    progress = data.get("progress", 0)

    if not task_id:
        logger.warning("Task progress without task_id", worker_id=worker_id)
        return

    try:
        task_uuid = UUID(task_id)
    except ValueError:
        logger.warning("Invalid task_id format", worker_id=worker_id, task_id=task_id)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Task).where(Task.task_id == task_uuid)
        )
        task = result.scalar_one_or_none()

        if task:
            task.progress = min(100, max(0, progress))
            if task.status == "assigned":
                task.status = "running"
            await db.commit()

            logger.debug(
                "Task progress updated",
                task_id=task_id,
                progress=progress,
            )


async def handle_task_result(worker_id: str, data: dict) -> None:
    """Handle task completion from worker."""
    task_id = data.get("task_id")
    result_data = data.get("result")

    if not task_id:
        logger.warning("Task result without task_id", worker_id=worker_id)
        return

    try:
        task_uuid = UUID(task_id)
        worker_uuid = UUID(worker_id)
    except ValueError:
        logger.warning("Invalid UUID format", worker_id=worker_id, task_id=task_id)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Task).where(
                Task.task_id == task_uuid,
                Task.worker_id == worker_uuid,
            )
        )
        task = result.scalar_one_or_none()

        if task:
            task.status = "completed"
            task.result = result_data
            task.progress = 100
            task.completed_at = datetime.utcnow()
            task.version += 1

            # Update worker status
            worker_result = await db.execute(
                select(Worker).where(Worker.worker_id == worker_uuid)
            )
            worker = worker_result.scalar_one_or_none()
            if worker:
                worker.status = "idle"

            await db.commit()

            logger.info(
                "Task completed via WebSocket",
                task_id=task_id,
                worker_id=worker_id,
            )


async def handle_task_failed(worker_id: str, data: dict) -> None:
    """Handle task failure from worker."""
    task_id = data.get("task_id")
    error = data.get("error", "Unknown error")

    if not task_id:
        logger.warning("Task failed without task_id", worker_id=worker_id)
        return

    try:
        task_uuid = UUID(task_id)
        worker_uuid = UUID(worker_id)
    except ValueError:
        logger.warning("Invalid UUID format", worker_id=worker_id, task_id=task_id)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Task).where(
                Task.task_id == task_uuid,
                Task.worker_id == worker_uuid,
            )
        )
        task = result.scalar_one_or_none()

        if task:
            task.status = "failed"
            task.error = error
            task.completed_at = datetime.utcnow()
            task.version += 1

            # Update worker status
            worker_result = await db.execute(
                select(Worker).where(Worker.worker_id == worker_uuid)
            )
            worker = worker_result.scalar_one_or_none()
            if worker:
                worker.status = "idle"

            await db.commit()

            logger.info(
                "Task failed via WebSocket",
                task_id=task_id,
                worker_id=worker_id,
                error=error,
            )


async def handle_register(worker_id: str, data: dict, websocket: WebSocket) -> None:
    """Handle worker registration/update via WebSocket."""
    worker_uuid = UUID(worker_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Worker).where(Worker.worker_id == worker_uuid)
        )
        worker = result.scalar_one_or_none()

        if worker:
            # Update worker info
            if "tools" in data:
                worker.tools = data["tools"]
            if "system_info" in data:
                worker.system_info = data["system_info"]
            if "machine_name" in data:
                worker.machine_name = data["machine_name"]

            worker.last_heartbeat = datetime.utcnow()
            worker.status = "idle"
            await db.commit()

            await websocket.send_json({
                "type": "register_ack",
                "data": {
                    "worker_id": worker_id,
                    "status": "updated",
                },
                "timestamp": datetime.utcnow().isoformat(),
            })
        else:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": "Worker not found. Please register via HTTP first.",
                },
                "timestamp": datetime.utcnow().isoformat(),
            })


# Helper functions for external use

async def send_task_to_worker(worker_id: str, task: dict) -> bool:
    """
    Send a task assignment to a worker via WebSocket.

    Args:
        worker_id: The worker's UUID as string
        task: Task data dictionary

    Returns:
        True if task was sent successfully
    """
    return await manager.send_to_worker(worker_id, {
        "type": "task_assignment",
        "data": task,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def broadcast_notification(notification: dict, exclude: Optional[list] = None) -> int:
    """
    Broadcast a notification to all connected workers.

    Args:
        notification: Notification data
        exclude: Worker IDs to exclude

    Returns:
        Number of workers notified
    """
    return await manager.broadcast({
        "type": "notification",
        "data": notification,
        "timestamp": datetime.utcnow().isoformat(),
    }, exclude=exclude)
