"""
Claude Code MCP Server

MCP-compatible server wrapper for Claude Code CLI.
Exposes Claude Code functionality as MCP tools for use by the GarageSwarm platform.
"""

import asyncio
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ..types import (
    ToolDefinition,
    ToolResult,
    ToolResultStatus,
    MCPServerStatus,
)


logger = logging.getLogger(__name__)


class ClaudeCodeError(Exception):
    """Base exception for Claude Code MCP server errors."""

    def __init__(
        self,
        message: str,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.details = details or {}


class ClaudeCodeTimeoutError(ClaudeCodeError):
    """Timeout error for Claude Code execution."""

    def __init__(self, timeout: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Claude Code execution timed out after {timeout} seconds",
            retryable=False,
            details=details
        )
        self.timeout = timeout


class ClaudeCodeCLINotFoundError(ClaudeCodeError):
    """Claude Code CLI not found error."""

    def __init__(self, cli_path: str):
        super().__init__(
            f"Claude Code CLI not found at: {cli_path}",
            retryable=False,
            details={"cli_path": cli_path}
        )


class ClaudeCodeExecutionError(ClaudeCodeError):
    """Claude Code execution error."""

    def __init__(
        self,
        message: str,
        exit_code: int,
        stderr: str,
        retryable: bool = False
    ):
        super().__init__(
            message,
            retryable=retryable,
            details={"exit_code": exit_code, "stderr": stderr}
        )
        self.exit_code = exit_code
        self.stderr = stderr


class ClaudeCodeServerConfig(BaseModel):
    """Configuration for Claude Code MCP Server."""

    cli_path: str = Field(
        default="claude",
        description="Path to Claude Code CLI binary"
    )
    working_directory: Optional[str] = Field(
        default=None,
        description="Default working directory for Claude Code execution"
    )
    timeout: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Default timeout in seconds for tool execution"
    )
    allowed_tools: List[str] = Field(
        default_factory=lambda: [
            "claude_code.execute",
            "claude_code.chat",
            "claude_code.analyze"
        ],
        description="List of allowed tool names"
    )
    env_vars: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variables for Claude Code"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for retryable errors"
    )
    retry_base_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Base delay in seconds for retry backoff"
    )
    enable_json_parsing: bool = Field(
        default=True,
        description="Enable JSON parsing from Claude Code output"
    )
    dangerously_skip_permissions: bool = Field(
        default=False,
        description="Skip permission prompts (use with caution)"
    )

    model_config = {"extra": "forbid"}


