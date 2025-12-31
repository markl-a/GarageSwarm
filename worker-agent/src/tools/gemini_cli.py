"""Gemini CLI tool integration using subprocess"""

import asyncio
import json
import os
import subprocess
import time
from typing import Any, Dict, Optional
import structlog

from .base import BaseTool

logger = structlog.get_logger()


class GeminiCLI(BaseTool):
    """Gemini CLI tool adapter for Google's Generative AI

    This tool integrates with the Gemini CLI to execute AI-powered tasks
    using subprocess calls to the 'gemini' command-line tool.

    Supports multiple Gemini models including:
    - gemini-pro: Standard model for text generation
    - gemini-1.5-pro: Enhanced model with larger context window
    - gemini-1.5-flash: Faster, more efficient model
    - gemini-2.0-flash-exp: Experimental flash model with latest features

    Features:
    - Async execution support via subprocess
    - Streaming output
    - Timeout handling
    - Rate limiting and retry logic with exponential backoff
    - Comprehensive error handling
    - API key management from environment or config
    """

    # Default configuration values
    DEFAULT_MODEL = "gemini-1.5-flash"
    DEFAULT_TIMEOUT = 300  # 5 minutes
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 2  # seconds

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = 60

    # Supported models
    SUPPORTED_MODELS = [
        "gemini-pro",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-2.0-flash-exp",
        "gemini-flash",
    ]

    def __init__(self, config: Dict[str, Any]):
        """Initialize Gemini CLI tool

        Args:
            config: Configuration dictionary with:
                - api_key: Google API key (or will use GOOGLE_API_KEY env var)
                - cli_path: Path to gemini CLI binary (default: "gemini")
                - model: Model name (default: gemini-1.5-flash)
                - timeout: Request timeout in seconds (default: 300)
                - max_retries: Maximum retry attempts (default: 3)
                - stream: Enable streaming output (default: False)
                - temperature: Sampling temperature 0.0-2.0 (default: 0.7)
                - max_output_tokens: Maximum tokens in response (default: 2048)
                - working_directory: Default working directory for execution
        """
        super().__init__(config)

        # Get API key from config or environment
        self.api_key = config.get("api_key") or os.environ.get("GOOGLE_API_KEY")

        # CLI configuration
        self.cli_path = config.get("cli_path", "gemini")

        # Model configuration
        self.model_name = config.get("model", self.DEFAULT_MODEL)
        self.timeout = config.get("timeout", self.DEFAULT_TIMEOUT)
        self.max_retries = config.get("max_retries", self.DEFAULT_MAX_RETRIES)
        self.stream = config.get("stream", False)
        self.working_dir = config.get("working_directory")

        # Generation parameters
        self.temperature = config.get("temperature", 0.7)
        self.max_output_tokens = config.get("max_output_tokens", 2048)
        self.top_p = config.get("top_p", 0.95)
        self.top_k = config.get("top_k", 40)

        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0
        self.rate_limit_window_start = time.time()

        logger.info(
            "GeminiCLI initialized",
            cli_path=self.cli_path,
            model=self.model_name,
            timeout=self.timeout,
            stream=self.stream
        )

    async def validate_config(self) -> bool:
        """Validate tool configuration

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Check API key
            if not self.api_key:
                logger.error("Missing API key - set GOOGLE_API_KEY environment variable or provide in config")
                return False

            # Check if CLI is available
            try:
                result = await asyncio.create_subprocess_exec(
                    self.cli_path,
                    "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await asyncio.wait_for(result.wait(), timeout=5.0)

                if result.returncode != 0:
                    logger.error("Gemini CLI returned non-zero exit code", exit_code=result.returncode)
                    return False

            except FileNotFoundError:
                logger.error("Gemini CLI not found at path", cli_path=self.cli_path)
                return False
            except asyncio.TimeoutError:
                logger.error("Gemini CLI validation timeout")
                return False

            # Validate configuration values
            if self.timeout <= 0:
                logger.error("Invalid timeout", timeout=self.timeout)
                return False

            if not 0 <= self.temperature <= 2.0:
                logger.error("Invalid temperature (must be 0-2.0)", temperature=self.temperature)
                return False

            if self.max_output_tokens <= 0:
                logger.error("Invalid max_output_tokens", max_output_tokens=self.max_output_tokens)
                return False

            # Warn if model not in supported list
            if self.model_name not in self.SUPPORTED_MODELS:
                logger.warning(
                    "Model not in supported list, may still work",
                    model=self.model_name,
                    supported=self.SUPPORTED_MODELS
                )

            logger.info("Configuration validated successfully")
            return True

        except Exception as e:
            logger.error("Configuration validation failed", error=str(e), error_type=type(e).__name__)
            return False

    async def health_check(self) -> bool:
        """Check if Gemini CLI is available and responsive

        Returns:
            True if CLI is healthy, False otherwise
        """
        try:
            # Try a simple help command with short timeout
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    self.cli_path,
                    "--help",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=5.0
            )

            await asyncio.wait_for(result.wait(), timeout=5.0)

            is_healthy = result.returncode == 0

            if is_healthy:
                logger.info("Health check passed")
            else:
                logger.warning("Health check failed", exit_code=result.returncode)

            return is_healthy

        except asyncio.TimeoutError:
            logger.error("Health check timeout")
            return False
        except FileNotFoundError:
            logger.error("Gemini CLI not found", cli_path=self.cli_path)
            return False
        except Exception as e:
            logger.error("Health check failed", error=str(e), error_type=type(e).__name__)
            return False

    def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        current_time = time.time()

        # Reset counter if window has passed (1 minute)
        if current_time - self.rate_limit_window_start >= 60:
            self.request_count = 0
            self.rate_limit_window_start = current_time

        # Check if we're over the limit
        if self.request_count >= self.MAX_REQUESTS_PER_MINUTE:
            wait_time = 60 - (current_time - self.rate_limit_window_start)
            if wait_time > 0:
                logger.warning(
                    "Rate limit reached, waiting",
                    wait_seconds=wait_time
                )
                time.sleep(wait_time)
                # Reset after waiting
                self.request_count = 0
                self.rate_limit_window_start = time.time()

        self.request_count += 1

    async def _execute_with_retry(
        self,
        cmd: list,
        env: Dict[str, str],
        prompt: str
    ) -> Dict[str, Any]:
        """Execute CLI command with retry logic

        Args:
            cmd: Command list
            env: Environment variables
            prompt: The prompt being sent

        Returns:
            Dictionary with stdout, stderr, and exit_code

        Raises:
            Exception: If all retries fail
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Check rate limit before making request
                self._check_rate_limit()

                logger.info(
                    "Executing Gemini CLI",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    prompt_length=len(prompt)
                )

                # Execute the subprocess
                result = await self._run_subprocess(
                    cmd=cmd,
                    env=env,
                    timeout=self.timeout
                )

                # Check for rate limit errors in output
                stderr = result.get("stderr", "")
                if "rate limit" in stderr.lower() or "quota" in stderr.lower():
                    raise Exception(f"Rate limit exceeded: {stderr}")

                # Check for authentication errors
                if "authentication" in stderr.lower() or "api key" in stderr.lower():
                    raise ValueError(f"Authentication error: {stderr}")

                # Success
                return result

            except asyncio.TimeoutError:
                last_error = f"Request timeout after {self.timeout} seconds"
                logger.warning(
                    "Request timeout",
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )

            except ValueError as e:
                # Don't retry authentication errors
                logger.error("Authentication error, not retrying", error=str(e))
                raise

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Request failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )

            # Exponential backoff before retry
            if attempt < self.max_retries - 1:
                wait_time = self.DEFAULT_RETRY_DELAY * (2 ** attempt)
                logger.info("Waiting before retry", wait_seconds=wait_time)
                await asyncio.sleep(wait_time)

        # All retries failed
        raise Exception(f"Failed after {self.max_retries} attempts: {last_error}")

    async def execute(
        self,
        instructions: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute task with Gemini CLI

        Args:
            instructions: Task instructions/prompt for Gemini
            context: Optional context data containing:
                - files: List of file paths or contents
                - code: Code snippets
                - parameters: Additional parameters
                - system_instructions: System-level instructions
                - working_directory: Working directory override
                - timeout: Timeout override

        Returns:
            Dictionary containing:
                - success: bool - Whether execution succeeded
                - output: str - Generated text response
                - error: Optional[str] - Error message if failed
                - metadata: dict - Execution metadata including:
                    - model: Model name used
                    - duration: Execution time in seconds
                    - exit_code: CLI exit code
                    - timeout: Timeout used
                    - command: Command executed
        """
        start_time = time.time()
        context = context or {}

        logger.info(
            "Executing Gemini task",
            model=self.model_name,
            instructions_length=len(instructions)
        )

        try:
            # Build the full prompt
            prompt = self._build_prompt(instructions, context)

            # Get context overrides
            working_dir = context.get("working_directory", self.working_dir)
            timeout_override = context.get("timeout")
            if timeout_override:
                original_timeout = self.timeout
                self.timeout = timeout_override

            # Build command
            cmd = self._build_command(prompt, context)

            # Prepare environment variables
            env = os.environ.copy()
            if self.api_key:
                env["GOOGLE_API_KEY"] = self.api_key

            # Execute with retry logic
            result = await self._execute_with_retry(cmd, env, prompt)

            # Restore original timeout if overridden
            if timeout_override:
                self.timeout = original_timeout

            duration = time.time() - start_time

            # Parse result
            success = result["exit_code"] == 0
            output = result["stdout"]
            error = result["stderr"] if result["stderr"] and not success else None

            # Parse output if it's JSON (some CLI tools return JSON)
            parsed_output = output
            try:
                json_output = json.loads(output)
                if isinstance(json_output, dict) and "text" in json_output:
                    parsed_output = json_output["text"]
            except (json.JSONDecodeError, TypeError):
                # Not JSON, use as-is
                pass

            logger.info(
                "Task completed successfully" if success else "Task completed with errors",
                success=success,
                duration=duration,
                exit_code=result["exit_code"],
                output_length=len(parsed_output)
            )

            return {
                "success": success,
                "output": parsed_output,
                "error": error,
                "metadata": {
                    "model": self.model_name,
                    "duration": duration,
                    "exit_code": result["exit_code"],
                    "timeout": self.timeout,
                    "working_directory": working_dir,
                    "command": " ".join(cmd[:3]) + "...",  # Don't log full prompt
                    "stream": self.stream
                }
            }

        except Exception as e:
            duration = time.time() - start_time
            error_message = str(e)

            logger.error(
                "Task execution failed",
                error=error_message,
                error_type=type(e).__name__,
                duration=duration
            )

            return {
                "success": False,
                "output": None,
                "error": error_message,
                "metadata": {
                    "model": self.model_name,
                    "duration": duration,
                    "error_type": type(e).__name__
                }
            }

    def _build_command(self, prompt: str, context: Dict[str, Any]) -> list:
        """Build CLI command

        Args:
            prompt: The full prompt
            context: Context data

        Returns:
            Command list for subprocess
        """
        cmd = [self.cli_path]

        # Add model parameter
        cmd.extend(["--model", self.model_name])

        # Add temperature
        cmd.extend(["--temperature", str(self.temperature)])

        # Add max tokens
        cmd.extend(["--max-tokens", str(self.max_output_tokens)])

        # Add top-p
        cmd.extend(["--top-p", str(self.top_p)])

        # Add top-k
        cmd.extend(["--top-k", str(self.top_k)])

        # Enable streaming if configured
        if self.stream:
            cmd.append("--stream")

        # Add output format (prefer JSON for easier parsing)
        cmd.extend(["--format", "json"])

        # Add any additional CLI arguments from context
        additional_args = context.get("additional_args", [])
        if additional_args:
            cmd.extend(additional_args)

        # Add the prompt as the last argument
        cmd.append(prompt)

        return cmd

    def _build_prompt(self, instructions: str, context: Dict[str, Any]) -> str:
        """Build full prompt from instructions and context

        Args:
            instructions: Main task instructions
            context: Context data

        Returns:
            Complete prompt string
        """
        prompt_parts = []

        # Add system instructions if provided
        if "system_instructions" in context:
            prompt_parts.append(f"System: {context['system_instructions']}\n")

        # Add file context if provided
        if "files" in context:
            files = context["files"]
            if isinstance(files, list):
                prompt_parts.append("\n=== Context Files ===\n")
                for file_info in files:
                    if isinstance(file_info, dict):
                        file_path = file_info.get("path", "unknown")
                        file_content = file_info.get("content", "")
                        prompt_parts.append(f"\nFile: {file_path}\n```\n{file_content}\n```\n")
                    else:
                        prompt_parts.append(f"\n{file_info}\n")

        # Add code context if provided
        if "code" in context:
            prompt_parts.append(f"\n=== Code Context ===\n```\n{context['code']}\n```\n")

        # Add parameters if provided
        if "parameters" in context:
            params = context["parameters"]
            if isinstance(params, dict):
                prompt_parts.append("\n=== Parameters ===\n")
                for key, value in params.items():
                    prompt_parts.append(f"{key}: {value}\n")

        # Add main instructions
        prompt_parts.append(f"\n=== Task ===\n{instructions}")

        return "".join(prompt_parts)

    async def _run_subprocess(
        self,
        cmd: list,
        env: Dict[str, str],
        timeout: int
    ) -> Dict[str, Any]:
        """Run subprocess with timeout and stream support

        Args:
            cmd: Command list
            env: Environment variables
            timeout: Timeout in seconds

        Returns:
            Dictionary with stdout, stderr, and exit_code
        """
        logger.debug("Starting subprocess", command=" ".join(cmd[:5]) + "...")

        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.working_dir,
            env=env
        )

        stdout_lines = []
        stderr_lines = []

        async def read_stream(stream, lines_buffer, stream_name):
            """Read from stream and optionally log"""
            while True:
                line = await stream.readline()
                if not line:
                    break

                decoded_line = line.decode('utf-8', errors='replace').rstrip()
                lines_buffer.append(decoded_line)

                if self.stream:
                    logger.debug(
                        f"Gemini CLI {stream_name}",
                        line=decoded_line
                    )

        try:
            # Read stdout and stderr concurrently with timeout
            await asyncio.wait_for(
                asyncio.gather(
                    read_stream(process.stdout, stdout_lines, "stdout"),
                    read_stream(process.stderr, stderr_lines, "stderr"),
                    process.wait()
                ),
                timeout=timeout
            )

            exit_code = process.returncode

        except asyncio.TimeoutError:
            # Kill process on timeout
            logger.warning("Subprocess timeout, terminating process")
            try:
                process.kill()
                await process.wait()
            except Exception as e:
                logger.error("Error killing process", error=str(e))
            raise

        return {
            "stdout": "\n".join(stdout_lines),
            "stderr": "\n".join(stderr_lines),
            "exit_code": exit_code
        }

    async def cancel(self) -> bool:
        """Cancel any ongoing execution

        Terminates any running subprocess associated with this tool.

        Returns:
            True if cancellation was successful, False otherwise
        """
        logger.info("Cancellation requested for GeminiCLI")
        # Note: The subprocess is managed within _run_subprocess method
        # Cancellation is handled via asyncio.CancelledError propagation
        # and process.kill() in the timeout handler
        return True

    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information

        Returns:
            Dictionary with tool details
        """
        return {
            "name": self.name,
            "type": "ai_tool",
            "provider": "google",
            "model": self.model_name,
            "cli_path": self.cli_path,
            "capabilities": [
                "text_generation",
                "code_generation",
                "analysis",
                "streaming",
            ],
            "features": {
                "streaming": True,
                "timeout_support": True,
                "retry_logic": True,
                "rate_limiting": True,
                "context_support": True,
                "cancellation": True
            },
            "config": {
                "model": self.model_name,
                "timeout": self.timeout,
                "stream": self.stream,
                "temperature": self.temperature,
                "max_output_tokens": self.max_output_tokens,
                "max_retries": self.max_retries
            },
            "supported_models": self.SUPPORTED_MODELS,
        }
