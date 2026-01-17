"""Aider authentication handler"""

import os
from typing import Any, Dict, List, Optional
import structlog

from .base import BaseAuth, AuthResult, AuthStatus

logger = structlog.get_logger()


class AiderAuth(BaseAuth):
    """Aider authentication handler

    Aider supports multiple LLM providers:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - Azure OpenAI
    - Ollama (local)
    - Many others via litellm

    Each provider has its own authentication method.
    """

    # API key environment variables by provider
    PROVIDER_AUTH = {
        "openai": {
            "env_vars": ["OPENAI_API_KEY"],
            "config_key": "openai_api_key",
        },
        "anthropic": {
            "env_vars": ["ANTHROPIC_API_KEY"],
            "config_key": "anthropic_api_key",
        },
        "azure": {
            "env_vars": ["AZURE_API_KEY", "AZURE_OPENAI_API_KEY"],
            "config_key": "azure_api_key",
        },
        "google": {
            "env_vars": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
            "config_key": "google_api_key",
        },
        "ollama": {
            "env_vars": [],  # No API key needed for local Ollama
            "config_key": None,
            "base_url_env": "OLLAMA_API_BASE",
            "default_url": "http://localhost:11434",
        },
    }

    # Aider config file paths
    CONFIG_PATHS = [
        "~/.aider/.env",
        "~/.aider/config.yml",
        ".aider.conf.yml",
        ".env",
    ]

    def __init__(self):
        super().__init__("aider")

    def check_auth(self) -> AuthResult:
        """Check Aider authentication status

        Aider can work with any authenticated LLM provider.
        Returns success if at least one provider is configured.

        Returns:
            AuthResult with status and details
        """
        details = {
            "providers": {}
        }
        authenticated_providers = []

        # Check each provider
        for provider, auth_info in self.PROVIDER_AUTH.items():
            provider_auth = self._check_provider(provider, auth_info)

            if provider_auth["authenticated"]:
                authenticated_providers.append(provider)
                details["providers"][provider] = {
                    "status": "authenticated",
                    "method": provider_auth["method"]
                }
            else:
                details["providers"][provider] = {
                    "status": "not_configured"
                }

        # Check for aider config files
        config_found = None
        for config_path in self.CONFIG_PATHS:
            expanded_path = os.path.expanduser(config_path)
            if os.path.exists(expanded_path):
                config_found = expanded_path
                details["config_file"] = expanded_path
                break

        # Determine overall status
        if authenticated_providers:
            details["authenticated_providers"] = authenticated_providers
            details["primary_provider"] = authenticated_providers[0]

            return AuthResult(
                status=AuthStatus.AUTHENTICATED,
                message=f"Authenticated with: {', '.join(authenticated_providers)}",
                details=details
            )

        # No providers authenticated
        return AuthResult(
            status=AuthStatus.NOT_CONFIGURED,
            message="No LLM provider authenticated for Aider",
            details=details
        )

    def _check_provider(self, provider: str, auth_info: Dict) -> Dict[str, Any]:
        """Check authentication for a specific provider

        Args:
            provider: Provider name
            auth_info: Provider authentication info

        Returns:
            Dict with authenticated status and method
        """
        # Special case for Ollama (no API key needed)
        if provider == "ollama":
            base_url = self.get_env_var(auth_info.get("base_url_env", "")) or auth_info.get("default_url")
            if base_url:
                # Could add actual connectivity check here
                return {
                    "authenticated": True,
                    "method": "local",
                    "base_url": base_url
                }
            return {"authenticated": False}

        # Check environment variables
        for env_var in auth_info.get("env_vars", []):
            api_key = self.get_env_var(env_var)
            if api_key:
                return {
                    "authenticated": True,
                    "method": "api_key",
                    "env_var": env_var
                }

        return {"authenticated": False}

    def get_auth_methods(self) -> List[str]:
        """Get supported authentication methods"""
        return ["api_key", "config_file", "local_ollama"]

    def get_providers(self) -> List[str]:
        """Get list of supported LLM providers"""
        return list(self.PROVIDER_AUTH.keys())

    def get_setup_instructions(self) -> str:
        """Get setup instructions for Aider"""
        return """
Aider Authentication Setup
==========================

Aider works with multiple LLM providers. Configure at least one:

Option 1: OpenAI (GPT-4)
------------------------
Set the OPENAI_API_KEY environment variable:

  export OPENAI_API_KEY=sk-your-openai-key

Option 2: Anthropic (Claude)
----------------------------
Set the ANTHROPIC_API_KEY environment variable:

  export ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

Option 3: Ollama (Local)
------------------------
Install and run Ollama locally:

  ollama serve
  ollama pull codellama

Then run aider with:

  aider --model ollama/codellama

Option 4: Config File
---------------------
Create ~/.aider/.env with:

  OPENAI_API_KEY=sk-xxx
  ANTHROPIC_API_KEY=sk-ant-xxx

Or create ~/.aider/config.yml:

  model: gpt-4
  openai-api-key: sk-xxx

For Docker
----------
Pass API keys:

  docker run -e OPENAI_API_KEY=xxx worker
  docker run -e ANTHROPIC_API_KEY=xxx worker

Or mount config:

  docker run -v ~/.aider:/root/.aider worker
"""

    def get_recommended_model(self) -> Optional[str]:
        """Get recommended model based on available providers

        Returns:
            Model name or None if no providers configured
        """
        result = self.check_auth()

        if result.status != AuthStatus.AUTHENTICATED:
            return None

        providers = result.details.get("authenticated_providers", [])

        # Preference order
        if "anthropic" in providers:
            return "claude-3-5-sonnet-20241022"
        if "openai" in providers:
            return "gpt-4"
        if "ollama" in providers:
            return "ollama/codellama"
        if "google" in providers:
            return "gemini-pro"

        return None
