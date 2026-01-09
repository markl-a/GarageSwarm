"""WebSocket client with auto-reconnect and heartbeat support"""

import asyncio
import json
from typing import Callable, Optional, Any
from uuid import UUID

import structlog
import websockets
from websockets.exceptions import WebSocketException

logger = structlog.get_logger()


class WebSocketClient:
    """WebSocket client with automatic reconnection and heartbeat

    Features:
    - Auto-reconnect with exponential backoff
    - Heartbeat/ping-pong to keep connection alive
    - Graceful handling of connection failures
    - Message queue for sending during reconnection
    """

    # Reconnection backoff configuration
    MIN_RECONNECT_DELAY = 1.0  # seconds
    MAX_RECONNECT_DELAY = 60.0  # seconds
    BACKOFF_MULTIPLIER = 2.0

    # Heartbeat configuration
    HEARTBEAT_INTERVAL = 30.0  # seconds
    HEARTBEAT_TIMEOUT = 10.0  # seconds

    def __init__(
        self,
        ws_url: str,
        worker_id: UUID,
        message_handler: Callable[[dict], Any],
        on_connect: Optional[Callable[[], Any]] = None,
        on_disconnect: Optional[Callable[[], Any]] = None,
        api_key: str = ""
    ):
        """Initialize WebSocket client

        Args:
            ws_url: WebSocket URL to connect to
            worker_id: Worker UUID
            message_handler: Async function to handle incoming messages
            on_connect: Optional callback when connection established
            on_disconnect: Optional callback when connection lost
            api_key: Worker API key for authentication
        """
        self.ws_url = ws_url
        self.worker_id = worker_id
        self.message_handler = message_handler
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.api_key = api_key

        # Connection state (use locks to prevent race conditions)
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._state_lock = asyncio.Lock()
        self.connected = False
        self.running = False
        self.reconnect_delay = self.MIN_RECONNECT_DELAY

        # Background tasks
        self.receive_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None

        # Message queue for sending during disconnection
        self.send_queue: asyncio.Queue = asyncio.Queue()

        # Connection attempt tracking
        self._connection_attempt = 0

        logger.info(
            "WebSocketClient initialized",
            ws_url=ws_url,
            worker_id=str(worker_id)
        )

    async def connect(self):
        """Connect to WebSocket server with retry logic"""
        async with self._state_lock:
            if self.running:
                logger.warning("WebSocket client already running")
                return

            self.running = True

        while self.running:
            self._connection_attempt += 1

            try:
                # Build WebSocket endpoint URL
                ws_endpoint = f"{self.ws_url}/api/v1/workers/{self.worker_id}/ws"

                logger.info(
                    "Connecting to WebSocket",
                    url=ws_endpoint,
                    attempt=self._connection_attempt,
                    attempt_delay=self.reconnect_delay
                )

                # Connect to WebSocket with API key authentication
                extra_headers = {
                    "X-Worker-API-Key": self.api_key,
                }
                async with websockets.connect(
                    ws_endpoint,
                    ping_interval=None,  # We'll handle our own heartbeat
                    ping_timeout=None,
                    close_timeout=10.0,
                    max_size=10 * 1024 * 1024,  # 10MB max message size
                    extra_headers=extra_headers,
                ) as websocket:
                    # Atomically update connection state
                    async with self._state_lock:
                        self.ws = websocket
                        self.connected = True
                        self.reconnect_delay = self.MIN_RECONNECT_DELAY  # Reset backoff
                        self._connection_attempt = 0  # Reset attempt counter

                    logger.info("WebSocket connected successfully", attempt=self._connection_attempt)

                    # Call on_connect callback
                    if self.on_connect:
                        try:
                            if asyncio.iscoroutinefunction(self.on_connect):
                                await self.on_connect()
                            else:
                                self.on_connect()
                        except Exception as e:
                            logger.error("Error in on_connect callback", error=str(e))

                    # Start background tasks
                    self.receive_task = asyncio.create_task(self._receive_loop())
                    self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                    # Process queued messages
                    await self._process_send_queue()

                    # Wait for tasks to complete (connection lost)
                    await asyncio.gather(
                        self.receive_task,
                        self.heartbeat_task,
                        return_exceptions=True
                    )

            except websockets.exceptions.WebSocketException as e:
                logger.warning("WebSocket connection error", error=str(e))
            except Exception as e:
                logger.error("Unexpected WebSocket error", error=str(e), error_type=type(e).__name__)
            finally:
                # Cleanup
                await self._cleanup_connection()

            # Reconnect with exponential backoff
            if self.running:
                logger.info(
                    "Reconnecting to WebSocket",
                    delay=self.reconnect_delay
                )
                await asyncio.sleep(self.reconnect_delay)

                # Increase backoff delay (exponential)
                self.reconnect_delay = min(
                    self.reconnect_delay * self.BACKOFF_MULTIPLIER,
                    self.MAX_RECONNECT_DELAY
                )

    async def disconnect(self):
        """Disconnect from WebSocket server gracefully"""
        logger.info("Disconnecting WebSocket client")

        # Atomically stop the running flag
        async with self._state_lock:
            if not self.running:
                logger.debug("WebSocket client already disconnected")
                return
            self.running = False

        # Cancel background tasks
        if self.receive_task and not self.receive_task.done():
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass

        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket connection
        async with self._state_lock:
            if self.ws and not self.ws.closed:
                try:
                    await self.ws.close()
                except Exception as e:
                    logger.debug("Error closing WebSocket", error=str(e))

        await self._cleanup_connection()

        logger.info("WebSocket client disconnected")

    async def send_message(self, message: dict):
        """Send message via WebSocket

        Args:
            message: Message dictionary to send

        If not connected, the message will be queued for sending when reconnected.
        """
        # Check connection state atomically
        async with self._state_lock:
            is_connected = self.connected and self.ws is not None and not self.ws.closed
            ws_ref = self.ws

        if is_connected and ws_ref:
            try:
                await ws_ref.send(json.dumps(message))
                logger.debug("Message sent", message_type=message.get("type"))
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed while sending, queuing message")
                await self.send_queue.put(message)
            except Exception as e:
                logger.error("Failed to send message", error=str(e))
                # Queue message for retry
                await self.send_queue.put(message)
        else:
            # Queue message for sending when connected
            logger.debug(
                "WebSocket not connected, queuing message",
                message_type=message.get("type")
            )
            await self.send_queue.put(message)

    async def _receive_loop(self):
        """Receive messages from WebSocket"""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    logger.debug("Message received", message_type=data.get("type"))

                    # Handle message with user-provided handler
                    try:
                        if asyncio.iscoroutinefunction(self.message_handler):
                            await self.message_handler(data)
                        else:
                            self.message_handler(data)
                    except Exception as e:
                        logger.error(
                            "Error in message handler",
                            error=str(e),
                            message_type=data.get("type")
                        )

                except json.JSONDecodeError as e:
                    logger.error("Invalid JSON message", error=str(e), message=message[:100])
                except Exception as e:
                    logger.error("Error processing message", error=str(e))

        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")
            raise
        except Exception as e:
            logger.error("Receive loop error", error=str(e))

    async def _heartbeat_loop(self):
        """Send periodic heartbeat/ping to keep connection alive"""
        try:
            while self.connected and not self.ws.closed:
                try:
                    # Send ping message
                    ping_message = {
                        "type": "ping",
                        "worker_id": str(self.worker_id)
                    }

                    await self.ws.send(json.dumps(ping_message))
                    logger.debug("Heartbeat ping sent")

                    # Wait for next heartbeat interval
                    await asyncio.sleep(self.HEARTBEAT_INTERVAL)

                except websockets.exceptions.ConnectionClosed:
                    logger.debug("Connection closed during heartbeat")
                    break
                except Exception as e:
                    logger.error("Heartbeat error", error=str(e))
                    break

        except asyncio.CancelledError:
            logger.debug("Heartbeat loop cancelled")
            raise
        except Exception as e:
            logger.error("Heartbeat loop error", error=str(e))

    async def _process_send_queue(self):
        """Process any queued messages after reconnection"""
        queue_size = self.send_queue.qsize()

        if queue_size > 0:
            logger.info("Processing queued messages", count=queue_size)

            processed = 0
            while not self.send_queue.empty() and self.connected:
                try:
                    message = await asyncio.wait_for(
                        self.send_queue.get(),
                        timeout=1.0
                    )

                    if self.ws and not self.ws.closed:
                        await self.ws.send(json.dumps(message))
                        processed += 1
                    else:
                        # Put back in queue if connection lost
                        await self.send_queue.put(message)
                        break

                except asyncio.TimeoutError:
                    break
                except Exception as e:
                    logger.error("Error processing queued message", error=str(e))

            if processed > 0:
                logger.info("Queued messages processed", count=processed)

    async def _cleanup_connection(self):
        """Clean up connection state"""
        # Atomically update connection state
        async with self._state_lock:
            was_connected = self.connected
            self.connected = False
            self.ws = None

        # Call on_disconnect callback (outside lock to prevent deadlock)
        if was_connected and self.on_disconnect:
            try:
                if asyncio.iscoroutinefunction(self.on_disconnect):
                    await self.on_disconnect()
                else:
                    self.on_disconnect()
            except Exception as e:
                logger.error("Error in on_disconnect callback", error=str(e))

    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected

        Returns:
            True if connected, False otherwise

        Note: This is a non-blocking check. For critical operations,
        use the state lock to ensure atomicity.
        """
        return self.connected and self.ws is not None and not self.ws.closed

    def get_status(self) -> dict:
        """Get WebSocket client status

        Returns:
            Status dictionary
        """
        return {
            "connected": self.connected,
            "running": self.running,
            "reconnect_delay": self.reconnect_delay,
            "queued_messages": self.send_queue.qsize(),
            "ws_url": self.ws_url,
            "worker_id": str(self.worker_id)
        }
