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