class ClaudeCodeMCPServer:
    """
    MCP Server wrapper for Claude Code CLI.

    This server exposes Claude Code functionality as MCP-compatible tools
    that can be used by the GarageSwarm platform for AI-powered coding tasks.

    Tools exposed:
    - claude_code.execute: Execute a prompt with Claude Code
    - claude_code.chat: Interactive chat session with context
    - claude_code.analyze: Analyze code/files

    Example usage:
        config = ClaudeCodeServerConfig(
            cli_path="claude",
            working_directory="/path/to/project",
            timeout=300
        )
        server = ClaudeCodeMCPServer(config)
        await server.initialize()
        tools = await server.list_tools()
        result = await server.call_tool(
            "claude_code.execute",
            {"prompt": "Create a hello world function"}
        )
        await server.shutdown()
    """

    # Server identification
    SERVER_NAME = "claude_code"
    SERVER_VERSION = "1.0.0"

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

    def __init__(self, config: Optional[ClaudeCodeServerConfig] = None):
        """
        Initialize Claude Code MCP Server.

        Args:
            config: Server configuration. Uses defaults if not provided.
        """
        self.config = config or ClaudeCodeServerConfig()
        self._status = MCPServerStatus.DISCONNECTED
        self._cli_version: Optional[str] = None
        self._tools: Dict[str, ToolDefinition] = {}
        self._current_process: Optional[asyncio.subprocess.Process] = None
        self._cancelled = False
        self._initialized = False

        logger.info(
            "ClaudeCodeMCPServer created",
            extra={
                "cli_path": self.config.cli_path,
                "working_directory": self.config.working_directory,
                "timeout": self.config.timeout,
            }
        )

    @property
    def status(self) -> MCPServerStatus:
        """Get current server status."""
        return self._status

    @property
    def is_initialized(self) -> bool:
        """Check if server is initialized and ready."""
        return self._initialized and self._status == MCPServerStatus.CONNECTED

    async def initialize(self) -> bool:
        """
        Initialize the MCP server.

        Verifies that Claude Code CLI is available and sets up the server.

        Returns:
            True if initialization successful, False otherwise.

        Raises:
            ClaudeCodeCLINotFoundError: If Claude Code CLI is not found.
        """
        logger.info("Initializing ClaudeCodeMCPServer")
        self._status = MCPServerStatus.CONNECTING

        try:
            # Check if CLI exists and is executable
            cli_found = await self._verify_cli()
            if not cli_found:
                self._status = MCPServerStatus.ERROR
                raise ClaudeCodeCLINotFoundError(self.config.cli_path)

            # Get CLI version
            self._cli_version = await self._get_cli_version()

            # Register available tools
            self._register_tools()

            self._status = MCPServerStatus.CONNECTED
            self._initialized = True

            logger.info(
                "ClaudeCodeMCPServer initialized successfully",
                extra={
                    "version": self._cli_version,
                    "tools_count": len(self._tools),
                }
            )

            return True

        except ClaudeCodeError:
            self._status = MCPServerStatus.ERROR
            raise

        except Exception as e:
            self._status = MCPServerStatus.ERROR
            logger.error(f"Failed to initialize ClaudeCodeMCPServer: {e}")
            raise ClaudeCodeError(
                f"Initialization failed: {str(e)}",
                retryable=False,
                details={"exception_type": type(e).__name__}
            )

    async def list_tools(self) -> List[ToolDefinition]:
        """
        List all available tools exposed by this MCP server.

        Returns:
            List of tool definitions.

        Raises:
            ClaudeCodeError: If server is not initialized.
        """
        if not self._initialized:
            raise ClaudeCodeError(
                "Server not initialized. Call initialize() first.",
                retryable=False
            )

        # Filter tools based on allowed_tools config
        allowed = set(self.config.allowed_tools)
        return [
            tool for tool in self._tools.values()
            if tool.tool_path in allowed or tool.name in allowed
        ]

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> ToolResult:
        """
        Execute a tool by name with the given arguments.

        Args:
            name: Tool name (e.g., "claude_code.execute" or "execute")
            arguments: Tool arguments as a dictionary

        Returns:
            ToolResult containing execution result or error.

        Raises:
            ClaudeCodeError: If tool not found or execution fails.
        """
        start_time = time.time()

        if not self._initialized:
            raise ClaudeCodeError(
                "Server not initialized. Call initialize() first.",
                retryable=False
            )

        # Normalize tool name (accept both "execute" and "claude_code.execute")
        tool_name = name if "." in name else f"{self.SERVER_NAME}.{name}"

        # Check if tool is allowed
        if tool_name not in self.config.allowed_tools and name not in self.config.allowed_tools:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_path=tool_name,
                status=ToolResultStatus.ERROR,
                result=None,
                error=f"Tool '{tool_name}' is not in allowed_tools list",
                execution_time=execution_time,
                metadata={"allowed_tools": self.config.allowed_tools}
            )

        # Get tool definition
        tool = self._tools.get(tool_name)
        if not tool:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_path=tool_name,
                status=ToolResultStatus.ERROR,
                result=None,
                error=f"Tool '{tool_name}' not found",
                execution_time=execution_time,
                metadata={"available_tools": list(self._tools.keys())}
            )

        # Route to appropriate handler
        try:
            handler_name = name.split(".")[-1] if "." in name else name
            handler = self._get_tool_handler(handler_name)

            result = await handler(arguments)
            execution_time = time.time() - start_time

            return ToolResult(
                tool_path=tool_name,
                status=ToolResultStatus.SUCCESS,
                result=result,
                error=None,
                execution_time=execution_time,
                metadata={
                    "cli_version": self._cli_version,
                    "working_directory": self.config.working_directory,
                }
            )

        except asyncio.CancelledError:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_path=tool_name,
                status=ToolResultStatus.CANCELLED,
                result=None,
                error="Execution was cancelled",
                execution_time=execution_time,
            )

        except ClaudeCodeTimeoutError as e:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_path=tool_name,
                status=ToolResultStatus.TIMEOUT,
                result=None,
                error=str(e),
                execution_time=execution_time,
                metadata=e.details
            )

        except ClaudeCodeError as e:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_path=tool_name,
                status=ToolResultStatus.ERROR,
                result=None,
                error=str(e),
                execution_time=execution_time,
                metadata={"retryable": e.retryable, **e.details}
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Unexpected error in tool {tool_name}: {e}")
            return ToolResult(
                tool_path=tool_name,
                status=ToolResultStatus.ERROR,
                result=None,
                error=f"Unexpected error: {str(e)}",
                execution_time=execution_time,
                metadata={"exception_type": type(e).__name__}
            )

    async def shutdown(self) -> None:
        """
        Shutdown the MCP server and cleanup resources.

        Terminates any running processes and resets server state.
        """
        logger.info("Shutting down ClaudeCodeMCPServer")

        # Cancel any running process
        if self._current_process and self._current_process.returncode is None:
            self._cancelled = True
            await self._terminate_process(self._current_process)

        self._status = MCPServerStatus.DISCONNECTED
        self._initialized = False
        self._tools.clear()

        logger.info("ClaudeCodeMCPServer shutdown complete")

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the server.

        Returns:
            Dictionary with health status information.
        """
        start_time = time.time()

        try:
            is_available = await self._verify_cli()
            latency = (time.time() - start_time) * 1000

            return {
                "status": "healthy" if is_available else "unhealthy",
                "available": is_available,
                "latency_ms": round(latency, 2),
                "version": self._cli_version,
                "initialized": self._initialized,
                "server_name": self.SERVER_NAME,
                "tools_count": len(self._tools),
                "error": None if is_available else "CLI not available"
            }

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "available": False,
                "latency_ms": round(latency, 2),
                "version": None,
                "initialized": self._initialized,
                "server_name": self.SERVER_NAME,
                "tools_count": 0,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # Tool Handlers
    # -------------------------------------------------------------------------

    async def _handle_execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the 'execute' tool.

        Execute a prompt with Claude Code CLI.

        Args:
            arguments: Tool arguments containing:
                - prompt (required): The prompt/instructions for Claude Code
                - working_directory (optional): Working directory for execution
                - timeout (optional): Timeout in seconds
                - files (optional): List of file paths to include as context
                - output_format (optional): Output format (text, json)

        Returns:
            Dictionary with execution result.
        """
        prompt = arguments.get("prompt")
        if not prompt:
            raise ClaudeCodeError("'prompt' argument is required", retryable=False)

        working_dir = arguments.get("working_directory", self.config.working_directory)
        timeout = arguments.get("timeout", self.config.timeout)
        files = arguments.get("files", [])
        output_format = arguments.get("output_format", "text")

        return await self._execute_claude_code(
            prompt=prompt,
            working_dir=working_dir,
            timeout=timeout,
            files=files,
            output_format=output_format,
            mode="print"
        )

    async def _handle_chat(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the 'chat' tool.

        Start or continue a chat session with Claude Code.

        Args:
            arguments: Tool arguments containing:
                - message (required): The message to send
                - session_id (optional): Session ID to continue a conversation
                - working_directory (optional): Working directory
                - timeout (optional): Timeout in seconds
                - context (optional): Additional context to include

        Returns:
            Dictionary with chat response.
        """
        message = arguments.get("message")
        if not message:
            raise ClaudeCodeError("'message' argument is required", retryable=False)

        working_dir = arguments.get("working_directory", self.config.working_directory)
        timeout = arguments.get("timeout", self.config.timeout)
        context = arguments.get("context", "")
        session_id = arguments.get("session_id")

        # Build the chat prompt with context if provided
        chat_prompt = message
        if context:
            chat_prompt = f"Context:\n{context}\n\nMessage:\n{message}"

        result = await self._execute_claude_code(
            prompt=chat_prompt,
            working_dir=working_dir,
            timeout=timeout,
            files=[],
            output_format="text",
            mode="print",
            additional_args=["--continue"] if session_id else []
        )

        # Add session info to result
        result["session_id"] = session_id or "new"
        return result

    async def _handle_analyze(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the 'analyze' tool.

        Analyze code or files using Claude Code.

        Args:
            arguments: Tool arguments containing:
                - target (required): File path, directory, or code to analyze
                - analysis_type (optional): Type of analysis (review, security, performance, architecture)
                - working_directory (optional): Working directory
                - timeout (optional): Timeout in seconds
                - output_format (optional): Output format (text, json)

        Returns:
            Dictionary with analysis result.
        """
        target = arguments.get("target")
        if not target:
            raise ClaudeCodeError("'target' argument is required", retryable=False)

        analysis_type = arguments.get("analysis_type", "review")
        working_dir = arguments.get("working_directory", self.config.working_directory)
        timeout = arguments.get("timeout", self.config.timeout)
        output_format = arguments.get("output_format", "json")

        # Build analysis prompt based on type
        analysis_prompts = {
            "review": f"Please review the following code/file and provide feedback on code quality, potential issues, and suggestions for improvement:\n\n{target}",
            "security": f"Please perform a security analysis on the following code/file. Identify potential security vulnerabilities, risks, and provide recommendations:\n\n{target}",
            "performance": f"Please analyze the performance of the following code/file. Identify potential performance issues, bottlenecks, and optimization opportunities:\n\n{target}",
            "architecture": f"Please analyze the architecture and design of the following code/file. Evaluate patterns, structure, and provide architectural feedback:\n\n{target}",
        }

        prompt = analysis_prompts.get(
            analysis_type,
            f"Please analyze the following:\n\n{target}"
        )

        # Check if target is a file path
        files = []
        if os.path.exists(target):
            files = [target]
            prompt = f"Please perform a {analysis_type} analysis on the provided file(s)."

        result = await self._execute_claude_code(
            prompt=prompt,
            working_dir=working_dir,
            timeout=timeout,
            files=files,
            output_format=output_format,
            mode="print"
        )

        result["analysis_type"] = analysis_type
        return result

    # -------------------------------------------------------------------------
    # Internal Methods
    # -------------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register all available tools."""
        tools = [
            ToolDefinition(
                name="execute",
                description="Execute a prompt with Claude Code CLI. Use this for general coding tasks, file operations, and code generation.",
                server_name=self.SERVER_NAME,
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The prompt/instructions for Claude Code to execute"
                        },
                        "working_directory": {
                            "type": "string",
                            "description": "Working directory for execution (optional)"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (optional, default: 300)"
                        },
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of file paths to include as context (optional)"
                        },
                        "output_format": {
                            "type": "string",
                            "enum": ["text", "json"],
                            "description": "Output format (optional, default: text)"
                        }
                    },
                    "required": ["prompt"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "output": {"type": "string"},
                        "parsed_json": {"type": "object"},
                        "error": {"type": "string"},
                        "metadata": {"type": "object"}
                    }
                },
                metadata={"category": "execution"}
            ),
            ToolDefinition(
                name="chat",
                description="Interactive chat session with Claude Code. Use this for conversational interactions and follow-up questions.",
                server_name=self.SERVER_NAME,
                input_schema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The message to send to Claude Code"
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Session ID to continue a conversation (optional)"
                        },
                        "working_directory": {
                            "type": "string",
                            "description": "Working directory (optional)"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (optional, default: 300)"
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context to include (optional)"
                        }
                    },
                    "required": ["message"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "output": {"type": "string"},
                        "session_id": {"type": "string"},
                        "error": {"type": "string"},
                        "metadata": {"type": "object"}
                    }
                },
                metadata={"category": "chat"}
            ),
            ToolDefinition(
                name="analyze",
                description="Analyze code or files using Claude Code. Supports various analysis types including code review, security, performance, and architecture analysis.",
                server_name=self.SERVER_NAME,
                input_schema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "File path, directory path, or code string to analyze"
                        },
                        "analysis_type": {
                            "type": "string",
                            "enum": ["review", "security", "performance", "architecture"],
                            "description": "Type of analysis to perform (optional, default: review)"
                        },
                        "working_directory": {
                            "type": "string",
                            "description": "Working directory (optional)"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (optional, default: 300)"
                        },
                        "output_format": {
                            "type": "string",
                            "enum": ["text", "json"],
                            "description": "Output format (optional, default: json)"
                        }
                    },
                    "required": ["target"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "output": {"type": "string"},
                        "parsed_json": {"type": "object"},
                        "analysis_type": {"type": "string"},
                        "error": {"type": "string"},
                        "metadata": {"type": "object"}
                    }
                },
                metadata={"category": "analysis"}
            ),
        ]

        for tool in tools:
            tool_path = f"{self.SERVER_NAME}.{tool.name}"
            self._tools[tool_path] = tool

        logger.debug(f"Registered {len(tools)} tools")

    def _get_tool_handler(self, tool_name: str):
        """Get the handler function for a tool."""
        handlers = {
            "execute": self._handle_execute,
            "chat": self._handle_chat,
            "analyze": self._handle_analyze,
        }

        handler = handlers.get(tool_name)
        if not handler:
            raise ClaudeCodeError(
                f"No handler found for tool: {tool_name}",
                retryable=False
            )
        return handler

    async def _verify_cli(self) -> bool:
        """Verify that Claude Code CLI is available."""
        try:
            # First check with shutil.which for better cross-platform support
            cli_found = shutil.which(self.config.cli_path)
            if not cli_found:
                # Try running the command directly
                process = await asyncio.create_subprocess_exec(
                    self.config.cli_path,
                    "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await asyncio.wait_for(process.wait(), timeout=10.0)
                return process.returncode == 0

            return True

        except FileNotFoundError:
            return False
        except asyncio.TimeoutError:
            logger.warning("CLI verification timed out")
            return False
        except Exception as e:
            logger.warning(f"CLI verification failed: {e}")
            return False

    async def _get_cli_version(self) -> Optional[str]:
        """Get the version of Claude Code CLI."""
        try:
            process = await asyncio.create_subprocess_exec(
                self.config.cli_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=10.0
            )

            if process.returncode == 0 and stdout:
                return stdout.decode("utf-8", errors="replace").strip()

            return None

        except Exception as e:
            logger.warning(f"Failed to get CLI version: {e}")
            return None

    async def _execute_claude_code(
        self,
        prompt: str,
        working_dir: Optional[str],
        timeout: int,
        files: List[str],
        output_format: str,
        mode: str = "print",
        additional_args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute Claude Code CLI with the given parameters.

        Args:
            prompt: The prompt to send to Claude Code
            working_dir: Working directory for execution
            timeout: Timeout in seconds
            files: List of file paths to include
            output_format: Output format (text, json)
            mode: Execution mode (print, interactive)
            additional_args: Additional CLI arguments

        Returns:
            Dictionary with execution result.
        """
        start_time = time.time()
        self._cancelled = False

        # Build command
        cmd = [self.config.cli_path]

        # Add print mode for non-interactive execution
        if mode == "print":
            cmd.append("-p")

        # Add dangerously skip permissions if configured
        if self.config.dangerously_skip_permissions:
            cmd.append("--dangerously-skip-permissions")

        # Add output format
        if output_format == "json":
            cmd.extend(["--output-format", "json"])

        # Add additional arguments
        if additional_args:
            cmd.extend(additional_args)

        # Add file paths if provided
        for file_path in files:
            if os.path.exists(file_path):
                cmd.extend(["--file", file_path])
            else:
                logger.warning(f"File not found: {file_path}")

        # Prepare environment
        env = os.environ.copy()
        env.update(self.config.env_vars)

        logger.debug(
            f"Executing Claude Code",
            extra={
                "command": " ".join(cmd),
                "working_dir": working_dir,
                "timeout": timeout,
            }
        )

        try:
            # Create subprocess with stdin for prompt
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=env
            )

            self._current_process = process

            # Send prompt via stdin
            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(input=prompt.encode("utf-8")),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                await self._terminate_process(process)
                raise ClaudeCodeTimeoutError(
                    timeout=timeout,
                    details={"duration": time.time() - start_time}
                )
            finally:
                self._current_process = None

            # Check if cancelled
            if self._cancelled:
                raise ClaudeCodeError(
                    "Execution was cancelled",
                    retryable=False,
                    details={"duration": time.time() - start_time}
                )

            duration = time.time() - start_time
            stdout = stdout_data.decode("utf-8", errors="replace")
            stderr = stderr_data.decode("utf-8", errors="replace")

            # Check for errors
            if process.returncode != 0:
                retryable = self._is_retryable_error(process.returncode, stderr)
                error_msg = f"Claude Code failed with exit code {process.returncode}"
                if stderr:
                    error_msg += f": {stderr[:500]}"

                raise ClaudeCodeExecutionError(
                    error_msg,
                    exit_code=process.returncode,
                    stderr=stderr,
                    retryable=retryable
                )

            # Parse JSON from output if enabled
            parsed_json = None
            if self.config.enable_json_parsing and stdout:
                parsed_json = self._parse_json_output(stdout)

            logger.info(
                f"Claude Code execution completed",
                extra={
                    "duration": duration,
                    "exit_code": process.returncode,
                    "has_json": parsed_json is not None,
                }
            )

            return {
                "success": True,
                "output": stdout,
                "parsed_json": parsed_json,
                "error": None,
                "metadata": {
                    "duration": duration,
                    "exit_code": process.returncode,
                    "working_directory": working_dir,
                    "files_included": len(files),
                }
            }

        except ClaudeCodeError:
            raise

        except FileNotFoundError:
            raise ClaudeCodeCLINotFoundError(self.config.cli_path)

        except Exception as e:
            duration = time.time() - start_time
            raise ClaudeCodeError(
                f"Execution error: {str(e)}",
                retryable=False,
                details={
                    "exception_type": type(e).__name__,
                    "duration": duration
                }
            )

    async def _terminate_process(self, process: asyncio.subprocess.Process) -> None:
        """Terminate a process gracefully, then force kill if needed."""
        try:
            process.terminate()

            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
                logger.debug("Process terminated gracefully")
            except asyncio.TimeoutError:
                logger.warning("Forcefully killing process")
                process.kill()
                await process.wait()

        except Exception as e:
            logger.error(f"Error terminating process: {e}")

    def _is_retryable_error(self, exit_code: int, stderr: str) -> bool:
        """Determine if an error is retryable based on exit code and stderr."""
        if exit_code in self.RETRYABLE_EXIT_CODES:
            return True

        if stderr:
            stderr_lower = stderr.lower()
            for pattern in self.RETRYABLE_ERROR_PATTERNS:
                if pattern in stderr_lower:
                    return True

        return False

    def _parse_json_output(self, output: str) -> Optional[Any]:
        """Parse JSON from Claude Code output."""
        if not output or not output.strip():
            return None

        # Strategy 1: Try parsing entire output as JSON
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from JSON code blocks
        json_marker = "```json"
        if json_marker in output:
            try:
                start_idx = output.find(json_marker)
                if start_idx != -1:
                    start_idx += len(json_marker)
                    end_idx = output.find("```", start_idx)
                    if end_idx != -1:
                        json_str = output[start_idx:end_idx].strip()
                        return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                pass

        # Strategy 3: Find JSON objects in output
        try:
            for i, char in enumerate(output):
                if char in "{[":
                    end_char = "}" if char == "{" else "]"
                    depth = 0
                    for j, c in enumerate(output[i:]):
                        if c == char:
                            depth += 1
                        elif c == end_char:
                            depth -= 1
                            if depth == 0:
                                json_str = output[i:i + j + 1]
                                try:
                                    return json.loads(json_str)
                                except json.JSONDecodeError:
                                    break
                    break
        except Exception:
            pass

        return None

    async def cancel_execution(self) -> bool:
        """
        Cancel any ongoing execution.

        Returns:
            True if cancellation was initiated, False if no execution was running.
        """
        if self._current_process and self._current_process.returncode is None:
            logger.info("Cancelling Claude Code execution")
            self._cancelled = True
            await self._terminate_process(self._current_process)
            return True
        return False

    def get_server_info(self) -> Dict[str, Any]:
        """
        Get information about this MCP server.

        Returns:
            Dictionary with server information.
        """
        return {
            "name": self.SERVER_NAME,
            "version": self.SERVER_VERSION,
            "status": self._status.value,
            "initialized": self._initialized,
            "cli_version": self._cli_version,
            "cli_path": self.config.cli_path,
            "working_directory": self.config.working_directory,
            "timeout": self.config.timeout,
            "tools_count": len(self._tools),
            "allowed_tools": self.config.allowed_tools,
            "capabilities": [
                "code_generation",
                "code_editing",
                "code_analysis",
                "debugging",
                "refactoring",
                "testing",
                "documentation"
            ]
        }
