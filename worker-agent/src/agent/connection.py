"""Connection management for worker agent"""

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID
import httpx
import websockets
import structlog

from .websocket_client import WebSocketClient

logger = structlog.get_logger()


class ConnectionManager:
    """Manage HTTP and WebSocket connections to backend"""

    def __init__(self, config: dict):
        """Initialize connection manager

        Args:
            config: Configuration dictionary with backend_url, api_key, etc.
        """
        self.backend_url = config["backend_url"]
        self.api_key = config.get("api_key", "")
        self.client: Optional[httpx.AsyncClient] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.ws_url = self.backend_url.replace("http://", "ws://").replace("https://", "wss://")
        self.connected = False

        # WebSocket client instance
        self.ws_client: Optional[WebSocketClient] = None

    async def connect(self):
        """Initialize HTTP client with API key authentication"""
        if self.client is None:
            headers = {
                "User-Agent": "MultiAgent-Worker/1.0",
                "X-Worker-API-Key": self.api_key,
            }
            self.client = httpx.AsyncClient(
                base_url=self.backend_url,
                timeout=30.0,
                headers=headers
            )
            logger.info("HTTP client initialized", backend_url=self.backend_url)

    async def close(self):
        """Close HTTP and WebSocket connections"""
        # Close WebSocket client
        if self.ws_client:
            await self.ws_client.disconnect()
            self.ws_client = None
            logger.info("WebSocket client closed")

        # Close HTTP client
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("HTTP client closed")

        # Close legacy WebSocket (if any)
        if self.ws:
            await self.ws.close()
            self.ws = None
            logger.info("WebSocket closed")

        self.connected = False

    async def register(
        self,
        machine_id: str,
        machine_name: str,
        system_info: dict,
        tools: List[str]
    ) -> UUID:
        """Register worker with backend

        Args:
            machine_id: Unique machine identifier
            machine_name: Human-readable machine name
            system_info: System information dictionary
            tools: List of available tool names

        Returns:
            UUID of registered worker

        Raises:
            httpx.HTTPError: If registration fails
        """
        await self.connect()

        logger.info(
            "Registering worker",
            machine_id=machine_id,
            machine_name=machine_name,
            tools=tools
        )

        response = await self.client.post(
            "/api/v1/workers/register",
            json={
                "machine_id": machine_id,
                "machine_name": machine_name,
                "system_info": system_info,
                "tools": tools
            }
        )
        response.raise_for_status()
        data = response.json()

        worker_id = UUID(data["worker_id"])
        logger.info("Worker registered successfully", worker_id=str(worker_id))

        self.connected = True
        return worker_id

    async def send_heartbeat(
        self,
        worker_id: UUID,
        resources: dict,
        status: str = "online"
    ) -> dict:
        """Send heartbeat to backend

        Args:
            worker_id: Worker UUID
            resources: Current resource usage dictionary with keys:
                - cpu_percent: CPU usage percentage
                - memory_percent: Memory usage percentage
                - disk_percent: Disk usage percentage
            status: Worker status (online, busy, idle)

        Returns:
            Backend response dictionary

        Raises:
            httpx.HTTPError: If heartbeat fails
        """
        if not self.client:
            await self.connect()

        response = await self.client.post(
            f"/api/v1/workers/{worker_id}/heartbeat",
            json={
                "status": status,
                "cpu_percent": resources.get("cpu_percent"),
                "memory_percent": resources.get("memory_percent"),
                "disk_percent": resources.get("disk_percent"),
            }
        )
        response.raise_for_status()
        return response.json()

    async def report_task_result(
        self,
        worker_id: UUID,
        subtask_id: UUID,
        result: dict
    ) -> dict:
        """Report task execution result to backend

        Args:
            worker_id: Worker UUID
            subtask_id: Subtask UUID
            result: Task result dictionary

        Returns:
            Backend response dictionary

        Raises:
            httpx.HTTPError: If report fails
        """
        if not self.client:
            await self.connect()

        logger.info(
            "Reporting task result",
            worker_id=str(worker_id),
            subtask_id=str(subtask_id),
            success=result.get("success")
        )

        response = await self.client.post(
            f"/api/v1/workers/{worker_id}/tasks/{subtask_id}/result",
            json=result
        )
        response.raise_for_status()
        return response.json()

    async def connect_websocket(
        self,
        worker_id: UUID,
        message_handler: Callable[[dict], Any],
        on_connect: Optional[Callable[[], Any]] = None,
        on_disconnect: Optional[Callable[[], Any]] = None
    ):
        """Connect to WebSocket with auto-reconnect and heartbeat

        Args:
            worker_id: Worker UUID
            message_handler: Async function to handle incoming messages
            on_connect: Optional callback when connection established
            on_disconnect: Optional callback when connection lost

        Note:
            This method will run indefinitely with automatic reconnection.
            Call disconnect_websocket() to stop the connection.
        """
        # Create WebSocket client if not already created
        if self.ws_client is None:
            self.ws_client = WebSocketClient(
                ws_url=self.ws_url,
                worker_id=worker_id,
                message_handler=message_handler,
                on_connect=on_connect,
                on_disconnect=on_disconnect,
                api_key=self.api_key
            )

        # Connect (this will run indefinitely with auto-reconnect)
        await self.ws_client.connect()

    async def disconnect_websocket(self):
        """Disconnect WebSocket client gracefully"""
        if self.ws_client:
            await self.ws_client.disconnect()
            self.ws_client = None

    def is_websocket_connected(self) -> bool:
        """Check if WebSocket is currently connected

        Returns:
            True if connected, False otherwise
        """
        return self.ws_client is not None and self.ws_client.is_connected()

    async def send_websocket_message(self, message: dict):
        """Send message via WebSocket

        Args:
            message: Message dictionary to send

        Note:
            If WebSocket is not connected, the message will be queued
            for sending when the connection is re-established.
        """
        if self.ws_client:
            await self.ws_client.send_message(message)
        else:
            logger.warning(
                "WebSocket client not initialized, message not sent",
                message_type=message.get("type")
            )

    async def unregister(self, worker_id: UUID) -> bool:
        """Unregister worker from backend (graceful shutdown)

        Args:
            worker_id: Worker UUID to unregister

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            await self.connect()

        logger.info("Unregistering worker", worker_id=str(worker_id))

        try:
            response = await self.client.post(
                f"/api/v1/workers/{worker_id}/unregister"
            )
            response.raise_for_status()
            logger.info("Worker unregistered successfully", worker_id=str(worker_id))
            return True
        except Exception as e:
            logger.error("Failed to unregister worker", worker_id=str(worker_id), error=str(e))
            return False

    async def send_final_heartbeat(
        self,
        worker_id: UUID,
        resources: dict
    ) -> bool:
        """Send final heartbeat with offline status before shutdown

        Args:
            worker_id: Worker UUID
            resources: Current resource usage dictionary

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            await self.connect()

        logger.info("Sending final heartbeat (offline)", worker_id=str(worker_id))

        try:
            response = await self.client.post(
                f"/api/v1/workers/{worker_id}/heartbeat",
                json={
                    "status": "offline",
                    "cpu_percent": resources.get("cpu_percent"),
                    "memory_percent": resources.get("memory_percent"),
                    "disk_percent": resources.get("disk_percent"),
                }
            )
            response.raise_for_status()
            logger.info("Final heartbeat sent", worker_id=str(worker_id))
            return True
        except Exception as e:
            logger.error("Failed to send final heartbeat", worker_id=str(worker_id), error=str(e))
            return False

    async def poll_for_tasks(self, worker_id: UUID) -> Optional[dict]:
        """Poll backend for pending task assignments (fallback when WebSocket unavailable)

        Args:
            worker_id: Worker UUID

        Returns:
            Task assignment dictionary or None if no tasks available

        Raises:
            httpx.HTTPError: If polling fails
        """
        if not self.client:
            await self.connect()

        try:
            response = await self.client.get(
                f"/api/v1/workers/{worker_id}/pull-task",
                timeout=10.0
            )

            # 204 No Content means no tasks available
            if response.status_code == 204:
                return None

            response.raise_for_status()
            backend_data = response.json()

            # No task available (null response)
            if backend_data is None:
                return None

            # Map backend field names to worker-agent expected format
            # Backend sends: task_id, description, tool_preference, priority, workflow_id, metadata
            # Worker expects: subtask_id, description, assigned_tool, context
            task_data = {
                "subtask_id": str(backend_data.get("task_id")),
                "description": backend_data.get("description"),
                "assigned_tool": backend_data.get("tool_preference") or "claude_code",  # Default to claude_code
                "context": backend_data.get("metadata") or {},
                "priority": backend_data.get("priority"),
                "workflow_id": str(backend_data.get("workflow_id")) if backend_data.get("workflow_id") else None,
            }

            logger.info(
                "Task polled from backend",
                worker_id=str(worker_id),
                subtask_id=task_data.get("subtask_id"),
                tool=task_data.get("assigned_tool")
            )

            return task_data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Worker not found or no tasks available
                return None
            logger.error("Task polling failed", worker_id=str(worker_id), error=str(e))
            raise
        except Exception as e:
            logger.error("Task polling error", worker_id=str(worker_id), error=str(e))
            raise

    async def upload_subtask_result(
        self,
        worker_id: UUID,
        subtask_id: UUID,
        result: dict
    ) -> dict:
        """Upload subtask execution result to backend

        Args:
            worker_id: Worker UUID
            subtask_id: Task/Subtask UUID
            result: Result dictionary containing:
                - success: bool
                - output: Any - Execution output
                - error: Optional[str] - Error message if failed
                - metadata: dict - Execution metadata
                - execution_time: float - Execution time in seconds (optional)

        Returns:
            Backend response dictionary

        Raises:
            httpx.HTTPError: If upload fails
        """
        if not self.client:
            await self.connect()

        success = result.get("success", False)

        logger.info(
            "Uploading task result",
            worker_id=str(worker_id),
            task_id=str(subtask_id),
            success=success
        )

        if success:
            # Use task-complete endpoint
            request_body = {
                "task_id": str(subtask_id),
                "result": {
                    "output": result.get("output"),
                    "metadata": result.get("metadata", {}),
                    "execution_time": result.get("execution_time", 0.0)
                }
            }
            response = await self.client.post(
                f"/api/v1/workers/{worker_id}/task-complete",
                json=request_body
            )
        else:
            # Use task-failed endpoint
            request_body = {
                "task_id": str(subtask_id),
                "error": result.get("error", "Unknown error")
            }
            response = await self.client.post(
                f"/api/v1/workers/{worker_id}/task-failed",
                json=request_body
            )

        response.raise_for_status()

        logger.info("Task result uploaded successfully", task_id=str(subtask_id))
        return response.json()

    async def stream_execution_log(
        self,
        subtask_id: UUID,
        log_line: str,
        log_level: str = "info",
        metadata: Optional[dict] = None
    ) -> bool:
        """Stream execution log line to backend in real-time

        Args:
            subtask_id: Subtask UUID
            log_line: Log message/line to stream
            log_level: Log level (debug, info, warning, error)
            metadata: Optional metadata dictionary

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            await self.connect()

        try:
            response = await self.client.post(
                f"/api/v1/subtasks/{subtask_id}/logs",
                json={
                    "log_line": log_line,
                    "log_level": log_level,
                    "metadata": metadata or {}
                },
                timeout=5.0  # Short timeout for log streaming
            )
            response.raise_for_status()
            return True
        except Exception as e:
            # Don't raise - log streaming is non-critical
            logger.debug(
                "Failed to stream log",
                subtask_id=str(subtask_id),
                error=str(e)
            )
            return False

    async def update_worker_status(
        self,
        worker_id: UUID,
        status: str,
        current_task: Optional[UUID] = None
    ) -> bool:
        """Update worker status (online/busy/idle)

        Args:
            worker_id: Worker UUID
            status: Worker status (online, busy, idle)
            current_task: Optional current task UUID if busy

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            await self.connect()

        try:
            # Use heartbeat endpoint for status updates
            resources = {"cpu_percent": 0, "memory_percent": 0, "disk_percent": 0}

            response = await self.client.post(
                f"/api/v1/workers/{worker_id}/heartbeat",
                json={
                    "status": status,
                    "resources": resources,
                    "current_task": str(current_task) if current_task else None
                },
                timeout=10.0
            )
            response.raise_for_status()

            logger.debug(
                "Worker status updated",
                worker_id=str(worker_id),
                status=status,
                current_task=str(current_task) if current_task else None
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to update worker status",
                worker_id=str(worker_id),
                status=status,
                error=str(e)
            )
            return False
