"""Task execution management"""

import asyncio
import time
from typing import Any, Callable, Dict, Optional
from uuid import UUID

import structlog

from tools.base import BaseTool
from .result_reporter import ResultReporter

logger = structlog.get_logger()


class TaskExecutor:
    """Execute tasks using registered AI tools

    The TaskExecutor handles task execution with optional automatic result
    reporting via the ResultReporter integration.

    Attributes:
        tools: Dictionary of registered AI tools
        current_task: UUID of currently executing task
        is_busy: Whether executor is currently executing a task
        is_cancelled: Whether current task has been cancelled
        result_reporter: Optional ResultReporter for automatic result submission
        worker_id: Worker ID for result reporting (required if result_reporter is set)
    """

    def __init__(
        self,
        result_reporter: Optional[ResultReporter] = None,
        worker_id: Optional[str] = None
    ):
        """Initialize task executor

        Args:
            result_reporter: Optional ResultReporter instance for automatic
                result submission to backend
            worker_id: Worker ID (required if result_reporter is provided)
        """
        self.tools: Dict[str, BaseTool] = {}
        self.current_task: Optional[UUID] = None
        self.is_busy = False
        self.is_cancelled = False
        self._cancel_event = asyncio.Event()
        self._execution_task: Optional[asyncio.Task] = None
        self.log_callback: Optional[Callable[[str, str], None]] = None

        # Result reporting integration
        self.result_reporter: Optional[ResultReporter] = result_reporter
        self.worker_id: Optional[str] = worker_id

        if result_reporter and not worker_id:
            logger.warning(
                "ResultReporter provided without worker_id - automatic result reporting disabled"
            )

    def register_tool(self, name: str, tool: BaseTool):
        """Register an AI tool

        Args:
            name: Tool name (e.g., "claude_code", "gemini_cli", "ollama")
            tool: BaseTool implementation instance
        """
        self.tools[name] = tool
        logger.info("Tool registered", tool=name)

    def unregister_tool(self, name: str):
        """Unregister an AI tool

        Args:
            name: Tool name to unregister
        """
        if name in self.tools:
            del self.tools[name]
            logger.info("Tool unregistered", tool=name)

    def get_available_tools(self) -> list[str]:
        """Get list of registered tool names

        Returns:
            List of tool names
        """
        return list(self.tools.keys())

    def has_tool(self, tool_name: str) -> bool:
        """Check if tool is registered

        Args:
            tool_name: Name of tool to check

        Returns:
            True if tool is registered, False otherwise
        """
        return tool_name in self.tools

    def set_log_callback(self, callback: Callable[[str, str], None]):
        """Set callback function for streaming execution logs

        Args:
            callback: Async function that takes (log_line, log_level) as parameters
        """
        self.log_callback = callback

    def set_result_reporter(
        self,
        result_reporter: ResultReporter,
        worker_id: str
    ):
        """Set or update the result reporter for automatic result submission

        Args:
            result_reporter: ResultReporter instance
            worker_id: Worker ID for result reporting
        """
        self.result_reporter = result_reporter
        self.worker_id = worker_id
        logger.info("ResultReporter configured for TaskExecutor", worker_id=worker_id)

    def clear_result_reporter(self):
        """Clear the result reporter (disable automatic result submission)"""
        self.result_reporter = None
        self.worker_id = None
        logger.info("ResultReporter cleared from TaskExecutor")

    async def _report_result(
        self,
        subtask_id: str,
        result: dict,
        execution_time_ms: int = 0
    ) -> bool:
        """Internal method to report result via ResultReporter if configured

        Args:
            subtask_id: Task/subtask ID
            result: Execution result dictionary
            execution_time_ms: Execution time in milliseconds

        Returns:
            True if reported successfully or reporter not configured, False on error
        """
        if not self.result_reporter or not self.worker_id:
            return True  # No reporter configured, consider it success

        try:
            status = "completed" if result.get("success") else "failed"
            await self.result_reporter.report_result(
                worker_id=self.worker_id,
                task_id=subtask_id,
                status=status,
                result=result,
                error=result.get("error"),
                execution_time_ms=execution_time_ms,
                metadata=result.get("metadata")
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to report result via ResultReporter",
                subtask_id=subtask_id,
                error=str(e)
            )
            return False

    async def _log(self, message: str, level: str = "info"):
        """Internal logging method that streams to backend if callback is set

        Args:
            message: Log message
            level: Log level (debug, info, warning, error)
        """
        # Always log locally
        if level == "debug":
            logger.debug(message)
        elif level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)

        # Stream to backend if callback is set
        if self.log_callback:
            try:
                if asyncio.iscoroutinefunction(self.log_callback):
                    await self.log_callback(message, level)
                else:
                    self.log_callback(message, level)
            except Exception as e:
                logger.debug(f"Failed to stream log: {e}")

    async def execute_task(self, subtask: dict) -> dict:
        """Execute a subtask using the assigned tool

        Args:
            subtask: Subtask dictionary containing:
                - subtask_id: UUID of subtask
                - description: Task description
                - assigned_tool: Name of tool to use
                - context: Optional context data

        Returns:
            Result dictionary containing:
                - success: bool
                - output: Any - Task output
                - error: Optional[str] - Error message if failed
                - metadata: dict - Execution metadata
        """
        subtask_id = subtask.get("subtask_id")
        tool_name = subtask.get("assigned_tool")
        description = subtask.get("description")
        context = subtask.get("context", {})

        # Reset cancellation state for new task
        self.reset_cancellation()

        await self._log(
            f"Executing task {subtask_id} with tool {tool_name}",
            level="info"
        )

        # Validation
        if not tool_name:
            error_msg = "No tool assigned to subtask"
            await self._log(error_msg, level="error")
            return {
                "success": False,
                "output": None,
                "error": error_msg,
                "metadata": {}
            }

        if tool_name not in self.tools:
            error_msg = f"Tool '{tool_name}' not available. Available tools: {list(self.tools.keys())}"
            await self._log(error_msg, level="error")
            return {
                "success": False,
                "output": None,
                "error": error_msg,
                "metadata": {}
            }

        # Mark as busy
        self.is_busy = True
        self.current_task = subtask_id

        try:
            # Check for cancellation before starting
            if self.is_cancelled:
                return {
                    "success": False,
                    "output": None,
                    "error": "Task was cancelled before execution",
                    "metadata": {"cancelled": True}
                }

            # Get tool and execute
            tool = self.tools[tool_name]

            await self._log(
                f"Starting execution with {tool_name}",
                level="info"
            )

            # Execute task
            result = await tool.execute(
                instructions=description,
                context=context
            )

            # Check for cancellation after execution
            if self.is_cancelled:
                return {
                    "success": False,
                    "output": result.get("output"),
                    "error": "Task was cancelled during execution",
                    "metadata": {"cancelled": True, "partial_result": True}
                }

            await self._log(
                f"Task execution {'completed successfully' if result.get('success') else 'failed'}",
                level="info" if result.get("success") else "warning"
            )

            return result

        except asyncio.CancelledError:
            await self._log("Task execution was cancelled", level="warning")
            return {
                "success": False,
                "output": None,
                "error": "Task execution was cancelled",
                "metadata": {"cancelled": True}
            }

        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            await self._log(error_msg, level="error")

            return {
                "success": False,
                "output": None,
                "error": error_msg,
                "metadata": {"exception_type": type(e).__name__}
            }

        finally:
            # Mark as not busy
            self.is_busy = False
            self.current_task = None
            self._execution_task = None

    async def execute_task_with_timeout(
        self,
        subtask: dict,
        timeout: int = 3600
    ) -> dict:
        """Execute task with timeout

        Args:
            subtask: Subtask dictionary
            timeout: Timeout in seconds (default 3600 = 1 hour)

        Returns:
            Result dictionary
        """
        try:
            return await asyncio.wait_for(
                self.execute_task(subtask),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(
                "Task execution timeout",
                subtask_id=str(subtask.get("subtask_id")),
                timeout=timeout
            )

            return {
                "success": False,
                "output": None,
                "error": f"Task execution timeout after {timeout} seconds",
                "metadata": {"timeout": timeout}
            }

    async def execute_task_and_report(
        self,
        subtask: dict,
        timeout: int = 3600,
        auto_report: bool = True
    ) -> dict:
        """Execute task and automatically report result to backend

        This is a convenience method that combines task execution with
        automatic result reporting via the configured ResultReporter.

        Args:
            subtask: Subtask dictionary containing:
                - subtask_id: UUID of subtask
                - description: Task description
                - assigned_tool: Name of tool to use
                - context: Optional context data
            timeout: Timeout in seconds (default 3600 = 1 hour)
            auto_report: Whether to automatically report result (default True)

        Returns:
            Result dictionary containing:
                - success: bool
                - output: Any - Task output
                - error: Optional[str] - Error message if failed
                - metadata: dict - Execution metadata
                - reported: bool - Whether result was reported to backend
                - execution_time_ms: int - Execution time in milliseconds
        """
        subtask_id = subtask.get("subtask_id")
        start_time = time.time()

        try:
            # Execute task with timeout
            result = await self.execute_task_with_timeout(subtask, timeout)

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            result["execution_time_ms"] = execution_time_ms

            # Report result if auto_report is enabled
            reported = False
            if auto_report and subtask_id:
                reported = await self._report_result(
                    subtask_id=str(subtask_id),
                    result=result,
                    execution_time_ms=execution_time_ms
                )

            result["reported"] = reported

            logger.info(
                "Task execution and reporting complete",
                subtask_id=str(subtask_id) if subtask_id else None,
                success=result.get("success"),
                reported=reported,
                execution_time_ms=execution_time_ms
            )

            return result

        except Exception as e:
            # Calculate execution time even on failure
            execution_time_ms = int((time.time() - start_time) * 1000)

            error_result = {
                "success": False,
                "output": None,
                "error": f"Execution error: {str(e)}",
                "metadata": {"exception_type": type(e).__name__},
                "execution_time_ms": execution_time_ms,
                "reported": False
            }

            # Try to report the error
            if auto_report and subtask_id:
                error_result["reported"] = await self._report_result(
                    subtask_id=str(subtask_id),
                    result=error_result,
                    execution_time_ms=execution_time_ms
                )

            logger.error(
                "Task execution failed",
                subtask_id=str(subtask_id) if subtask_id else None,
                error=str(e),
                execution_time_ms=execution_time_ms
            )

            return error_result

    def get_status(self) -> dict:
        """Get executor status

        Returns:
            Status dictionary with current task and busy state
        """
        return {
            "is_busy": self.is_busy,
            "current_task": str(self.current_task) if self.current_task else None,
            "available_tools": list(self.tools.keys()),
            "tool_count": len(self.tools),
            "is_cancelled": self.is_cancelled,
            "result_reporter_configured": self.result_reporter is not None,
            "worker_id": self.worker_id
        }

    async def cancel_current_task(self) -> bool:
        """Cancel the currently executing task

        Returns:
            True if a task was cancelled, False if no task was running
        """
        if not self.is_busy or not self.current_task:
            logger.info("No task to cancel")
            return False

        task_id = self.current_task
        logger.info("Cancelling task", task_id=str(task_id))

        # Set cancellation flag
        self.is_cancelled = True
        self._cancel_event.set()

        # Cancel the execution task if it exists
        if self._execution_task and not self._execution_task.done():
            self._execution_task.cancel()
            try:
                await self._execution_task
            except asyncio.CancelledError:
                logger.info("Task execution cancelled", task_id=str(task_id))

        # Cancel any tool-level execution
        for tool_name, tool in self.tools.items():
            if hasattr(tool, 'cancel'):
                try:
                    await tool.cancel()
                    logger.debug("Tool cancelled", tool=tool_name)
                except Exception as e:
                    logger.warning("Failed to cancel tool", tool=tool_name, error=str(e))

        # Reset state
        self.is_busy = False
        self.current_task = None
        self._execution_task = None
        self._cancel_event.clear()

        await self._log(f"Task {task_id} cancelled successfully", level="info")
        return True

    def reset_cancellation(self):
        """Reset cancellation state for new task"""
        self.is_cancelled = False
        self._cancel_event.clear()
