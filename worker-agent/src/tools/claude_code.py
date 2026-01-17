"""Claude Code (MCP) tool integration"""

import asyncio
import json
import os
import subprocess
import time
from typing import Any, Dict, Optional, List
import structlog

from .base import BaseTool

# Import retry utility if available, otherwise define inline
try:
    from ..utils.retry import retry_with_backoff
except ImportError:
    # Fallback if utils.retry not available
    async def retry_with_backoff(func, max_retries=3, base_delay=1.0, **kwargs):
        """Simple retry implementation"""
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                return await func()
            except Exception as e:
                last_exception = e
                if attempt == max_retries:
                    raise
                await asyncio.sleep(base_delay * (2 ** attempt))
        if last_exception:
            raise last_exception

logger = structlog.get_logger()


class ClaudeCodeError(Exception):
    """Base exception for Claude Code errors"""

    def __init__(self, message: str, retryable: bool = False, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.details = details or {}


class ClaudeCodeTimeoutError(ClaudeCodeError):
    """Timeout error for Claude Code execution"""

    def __init__(self, timeout: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Claude Code execution timed out after {timeout} seconds",
            retryable=False,
            details=details
        )


class ClaudeCodeCLINotFoundError(ClaudeCodeError):
    """Claude Code CLI not found error"""

    def __init__(self, cli_path: str):
        super().__init__(
            f"Claude Code CLI not found at: {cli_path}",
            retryable=False,
            details={"cli_path": cli_path}
        )


class ClaudeCodeExecutionError(ClaudeCodeError):
    """Claude Code execution error"""

    def __init__(self, message: str, exit_code: int, stderr: str, retryable: bool = False):
        super().__init__(
            message,
            retryable=retryable,
            details={"exit_code": exit_code, "stderr": stderr}
        )


class ClaudeCodeTool(BaseTool):
    """Claude Code CLI tool integration

    This tool integrates with Claude Code (MCP) CLI to execute AI-powered
    coding tasks using subprocess calls with advanced features:
    - Streaming output
    - JSON response parsing
    - Timeout handling with cancellation
    - Automatic retry with exponential backoff
    - Error classification (retryable vs fatal)
    """

    # Exit codes that indicate retryable errors
    RETRYABLE_EXIT_CODES = {
        124,  # Timeout (from timeout command)
        137,  # SIGKILL (out of memory or killed)
        143,  # SIGTERM
    }

    # Error patterns in stderr that indicate retryable errors
    RETRYABLE_ERROR_PATTERNS = [
        "rate limit",
        "timeout",
        "connection",
        "network",
        "temporary",
        "unavailable",
        "try again",
    ]

    def __init__(self, config: Dict[str, Any]):
        """Initialize Claude Code tool

        Args:
            config: Configuration dictionary with optional keys:
                - cli_path: Path to claude CLI binary (default: "claude")
                - default_timeout: Default timeout in seconds (default: 300)
                - working_directory: Default working directory for execution
                - env_vars: Additional environment variables
                - max_retries: Maximum retry attempts for retryable errors (default: 3)
                - retry_base_delay: Base delay for retry backoff (default: 1.0)
                - enable_json_parsing: Parse JSON responses (default: True)
                - json_output_marker: Marker for JSON output start (default: "```json")
        """
        super().__init__(config)
        self.cli_path = config.get("cli_path", "claude")
        self.default_timeout = config.get("default_timeout", 300)
        self.default_working_dir = config.get("working_directory")
        self.env_vars = config.get("env_vars", {})

        # Retry configuration
        self.max_retries = config.get("max_retries", 3)
        self.retry_base_delay = config.get("retry_base_delay", 1.0)

        # JSON parsing configuration
        self.enable_json_parsing = config.get("enable_json_parsing", True)
        self.json_output_marker = config.get("json_output_marker", "```json")

        # Cancellation support
        self._current_process: Optional[asyncio.subprocess.Process] = None
        self._cancelled = False

    async def execute(
        self,
        instructions: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute task using Claude Code CLI

        Args:
            instructions: Task instructions/prompt for Claude Code
            context: Optional context containing:
                - working_directory: Working directory for execution
                - timeout: Timeout in seconds (overrides default)
                - additional_args: Additional CLI arguments
                - files: List of file paths to include in context
                - stream: Whether to stream output (default: True)
                - parse_json: Parse JSON from output (default: from config)
                - retry: Enable retry logic (default: True)
                - max_retries: Override default max_retries

        Returns:
            Dictionary containing:
                - success: bool - Whether execution succeeded
                - output: str - Claude Code output
                - parsed_json: Optional[Any] - Parsed JSON if found
                - error: Optional[str] - Error message if failed
                - retryable: bool - Whether error is retryable
                - metadata: Dict - Execution metadata (duration, exit_code, etc.)
        """
        start_time = time.time()
        context = context or {}

        # Extract context parameters
        working_dir = context.get("working_directory", self.default_working_dir)
        timeout = context.get("timeout", self.default_timeout)
        additional_args = context.get("additional_args", [])
        files = context.get("files", [])
        stream_output = context.get("stream", True)
        parse_json = context.get("parse_json", self.enable_json_parsing)
        enable_retry = context.get("retry", True)
        max_retries = context.get("max_retries", self.max_retries)

        logger.info(
            "Executing Claude Code task",
            working_dir=working_dir,
            timeout=timeout,
            has_files=len(files) > 0,
            retry_enabled=enable_retry
        )

        # Define execution function for retry
        async def _execute():
            return await self._execute_internal(
                instructions=instructions,
                working_dir=working_dir,
                timeout=timeout,
                additional_args=additional_args,
                files=files,
                stream_output=stream_output,
                parse_json=parse_json
            )

        try:
            if enable_retry and max_retries > 0:
                # Execute with retry logic
                result = await retry_with_backoff(
                    _execute,
                    max_retries=max_retries,
                    base_delay=self.retry_base_delay,
                    exceptions=(ClaudeCodeError,)
                )
            else:
                # Execute without retry
                result = await _execute()

            duration = time.time() - start_time
            result["metadata"]["total_duration"] = duration

            return result

        except ClaudeCodeError as e:
            duration = time.time() - start_time

            logger.error(
                "Claude Code execution failed",
                error=str(e),
                retryable=e.retryable,
                duration=duration,
                details=e.details
            )

            return {
                "success": False,
                "output": None,
                "parsed_json": None,
                "error": str(e),
                "retryable": e.retryable,
                "metadata": {
                    "duration": duration,
                    "timeout": timeout,
                    "working_directory": working_dir,
                    "error_details": e.details
                }
            }

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Unexpected error: {str(e)}"

            logger.error(
                "Claude Code unexpected error",
                error=str(e),
                exception_type=type(e).__name__,
                duration=duration
            )

            return {
                "success": False,
                "output": None,
                "parsed_json": None,
                "error": error_msg,
                "retryable": False,
                "metadata": {
                    "duration": duration,
                    "exception_type": type(e).__name__,
                    "working_directory": working_dir
                }
            }

    async def _execute_internal(
        self,
        instructions: str,
        working_dir: Optional[str],
        timeout: int,
        additional_args: List[str],
        files: List[str],
        stream_output: bool,
        parse_json: bool
    ) -> Dict[str, Any]:
        """Internal execution method (used by retry logic)"""
        start_time = time.time()

        # Reset cancellation flag
        self._cancelled = False

        try:
            # Build command
            cmd = [self.cli_path]

            # Add print mode flag for non-interactive execution
            cmd.extend(["-p"])

            # Add additional arguments
            if additional_args:
                cmd.extend(additional_args)

            # Add file paths if provided
            if files:
                for file_path in files:
                    if os.path.exists(file_path):
                        cmd.extend(["--file", file_path])
                    else:
                        logger.warning("File not found", file_path=file_path)

            # Note: Instructions are passed via stdin for better handling of long prompts
            # cmd.append(instructions)  # Removed - using stdin instead

            # Prepare environment variables
            env = os.environ.copy()
            env.update(self.env_vars)

            # Execute subprocess with stdin input
            result = await self._run_subprocess(
                cmd=cmd,
                working_dir=working_dir,
                timeout=timeout,
                env=env,
                stream=stream_output,
                stdin_input=instructions  # Pass instructions via stdin
            )

            duration = time.time() - start_time

            # Check if cancelled
            if self._cancelled:
                raise ClaudeCodeError(
                    "Execution was cancelled",
                    retryable=False,
                    details={"duration": duration}
                )

            # Parse result
            success = result["exit_code"] == 0
            output = result["stdout"]
            stderr = result["stderr"]

            # Parse JSON from output if enabled
            parsed_json = None
            if parse_json and output:
                parsed_json = self._parse_json_output(output)

            # Check for errors
            if not success:
                retryable = self._is_retryable_error(result["exit_code"], stderr)
                error_msg = f"Claude Code failed with exit code {result['exit_code']}"

                if stderr:
                    error_msg += f": {stderr[:500]}"  # Limit error message length

                raise ClaudeCodeExecutionError(
                    error_msg,
                    exit_code=result["exit_code"],
                    stderr=stderr,
                    retryable=retryable
                )

            logger.info(
                "Claude Code execution completed",
                success=success,
                duration=duration,
                exit_code=result["exit_code"],
                has_json=parsed_json is not None
            )

            return {
                "success": True,
                "output": output,
                "parsed_json": parsed_json,
                "error": None,
                "retryable": False,
                "metadata": {
                    "duration": duration,
                    "exit_code": result["exit_code"],
                    "timeout": timeout,
                    "working_directory": working_dir,
                    "command": " ".join(cmd),
                    "files_included": len(files),
                    "has_json": parsed_json is not None
                }
            }

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            raise ClaudeCodeTimeoutError(
                timeout=timeout,
                details={"duration": duration}
            )

        except ClaudeCodeError:
            # Re-raise ClaudeCodeError as-is
            raise

        except FileNotFoundError:
            raise ClaudeCodeCLINotFoundError(self.cli_path)

        except Exception as e:
            # Wrap other exceptions
            raise ClaudeCodeError(
                f"Execution error: {str(e)}",
                retryable=False,
                details={"exception_type": type(e).__name__}
            )

    async def _run_subprocess(
        self,
        cmd: List[str],
        working_dir: Optional[str],
        timeout: int,
        env: Dict[str, str],
        stream: bool = True,
        stdin_input: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run subprocess with timeout and stream support

        Args:
            cmd: Command list
            working_dir: Working directory
            timeout: Timeout in seconds
            env: Environment variables
            stream: Whether to stream output
            stdin_input: Optional input to send via stdin

        Returns:
            Dictionary with stdout, stderr, and exit_code
        """
        logger.debug("Starting subprocess", command=" ".join(cmd), has_stdin=stdin_input is not None)

        # Create subprocess with stdin if input provided
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE if stdin_input else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
            env=env
        )

        # Store process reference for cancellation
        self._current_process = process

        stdout_lines = []
        stderr_lines = []

        async def read_stream(stream_obj, lines_buffer, stream_name):
            """Read from stream and optionally log"""
            try:
                while True:
                    # Check for cancellation
                    if self._cancelled:
                        break

                    line = await stream_obj.readline()
                    if not line:
                        break

                    decoded_line = line.decode('utf-8', errors='replace').rstrip()
                    lines_buffer.append(decoded_line)

                    if stream:
                        logger.debug(
                            f"Claude Code {stream_name}",
                            line=decoded_line
                        )
            except Exception as e:
                logger.warning(f"Error reading {stream_name}", error=str(e))

        try:
            # Write stdin input if provided
            if stdin_input and process.stdin:
                process.stdin.write(stdin_input.encode('utf-8'))
                await process.stdin.drain()
                process.stdin.close()
                await process.stdin.wait_closed()
                logger.debug("Stdin input sent to subprocess")

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
            await self._terminate_process(process)
            raise

        finally:
            self._current_process = None

        return {
            "stdout": "\n".join(stdout_lines),
            "stderr": "\n".join(stderr_lines),
            "exit_code": exit_code
        }

    async def _terminate_process(self, process: asyncio.subprocess.Process):
        """Terminate process gracefully, then force kill if needed"""
        try:
            # Try graceful termination first
            process.terminate()

            # Wait up to 5 seconds for graceful shutdown
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
                logger.debug("Process terminated gracefully")
            except asyncio.TimeoutError:
                # Force kill if graceful shutdown failed
                logger.warning("Forcefully killing process")
                process.kill()
                await process.wait()
        except Exception as e:
            logger.error("Error terminating process", error=str(e))

    def _is_retryable_error(self, exit_code: int, stderr: str) -> bool:
        """Determine if error is retryable based on exit code and stderr

        Args:
            exit_code: Process exit code
            stderr: Standard error output

        Returns:
            True if error is retryable, False otherwise
        """
        # Check exit code
        if exit_code in self.RETRYABLE_EXIT_CODES:
            return True

        # Check stderr for retryable error patterns
        if stderr:
            stderr_lower = stderr.lower()
            for pattern in self.RETRYABLE_ERROR_PATTERNS:
                if pattern in stderr_lower:
                    return True

        return False

    def _parse_json_output(self, output: str) -> Optional[Any]:
        """Parse JSON from Claude Code output

        Tries multiple strategies:
        1. Parse entire output as JSON
        2. Extract JSON from code blocks (```json ... ```)
        3. Find JSON objects in output

        Args:
            output: Claude Code output

        Returns:
            Parsed JSON object or None if not found
        """
        if not output or not output.strip():
            return None

        # Strategy 1: Try parsing entire output as JSON
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from JSON code blocks
        if self.json_output_marker in output:
            try:
                # Find JSON code block
                start_marker = self.json_output_marker
                end_marker = "```"

                start_idx = output.find(start_marker)
                if start_idx != -1:
                    start_idx += len(start_marker)
                    end_idx = output.find(end_marker, start_idx)

                    if end_idx != -1:
                        json_str = output[start_idx:end_idx].strip()
                        return json.loads(json_str)
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug("Failed to parse JSON from code block", error=str(e))

        # Strategy 3: Find JSON objects in output
        try:
            # Look for { ... } or [ ... ] patterns
            lines = output.split('\n')
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('{') or stripped.startswith('['):
                    # Try parsing from this line to end
                    potential_json = '\n'.join(lines[i:])

                    # Find the matching closing bracket
                    depth = 0
                    start_char = stripped[0]
                    end_char = '}' if start_char == '{' else ']'

                    for j, char in enumerate(potential_json):
                        if char == start_char:
                            depth += 1
                        elif char == end_char:
                            depth -= 1
                            if depth == 0:
                                json_str = potential_json[:j+1]
                                try:
                                    return json.loads(json_str)
                                except json.JSONDecodeError:
                                    break
        except Exception as e:
            logger.debug("Failed to find JSON in output", error=str(e))

        return None

    async def cancel(self):
        """Cancel current execution"""
        self._cancelled = True

        if self._current_process and self._current_process.returncode is None:
            logger.info("Cancelling Claude Code execution")
            await self._terminate_process(self._current_process)

    async def validate_config(self) -> bool:
        """Validate tool configuration

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Check if CLI is available
            result = await asyncio.create_subprocess_exec(
                self.cli_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            await result.wait()

            if result.returncode == 0:
                logger.info("Claude Code CLI validation successful")
                return True
            else:
                logger.error(
                    "Claude Code CLI validation failed",
                    exit_code=result.returncode
                )
                return False

        except FileNotFoundError:
            logger.error(
                "Claude Code CLI not found",
                cli_path=self.cli_path
            )
            return False

        except Exception as e:
            logger.error(
                "Claude Code validation error",
                error=str(e),
                exception_type=type(e).__name__
            )
            return False

    async def health_check(self) -> bool:
        """Check if Claude Code CLI is available and responsive

        Returns:
            True if tool is healthy, False otherwise
        """
        try:
            # Try a simple command with short timeout
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
                logger.debug("Claude Code health check passed")
            else:
                logger.warning(
                    "Claude Code health check failed",
                    exit_code=result.returncode
                )

            return is_healthy

        except asyncio.TimeoutError:
            logger.error("Claude Code health check timeout")
            return False

        except Exception as e:
            logger.error(
                "Claude Code health check error",
                error=str(e),
                exception_type=type(e).__name__
            )
            return False

    async def detailed_health_check(self) -> Dict[str, Any]:
        """Perform detailed health check with version info

        Returns:
            Dictionary with detailed health status
        """
        import time
        start_time = time.time()

        try:
            # Get version info
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    self.cli_path,
                    "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=5.0
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=5.0
            )

            latency = (time.time() - start_time) * 1000
            is_healthy = process.returncode == 0

            version = None
            if is_healthy and stdout:
                version = stdout.decode('utf-8', errors='replace').strip()

            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "available": is_healthy,
                "latency": round(latency, 2),
                "version": version,
                "error": None if is_healthy else "Version check failed",
                "metadata": {
                    "tool_name": self.name,
                    "cli_path": self.cli_path,
                    "exit_code": process.returncode
                }
            }

        except asyncio.TimeoutError:
            latency = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "available": False,
                "latency": round(latency, 2),
                "version": None,
                "error": "Health check timeout",
                "metadata": {
                    "tool_name": self.name,
                    "cli_path": self.cli_path
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
                    "cli_path": self.cli_path,
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
            "provider": "anthropic",
            "cli_path": self.cli_path,
            "capabilities": [
                "code_generation",
                "code_editing",
                "code_analysis",
                "debugging",
                "refactoring",
                "testing",
                "documentation"
            ],
            "features": {
                "streaming": True,
                "file_context": True,
                "timeout_support": True,
                "working_directory": True,
                "json_parsing": self.enable_json_parsing,
                "retry_logic": True,
                "cancellation": True,
                "error_classification": True
            },
            "config": {
                "default_timeout": self.default_timeout,
                "default_working_dir": self.default_working_dir,
                "max_retries": self.max_retries,
                "retry_base_delay": self.retry_base_delay
            }
        }
