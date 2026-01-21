"""
Gemini CLI MCP Server

MCP-compatible server wrapper for Google's Gemini CLI tool.
Exposes Gemini CLI capabilities through the MCP protocol interface.
"""

import asyncio
import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
import structlog

from ..types import (
    ToolDefinition,
    ToolResult,
    ToolResultStatus,
    MCPServerStatus,
)

logger = structlog.get_logger()


class GeminiCLIServerConfig(BaseModel):
    """Configuration for the Gemini CLI MCP Server."""

    cli_path: str = Field(
        default="gemini",
        description="Path to the Gemini CLI executable"
    )
    model: str = Field(
        default="gemini-2.0-flash",
        description="Default Gemini model to use"
    )
    timeout: float = Field(
        default=300.0,
        ge=1.0,
        le=600.0,
        description="Default timeout in seconds for CLI operations"
    )
    api_key_env: str = Field(
        default="GOOGLE_API_KEY",
        description="Environment variable name containing the Google API key"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed operations"
    )
    retry_delay: float = Field(
        default=2.0,
        ge=0.1,
        le=30.0,
        description="Base delay between retry attempts in seconds"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for generation"
    )
    max_output_tokens: int = Field(
        default=8192,
        ge=1,
        le=32768,
        description="Maximum tokens in response"
    )
    working_directory: Optional[str] = Field(
        default=None,
        description="Working directory for CLI execution"
    )

    # Supported models
    SUPPORTED_MODELS: List[str] = [
        "gemini-pro",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-exp",
    ]

    model_config = {"extra": "forbid"}


