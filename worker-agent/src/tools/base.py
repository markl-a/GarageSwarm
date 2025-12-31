"""Base tool interface for AI tool integration"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseTool(ABC):
    """Abstract base class for AI tools

    All AI tools (Claude Code, Gemini CLI, Ollama) must implement this interface.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize tool with configuration

        Args:
            config: Tool-specific configuration dictionary
        """
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    async def execute(
        self,
        instructions: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute task with the AI tool

        Args:
            instructions: Task instructions/prompt for the AI tool
            context: Optional context data (code, files, parameters, etc.)

        Returns:
            Dictionary containing:
                - success: bool - Whether execution succeeded
                - output: Any - Tool output (text, code, etc.)
                - error: Optional[str] - Error message if failed
                - metadata: Dict - Additional metadata (tokens used, duration, etc.)
        """
        pass

    @abstractmethod
    async def validate_config(self) -> bool:
        """Validate tool configuration

        Returns:
            True if configuration is valid, False otherwise
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if tool is available and responsive

        Returns:
            True if tool is healthy, False otherwise
        """
        pass

    async def detailed_health_check(self) -> Dict[str, Any]:
        """Perform detailed health check with structured status

        Returns:
            Dictionary containing:
                - status: str - Health status (healthy/degraded/unhealthy)
                - available: bool - Whether tool is available
                - latency: Optional[float] - Response time in milliseconds
                - version: Optional[str] - Tool version if available
                - error: Optional[str] - Error message if unhealthy
                - metadata: Dict - Additional metadata

        Default implementation uses the basic health_check method.
        Tools can override this for more detailed checks.
        """
        import time
        start_time = time.time()

        try:
            is_healthy = await self.health_check()
            latency = (time.time() - start_time) * 1000

            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "available": is_healthy,
                "latency": round(latency, 2),
                "version": None,
                "error": None if is_healthy else "Health check failed",
                "metadata": {
                    "tool_name": self.name
                }
            }
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "available": False,
                "latency": round(latency, 2),
                "version": None,
                "error": f"Health check error: {str(e)}",
                "metadata": {
                    "tool_name": self.name,
                    "error_type": type(e).__name__
                }
            }

    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information

        Returns:
            Dictionary with tool name, version, capabilities, etc.
        """
        return {
            "name": self.name,
            "type": "ai_tool",
            "capabilities": []
        }

    async def cancel(self) -> bool:
        """Cancel any ongoing execution

        Override this method to implement tool-specific cancellation logic.
        For example, terminate subprocess, abort API call, etc.

        Returns:
            True if cancellation was successful, False otherwise
        """
        # Default implementation - no-op
        # Tools should override this for proper cancellation support
        return True
