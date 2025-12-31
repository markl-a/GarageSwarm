"""Task execution management"""

import asyncio
from typing import Any, Callable, Dict, Optional
from uuid import UUID

import structlog

from tools.base import BaseTool

logger = structlog.get_logger()


class TaskExecutor:
    """Execute tasks using registered AI tools"""

    def __init__(self):
        """Initialize task executor"""
        self.tools: Dict[str, BaseTool] = {}
        self.current_task: Optional[UUID] = None
        self.is_busy = False
        self.is_cancelled = False
        self._cancel_event = asyncio.Event()
        self._execution_task: Optional[asyncio.Task] = None
        self.log_callback: Optional[Callable[[str, str], None]] = None

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
            "is_cancelled": self.is_cancelled
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
