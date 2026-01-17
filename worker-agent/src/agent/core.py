"""Worker Agent core implementation"""

import asyncio
import signal
import sys
from typing import Dict, Optional
from uuid import UUID

import structlog

from config import load_or_create_machine_id
from tools.base import BaseTool
from .connection import ConnectionManager
from .executor import TaskExecutor
from .monitor import ResourceMonitor

logger = structlog.get_logger()


class WorkerAgent:
    """Main Worker Agent class

    Coordinates:
    - Connection to backend
    - Task execution
    - Resource monitoring
    - Heartbeat loop
    - Graceful shutdown handling
    """

    # Default shutdown timeout in seconds
    DEFAULT_SHUTDOWN_TIMEOUT = 60

    def __init__(self, config: dict):
        """Initialize Worker Agent

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.worker_id: Optional[UUID] = None
        self.machine_id = load_or_create_machine_id()

        # Initialize components
        self.connection_manager = ConnectionManager(config)
        self.task_executor = TaskExecutor()
        self.resource_monitor = ResourceMonitor()

        # State
        self.running = False
        self.shutting_down = False
        self.accepting_tasks = True
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.ws_task: Optional[asyncio.Task] = None
        self.polling_task: Optional[asyncio.Task] = None
        self._shutdown_event: Optional[asyncio.Event] = None
        self.use_websocket = config.get("use_websocket", True)
        self.use_polling = config.get("use_polling_fallback", True)
        self.polling_interval = config.get("polling_interval", 10)  # seconds
        self.ws_connected = False  # Track WebSocket connection state

        # Shutdown configuration
        self.shutdown_timeout = config.get("shutdown_timeout", self.DEFAULT_SHUTDOWN_TIMEOUT)

        logger.info(
            "WorkerAgent initialized",
            machine_id=self.machine_id,
            machine_name=config["machine_name"],
            shutdown_timeout=self.shutdown_timeout
        )

    def register_tool(self, name: str, tool: BaseTool):
        """Register an AI tool

        Args:
            name: Tool name
            tool: BaseTool instance
        """
        self.task_executor.register_tool(name, tool)

    async def start(self):
        """Start the Worker Agent

        1. Register with backend
        2. Start heartbeat loop
        3. Start WebSocket listener
        """
        if self.running:
            logger.warning("Worker Agent already running")
            return

        logger.info("Starting Worker Agent...")

        try:
            # Step 1: Register with backend
            self.worker_id = await self.connection_manager.register(
                machine_id=self.machine_id,
                machine_name=self.config["machine_name"],
                system_info=self.resource_monitor.get_system_info(),
                tools=self.task_executor.get_available_tools()
            )

            self.running = True

            # Step 2: Start heartbeat loop
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # Step 3: Start WebSocket listener (if enabled)
            if self.use_websocket:
                self.ws_task = asyncio.create_task(self._websocket_loop())
                logger.info("WebSocket task receiving enabled")

            # Step 4: Start polling loop (if enabled and WebSocket not available)
            if self.use_polling:
                self.polling_task = asyncio.create_task(self._polling_loop())
                logger.info("Polling task receiving enabled", interval=self.polling_interval)

            logger.info(
                "Worker Agent started",
                worker_id=str(self.worker_id),
                tools=self.task_executor.get_available_tools(),
                websocket_enabled=self.use_websocket,
                polling_enabled=self.use_polling
            )

        except Exception as e:
            logger.error("Failed to start Worker Agent", error=str(e))
            await self.stop()
            raise

    async def stop(self):
        """Stop the Worker Agent gracefully

        Graceful shutdown process:
        1. Stop accepting new tasks
        2. Wait for current task to complete (with timeout)
        3. Send final heartbeat with offline status
        4. Unregister from backend
        5. Clean up resources and connections
        """
        if not self.running:
            return

        if self.shutting_down:
            logger.warning("Shutdown already in progress")
            return

        self.shutting_down = True
        self.accepting_tasks = False
        logger.info("Initiating graceful shutdown...")

        # Step 1: Wait for current task to complete
        if self.task_executor.is_busy:
            logger.info(
                "Waiting for current task to complete",
                timeout=self.shutdown_timeout
            )
            try:
                await asyncio.wait_for(
                    self._wait_for_task_completion(),
                    timeout=self.shutdown_timeout
                )
                logger.info("Current task completed successfully")
            except asyncio.TimeoutError:
                logger.warning(
                    "Task did not complete within timeout, forcing shutdown",
                    timeout=self.shutdown_timeout
                )

        self.running = False

        # Step 2: Send final heartbeat with offline status
        if self.worker_id:
            try:
                resources = self.resource_monitor.get_resources()
                await self.connection_manager.send_final_heartbeat(
                    worker_id=self.worker_id,
                    resources=resources
                )
            except Exception as e:
                logger.error("Failed to send final heartbeat", error=str(e))

        # Step 3: Unregister from backend
        if self.worker_id:
            try:
                await self.connection_manager.unregister(self.worker_id)
            except Exception as e:
                logger.error("Failed to unregister worker", error=str(e))

        # Step 4: Cancel background tasks
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.ws_task:
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass

        if self.polling_task:
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass

        # Step 5: Close connections
        await self.connection_manager.close()

        # Signal shutdown complete
        if self._shutdown_event:
            self._shutdown_event.set()

        logger.info("Worker Agent stopped gracefully")

    async def _wait_for_task_completion(self):
        """Wait for the current task to complete"""
        while self.task_executor.is_busy:
            await asyncio.sleep(0.5)

    def setup_signal_handlers(self, loop: asyncio.AbstractEventLoop):
        """Setup signal handlers for graceful shutdown

        Args:
            loop: Event loop to use for signal handling
        """
        self._shutdown_event = asyncio.Event()

        def signal_handler(sig, frame):
            sig_name = signal.Signals(sig).name
            logger.info(f"Received {sig_name}, initiating graceful shutdown...")
            # Schedule the shutdown coroutine
            asyncio.ensure_future(self.stop())

        # Register signal handlers (Unix-style)
        # On Windows, only SIGINT (Ctrl+C) is supported
        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._handle_signal(s))
                )
        else:
            # Windows: use signal.signal for SIGINT
            signal.signal(signal.SIGINT, signal_handler)

        logger.info("Signal handlers configured for graceful shutdown")

    async def _handle_signal(self, sig: signal.Signals):
        """Handle shutdown signal asynchronously

        Args:
            sig: Signal received
        """
        sig_name = signal.Signals(sig).name
        logger.info(f"Received {sig_name}, initiating graceful shutdown...")
        await self.stop()

    async def wait_for_shutdown(self):
        """Wait for shutdown signal

        Returns when shutdown is complete
        """
        if self._shutdown_event:
            await self._shutdown_event.wait()
        else:
            # Fallback: wait indefinitely
            await asyncio.Event().wait()

    async def _heartbeat_loop(self):
        """Periodic heartbeat to backend"""
        interval = self.config.get("heartbeat_interval", 30)

        logger.info("Starting heartbeat loop", interval=interval)

        while self.running:
            try:
                # Get current resources
                resources = self.resource_monitor.get_resources()

                # Determine status
                if self.task_executor.is_busy:
                    status = "busy"
                else:
                    status = "idle"

                # Send heartbeat
                await self.connection_manager.send_heartbeat(
                    worker_id=self.worker_id,
                    resources=resources,
                    status=status
                )

                logger.debug(
                    "Heartbeat sent",
                    status=status,
                    cpu=resources["cpu_percent"],
                    memory=resources["memory_percent"]
                )

                # Check resource thresholds
                thresholds = self.config.get("resource_monitoring", {})
                threshold_status = self.resource_monitor.check_resource_thresholds(
                    cpu_threshold=thresholds.get("cpu_threshold", 90),
                    memory_threshold=thresholds.get("memory_threshold", 85),
                    disk_threshold=thresholds.get("disk_threshold", 90)
                )

                if threshold_status["any_exceeded"]:
                    logger.warning(
                        "Resource threshold exceeded",
                        cpu_exceeded=threshold_status["cpu_exceeded"],
                        memory_exceeded=threshold_status["memory_exceeded"],
                        disk_exceeded=threshold_status["disk_exceeded"]
                    )

            except Exception as e:
                logger.error("Heartbeat error", error=str(e))

            # Wait for next interval
            await asyncio.sleep(interval)

    async def _websocket_loop(self):
        """WebSocket connection loop with auto-reconnection

        The WebSocketClient handles reconnection internally with exponential backoff.
        """
        logger.info("Starting WebSocket connection loop")

        try:
            # Connect to WebSocket (runs indefinitely with auto-reconnect)
            await self.connection_manager.connect_websocket(
                worker_id=self.worker_id,
                message_handler=self._handle_websocket_message,
                on_connect=self._on_websocket_connect,
                on_disconnect=self._on_websocket_disconnect
            )
        except asyncio.CancelledError:
            logger.info("WebSocket loop cancelled")
            raise
        except Exception as e:
            logger.error("WebSocket loop error", error=str(e))

    def _on_websocket_connect(self):
        """Callback when WebSocket connection is established"""
        self.ws_connected = True
        logger.info(
            "WebSocket connected - task push enabled",
            polling_fallback=self.use_polling
        )

    def _on_websocket_disconnect(self):
        """Callback when WebSocket connection is lost"""
        self.ws_connected = False
        logger.warning(
            "WebSocket disconnected - falling back to polling",
            polling_enabled=self.use_polling,
            polling_interval=self.polling_interval
        )

    async def _polling_loop(self):
        """Polling loop for task assignments (fallback when WebSocket is disconnected)

        This loop only polls when:
        1. WebSocket is not connected (fallback mode)
        2. Worker is not busy
        3. Worker is accepting tasks
        """
        logger.info(
            "Starting polling loop (fallback mode)",
            interval=self.polling_interval
        )

        while self.running:
            try:
                # Only poll when WebSocket is disconnected
                if not self.ws_connected:
                    # Only poll if not currently busy and accepting tasks
                    if not self.task_executor.is_busy and self.accepting_tasks:
                        task_data = await self.connection_manager.poll_for_tasks(
                            worker_id=self.worker_id
                        )

                        if task_data:
                            logger.info(
                                "Task received via polling (fallback)",
                                subtask_id=task_data.get("subtask_id")
                            )
                            # Handle the task assignment
                            await self._handle_task_assignment(task_data)
                else:
                    # WebSocket is connected, skip polling
                    logger.debug("WebSocket connected, skipping poll")

            except Exception as e:
                logger.error("Polling loop error", error=str(e))

            # Wait for next polling interval
            await asyncio.sleep(self.polling_interval)

    async def _handle_websocket_message(self, message: dict):
        """Handle incoming WebSocket message

        Args:
            message: Message dictionary from backend
        """
        msg_type = message.get("type")

        logger.info("Received WebSocket message", type=msg_type)

        if msg_type == "task_assignment":
            # Check if we're accepting tasks
            if not self.accepting_tasks:
                logger.warning(
                    "Rejecting task assignment - shutdown in progress",
                    subtask_id=message.get("data", {}).get("subtask_id")
                )
                # Notify backend that task was rejected
                await self.connection_manager.send_websocket_message({
                    "type": "task_rejected",
                    "worker_id": str(self.worker_id),
                    "reason": "shutdown_in_progress",
                    "subtask_id": message.get("data", {}).get("subtask_id")
                })
                return
            # Task assigned to this worker
            await self._handle_task_assignment(message.get("data"))

        elif msg_type == "task_cancel":
            # Task cancellation request
            await self._handle_task_cancel(message.get("data"))

        elif msg_type == "ping":
            # Ping/pong for keep-alive
            await self.connection_manager.send_websocket_message({
                "type": "pong",
                "worker_id": str(self.worker_id)
            })

        else:
            logger.warning("Unknown message type", type=msg_type)

    async def _handle_task_assignment(self, task_data: dict):
        """Handle task assignment

        Args:
            task_data: Task data from backend containing:
                - subtask_id: UUID of subtask
                - description: Task description
                - assigned_tool: Tool to use for execution
                - context: Optional context data
        """
        subtask_id = task_data.get("subtask_id")

        logger.info(
            "Task assigned",
            subtask_id=subtask_id,
            tool=task_data.get("assigned_tool")
        )

        # Set up log streaming callback for this task
        async def log_stream_callback(log_line: str, log_level: str):
            """Callback to stream logs to backend"""
            await self.connection_manager.stream_execution_log(
                subtask_id=UUID(subtask_id),
                log_line=log_line,
                log_level=log_level
            )

        self.task_executor.set_log_callback(log_stream_callback)

        try:
            # Step 1: Update worker status to "busy"
            await self.connection_manager.update_worker_status(
                worker_id=self.worker_id,
                status="busy",
                current_task=UUID(subtask_id) if subtask_id else None
            )

            # Step 2: Stream initial log
            await self.connection_manager.stream_execution_log(
                subtask_id=UUID(subtask_id),
                log_line=f"Worker received task assignment: {task_data.get('description', '')[:100]}",
                log_level="info"
            )

            # Step 3: Execute task (logs will be streamed via callback)
            result = await self.task_executor.execute_task(task_data)

            # Step 4: Stream completion log
            await self.connection_manager.stream_execution_log(
                subtask_id=UUID(subtask_id),
                log_line=f"Task execution {'completed successfully' if result.get('success') else 'failed'}",
                log_level="info" if result.get("success") else "error"
            )

            # Step 5: Upload result to backend using new endpoint
            await self.connection_manager.upload_subtask_result(
                worker_id=self.worker_id,
                subtask_id=UUID(subtask_id),
                result=result
            )

            logger.info(
                "Task result uploaded",
                subtask_id=subtask_id,
                success=result.get("success")
            )

        except Exception as e:
            logger.error("Task handling error", subtask_id=subtask_id, error=str(e))

            # Stream error log
            await self.connection_manager.stream_execution_log(
                subtask_id=UUID(subtask_id),
                log_line=f"Task handling error: {str(e)}",
                log_level="error"
            )

            # Report error using new endpoint
            try:
                await self.connection_manager.upload_subtask_result(
                    worker_id=self.worker_id,
                    subtask_id=UUID(subtask_id),
                    result={
                        "success": False,
                        "output": None,
                        "error": f"Task handling error: {str(e)}",
                        "metadata": {}
                    }
                )
            except Exception as upload_error:
                logger.error(
                    "Failed to upload error result",
                    subtask_id=subtask_id,
                    error=str(upload_error)
                )

        finally:
            # Step 6: Update worker status back to "online"
            await self.connection_manager.update_worker_status(
                worker_id=self.worker_id,
                status="online",
                current_task=None
            )

            # Clear log callback
            self.task_executor.set_log_callback(None)

    async def _handle_task_cancel(self, cancel_data: dict):
        """Handle task cancellation request from backend

        This method cancels the currently executing task if it matches the
        requested subtask_id.

        Args:
            cancel_data: Cancellation data from backend containing:
                - subtask_id: UUID of the subtask to cancel
                - reason: Optional cancellation reason
        """
        subtask_id = cancel_data.get("subtask_id")
        reason = cancel_data.get("reason", "Cancelled by backend")

        logger.warning(
            "Task cancellation requested",
            subtask_id=subtask_id,
            reason=reason
        )

        # Check if the current task matches the cancellation request
        current_task_id = self.task_executor.current_task
        if current_task_id and str(current_task_id) == str(subtask_id):
            # Cancel the current task
            cancelled = await self.task_executor.cancel_current_task()

            if cancelled:
                logger.info(
                    "Task cancelled successfully",
                    subtask_id=subtask_id,
                    reason=reason
                )

                # Report cancellation to backend
                try:
                    await self.connection_manager.report_task_result(
                        worker_id=self.worker_id,
                        subtask_id=subtask_id,
                        result={
                            "success": False,
                            "output": None,
                            "error": f"Task cancelled: {reason}",
                            "metadata": {"cancelled": True, "reason": reason}
                        }
                    )
                except Exception as e:
                    logger.error(
                        "Failed to report task cancellation",
                        subtask_id=subtask_id,
                        error=str(e)
                    )
            else:
                logger.warning(
                    "Task cancellation failed",
                    subtask_id=subtask_id
                )
        else:
            logger.debug(
                "Cancellation request does not match current task",
                requested_subtask_id=subtask_id,
                current_task_id=str(current_task_id) if current_task_id else None
            )

    def get_status(self) -> dict:
        """Get Worker Agent status

        Returns:
            Status dictionary
        """
        status = {
            "running": self.running,
            "worker_id": str(self.worker_id) if self.worker_id else None,
            "machine_id": self.machine_id,
            "machine_name": self.config["machine_name"],
            "connected": self.connection_manager.connected,
            "websocket_connected": self.ws_connected,
            "websocket_enabled": self.use_websocket,
            "polling_enabled": self.use_polling,
            "polling_interval": self.polling_interval,
            "executor_status": self.task_executor.get_status(),
            "resources": self.resource_monitor.get_resources()
        }

        # Add WebSocket client status if available
        if self.connection_manager.ws_client:
            status["websocket_client"] = self.connection_manager.ws_client.get_status()

        return status
