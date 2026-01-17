"""Authentication module for multi-tool support"""

from .base import BaseAuth, AuthStatus
from .claude_auth import ClaudeAuth
from .gemini_auth import GeminiAuth
from .aider_auth import AiderAuth

__all__ = [
    "BaseAuth",
    "AuthStatus",
    "ClaudeAuth",
    "GeminiAuth",
    "AiderAuth",
]
