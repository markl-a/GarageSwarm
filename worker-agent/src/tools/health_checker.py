"""AI Tool Health Check System

This module provides comprehensive health checking for all AI tools in the worker-agent.
It checks availability, configuration, version detection, and provides structured health status.
"""

import asyncio
import os
import subprocess
import time
from typing import Any, Dict, List, Optional
from enum import Enum

import structlog

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


logger = structlog.get_logger()


class HealthStatus(str, Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ToolHealthChecker:
    """Comprehensive health checker for AI tools

    Performs health checks on:
    - Claude Code CLI
    - Gemini API
    - Ollama local service

    Features:
    - Version detection
    - Timeout handling
    - Graceful degradation
    - Detailed status reporting
    """

    # Default timeouts (in seconds)
    DEFAULT_TIMEOUT = 10.0
    QUICK_TIMEOUT = 5.0

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        """Initialize health checker

        Args:
            timeout: Default timeout for health checks in seconds
        """
        self.timeout = timeout

    async def check_all_tools(
        self,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Check health of all AI tools

        Args:
            config: Optional configuration for tools

        Returns:
            Dictionary with health status for all tools:
                - timestamp: Check timestamp
                - overall_status: Overall health status
                - tools: Dictionary of tool statuses
                - summary: Summary statistics
        """
        start_time = time.time()
        config = config or {}

        logger.info("Starting health check for all AI tools")

        # Run all health checks concurrently
        claude_task = self.check_claude_code(config.get("claude_code", {}))
        gemini_task = self.check_gemini(config.get("gemini", {}))
        ollama_task = self.check_ollama(config.get("ollama", {}))

        claude_status, gemini_status, ollama_status = await asyncio.gather(
            claude_task,
            gemini_task,
            ollama_task,
            return_exceptions=True
        )

        # Handle any exceptions from health checks
        claude_status = self._handle_check_exception(claude_status, "Claude Code")
        gemini_status = self._handle_check_exception(gemini_status, "Gemini")
        ollama_status = self._handle_check_exception(ollama_status, "Ollama")

        tools_status = {
            "claude_code": claude_status,
            "gemini": gemini_status,
            "ollama": ollama_status
        }

        # Calculate overall status
        overall_status = self._calculate_overall_status(tools_status)

        # Generate summary
        summary = self._generate_summary(tools_status)

        duration = time.time() - start_time

        result = {
            "timestamp": time.time(),
            "duration": duration,
            "overall_status": overall_status,
            "tools": tools_status,
            "summary": summary
        }

        logger.info(
            "Health check completed",
            overall_status=overall_status,
            duration=duration,
            healthy_count=summary["healthy_count"],
            total_count=summary["total_count"]
        )

        return result

    async def check_claude_code(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check Claude Code CLI health

        Args:
            config: Configuration dictionary with optional:
                - cli_path: Path to claude CLI binary

        Returns:
            Health status dictionary with:
                - status: Health status (healthy/degraded/unhealthy)
                - available: Whether CLI is available
                - version: Version string if available
                - path: CLI path
                - latency: Response time in milliseconds
                - error: Error message if unhealthy
        """
        start_time = time.time()
        cli_path = config.get("cli_path", "claude")

        logger.debug("Checking Claude Code health", cli_path=cli_path)

        result = {
            "name": "Claude Code",
            "status": HealthStatus.UNKNOWN,
            "available": False,
            "version": None,
            "path": cli_path,
            "latency": None,
            "error": None,
            "checked_at": start_time
        }

        try:
            # Try to get version
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    cli_path,
                    "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=self.QUICK_TIMEOUT
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.QUICK_TIMEOUT
            )

            latency = (time.time() - start_time) * 1000  # Convert to ms
            result["latency"] = round(latency, 2)

            if process.returncode == 0:
                result["available"] = True
                result["status"] = HealthStatus.HEALTHY

                # Extract version from output
                version_output = stdout.decode('utf-8', errors='replace').strip()
                if version_output:
                    result["version"] = version_output

                logger.info(
                    "Claude Code is healthy",
                    version=result["version"],
                    latency=result["latency"]
                )
            else:
                result["status"] = HealthStatus.DEGRADED
                result["error"] = f"CLI returned exit code {process.returncode}"
                logger.warning("Claude Code check failed", error=result["error"])

        except asyncio.TimeoutError:
            result["status"] = HealthStatus.UNHEALTHY
            result["error"] = f"Health check timeout after {self.QUICK_TIMEOUT}s"
            logger.error("Claude Code health check timeout")

        except FileNotFoundError:
            result["status"] = HealthStatus.UNHEALTHY
            result["error"] = f"CLI not found at path: {cli_path}"
            logger.error("Claude Code CLI not found", cli_path=cli_path)

        except Exception as e:
            result["status"] = HealthStatus.UNHEALTHY
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error(
                "Claude Code health check error",
                error=str(e),
                error_type=type(e).__name__
            )

        return result

    async def check_gemini(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check Gemini API health

        Args:
            config: Configuration dictionary with:
                - api_key: Google API key (or uses GOOGLE_API_KEY env var)
                - model: Model name (optional)

        Returns:
            Health status dictionary with:
                - status: Health status
                - available: Whether API is available
                - configured: Whether API key is configured
                - model: Model name
                - latency: Response time in milliseconds
                - error: Error message if unhealthy
        """
        start_time = time.time()
        api_key = config.get("api_key") or os.environ.get("GOOGLE_API_KEY")
        model_name = config.get("model", "gemini-1.5-flash")

        logger.debug("Checking Gemini health", model=model_name)

        result = {
            "name": "Gemini",
            "status": HealthStatus.UNKNOWN,
            "available": False,
            "configured": False,
            "model": model_name,
            "version": None,
            "latency": None,
            "error": None,
            "checked_at": start_time
        }

        # Check if SDK is available
        if not GENAI_AVAILABLE:
            result["status"] = HealthStatus.UNHEALTHY
            result["error"] = "google-generativeai package not installed"
            logger.warning("Gemini SDK not available")
            return result

        # Check if API key is configured
        if not api_key:
            result["status"] = HealthStatus.UNHEALTHY
            result["error"] = "GOOGLE_API_KEY not configured"
            logger.warning("Gemini API key not configured")
            return result

        result["configured"] = True

        try:
            # Configure API
            genai.configure(api_key=api_key)

            # Try a simple test request
            model = genai.GenerativeModel(model_name)

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    model.generate_content,
                    "Hello",
                    generation_config={"max_output_tokens": 10}
                ),
                timeout=self.timeout
            )

            latency = (time.time() - start_time) * 1000
            result["latency"] = round(latency, 2)

            if response and response.text:
                result["available"] = True
                result["status"] = HealthStatus.HEALTHY

                # Try to get model version info
                try:
                    result["version"] = model_name
                except Exception:
                    pass

                logger.info(
                    "Gemini is healthy",
                    model=model_name,
                    latency=result["latency"]
                )
            else:
                result["status"] = HealthStatus.DEGRADED
                result["error"] = "API responded but returned empty response"
                logger.warning("Gemini returned empty response")

        except asyncio.TimeoutError:
            result["status"] = HealthStatus.UNHEALTHY
            result["error"] = f"Health check timeout after {self.timeout}s"
            logger.error("Gemini health check timeout")

        except Exception as e:
            result["status"] = HealthStatus.UNHEALTHY
            result["error"] = f"API error: {str(e)}"
            logger.error(
                "Gemini health check error",
                error=str(e),
                error_type=type(e).__name__
            )

        return result

    async def check_ollama(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check Ollama service health

        Args:
            config: Configuration dictionary with:
                - url: Ollama service URL (default: http://localhost:11434)
                - model: Model name to check (optional)

        Returns:
            Health status dictionary with:
                - status: Health status
                - available: Whether service is available
                - url: Service URL
                - models_available: List of available models
                - version: Ollama version if available
                - latency: Response time in milliseconds
                - error: Error message if unhealthy
        """
        start_time = time.time()
        url = config.get("url", "http://localhost:11434").rstrip("/")
        model_name = config.get("model")

        logger.debug("Checking Ollama health", url=url, model=model_name)

        result = {
            "name": "Ollama",
            "status": HealthStatus.UNKNOWN,
            "available": False,
            "url": url,
            "model": model_name,
            "models_available": [],
            "version": None,
            "latency": None,
            "error": None,
            "checked_at": start_time
        }

        # Check if httpx is available
        if not HTTPX_AVAILABLE:
            result["status"] = HealthStatus.UNHEALTHY
            result["error"] = "httpx package not installed"
            logger.warning("httpx not available for Ollama check")
            return result

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Check service availability via tags endpoint
                response = await client.get(f"{url}/api/tags")
                response.raise_for_status()

                latency = (time.time() - start_time) * 1000
                result["latency"] = round(latency, 2)

                data = response.json()

                # Extract available models
                models = data.get("models", [])
                result["models_available"] = [
                    m.get("name", "").split(":")[0] for m in models
                ]

                result["available"] = True

                # Check if specific model is available (if specified)
                if model_name:
                    model_base = model_name.split(":")[0]
                    model_available = any(
                        model_base in m.get("name", "") for m in models
                    )

                    if model_available:
                        result["status"] = HealthStatus.HEALTHY
                        logger.info(
                            "Ollama is healthy",
                            url=url,
                            model=model_name,
                            latency=result["latency"]
                        )
                    else:
                        result["status"] = HealthStatus.DEGRADED
                        result["error"] = f"Model '{model_name}' not available"
                        logger.warning(
                            "Ollama model not available",
                            model=model_name,
                            available_models=result["models_available"]
                        )
                else:
                    # No specific model to check, just check service
                    if models:
                        result["status"] = HealthStatus.HEALTHY
                        logger.info(
                            "Ollama is healthy",
                            url=url,
                            model_count=len(models),
                            latency=result["latency"]
                        )
                    else:
                        result["status"] = HealthStatus.DEGRADED
                        result["error"] = "Service running but no models available"
                        logger.warning("Ollama has no models available")

                # Try to get version info from version endpoint
                try:
                    version_response = await client.get(f"{url}/api/version")
                    if version_response.status_code == 200:
                        version_data = version_response.json()
                        result["version"] = version_data.get("version")
                except Exception:
                    # Version endpoint may not be available in all versions
                    pass

        except httpx.ConnectError as e:
            result["status"] = HealthStatus.UNHEALTHY
            result["error"] = f"Cannot connect to service at {url}"
            logger.error("Ollama connection failed", url=url, error=str(e))

        except httpx.TimeoutException:
            result["status"] = HealthStatus.UNHEALTHY
            result["error"] = f"Health check timeout after {self.timeout}s"
            logger.error("Ollama health check timeout", url=url)

        except httpx.HTTPStatusError as e:
            result["status"] = HealthStatus.UNHEALTHY
            result["error"] = f"HTTP error {e.response.status_code}"
            logger.error(
                "Ollama HTTP error",
                url=url,
                status_code=e.response.status_code
            )

        except Exception as e:
            result["status"] = HealthStatus.UNHEALTHY
            result["error"] = f"Unexpected error: {str(e)}"
            logger.error(
                "Ollama health check error",
                url=url,
                error=str(e),
                error_type=type(e).__name__
            )

        return result

    def _handle_check_exception(
        self,
        result: Any,
        tool_name: str
    ) -> Dict[str, Any]:
        """Handle exceptions from health check tasks

        Args:
            result: Result from asyncio.gather (may be exception)
            tool_name: Name of the tool

        Returns:
            Health status dictionary
        """
        if isinstance(result, Exception):
            logger.error(
                "Health check raised exception",
                tool=tool_name,
                error=str(result),
                error_type=type(result).__name__
            )
            return {
                "name": tool_name,
                "status": HealthStatus.UNHEALTHY,
                "available": False,
                "error": f"Health check failed: {str(result)}",
                "checked_at": time.time()
            }
        return result

    def _calculate_overall_status(
        self,
        tools_status: Dict[str, Dict[str, Any]]
    ) -> str:
        """Calculate overall health status from individual tool statuses

        Args:
            tools_status: Dictionary of tool statuses

        Returns:
            Overall status string
        """
        statuses = [tool["status"] for tool in tools_status.values()]

        # If any unhealthy, overall is unhealthy
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY

        # If any degraded, overall is degraded
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED

        # If all healthy, overall is healthy
        if all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY

        # Otherwise unknown
        return HealthStatus.UNKNOWN

    def _generate_summary(
        self,
        tools_status: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate summary statistics from tool statuses

        Args:
            tools_status: Dictionary of tool statuses

        Returns:
            Summary dictionary with counts and lists
        """
        healthy = []
        degraded = []
        unhealthy = []

        for tool_name, status in tools_status.items():
            if status["status"] == HealthStatus.HEALTHY:
                healthy.append(tool_name)
            elif status["status"] == HealthStatus.DEGRADED:
                degraded.append(tool_name)
            elif status["status"] == HealthStatus.UNHEALTHY:
                unhealthy.append(tool_name)

        return {
            "total_count": len(tools_status),
            "healthy_count": len(healthy),
            "degraded_count": len(degraded),
            "unhealthy_count": len(unhealthy),
            "healthy_tools": healthy,
            "degraded_tools": degraded,
            "unhealthy_tools": unhealthy
        }


async def quick_health_check(
    tools: Optional[List[str]] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Convenience function for quick health check

    Args:
        tools: Optional list of tool names to check (default: all)
        config: Optional configuration for tools

    Returns:
        Health status dictionary
    """
    checker = ToolHealthChecker(timeout=ToolHealthChecker.QUICK_TIMEOUT)

    if tools is None:
        # Check all tools
        return await checker.check_all_tools(config)

    # Check specific tools
    result = {
        "timestamp": time.time(),
        "tools": {}
    }

    config = config or {}

    if "claude_code" in tools:
        result["tools"]["claude_code"] = await checker.check_claude_code(
            config.get("claude_code", {})
        )

    if "gemini" in tools:
        result["tools"]["gemini"] = await checker.check_gemini(
            config.get("gemini", {})
        )

    if "ollama" in tools:
        result["tools"]["ollama"] = await checker.check_ollama(
            config.get("ollama", {})
        )

    return result
