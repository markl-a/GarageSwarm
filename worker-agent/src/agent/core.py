"""Worker Agent core implementation"""

import asyncio
import signal
import sys
from typing import Dict, Optional
from uuid import UUID
import structlog

from .connection import ConnectionManager
from .executor import TaskExecutor
from .monitor import ResourceMonitor
from tools.base import BaseTool
from config import load_or_create_machine_id

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
        self._shutdown_event: Optional[asyncio.Event] = None

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

            # Step 3: Start WebSocket listener
            self.ws_task = asyncio.create_task(self._websocket_loop())

            logger.info(
                "Worker Agent started",
                worker_id=str(self.worker_id),
                tools=self.task_executor.get_available_tools()
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
        """WebSocket connection loop with reconnection"""
        while self.running:
            try:
                logger.info("Establishing WebSocket connection...")
                await self.connection_manager.connect_websocket(
                    worker_id=self.worker_id,
                    message_handler=self._handle_websocket_message
                )
            except Exception as e:
                logger.error("WebSocket error", error=str(e))

            if self.running:
                # Reconnect after 5 seconds
                logger.info("Reconnecting WebSocket in 5 seconds...")
                await asyncio.sleep(5)

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
            task_data: Task data from backend
        """
        subtask_id = task_data.get("subtask_id")

        logger.info("Task assigned", subtask_id=subtask_id)

        try:
            # Execute task
            result = await self.task_executor.execute_task(task_data)

            # Report result to backend
            await self.connection_manager.report_task_result(
                worker_id=self.worker_id,
                subtask_id=UUID(subtask_id),
                result=result
            )

            logger.info(
                "Task result reported",
                subtask_id=subtask_id,
                success=result.get("success")
            )

        except Exception as e:
            logger.error("Task handling error", subtask_id=subtask_id, error=str(e))

            # Report error
            await self.connection_manager.report_task_result(
                worker_id=self.worker_id,
                subtask_id=UUID(subtask_id),
                result={
                    "success": False,
                    "output": None,
                    "error": f"Task handling error: {str(e)}",
                    "metadata": {}
                }
            )

    async def _handle_task_cancel(self, cancel_data: dict):
        """Handle task cancellation request

        Args:
            cancel_data: Cancellation data from backend
        """
        subtask_id = cancel_data.get("subtask_id")
        logger.warning("Task cancellation requested", subtask_id=subtask_id)

        # TODO: Implement task cancellation logic
        # For now, just log it

    def get_status(self) -> dict:
        """Get Worker Agent status

        Returns:
            Status dictionary
        """
        return {
            "running": self.running,
            "worker_id": str(self.worker_id) if self.worker_id else None,
            "machine_id": self.machine_id,
            "machine_name": self.config["machine_name"],
            "connected": self.connection_manager.connected,
            "executor_status": self.task_executor.get_status(),
            "resources": self.resource_monitor.get_resources()
        }
