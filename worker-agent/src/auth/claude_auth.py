"""Claude Code authentication handler"""

import json
import os
from typing import Any, Dict, List, Optional
import structlog

from .base import BaseAuth, AuthResult, AuthStatus

logger = structlog.get_logger()


class ClaudeAuth(BaseAuth):
    """Claude Code CLI authentication handler

    Supports multiple authentication methods:
    1. ANTHROPIC_API_KEY environment variable
    2. Claude CLI config file (~/.claude/config.json)
    3. OAuth session (managed by Claude CLI)
    """

    # Environment variable for API key
    API_KEY_ENV = "ANTHROPIC_API_KEY"

    # Config file paths (in order of preference)
    CONFIG_PATHS = [
        "~/.claude/config.json",
        "~/.claude.json",
    ]

    # OAuth session file
    SESSION_PATH = "~/.claude/session.json"

    def __init__(self):
        super().__init__("claude_code")

    def check_auth(self) -> AuthResult:
        """Check Claude Code authentication status

        Checks in order:
        1. API key environment variable
        2. Config file
        3. OAuth session

        Returns:
            AuthResult with status and details
        """
        details = {}

        # Method 1: Check API key
        api_key = self.get_env_var(self.API_KEY_ENV)
        if api_key:
            # Validate API key format (starts with sk-ant-)
            if api_key.startswith("sk-ant-"):
                details["method"] = "api_key"
                details["api_key_prefix"] = api_key[:12] + "..."
                return AuthResult(
                    status=AuthStatus.AUTHENTICATED,
                    message="Authenticated via API key",
                    details=details
                )
            else:
                logger.warning("Invalid Anthropic API key format")
                details["method"] = "api_key"
                details["error"] = "Invalid API key format (should start with 'sk-ant-')"
                return AuthResult(
                    status=AuthStatus.INVALID,
                    message="API key has invalid format",
                    details=details
                )

        # Method 2: Check config file
        for config_path in self.CONFIG_PATHS:
            expanded_path = os.path.expanduser(config_path)
            if os.path.exists(expanded_path):
                try:
                    with open(expanded_path, "r") as f:
                        config = json.load(f)

                    # Check for API key in config
                    if config.get("api_key") or config.get("anthropic_api_key"):
                        details["method"] = "config_file"
                        details["config_path"] = expanded_path
                        return AuthResult(
                            status=AuthStatus.AUTHENTICATED,
                            message=f"Authenticated via config file: {config_path}",
                            details=details
                        )

                    # Check for OAuth tokens
                    if config.get("access_token") or config.get("refresh_token"):
                        details["method"] = "oauth"
                        details["config_path"] = expanded_path
                        return AuthResult(
                            status=AuthStatus.AUTHENTICATED,
                            message="Authenticated via OAuth",
                            details=details
                        )

                except json.JSONDecodeError:
                    logger.warning(
                        "Invalid JSON in config file",
                        path=expanded_path
                    )
                except Exception as e:
                    logger.warning(
                        "Error reading config file",
                        path=expanded_path,
                        error=str(e)
                    )

        # Method 3: Check session file (OAuth)
        session_path = os.path.expanduser(self.SESSION_PATH)
        if os.path.exists(session_path):
            try:
                with open(session_path, "r") as f:
                    session = json.load(f)

                if session.get("access_token"):
                    details["method"] = "oauth_session"
                    details["session_path"] = session_path

                    # Check if session has expiry
                    if "expires_at" in session:
                        import time
                        if session["expires_at"] < time.time():
                            return AuthResult(
                                status=AuthStatus.EXPIRED,
                                message="OAuth session has expired",
                                details=details
                            )

                    return AuthResult(
                        status=AuthStatus.AUTHENTICATED,
                        message="Authenticated via OAuth session",
                        details=details
                    )

            except Exception as e:
                logger.warning(
                    "Error reading session file",
                    path=session_path,
                    error=str(e)
                )

        # No authentication found
        return AuthResult(
            status=AuthStatus.NOT_CONFIGURED,
            message="No Claude authentication found",
            details={
                "checked": {
                    "api_key_env": self.API_KEY_ENV,
                    "config_files": self.CONFIG_PATHS,
                    "session_file": self.SESSION_PATH
                }
            }
        )

    def get_auth_methods(self) -> List[str]:
        """Get supported authentication methods"""
        return ["api_key", "config_file", "oauth"]

    def get_setup_instructions(self) -> str:
        """Get setup instructions for Claude Code"""
        return """
Claude Code Authentication Setup
================================

Option 1: API Key (Recommended for automation)
----------------------------------------------
Set the ANTHROPIC_API_KEY environment variable:

  export ANTHROPIC_API_KEY=sk-ant-your-api-key

Option 2: Claude CLI Login (Interactive)
----------------------------------------
Run the Claude CLI login command:

  claude login

This will open a browser for OAuth authentication.

Option 3: Config File
---------------------
Create ~/.claude/config.json with:

  {
    "api_key": "sk-ant-your-api-key"
  }

For Docker
----------
1. Mount your local config:
   docker run -v ~/.claude:/root/.claude worker

2. Or pass API key:
   docker run -e ANTHROPIC_API_KEY=sk-ant-xxx worker
"""
