"""Ollama MCP Server - Model Context Protocol wrapper for Ollama API

This module provides an MCP-compatible server that exposes Ollama's
capabilities as tools that can be invoked by MCP clients.

MCP (Model Context Protocol) is a standard for AI tool integration
that allows uniform access to different AI capabilities.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp


class MCPToolType(str, Enum):
    """MCP tool types supported by the server"""
    GENERATE = "ollama.generate"
    CHAT = "ollama.chat"
    LIST_MODELS = "ollama.list_models"


@dataclass
class OllamaServerConfig:
    """Configuration for Ollama MCP Server

    Attributes:
        host: Ollama API URL (default: http://localhost:11434)
        default_model: Default model to use (default: llama3.2:1b)
        timeout: Request timeout in seconds (default: 300)
        connect_timeout: Connection timeout in seconds (default: 10)
        max_retries: Maximum retry attempts for failed requests (default: 3)
        retry_delay: Delay between retries in seconds (default: 1.0)
    """
    host: str = "http://localhost:11434"
    default_model: str = "llama3.2:1b"
    timeout: float = 300.0
    connect_timeout: float = 10.0
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class MCPTool:
    """Represents an MCP tool definition

    Attributes:
        name: Tool name (e.g., "ollama.generate")
        description: Human-readable description of the tool
        input_schema: JSON Schema defining the tool's input parameters
    """
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP tool format"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


@dataclass
class MCPToolResult:
    """Result from an MCP tool call

    Attributes:
        content: List of content blocks (text, images, etc.)
        is_error: Whether the result represents an error
        metadata: Additional metadata about the execution
    """
    content: List[Dict[str, Any]] = field(default_factory=list)
    is_error: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP result format"""
        return {
            "content": self.content,
            "isError": self.is_error,
            "_meta": self.metadata
        }

    @classmethod
    def text(cls, text: str, metadata: Optional[Dict[str, Any]] = None) -> "MCPToolResult":
        """Create a text result"""
        return cls(
            content=[{"type": "text", "text": text}],
            is_error=False,
            metadata=metadata or {}
        )

    @classmethod
    def error(cls, message: str, metadata: Optional[Dict[str, Any]] = None) -> "MCPToolResult":
        """Create an error result"""
        return cls(
            content=[{"type": "text", "text": message}],
            is_error=True,
            metadata=metadata or {}
        )


class OllamaMCPServer:
    """MCP Server wrapper for Ollama API

    This class implements the MCP server interface for Ollama,
    exposing text generation, chat, and model management capabilities
    as MCP tools.

    Usage:
        config = OllamaServerConfig(host="http://localhost:11434")
        server = OllamaMCPServer(config)
        await server.initialize()

        tools = await server.list_tools()
        result = await server.call_tool("ollama.generate", {"prompt": "Hello!"})

        await server.shutdown()
    """

    # API endpoints
    GENERATE_ENDPOINT = "/api/generate"
    CHAT_ENDPOINT = "/api/chat"
    TAGS_ENDPOINT = "/api/tags"

    def __init__(self, config: Optional[OllamaServerConfig] = None):
        """Initialize Ollama MCP Server

        Args:
            config: Server configuration. Uses defaults if not provided.
        """
        self.config = config or OllamaServerConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        self._initialized: bool = False
        self._server_info: Dict[str, Any] = {}

        # Define available tools
        self._tools: Dict[str, MCPTool] = {
            MCPToolType.GENERATE: MCPTool(
                name=MCPToolType.GENERATE,
                description="Generate text using Ollama. Suitable for single-turn text generation tasks.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The prompt text to generate from"
                        },
                        "model": {
                            "type": "string",
                            "description": f"Model to use (default: {self.config.default_model})"
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Sampling temperature (0.0-2.0, default: 0.7)",
                            "minimum": 0.0,
                            "maximum": 2.0
                        },
                        "max_tokens": {
                            "type": "integer",
                            "description": "Maximum tokens to generate",
                            "minimum": 1
                        },
                        "system": {
                            "type": "string",
                            "description": "System prompt to prepend"
                        }
                    },
                    "required": ["prompt"]
                }
            ),
            MCPToolType.CHAT: MCPTool(
                name=MCPToolType.CHAT,
                description="Chat completion using Ollama. Suitable for multi-turn conversations.",
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
                                        "enum": ["system", "user", "assistant"],
                                        "description": "Role of the message sender"
                                    },
                                    "content": {
                                        "type": "string",
                                        "description": "Content of the message"
                                    }
                                },
                                "required": ["role", "content"]
                            }
                        },
                        "model": {
                            "type": "string",
                            "description": f"Model to use (default: {self.config.default_model})"
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Sampling temperature (0.0-2.0, default: 0.7)",
                            "minimum": 0.0,
                            "maximum": 2.0
                        },
                        "max_tokens": {
                            "type": "integer",
                            "description": "Maximum tokens to generate",
                            "minimum": 1
                        }
                    },
                    "required": ["messages"]
                }
            ),
            MCPToolType.LIST_MODELS: MCPTool(
                name=MCPToolType.LIST_MODELS,
                description="List all available Ollama models on the server.",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        }

    async def initialize(self) -> Dict[str, Any]:
        """Initialize the MCP server and connect to Ollama

        Returns:
            Server info dictionary with capabilities and status

        Raises:
            ConnectionError: If unable to connect to Ollama
        """
        if self._initialized:
            return self._server_info

        # Create aiohttp session with configured timeouts
        timeout = aiohttp.ClientTimeout(
            total=self.config.timeout,
            connect=self.config.connect_timeout
        )
        self._session = aiohttp.ClientSession(timeout=timeout)

        # Verify Ollama is accessible
        try:
            health = await self._check_ollama_health()
            if not health["available"]:
                raise ConnectionError(
                    f"Ollama is not available at {self.config.host}: {health.get('error', 'Unknown error')}"
                )
        except Exception as e:
            await self._session.close()
            self._session = None
            raise ConnectionError(f"Failed to connect to Ollama: {str(e)}")

        self._initialized = True
        self._server_info = {
            "name": "ollama-mcp-server",
            "version": "0.1.0",
            "protocol_version": "2024-11-05",
            "capabilities": {
                "tools": True,
                "resources": False,
                "prompts": False,
                "logging": False
            },
            "ollama": {
                "host": self.config.host,
                "default_model": self.config.default_model,
                "available_models": health.get("models", [])
            }
        }

        return self._server_info

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools

        Returns:
            List of tool definitions in MCP format

        Raises:
            RuntimeError: If server is not initialized
        """
        self._ensure_initialized()
        return [tool.to_dict() for tool in self._tools.values()]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Execute a tool by name

        Args:
            name: Tool name (e.g., "ollama.generate")
            arguments: Tool-specific arguments

        Returns:
            MCPToolResult with the tool output

        Raises:
            RuntimeError: If server is not initialized
            ValueError: If tool name is unknown
        """
        self._ensure_initialized()

        start_time = time.time()

        try:
            if name == MCPToolType.GENERATE:
                return await self._tool_generate(arguments)
            elif name == MCPToolType.CHAT:
                return await self._tool_chat(arguments)
            elif name == MCPToolType.LIST_MODELS:
                return await self._tool_list_models(arguments)
            else:
                return MCPToolResult.error(
                    f"Unknown tool: {name}. Available tools: {list(self._tools.keys())}",
                    metadata={"duration": time.time() - start_time}
                )
        except Exception as e:
            return MCPToolResult.error(
                f"Tool execution failed: {str(e)}",
                metadata={
                    "duration": time.time() - start_time,
                    "error_type": type(e).__name__
                }
            )

    async def shutdown(self) -> None:
        """Cleanup and close connections"""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        self._initialized = False
        self._server_info = {}

    # ==================== Tool Implementations ====================

    async def _tool_generate(self, arguments: Dict[str, Any]) -> MCPToolResult:
        """Execute ollama.generate tool

        Args:
            arguments: Tool arguments including prompt, model, etc.

        Returns:
            MCPToolResult with generated text
        """
        start_time = time.time()

        prompt = arguments.get("prompt")
        if not prompt:
            return MCPToolResult.error("Missing required argument: prompt")

        model = arguments.get("model", self.config.default_model)
        temperature = arguments.get("temperature", 0.7)
        max_tokens = arguments.get("max_tokens")
        system = arguments.get("system")

        url = f"{self.config.host.rstrip('/')}{self.GENERATE_ENDPOINT}"

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        if system:
            payload["system"] = system

        result = await self._make_request_with_retry(url, payload)

        if result.get("error"):
            return MCPToolResult.error(
                result["error"],
                metadata={
                    "model": model,
                    "duration": time.time() - start_time
                }
            )

        response_text = result.get("response", "")

        return MCPToolResult.text(
            response_text,
            metadata={
                "model": model,
                "duration": time.time() - start_time,
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "completion_tokens": result.get("eval_count", 0),
                "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
                "load_duration_ns": result.get("load_duration", 0),
                "eval_duration_ns": result.get("eval_duration", 0)
            }
        )

    async def _tool_chat(self, arguments: Dict[str, Any]) -> MCPToolResult:
        """Execute ollama.chat tool

        Args:
            arguments: Tool arguments including messages, model, etc.

        Returns:
            MCPToolResult with chat response
        """
        start_time = time.time()

        messages = arguments.get("messages")
        if not messages:
            return MCPToolResult.error("Missing required argument: messages")

        if not isinstance(messages, list):
            return MCPToolResult.error("messages must be an array")

        model = arguments.get("model", self.config.default_model)
        temperature = arguments.get("temperature", 0.7)
        max_tokens = arguments.get("max_tokens")

        url = f"{self.config.host.rstrip('/')}{self.CHAT_ENDPOINT}"

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        result = await self._make_request_with_retry(url, payload)

        if result.get("error"):
            return MCPToolResult.error(
                result["error"],
                metadata={
                    "model": model,
                    "duration": time.time() - start_time
                }
            )

        # Extract response from message format
        response_text = ""
        if "message" in result and "content" in result["message"]:
            response_text = result["message"]["content"]

        return MCPToolResult.text(
            response_text,
            metadata={
                "model": model,
                "duration": time.time() - start_time,
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "completion_tokens": result.get("eval_count", 0),
                "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
                "load_duration_ns": result.get("load_duration", 0),
                "eval_duration_ns": result.get("eval_duration", 0)
            }
        )

    async def _tool_list_models(self, arguments: Dict[str, Any]) -> MCPToolResult:
        """Execute ollama.list_models tool

        Args:
            arguments: Tool arguments (currently unused)

        Returns:
            MCPToolResult with list of available models
        """
        start_time = time.time()

        url = f"{self.config.host.rstrip('/')}{self.TAGS_ENDPOINT}"

        try:
            async with self._session.get(url) as response:
                response.raise_for_status()
                data = await response.json()

                models = data.get("models", [])

                # Format model information
                model_list = []
                for model in models:
                    model_info = {
                        "name": model.get("name", ""),
                        "size": model.get("size", 0),
                        "modified_at": model.get("modified_at", ""),
                        "digest": model.get("digest", "")[:12] if model.get("digest") else ""
                    }
                    model_list.append(model_info)

                import json
                formatted_output = json.dumps(model_list, indent=2)

                return MCPToolResult.text(
                    formatted_output,
                    metadata={
                        "duration": time.time() - start_time,
                        "model_count": len(model_list)
                    }
                )

        except aiohttp.ClientResponseError as e:
            return MCPToolResult.error(
                f"HTTP error {e.status}: {e.message}",
                metadata={"duration": time.time() - start_time}
            )
        except Exception as e:
            return MCPToolResult.error(
                f"Failed to list models: {str(e)}",
                metadata={"duration": time.time() - start_time}
            )

    # ==================== Helper Methods ====================

    def _ensure_initialized(self) -> None:
        """Ensure server is initialized

        Raises:
            RuntimeError: If server is not initialized
        """
        if not self._initialized:
            raise RuntimeError(
                "Server not initialized. Call initialize() first."
            )

    async def _check_ollama_health(self) -> Dict[str, Any]:
        """Check if Ollama is available and get model list

        Returns:
            Health status dictionary with available models
        """
        url = f"{self.config.host.rstrip('/')}{self.TAGS_ENDPOINT}"

        try:
            async with self._session.get(url) as response:
                response.raise_for_status()
                data = await response.json()

                models = [m.get("name", "") for m in data.get("models", [])]

                return {
                    "available": True,
                    "models": models,
                    "error": None
                }

        except aiohttp.ClientConnectorError as e:
            return {
                "available": False,
                "models": [],
                "error": f"Connection failed: {str(e)}. Is Ollama running?"
            }
        except aiohttp.ClientResponseError as e:
            return {
                "available": False,
                "models": [],
                "error": f"HTTP error {e.status}: {e.message}"
            }
        except Exception as e:
            return {
                "available": False,
                "models": [],
                "error": str(e)
            }

    async def _make_request_with_retry(
        self,
        url: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make HTTP POST request with retry logic

        Args:
            url: API endpoint URL
            payload: Request payload

        Returns:
            Response dictionary or error dictionary
        """
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                async with self._session.post(url, json=payload) as response:
                    response.raise_for_status()
                    return await response.json()

            except aiohttp.ClientConnectorError as e:
                last_error = f"Connection failed: {str(e)}. Is Ollama running?"
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))

            except asyncio.TimeoutError:
                last_error = f"Request timed out after {self.config.timeout}s"
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))

            except aiohttp.ClientResponseError as e:
                # Don't retry on client errors (4xx)
                if 400 <= e.status < 500:
                    return {"error": f"HTTP error {e.status}: {e.message}"}
                last_error = f"HTTP error {e.status}: {e.message}"
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                break

        return {"error": last_error or "All retry attempts failed"}

    # ==================== Context Manager Support ====================

    async def __aenter__(self) -> "OllamaMCPServer":
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit"""
        await self.shutdown()


# ==================== Convenience Functions ====================

async def create_ollama_server(
    host: str = "http://localhost:11434",
    default_model: str = "llama3.2:1b",
    timeout: float = 300.0
) -> OllamaMCPServer:
    """Create and initialize an Ollama MCP server

    Args:
        host: Ollama API URL
        default_model: Default model to use
        timeout: Request timeout in seconds

    Returns:
        Initialized OllamaMCPServer instance

    Example:
        server = await create_ollama_server()
        result = await server.call_tool("ollama.generate", {"prompt": "Hello!"})
        await server.shutdown()
    """
    config = OllamaServerConfig(
        host=host,
        default_model=default_model,
        timeout=timeout
    )
    server = OllamaMCPServer(config)
    await server.initialize()
    return server
