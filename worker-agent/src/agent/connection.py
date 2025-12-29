"""Connection management for worker agent"""

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID
import httpx
import websockets
import structlog

logger = structlog.get_logger()


class ConnectionManager:
    """Manage HTTP and WebSocket connections to backend"""

    def __init__(self, config: dict):
        """Initialize connection manager

        Args:
            config: Configuration dictionary with backend_url, etc.
        """
        self.backend_url = config["backend_url"]
        self.client: Optional[httpx.AsyncClient] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.ws_url = self.backend_url.replace("http://", "ws://").replace("https://", "wss://")
        self.connected = False

    async def connect(self):
        """Initialize HTTP client"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.backend_url,
                timeout=30.0,
                headers={"User-Agent": "MultiAgent-Worker/1.0"}
            )
            logger.info("HTTP client initialized", backend_url=self.backend_url)

    async def close(self):
        """Close HTTP and WebSocket connections"""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("HTTP client closed")

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
            resources: Current resource usage dictionary
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
                "resources": resources
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
        message_handler: Callable[[dict], Any]
    ):
        """Connect to WebSocket and listen for messages

        Args:
            worker_id: Worker UUID
            message_handler: Async function to handle incoming messages

        Raises:
            websockets.WebSocketException: If connection fails
        """
        ws_endpoint = f"{self.ws_url}/api/v1/workers/{worker_id}/ws"
        logger.info("Connecting to WebSocket", url=ws_endpoint)

        try:
            async with websockets.connect(ws_endpoint) as websocket:
                self.ws = websocket
                logger.info("WebSocket connected")

                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await message_handler(data)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON message", message=message)
                    except Exception as e:
                        logger.error("Error handling message", error=str(e))

        except websockets.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.ws = None
        except Exception as e:
            logger.error("WebSocket connection error", error=str(e))
            self.ws = None
            raise

    async def send_websocket_message(self, message: dict):
        """Send message via WebSocket

        Args:
            message: Message dictionary to send

        Raises:
            RuntimeError: If WebSocket not connected
        """
        if not self.ws:
            raise RuntimeError("WebSocket not connected")

        await self.ws.send(json.dumps(message))

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
                    "resources": resources
                }
            )
            response.raise_for_status()
            logger.info("Final heartbeat sent", worker_id=str(worker_id))
            return True
        except Exception as e:
            logger.error("Failed to send final heartbeat", worker_id=str(worker_id), error=str(e))
            return False
