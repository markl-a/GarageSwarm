# Adding New AI Tools

This guide explains how to integrate new AI tools into the Multi-Agent on the Web platform. AI tools are pluggable components that execute tasks on worker machines.

## Table of Contents

- [Overview](#overview)
- [BaseTool Interface](#basetool-interface)
- [Creating a New Tool](#creating-a-new-tool)
- [Example: OpenAI GPT Tool](#example-openai-gpt-tool)
- [Configuration Management](#configuration-management)
- [Error Handling](#error-handling)
- [Testing Your Tool](#testing-your-tool)
- [Registering the Tool](#registering-the-tool)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

### AI Tool Architecture

The platform uses a **plugin architecture** for AI tools, allowing easy integration of different AI providers:

```
┌──────────────────────────────────────────────┐
│          Worker Agent                        │
│  ┌────────────────────────────────────────┐ │
│  │        TaskExecutor                    │ │
│  │  ┌──────────────────────────────────┐ │ │
│  │  │      Tool Registry               │ │ │
│  │  │  {                               │ │ │
│  │  │    "claude_code": ClaudeTool,   │ │ │
│  │  │    "gemini_cli": GeminiTool,    │ │ │
│  │  │    "ollama": OllamaTool,        │ │ │
│  │  │    "openai": OpenAITool  ← NEW  │ │ │
│  │  │  }                               │ │ │
│  │  └──────────────────────────────────┘ │ │
│  └────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

### Tool Execution Flow

```
1. Backend assigns subtask to worker
       │
       ▼
2. TaskExecutor receives task with "assigned_tool"
       │
       ▼
3. TaskExecutor looks up tool in registry
       │
       ▼
4. Tool.execute(instructions, context) is called
       │
       ▼
5. Tool returns result dictionary
       │
       ▼
6. TaskExecutor uploads result to backend
```

## BaseTool Interface

All AI tools must implement the `BaseTool` abstract class:

```python
# worker-agent/src/tools/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseTool(ABC):
    """Abstract base class for AI tools

    All AI tools (Claude Code, Gemini CLI, Ollama, etc.) must implement this interface.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize tool with configuration

        Args:
            config: Tool-specific configuration dictionary
        """
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    async def execute(
        self,
        instructions: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute task with the AI tool

        Args:
            instructions: Task instructions/prompt for the AI tool
            context: Optional context data (code, files, parameters, etc.)

        Returns:
            Dictionary containing:
                - success: bool - Whether execution succeeded
                - output: Any - Tool output (text, code, etc.)
                - error: Optional[str] - Error message if failed
                - metadata: Dict - Additional metadata (tokens used, duration, etc.)
        """
        pass

    @abstractmethod
    async def validate_config(self) -> bool:
        """Validate tool configuration

        Returns:
            True if configuration is valid, False otherwise
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if tool is available and responsive

        Returns:
            True if tool is healthy, False otherwise
        """
        pass

    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information

        Returns:
            Dictionary with tool name, version, capabilities, etc.
        """
        return {
            "name": self.name,
            "type": "ai_tool",
            "capabilities": []
        }
```

### Method Responsibilities

| Method | Purpose | When Called |
|--------|---------|-------------|
| `__init__` | Initialize tool with configuration | Once when worker starts |
| `execute` | Execute AI task and return result | Every time a task is assigned |
| `validate_config` | Verify configuration is valid | During initialization |
| `health_check` | Ping the AI service | Periodically for monitoring |
| `get_tool_info` | Return tool metadata | During registration |

## Creating a New Tool

### Step 1: Create Tool File

Create a new file in `worker-agent/src/tools/`:

```bash
cd worker-agent/src/tools
touch openai_gpt.py
```

### Step 2: Implement BaseTool Interface

```python
# worker-agent/src/tools/openai_gpt.py

"""OpenAI GPT tool integration"""

import os
import time
import asyncio
from typing import Any, Dict, Optional
import structlog

try:
    import openai
except ImportError:
    openai = None

from .base import BaseTool

logger = structlog.get_logger()


class OpenAIGPTTool(BaseTool):
    """OpenAI GPT tool adapter

    Supports GPT-4, GPT-3.5-turbo, and other OpenAI models.
    """

    # Default configuration
    DEFAULT_MODEL = "gpt-4"
    DEFAULT_TIMEOUT = 300  # 5 minutes
    DEFAULT_MAX_RETRIES = 3

    # Supported models
    SUPPORTED_MODELS = [
        "gpt-4",
        "gpt-4-turbo-preview",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
    ]

    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenAI GPT tool

        Args:
            config: Configuration dictionary with:
                - api_key: OpenAI API key (or OPENAI_API_KEY env var)
                - model: Model name (default: gpt-4)
                - timeout: Request timeout in seconds (default: 300)
                - max_retries: Maximum retry attempts (default: 3)
                - temperature: Sampling temperature 0.0-2.0 (default: 0.7)
                - max_tokens: Maximum tokens in response (default: 2048)
        """
        super().__init__(config)

        # Validate openai package is installed
        if openai is None:
            raise ImportError(
                "openai package is required. Install it with: pip install openai"
            )

        # Get API key from config or environment
        self.api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be provided")

        # Model configuration
        self.model = config.get("model", self.DEFAULT_MODEL)
        self.timeout = config.get("timeout", self.DEFAULT_TIMEOUT)
        self.max_retries = config.get("max_retries", self.DEFAULT_MAX_RETRIES)

        # Generation parameters
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2048)
        self.top_p = config.get("top_p", 1.0)

        # Initialize OpenAI client
        self.client = openai.AsyncOpenAI(api_key=self.api_key)

        logger.info(
            "OpenAIGPTTool initialized",
            model=self.model,
            timeout=self.timeout
        )

    async def execute(
        self,
        instructions: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute task with OpenAI GPT

        Args:
            instructions: Task instructions/prompt
            context: Optional context data containing:
                - system_prompt: System-level instructions
                - files: List of file contents
                - code: Code snippets
                - parameters: Additional parameters

        Returns:
            Dictionary containing:
                - success: bool - Whether execution succeeded
                - output: str - Generated text response
                - error: Optional[str] - Error message if failed
                - metadata: dict - Execution metadata
        """
        start_time = time.time()
        context = context or {}

        logger.info(
            "Executing OpenAI task",
            model=self.model,
            instructions_length=len(instructions)
        )

        try:
            # Build messages
            messages = self._build_messages(instructions, context)

            # Make API call with retry logic
            response = await self._generate_with_retry(messages)

            # Extract output
            output_text = response.choices[0].message.content

            duration = time.time() - start_time

            # Build metadata
            metadata = {
                "model": self.model,
                "duration": duration,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "finish_reason": response.choices[0].finish_reason,
            }

            logger.info(
                "Task completed successfully",
                duration=duration,
                total_tokens=metadata["total_tokens"],
                output_length=len(output_text)
            )

            return {
                "success": True,
                "output": output_text,
                "error": None,
                "metadata": metadata
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
                    "model": self.model,
                    "duration": duration,
                    "error_type": type(e).__name__
                }
            }

    async def _generate_with_retry(self, messages: list) -> Any:
        """Generate content with retry logic

        Args:
            messages: List of message dictionaries

        Returns:
            OpenAI response object

        Raises:
            Exception: If all retries fail
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        top_p=self.top_p,
                    ),
                    timeout=self.timeout
                )

                return response

            except asyncio.TimeoutError:
                last_error = f"Request timeout after {self.timeout} seconds"
                logger.warning(
                    "Request timeout",
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )

            except openai.RateLimitError as e:
                last_error = f"Rate limit exceeded: {str(e)}"
                logger.warning(
                    "Rate limit exceeded",
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )
                # Exponential backoff
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)

            except openai.APIError as e:
                last_error = f"API error: {str(e)}"
                logger.error(
                    "OpenAI API error",
                    error=str(e),
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )

                # Retry on server errors
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2)

            except Exception as e:
                last_error = str(e)
                logger.error(
                    "Generation failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )

                # Don't retry on client errors
                if isinstance(e, (openai.AuthenticationError, openai.BadRequestError)):
                    raise

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2)

        # All retries failed
        raise Exception(f"Failed after {self.max_retries} attempts: {last_error}")

    def _build_messages(self, instructions: str, context: Dict[str, Any]) -> list:
        """Build messages for chat completion

        Args:
            instructions: Main task instructions
            context: Context data

        Returns:
            List of message dictionaries
        """
        messages = []

        # Add system message if provided
        system_prompt = context.get("system_prompt", "You are a helpful AI assistant for coding tasks.")
        messages.append({
            "role": "system",
            "content": system_prompt
        })

        # Build user message with context
        user_content_parts = []

        # Add file context
        if "files" in context:
            files = context["files"]
            if isinstance(files, list):
                user_content_parts.append("=== Context Files ===")
                for file_info in files:
                    if isinstance(file_info, dict):
                        file_path = file_info.get("path", "unknown")
                        file_content = file_info.get("content", "")
                        user_content_parts.append(f"\nFile: {file_path}\n```\n{file_content}\n```")

        # Add code context
        if "code" in context:
            user_content_parts.append(f"\n=== Code Context ===\n```\n{context['code']}\n```")

        # Add main instructions
        user_content_parts.append(f"\n=== Task ===\n{instructions}")

        messages.append({
            "role": "user",
            "content": "\n".join(user_content_parts)
        })

        return messages

    async def validate_config(self) -> bool:
        """Validate tool configuration

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Check API key
            if not self.api_key:
                logger.error("Missing API key")
                return False

            # Validate model name
            if self.model not in self.SUPPORTED_MODELS:
                logger.warning(
                    "Model not in supported list",
                    model=self.model,
                    supported=self.SUPPORTED_MODELS
                )

            # Validate parameters
            if self.timeout <= 0:
                logger.error("Invalid timeout", timeout=self.timeout)
                return False

            if not 0 <= self.temperature <= 2.0:
                logger.error("Invalid temperature", temperature=self.temperature)
                return False

            if self.max_tokens <= 0:
                logger.error("Invalid max_tokens", max_tokens=self.max_tokens)
                return False

            logger.info("Configuration validated successfully")
            return True

        except Exception as e:
            logger.error("Configuration validation failed", error=str(e))
            return False

    async def health_check(self) -> bool:
        """Check if OpenAI API is available and responsive

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Try a minimal API call
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5,
                ),
                timeout=10  # Short timeout for health check
            )

            if response and response.choices:
                logger.info("Health check passed")
                return True
            else:
                logger.warning("Health check received empty response")
                return False

        except asyncio.TimeoutError:
            logger.error("Health check timeout")
            return False
        except Exception as e:
            logger.error("Health check failed", error=str(e), error_type=type(e).__name__)
            return False

    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information

        Returns:
            Dictionary with tool details
        """
        return {
            "name": self.name,
            "type": "ai_tool",
            "provider": "openai",
            "model": self.model,
            "capabilities": [
                "text_generation",
                "code_generation",
                "code_editing",
                "analysis",
                "debugging",
                "refactoring",
            ],
            "config": {
                "model": self.model,
                "timeout": self.timeout,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
            "supported_models": self.SUPPORTED_MODELS,
        }
```

### Step 3: Add Tool Export

Update `worker-agent/src/tools/__init__.py`:

```python
# worker-agent/src/tools/__init__.py

from .base import BaseTool
from .claude_code import ClaudeCodeTool
from .gemini_cli import GeminiCLI
from .ollama import OllamaTool
from .openai_gpt import OpenAIGPTTool  # Add new tool

__all__ = [
    "BaseTool",
    "ClaudeCodeTool",
    "GeminiCLI",
    "OllamaTool",
    "OpenAIGPTTool",  # Add new tool
]
```

## Configuration Management

### Step 4: Update Agent Configuration

Add tool configuration to `worker-agent/config/agent.yaml`:

```yaml
# Worker Agent Configuration

# ... existing config ...

# AI Tools configuration
tools:
  claude_code:
    enabled: true
    api_key: "${ANTHROPIC_API_KEY}"

  gemini_cli:
    enabled: true
    api_key: "${GOOGLE_API_KEY}"

  ollama:
    enabled: false
    base_url: "http://localhost:11434"
    model: "llama2"

  # Add new tool configuration
  openai_gpt:
    enabled: true
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4"
    timeout: 300
    temperature: 0.7
    max_tokens: 2048
```

### Step 5: Update Environment Variables

Add API key to `.env`:

```bash
# .env
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_API_KEY=your-google-key
OPENAI_API_KEY=your-openai-key  # Add new key
```

## Error Handling

### Common Error Patterns

Implement robust error handling in your tool:

```python
async def execute(self, instructions: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        # ... execution logic ...
        return {
            "success": True,
            "output": result,
            "error": None,
            "metadata": {}
        }

    except asyncio.TimeoutError:
        # Handle timeout
        return {
            "success": False,
            "output": None,
            "error": "Request timeout",
            "metadata": {"error_type": "timeout"}
        }

    except ValueError as e:
        # Handle validation errors
        return {
            "success": False,
            "output": None,
            "error": f"Validation error: {str(e)}",
            "metadata": {"error_type": "validation"}
        }

    except Exception as e:
        # Handle unexpected errors
        logger.error("Unexpected error", error=str(e), exc_info=True)
        return {
            "success": False,
            "output": None,
            "error": f"Unexpected error: {str(e)}",
            "metadata": {"error_type": type(e).__name__}
        }
```

### Retry Logic

Implement exponential backoff for transient errors:

```python
async def _execute_with_retry(self, func, max_retries=3):
    """Execute function with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            return await func()
        except TransientError as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
            await asyncio.sleep(wait_time)
```

## Testing Your Tool

### Step 6: Write Unit Tests

Create `worker-agent/tests/unit/test_openai_gpt.py`:

```python
# worker-agent/tests/unit/test_openai_gpt.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tools.openai_gpt import OpenAIGPTTool


@pytest.fixture
def mock_config():
    """Mock tool configuration"""
    return {
        "api_key": "test-api-key",
        "model": "gpt-4",
        "timeout": 60,
        "temperature": 0.7,
        "max_tokens": 1024,
    }


@pytest.fixture
def tool(mock_config):
    """Create tool instance"""
    with patch('tools.openai_gpt.openai'):
        return OpenAIGPTTool(mock_config)


@pytest.mark.asyncio
async def test_execute_success(tool):
    """Test successful execution"""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(content="Generated code"),
            finish_reason="stop"
        )
    ]
    mock_response.usage = MagicMock(
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30
    )

    with patch.object(tool, '_generate_with_retry', return_value=mock_response):
        result = await tool.execute("Write hello world")

    assert result["success"] is True
    assert result["output"] == "Generated code"
    assert result["error"] is None
    assert result["metadata"]["total_tokens"] == 30


@pytest.mark.asyncio
async def test_execute_timeout(tool):
    """Test timeout handling"""
    with patch.object(tool, '_generate_with_retry', side_effect=asyncio.TimeoutError()):
        result = await tool.execute("Write hello world")

    assert result["success"] is False
    assert "timeout" in result["error"].lower()


@pytest.mark.asyncio
async def test_validate_config_success(tool):
    """Test configuration validation"""
    is_valid = await tool.validate_config()
    assert is_valid is True


@pytest.mark.asyncio
async def test_validate_config_missing_api_key():
    """Test validation fails without API key"""
    config = {"model": "gpt-4"}  # Missing api_key

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIGPTTool(config)


@pytest.mark.asyncio
async def test_health_check_success(tool):
    """Test health check passes"""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]

    with patch.object(tool.client.chat.completions, 'create', return_value=mock_response):
        is_healthy = await tool.health_check()

    assert is_healthy is True


@pytest.mark.asyncio
async def test_health_check_timeout(tool):
    """Test health check handles timeout"""
    with patch.object(
        tool.client.chat.completions,
        'create',
        side_effect=asyncio.TimeoutError()
    ):
        is_healthy = await tool.health_check()

    assert is_healthy is False


def test_get_tool_info(tool):
    """Test tool info retrieval"""
    info = tool.get_tool_info()

    assert info["name"] == "OpenAIGPTTool"
    assert info["provider"] == "openai"
    assert info["model"] == "gpt-4"
    assert "code_generation" in info["capabilities"]
```

### Step 7: Run Tests

```bash
cd worker-agent

# Run unit tests
pytest tests/unit/test_openai_gpt.py -v

# Run with coverage
pytest tests/unit/test_openai_gpt.py --cov=src/tools/openai_gpt --cov-report=html
```

### Step 8: Integration Testing

Create `worker-agent/tests/integration/test_openai_integration.py`:

```python
import pytest
import os
from tools.openai_gpt import OpenAIGPTTool


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)
@pytest.mark.asyncio
async def test_real_api_call():
    """Test real API call (requires API key)"""
    config = {
        "api_key": os.environ["OPENAI_API_KEY"],
        "model": "gpt-3.5-turbo",
        "max_tokens": 50,
    }

    tool = OpenAIGPTTool(config)

    result = await tool.execute("Say 'Hello World' in Python")

    assert result["success"] is True
    assert result["output"] is not None
    assert len(result["output"]) > 0
    assert "hello" in result["output"].lower() or "print" in result["output"].lower()
```

## Registering the Tool

### Step 9: Register in Worker Agent

Update `worker-agent/src/main.py`:

```python
# worker-agent/src/main.py

import asyncio
import yaml
from agent.core import WorkerAgent
from tools.claude_code import ClaudeCodeTool
from tools.gemini_cli import GeminiCLI
from tools.ollama import OllamaTool
from tools.openai_gpt import OpenAIGPTTool  # Import new tool


async def main():
    # Load configuration
    with open("config/agent.yaml") as f:
        config = yaml.safe_load(f)

    # Create worker agent
    agent = WorkerAgent(config)

    # Register tools
    tools_config = config.get("tools", {})

    # Claude Code
    if tools_config.get("claude_code", {}).get("enabled", False):
        claude_tool = ClaudeCodeTool(tools_config["claude_code"])
        agent.register_tool("claude_code", claude_tool)

    # Gemini CLI
    if tools_config.get("gemini_cli", {}).get("enabled", False):
        gemini_tool = GeminiCLI(tools_config["gemini_cli"])
        agent.register_tool("gemini_cli", gemini_tool)

    # Ollama
    if tools_config.get("ollama", {}).get("enabled", False):
        ollama_tool = OllamaTool(tools_config["ollama"])
        agent.register_tool("ollama", ollama_tool)

    # OpenAI GPT (NEW)
    if tools_config.get("openai_gpt", {}).get("enabled", False):
        openai_tool = OpenAIGPTTool(tools_config["openai_gpt"])
        agent.register_tool("openai_gpt", openai_tool)

    # Start worker agent
    await agent.start()

    # Wait for shutdown signal
    await agent.wait_for_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
```

### Step 10: Update Requirements

Add tool dependencies to `worker-agent/requirements.txt`:

```txt
# Existing dependencies
httpx==0.25.2
websockets==12.0
# ... other dependencies ...

# OpenAI tool dependency
openai==1.12.0
```

Install dependencies:

```bash
cd worker-agent
pip install -r requirements.txt
```

## Best Practices

### 1. Logging

Use structured logging for debugging:

```python
import structlog
logger = structlog.get_logger()

logger.info("Tool initialized", model=self.model, timeout=self.timeout)
logger.debug("Building messages", message_count=len(messages))
logger.warning("Rate limit reached", retry_after=retry_after)
logger.error("API call failed", error=str(e), error_type=type(e).__name__)
```

### 2. Timeouts

Always implement timeouts:

```python
response = await asyncio.wait_for(
    self.client.generate(...),
    timeout=self.timeout
)
```

### 3. Resource Cleanup

Clean up resources in case of errors:

```python
try:
    # Use API
    response = await self.client.generate(...)
except Exception:
    # Clean up
    await self.client.close()
    raise
```

### 4. Configuration Validation

Validate configuration early:

```python
def __init__(self, config):
    super().__init__(config)

    # Validate required fields
    if not config.get("api_key"):
        raise ValueError("api_key is required")

    # Validate value ranges
    if not 0 <= config.get("temperature", 0.7) <= 2.0:
        raise ValueError("temperature must be between 0 and 2")
```

### 5. Rate Limiting

Implement rate limiting to avoid API throttling:

```python
class RateLimiter:
    def __init__(self, max_requests_per_minute=60):
        self.max_requests = max_requests_per_minute
        self.request_times = []

    async def acquire(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()

        # Remove old requests outside the time window
        self.request_times = [
            t for t in self.request_times
            if now - t < 60
        ]

        # Check if we're at the limit
        if len(self.request_times) >= self.max_requests:
            wait_time = 60 - (now - self.request_times[0])
            await asyncio.sleep(wait_time)
            self.request_times = []

        self.request_times.append(now)
```

### 6. Streaming Support

Support streaming for real-time feedback:

```python
async def execute_streaming(self, instructions, context=None):
    """Execute with streaming output"""
    async for chunk in self.client.generate_stream(instructions):
        yield {
            "type": "chunk",
            "content": chunk.text,
            "done": False
        }

    yield {
        "type": "complete",
        "done": True
    }
```

## Troubleshooting

### Tool Not Recognized

**Problem:** Worker doesn't recognize the new tool

**Solutions:**
1. Check tool is registered in `main.py`
2. Verify tool is enabled in `agent.yaml`
3. Check tool name matches backend's recommended_tool

### Import Errors

**Problem:** `ImportError: cannot import name 'OpenAIGPTTool'`

**Solutions:**
1. Check tool is exported in `__init__.py`
2. Verify file name matches import statement
3. Run `pip install -r requirements.txt`

### Configuration Errors

**Problem:** Tool fails to initialize

**Solutions:**
1. Check API key is set in environment or config
2. Validate all required config fields are present
3. Check config file syntax (YAML indentation)

### API Errors

**Problem:** API calls fail or timeout

**Solutions:**
1. Verify API key is valid
2. Check network connectivity
3. Increase timeout value
4. Implement retry logic
5. Check API rate limits

### Health Check Fails

**Problem:** Health check returns False

**Solutions:**
1. Verify API endpoint is accessible
2. Check API key permissions
3. Ensure model name is valid
4. Review API status page for outages

## Next Steps

Now that you've added a new AI tool:

1. **Test thoroughly**: Run unit tests, integration tests, and manual testing
2. **Update documentation**: Add tool to README and architecture docs
3. **Monitor performance**: Track execution times, error rates, success rates
4. **Optimize**: Tune configuration based on real-world usage
5. **Share**: Submit a pull request to contribute back to the project

## Additional Resources

- [BaseTool Interface](../worker-agent/src/tools/base.py)
- [Claude Code Example](../worker-agent/src/tools/claude_code.py)
- [Gemini CLI Example](../worker-agent/src/tools/gemini_cli.py)
- [Testing Guide](./contributing.md#testing-guidelines)
- [Worker Agent Architecture](./architecture-deep-dive.md#worker-agent-architecture)
