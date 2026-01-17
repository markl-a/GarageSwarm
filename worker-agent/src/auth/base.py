"""Base authentication interface for AI tools"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()


class AuthStatus(Enum):
    """Authentication status"""
    AUTHENTICATED = "authenticated"
    NOT_CONFIGURED = "not_configured"
    INVALID = "invalid"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class AuthResult:
    """Authentication check result"""
    status: AuthStatus
    message: str
    details: Optional[Dict[str, Any]] = None


class BaseAuth(ABC):
    """Base authentication class for AI tools

    Each tool has different authentication methods:
    - API keys (environment variables)
    - OAuth tokens (config files)
    - Session cookies (browser-based)

    This class provides a unified interface for checking and managing
    authentication across different tools.
    """

    def __init__(self, tool_name: str):
        """Initialize authentication handler

        Args:
            tool_name: Name of the tool (e.g., "claude_code", "gemini_cli")
        """
        self.tool_name = tool_name

    @abstractmethod
    def check_auth(self) -> AuthResult:
        """Check if authentication is configured and valid

        Returns:
            AuthResult with status and details
        """
        pass

    @abstractmethod
    def get_auth_methods(self) -> List[str]:
        """Get list of supported authentication methods

        Returns:
            List of method names (e.g., ["api_key", "oauth", "config_file"])
        """
        pass

    @abstractmethod
    def get_setup_instructions(self) -> str:
        """Get human-readable setup instructions

        Returns:
            Instructions for setting up authentication
        """
        pass

    def get_env_var(self, var_name: str) -> Optional[str]:
        """Get environment variable value

        Args:
            var_name: Name of environment variable

        Returns:
            Value or None if not set
        """
        return os.environ.get(var_name)

    def check_file_exists(self, file_path: str) -> bool:
        """Check if a file exists

        Args:
            file_path: Path to file

        Returns:
            True if file exists
        """
        expanded_path = os.path.expanduser(file_path)
        return os.path.exists(expanded_path)

    def is_authenticated(self) -> bool:
        """Quick check if tool is authenticated

        Returns:
            True if authenticated, False otherwise
        """
        result = self.check_auth()
        return result.status == AuthStatus.AUTHENTICATED

    def get_auth_info(self) -> Dict[str, Any]:
        """Get authentication information summary

        Returns:
            Dictionary with auth info
        """
        result = self.check_auth()
        return {
            "tool": self.tool_name,
            "status": result.status.value,
            "message": result.message,
            "methods": self.get_auth_methods(),
            "details": result.details or {}
        }
