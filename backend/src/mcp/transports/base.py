"""
MCP Transport Base Classes

Abstract base class and configuration models for MCP transports.
Defines the interface that all transport implementations must follow.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class TransportType(str, Enum):
    """Supported transport types."""

    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


class TransportConfig(BaseModel):
    """
    Configuration for MCP transports.

    This model defines the common configuration options for all transport types,
    as well as type-specific options.
    """

    transport_type: TransportType = Field(
        ..., description="Type of transport to use"
    )

    # STDIO-specific config
    command: Optional[str] = Field(
        None, description="Command to execute (for STDIO transport)"
    )
    args: Optional[List[str]] = Field(
        default_factory=list, description="Command arguments (for STDIO transport)"
    )
    env: Optional[Dict[str, str]] = Field(
        None, description="Environment variables for subprocess (for STDIO transport)"
    )
    cwd: Optional[str] = Field(
        None, description="Working directory for subprocess (for STDIO transport)"
    )

    # HTTP/WebSocket-specific config
    url: Optional[str] = Field(
        None, description="Server URL (for HTTP/WebSocket transport)"
    )
    headers: Optional[Dict[str, str]] = Field(
        None, description="HTTP headers (for HTTP/WebSocket transport)"
    )

    # Common config
    timeout: float = Field(
        default=30.0, ge=1.0, le=300.0, description="Timeout in seconds for operations"
    )
    read_timeout: float = Field(
        default=60.0, ge=1.0, le=600.0, description="Timeout for read operations"
    )
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum retry attempts for failed operations"
    )

    model_config = {"extra": "forbid"}


class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 request message."""

    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Union[int, str] = Field(..., description="Request ID")
    method: str = Field(..., description="Method name to invoke")
    params: Optional[Dict[str, Any]] = Field(
        default=None, description="Method parameters"
    )


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 response message."""

    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Optional[Union[int, str]] = Field(None, description="Request ID (matches request)")
    result: Optional[Any] = Field(None, description="Method result (if successful)")
    error: Optional[Dict[str, Any]] = Field(None, description="Error object (if failed)")

    @property
    def is_error(self) -> bool:
        """Check if this response is an error."""
        return self.error is not None

    @property
    def error_code(self) -> Optional[int]:
        """Get error code if this is an error response."""
        if self.error:
            return self.error.get("code")
        return None

    @property
    def error_message(self) -> Optional[str]:
        """Get error message if this is an error response."""
        if self.error:
            return self.error.get("message")
        return None


class JsonRpcNotification(BaseModel):
    """JSON-RPC 2.0 notification (no id, no response expected)."""

    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name")
    params: Optional[Dict[str, Any]] = Field(
        default=None, description="Method parameters"
    )


class TransportError(Exception):
    """Base exception for transport errors."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        if self.cause:
            return f"{self.message}: {self.cause}"
        return self.message


class TransportConnectionError(TransportError):
    """Raised when connection to transport fails."""

    pass


class TransportTimeoutError(TransportError):
    """Raised when a transport operation times out."""

    pass


class TransportProtocolError(TransportError):
    """Raised when there's a protocol-level error (e.g., malformed JSON-RPC)."""

    pass


class Transport(ABC):
    """
    Abstract base class for MCP transports.

    All transport implementations must inherit from this class and implement
    the required methods for connecting, sending, receiving, and closing.
    """

    def __init__(self, config: TransportConfig):
        """
        Initialize the transport with configuration.

        Args:
            config: Transport configuration
        """
        self._config = config
        self._connected = False
        self._message_id = 0

    @property
    def config(self) -> TransportConfig:
        """Get the transport configuration."""
        return self._config

    @property
    def is_connected(self) -> bool:
        """Check if the transport is currently connected."""
        return self._connected

    def _next_message_id(self) -> int:
        """Generate the next message ID."""
        self._message_id += 1
        return self._message_id

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the MCP server.

        Raises:
            TransportConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def send(self, message: Union[JsonRpcRequest, JsonRpcNotification]) -> None:
        """
        Send a JSON-RPC message to the server.

        Args:
            message: The JSON-RPC request or notification to send

        Raises:
            TransportError: If send fails
            TransportConnectionError: If not connected
        """
        pass

    @abstractmethod
    async def receive(self, timeout: Optional[float] = None) -> JsonRpcResponse:
        """
        Receive a JSON-RPC response from the server.

        Args:
            timeout: Optional timeout override (uses config timeout if not specified)

        Returns:
            The JSON-RPC response

        Raises:
            TransportTimeoutError: If receive times out
            TransportError: If receive fails
            TransportConnectionError: If not connected
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close the transport connection.

        This should be called when done using the transport.
        Safe to call multiple times.
        """
        pass

    async def request(
        self, method: str, params: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None
    ) -> JsonRpcResponse:
        """
        Send a request and wait for the response.

        This is a convenience method that combines send() and receive().

        Args:
            method: The method name to invoke
            params: Optional method parameters
            timeout: Optional timeout override

        Returns:
            The JSON-RPC response

        Raises:
            TransportError: If the request fails
        """
        request = JsonRpcRequest(
            id=self._next_message_id(),
            method=method,
            params=params,
        )
        await self.send(request)
        return await self.receive(timeout=timeout)

    async def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """
        Send a notification (no response expected).

        Args:
            method: The method name to invoke
            params: Optional method parameters

        Raises:
            TransportError: If the notification fails
        """
        notification = JsonRpcNotification(
            method=method,
            params=params,
        )
        await self.send(notification)

    async def __aenter__(self) -> "Transport":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
