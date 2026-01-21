"""
MCP Transport Layer

Provides transport implementations for MCP communication:
- STDIOTransport: For subprocess-based MCP servers
- (Future) HTTPTransport: For HTTP/SSE-based MCP servers
- (Future) WebSocketTransport: For WebSocket-based MCP servers
"""

from .base import Transport, TransportConfig, TransportError, TransportConnectionError
from .stdio import STDIOTransport

__all__ = [
    "Transport",
    "TransportConfig",
    "TransportError",
    "TransportConnectionError",
    "STDIOTransport",
]
