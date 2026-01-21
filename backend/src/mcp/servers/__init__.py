"""
MCP Servers

This module provides MCP server implementations that wrap various AI tools
and expose them through the MCP protocol interface.

Available servers:
- OllamaMCPServer: Wraps Ollama for local LLM inference
- GeminiCLIMCPServer: Wraps Google's Gemini CLI for AI text generation
- ClaudeCodeMCPServer: Wraps Claude Code CLI for AI-powered coding tasks
"""

from .ollama import OllamaMCPServer, OllamaServerConfig, create_ollama_server
from .gemini_cli import GeminiCLIMCPServer, GeminiCLIServerConfig, BaseMCPServer
from .claude_code import ClaudeCodeMCPServer, ClaudeCodeServerConfig

__all__ = [
    "BaseMCPServer",
    # Ollama
    "OllamaMCPServer",
    "OllamaServerConfig",
    "create_ollama_server",
    # Gemini
    "GeminiCLIMCPServer",
    "GeminiCLIServerConfig",
    # Claude Code
    "ClaudeCodeMCPServer",
    "ClaudeCodeServerConfig",
]
