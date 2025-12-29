"""Task execution management"""

import asyncio
from typing import Any, Dict, Optional
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

        logger.info(
            "Executing task",
            subtask_id=str(subtask_id),
            tool=tool_name
        )

        # Validation
        if not tool_name:
            return {
                "success": False,
                "output": None,
                "error": "No tool assigned to subtask",
                "metadata": {}
            }

        if tool_name not in self.tools:
            return {
                "success": False,
                "output": None,
                "error": f"Tool '{tool_name}' not available. Available tools: {list(self.tools.keys())}",
                "metadata": {}
            }

        # Mark as busy
        self.is_busy = True
        self.current_task = subtask_id

        try:
            # Get tool and execute
            tool = self.tools[tool_name]

            # Execute task
            result = await tool.execute(
                instructions=description,
                context=context
            )

            logger.info(
                "Task execution completed",
                subtask_id=str(subtask_id),
                success=result.get("success")
            )

            return result

        except Exception as e:
            logger.error(
                "Task execution failed",
                subtask_id=str(subtask_id),
                error=str(e)
            )

            return {
                "success": False,
                "output": None,
                "error": f"Execution error: {str(e)}",
                "metadata": {"exception_type": type(e).__name__}
            }

        finally:
            # Mark as not busy
            self.is_busy = False
            self.current_task = None

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
            "tool_count": len(self.tools)
        }
