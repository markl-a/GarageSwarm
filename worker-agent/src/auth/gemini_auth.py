"""Gemini CLI authentication handler"""

import json
import os
from typing import Any, Dict, List, Optional
import structlog

from .base import BaseAuth, AuthResult, AuthStatus

logger = structlog.get_logger()


class GeminiAuth(BaseAuth):
    """Gemini CLI (google-generativeai) authentication handler

    Supports multiple authentication methods:
    1. GOOGLE_API_KEY environment variable
    2. GEMINI_API_KEY environment variable
    3. Google Application Default Credentials
    4. gcloud CLI credentials
    """

    # Environment variables for API key (in order of preference)
    API_KEY_ENVS = [
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_GENERATIVE_AI_KEY",
    ]

    # Application Default Credentials path
    ADC_PATH = "~/.config/gcloud/application_default_credentials.json"

    # gcloud config path
    GCLOUD_CONFIG_PATH = "~/.config/gcloud/configurations/config_default"

    def __init__(self):
        super().__init__("gemini_cli")

    def check_auth(self) -> AuthResult:
        """Check Gemini authentication status

        Checks in order:
        1. API key environment variables
        2. Application Default Credentials
        3. gcloud CLI credentials

        Returns:
            AuthResult with status and details
        """
        details = {}

        # Method 1: Check API key environment variables
        for env_var in self.API_KEY_ENVS:
            api_key = self.get_env_var(env_var)
            if api_key:
                # Validate API key format (typically starts with AI)
                details["method"] = "api_key"
                details["env_var"] = env_var
                details["api_key_prefix"] = api_key[:8] + "..." if len(api_key) > 8 else "***"

                return AuthResult(
                    status=AuthStatus.AUTHENTICATED,
                    message=f"Authenticated via {env_var}",
                    details=details
                )

        # Method 2: Check Application Default Credentials
        adc_path = os.path.expanduser(self.ADC_PATH)
        if os.path.exists(adc_path):
            try:
                with open(adc_path, "r") as f:
                    adc = json.load(f)

                # Check for various credential types
                if adc.get("client_id") or adc.get("refresh_token") or adc.get("service_account"):
                    details["method"] = "application_default_credentials"
                    details["adc_path"] = adc_path
                    details["credential_type"] = (
                        "service_account" if adc.get("type") == "service_account"
                        else "user_credentials"
                    )

                    return AuthResult(
                        status=AuthStatus.AUTHENTICATED,
                        message="Authenticated via Application Default Credentials",
                        details=details
                    )

            except json.JSONDecodeError:
                logger.warning("Invalid JSON in ADC file", path=adc_path)
            except Exception as e:
                logger.warning("Error reading ADC file", path=adc_path, error=str(e))

        # Method 3: Check gcloud CLI config
        gcloud_config_path = os.path.expanduser(self.GCLOUD_CONFIG_PATH)
        if os.path.exists(gcloud_config_path):
            try:
                # Check if gcloud is configured with an account
                import configparser
                config = configparser.ConfigParser()
                config.read(gcloud_config_path)

                if config.has_option("core", "account"):
                    account = config.get("core", "account")
                    details["method"] = "gcloud_cli"
                    details["account"] = account

                    return AuthResult(
                        status=AuthStatus.AUTHENTICATED,
                        message=f"Authenticated via gcloud CLI ({account})",
                        details=details
                    )

            except Exception as e:
                logger.warning(
                    "Error reading gcloud config",
                    path=gcloud_config_path,
                    error=str(e)
                )

        # Check GOOGLE_APPLICATION_CREDENTIALS env var
        google_app_creds = self.get_env_var("GOOGLE_APPLICATION_CREDENTIALS")
        if google_app_creds and os.path.exists(google_app_creds):
            details["method"] = "service_account_file"
            details["credentials_file"] = google_app_creds

            return AuthResult(
                status=AuthStatus.AUTHENTICATED,
                message="Authenticated via service account file",
                details=details
            )

        # No authentication found
        return AuthResult(
            status=AuthStatus.NOT_CONFIGURED,
            message="No Gemini authentication found",
            details={
                "checked": {
                    "api_key_envs": self.API_KEY_ENVS,
                    "adc_path": self.ADC_PATH,
                    "gcloud_config": self.GCLOUD_CONFIG_PATH
                }
            }
        )

    def get_auth_methods(self) -> List[str]:
        """Get supported authentication methods"""
        return ["api_key", "application_default_credentials", "gcloud_cli", "service_account"]

    def get_setup_instructions(self) -> str:
        """Get setup instructions for Gemini CLI"""
        return """
Gemini CLI Authentication Setup
===============================

Option 1: API Key (Recommended for automation)
----------------------------------------------
Set the GOOGLE_API_KEY environment variable:

  export GOOGLE_API_KEY=your-gemini-api-key

Get your API key from: https://aistudio.google.com/apikey

Option 2: gcloud CLI Login (Interactive)
----------------------------------------
Run the gcloud login command:

  gcloud auth login
  gcloud auth application-default login

Option 3: Service Account (For production)
------------------------------------------
1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Set GOOGLE_APPLICATION_CREDENTIALS:

  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json

For Docker
----------
1. Pass API key:
   docker run -e GOOGLE_API_KEY=xxx worker

2. Or mount credentials:
   docker run -v ~/.config/gcloud:/root/.config/gcloud worker
"""