class BaseMCPServer(ABC):
    """Abstract base class for MCP servers."""

    def __init__(self, name: str):
        """Initialize the MCP server.

        Args:
            name: Unique name for this server instance
        """
        self.name = name
        self._status = MCPServerStatus.DISCONNECTED
        self._initialized = False
        self._tools: Dict[str, ToolDefinition] = {}

    @property
    def status(self) -> MCPServerStatus:
        """Get the current server status."""
        return self._status

    @property
    def is_initialized(self) -> bool:
        """Check if the server has been initialized."""
        return self._initialized

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the server and verify availability.

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def list_tools(self) -> List[ToolDefinition]:
        """List all available tools.

        Returns:
            List of tool definitions
        """
        pass

    @abstractmethod
    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool.

        Args:
            name: Tool name to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the server and cleanup resources."""
        pass


class GeminiCLIMCPServer(BaseMCPServer):
    """MCP Server wrapper for Google's Gemini CLI.

    This server exposes Gemini CLI capabilities through the MCP protocol,
    providing tools for text generation, chat completion, and content analysis.

    Tools exposed:
        - gemini_cli.generate: Generate text with Gemini
        - gemini_cli.chat: Chat completion
        - gemini_cli.analyze: Analyze content

    Example usage:
        config = GeminiCLIServerConfig(model="gemini-2.0-flash")
        server = GeminiCLIMCPServer(config)

        await server.initialize()
        tools = await server.list_tools()

        result = await server.call_tool(
            "gemini_cli.generate",
            {"prompt": "Explain quantum computing in simple terms"}
        )

        await server.shutdown()
    """

    SERVER_NAME = "gemini_cli"

    def __init__(
        self,
        config: Optional[GeminiCLIServerConfig] = None,
        name: Optional[str] = None
    ):
        """Initialize the Gemini CLI MCP Server.

        Args:
            config: Server configuration (uses defaults if not provided)
            name: Optional server name override
        """
        super().__init__(name or self.SERVER_NAME)
        self.config = config or GeminiCLIServerConfig()
        self._api_key: Optional[str] = None
        self._cli_version: Optional[str] = None

        logger.info(
            "GeminiCLIMCPServer created",
            name=self.name,
            model=self.config.model,
            cli_path=self.config.cli_path
        )

    async def initialize(self) -> bool:
        """Initialize the server and verify Gemini CLI is available.

        Performs the following checks:
        1. Verifies API key is available
        2. Checks CLI executable exists and responds
        3. Validates configuration
        4. Registers available tools

        Returns:
            True if initialization successful, False otherwise
        """
        self._status = MCPServerStatus.CONNECTING

        try:
            logger.info("Initializing Gemini CLI MCP Server", name=self.name)

            # Check API key
            self._api_key = os.environ.get(self.config.api_key_env)
            if not self._api_key:
                logger.error(
                    "API key not found",
                    env_var=self.config.api_key_env
                )
                self._status = MCPServerStatus.ERROR
                return False

            # Verify CLI is available
            cli_available = await self._check_cli_availability()
            if not cli_available:
                logger.error("Gemini CLI not available", cli_path=self.config.cli_path)
                self._status = MCPServerStatus.ERROR
                return False

            # Validate model
            if self.config.model not in self.config.SUPPORTED_MODELS:
                logger.warning(
                    "Model not in supported list, may still work",
                    model=self.config.model,
                    supported=self.config.SUPPORTED_MODELS
                )

            # Register tools
            self._register_tools()

            self._initialized = True
            self._status = MCPServerStatus.CONNECTED

            logger.info(
                "Gemini CLI MCP Server initialized successfully",
                name=self.name,
                tool_count=len(self._tools),
                cli_version=self._cli_version
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to initialize Gemini CLI MCP Server",
                error=str(e),
                error_type=type(e).__name__
            )
            self._status = MCPServerStatus.ERROR
            return False

    async def _check_cli_availability(self) -> bool:
        """Check if Gemini CLI is available and get version.

        Returns:
            True if CLI is available, False otherwise
        """
        try:
            process = await asyncio.create_subprocess_exec(
                self.config.cli_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=10.0
            )

            if process.returncode == 0:
                self._cli_version = stdout.decode('utf-8').strip() or "unknown"
                logger.debug("CLI version check passed", version=self._cli_version)
                return True
            else:
                logger.warning(
                    "CLI version check failed",
                    returncode=process.returncode,
                    stderr=stderr.decode('utf-8')
                )
                return False

        except FileNotFoundError:
            logger.error("Gemini CLI not found", cli_path=self.config.cli_path)
            return False
        except asyncio.TimeoutError:
            logger.error("Gemini CLI version check timed out")
            return False
        except Exception as e:
            logger.error(
                "Error checking CLI availability",
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    def _register_tools(self) -> None:
        """Register all available tools."""

        # Tool: gemini_cli.generate
        self._tools["gemini_cli.generate"] = ToolDefinition(
            name="generate",
            description="Generate text using Gemini AI. Suitable for creative writing, code generation, explanations, and general text generation tasks.",
            server_name=self.name,
            input_schema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt or instructions for text generation"
                    },
                    "system_instructions": {
                        "type": "string",
                        "description": "Optional system-level instructions to guide the model's behavior"
                    },
                    "model": {
                        "type": "string",
                        "description": f"Model to use (default: {self.config.model})",
                        "enum": self.config.SUPPORTED_MODELS
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature (0.0-2.0)",
                        "minimum": 0.0,
                        "maximum": 2.0
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in response",
                        "minimum": 1,
                        "maximum": 32768
                    }
                },
                "required": ["prompt"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Generated text"},
                    "model": {"type": "string", "description": "Model used"},
                    "usage": {
                        "type": "object",
                        "properties": {
                            "prompt_tokens": {"type": "integer"},
                            "completion_tokens": {"type": "integer"},
                            "total_tokens": {"type": "integer"}
                        }
                    }
                }
            },
            metadata={
                "category": "text_generation",
                "capabilities": ["creative_writing", "code_generation", "explanations"]
            }
        )

        # Tool: gemini_cli.chat
        self._tools["gemini_cli.chat"] = ToolDefinition(
            name="chat",
            description="Chat completion with Gemini AI. Supports multi-turn conversations with message history.",
            server_name=self.name,
            input_schema={
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "description": "Array of chat messages",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {
                                    "type": "string",
                                    "enum": ["user", "assistant", "system"],
                                    "description": "Message role"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "Message content"
                                }
                            },
                            "required": ["role", "content"]
                        }
                    },
                    "model": {
                        "type": "string",
                        "description": f"Model to use (default: {self.config.model})"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature (0.0-2.0)"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in response"
                    }
                },
                "required": ["messages"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "response": {"type": "string", "description": "Assistant's response"},
                    "model": {"type": "string", "description": "Model used"}
                }
            },
            metadata={
                "category": "chat",
                "capabilities": ["multi_turn", "conversation"]
            }
        )

        # Tool: gemini_cli.analyze
        self._tools["gemini_cli.analyze"] = ToolDefinition(
            name="analyze",
            description="Analyze content using Gemini AI. Suitable for code review, text analysis, summarization, and content understanding.",
            server_name=self.name,
            input_schema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The content to analyze (code, text, etc.)"
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["code_review", "summarize", "explain", "critique", "security", "performance", "general"],
                        "description": "Type of analysis to perform",
                        "default": "general"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context or specific questions about the content"
                    },
                    "model": {
                        "type": "string",
                        "description": f"Model to use (default: {self.config.model})"
                    }
                },
                "required": ["content"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "analysis": {"type": "string", "description": "Analysis result"},
                    "analysis_type": {"type": "string", "description": "Type of analysis performed"},
                    "model": {"type": "string", "description": "Model used"}
                }
            },
            metadata={
                "category": "analysis",
                "capabilities": ["code_review", "summarization", "explanation", "security_analysis"]
            }
        )

        logger.debug(
            "Tools registered",
            tool_count=len(self._tools),
            tools=list(self._tools.keys())
        )

    async def list_tools(self) -> List[ToolDefinition]:
        """List all available tools.

        Returns:
            List of tool definitions

        Raises:
            RuntimeError: If server is not initialized
        """
        if not self._initialized:
            raise RuntimeError("Server not initialized. Call initialize() first.")

        return list(self._tools.values())

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool.

        Args:
            name: Tool name (e.g., "gemini_cli.generate" or just "generate")
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If server is not initialized
            ValueError: If tool name is invalid
        """
        if not self._initialized:
            raise RuntimeError("Server not initialized. Call initialize() first.")

        start_time = time.time()

        # Normalize tool name
        tool_path = name if name.startswith(f"{self.name}.") else f"{self.name}.{name}"

        if tool_path not in self._tools:
            return ToolResult(
                tool_path=tool_path,
                status=ToolResultStatus.ERROR,
                result=None,
                error=f"Unknown tool: {name}. Available tools: {list(self._tools.keys())}",
                execution_time=time.time() - start_time
            )

        logger.info(
            "Calling tool",
            tool=tool_path,
            arguments_keys=list(arguments.keys())
        )

        try:
            # Route to appropriate handler
            if tool_path == "gemini_cli.generate":
                result = await self._handle_generate(arguments)
            elif tool_path == "gemini_cli.chat":
                result = await self._handle_chat(arguments)
            elif tool_path == "gemini_cli.analyze":
                result = await self._handle_analyze(arguments)
            else:
                raise ValueError(f"No handler for tool: {tool_path}")

            execution_time = time.time() - start_time

            logger.info(
                "Tool execution completed",
                tool=tool_path,
                success=True,
                execution_time=execution_time
            )

            return ToolResult(
                tool_path=tool_path,
                status=ToolResultStatus.SUCCESS,
                result=result,
                error=None,
                execution_time=execution_time,
                metadata={
                    "model": arguments.get("model", self.config.model)
                }
            )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            logger.error(
                "Tool execution timed out",
                tool=tool_path,
                timeout=self.config.timeout
            )
            return ToolResult(
                tool_path=tool_path,
                status=ToolResultStatus.TIMEOUT,
                result=None,
                error=f"Execution timed out after {self.config.timeout} seconds",
                execution_time=execution_time
            )

        except asyncio.CancelledError:
            execution_time = time.time() - start_time
            logger.warning("Tool execution cancelled", tool=tool_path)
            return ToolResult(
                tool_path=tool_path,
                status=ToolResultStatus.CANCELLED,
                result=None,
                error="Execution was cancelled",
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "Tool execution failed",
                tool=tool_path,
                error=str(e),
                error_type=type(e).__name__
            )
            return ToolResult(
                tool_path=tool_path,
                status=ToolResultStatus.ERROR,
                result=None,
                error=str(e),
                execution_time=execution_time,
                metadata={"error_type": type(e).__name__}
            )

    async def _handle_generate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the generate tool.

        Args:
            arguments: Tool arguments containing prompt and optional parameters

        Returns:
            Generation result with text and metadata
        """
        prompt = arguments.get("prompt")
        if not prompt:
            raise ValueError("Missing required argument: prompt")

        system_instructions = arguments.get("system_instructions")
        model = arguments.get("model", self.config.model)
        temperature = arguments.get("temperature", self.config.temperature)
        max_tokens = arguments.get("max_tokens", self.config.max_output_tokens)

        # Build full prompt
        full_prompt = prompt
        if system_instructions:
            full_prompt = f"System: {system_instructions}\n\n{prompt}"

        # Execute CLI
        output = await self._execute_cli(
            prompt=full_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return {
            "text": output,
            "model": model,
            "usage": {
                "prompt_tokens": None,  # CLI doesn't provide token counts
                "completion_tokens": None,
                "total_tokens": None
            }
        }

    async def _handle_chat(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the chat tool.

        Args:
            arguments: Tool arguments containing messages and optional parameters

        Returns:
            Chat response with assistant's message
        """
        messages = arguments.get("messages")
        if not messages or not isinstance(messages, list):
            raise ValueError("Missing or invalid required argument: messages")

        model = arguments.get("model", self.config.model)
        temperature = arguments.get("temperature", self.config.temperature)
        max_tokens = arguments.get("max_tokens", self.config.max_output_tokens)

        # Build prompt from messages
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
            else:  # user
                prompt_parts.append(f"User: {content}")

        # Add prompt for assistant response
        prompt_parts.append("Assistant:")
        full_prompt = "\n\n".join(prompt_parts)

        # Execute CLI
        output = await self._execute_cli(
            prompt=full_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return {
            "response": output,
            "model": model
        }

    async def _handle_analyze(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the analyze tool.

        Args:
            arguments: Tool arguments containing content and optional parameters

        Returns:
            Analysis result
        """
        content = arguments.get("content")
        if not content:
            raise ValueError("Missing required argument: content")

        analysis_type = arguments.get("analysis_type", "general")
        context = arguments.get("context", "")
        model = arguments.get("model", self.config.model)

        # Build analysis prompt based on type
        analysis_prompts = {
            "code_review": "Please review the following code. Identify potential bugs, security issues, performance problems, and suggest improvements:",
            "summarize": "Please provide a concise summary of the following content:",
            "explain": "Please explain the following content in clear, simple terms:",
            "critique": "Please provide a critical analysis of the following content, identifying strengths and weaknesses:",
            "security": "Please analyze the following content for security vulnerabilities and concerns:",
            "performance": "Please analyze the following content for performance issues and optimization opportunities:",
            "general": "Please analyze the following content:"
        }

        base_prompt = analysis_prompts.get(analysis_type, analysis_prompts["general"])

        full_prompt = f"{base_prompt}\n\n```\n{content}\n```"
        if context:
            full_prompt += f"\n\nAdditional context/questions: {context}"

        # Execute CLI
        output = await self._execute_cli(
            prompt=full_prompt,
            model=model,
            temperature=0.3,  # Lower temperature for analysis
            max_tokens=self.config.max_output_tokens
        )

        return {
            "analysis": output,
            "analysis_type": analysis_type,
            "model": model
        }

    async def _execute_cli(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Execute Gemini CLI command with retry logic.

        Args:
            prompt: The prompt to send
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum output tokens

        Returns:
            CLI output text

        Raises:
            Exception: If all retries fail
        """
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                logger.debug(
                    "Executing Gemini CLI",
                    attempt=attempt + 1,
                    model=model,
                    prompt_length=len(prompt)
                )

                # Build command
                cmd = [
                    self.config.cli_path,
                    "--model", model,
                    "--temperature", str(temperature),
                    "--max-tokens", str(max_tokens),
                    prompt
                ]

                # Prepare environment
                env = os.environ.copy()
                if self._api_key:
                    env["GOOGLE_API_KEY"] = self._api_key

                # Execute subprocess
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.config.working_directory,
                    env=env
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout
                )

                stdout_text = stdout.decode('utf-8', errors='replace').strip()
                stderr_text = stderr.decode('utf-8', errors='replace').strip()

                # Check for errors
                if process.returncode != 0:
                    if "rate limit" in stderr_text.lower() or "quota" in stderr_text.lower():
                        raise Exception(f"Rate limit exceeded: {stderr_text}")
                    if "authentication" in stderr_text.lower() or "api key" in stderr_text.lower():
                        raise ValueError(f"Authentication error: {stderr_text}")
                    raise Exception(f"CLI error (exit code {process.returncode}): {stderr_text}")

                # Try to parse JSON output if present
                try:
                    json_output = json.loads(stdout_text)
                    if isinstance(json_output, dict) and "text" in json_output:
                        return json_output["text"]
                except (json.JSONDecodeError, TypeError):
                    pass

                return stdout_text

            except ValueError:
                # Don't retry authentication errors
                raise

            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.config.timeout} seconds"
                logger.warning(
                    "CLI timeout",
                    attempt=attempt + 1,
                    max_retries=self.config.max_retries
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "CLI execution failed",
                    error=str(e),
                    attempt=attempt + 1,
                    max_retries=self.config.max_retries
                )

            # Exponential backoff before retry
            if attempt < self.config.max_retries - 1:
                wait_time = self.config.retry_delay * (2 ** attempt)
                logger.debug("Waiting before retry", wait_seconds=wait_time)
                await asyncio.sleep(wait_time)

        raise Exception(f"Failed after {self.config.max_retries} attempts: {last_error}")

    async def shutdown(self) -> None:
        """Shutdown the server and cleanup resources."""
        logger.info("Shutting down Gemini CLI MCP Server", name=self.name)

        self._initialized = False
        self._status = MCPServerStatus.DISCONNECTED
        self._tools.clear()
        self._api_key = None

        logger.info("Gemini CLI MCP Server shutdown complete", name=self.name)

    def get_server_info(self) -> Dict[str, Any]:
        """Get information about this server.

        Returns:
            Dictionary containing server information
        """
        return {
            "name": self.name,
            "type": "gemini_cli",
            "status": self._status.value,
            "initialized": self._initialized,
            "cli_version": self._cli_version,
            "config": {
                "model": self.config.model,
                "cli_path": self.config.cli_path,
                "timeout": self.config.timeout,
                "max_retries": self.config.max_retries
            },
            "tools": list(self._tools.keys()),
            "capabilities": [
                "text_generation",
                "chat_completion",
                "content_analysis",
                "code_review"
            ]
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the server.

        Returns:
            Health check result with status and details
        """
        start_time = time.time()

        try:
            if not self._initialized:
                return {
                    "status": "unhealthy",
                    "available": False,
                    "latency": None,
                    "error": "Server not initialized"
                }

            # Check CLI availability
            cli_available = await self._check_cli_availability()
            latency = (time.time() - start_time) * 1000

            if cli_available:
                return {
                    "status": "healthy",
                    "available": True,
                    "latency": round(latency, 2),
                    "cli_version": self._cli_version,
                    "model": self.config.model,
                    "tool_count": len(self._tools)
                }
            else:
                return {
                    "status": "unhealthy",
                    "available": False,
                    "latency": round(latency, 2),
                    "error": "CLI not responding"
                }

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "available": False,
                "latency": round(latency, 2),
                "error": str(e)
            }
