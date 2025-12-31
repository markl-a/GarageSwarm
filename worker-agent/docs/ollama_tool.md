# Ollama Tool Documentation

## Overview

The `OllamaTool` provides integration with Ollama, a local LLM runtime that allows you to run open-source language models on your own hardware. This tool enables the worker-agent to leverage powerful local models without requiring API keys or cloud connectivity.

## Features

- **Local Execution**: Run LLMs entirely on your local machine
- **Multiple Model Support**: Works with llama2, codellama, mistral, qwen2.5-coder, and more
- **Dual API Support**: Use both `/api/generate` and `/api/chat` endpoints
- **Flexible Configuration**: Override model, temperature, and token limits per request
- **Streaming Support**: Built-in support for streaming responses (when enabled)
- **Robust Error Handling**: Graceful handling of connection errors, timeouts, and HTTP errors
- **Health Checks**: Verify Ollama availability and model presence
- **Detailed Metadata**: Returns token counts, duration, and performance metrics

## Prerequisites

1. **Install Ollama**:
   ```bash
   # Visit https://ollama.ai/ for installation instructions
   # Or use package managers:

   # macOS
   brew install ollama

   # Linux
   curl https://ollama.ai/install.sh | sh

   # Windows
   # Download installer from https://ollama.ai/download
   ```

2. **Pull Models**:
   ```bash
   # Pull a base model
   ollama pull llama2

   # Pull code-specific models
   ollama pull codellama
   ollama pull qwen2.5-coder

   # Pull other popular models
   ollama pull mistral
   ollama pull llama3
   ```

3. **Start Ollama Server**:
   ```bash
   # The service usually starts automatically
   # Or manually start it:
   ollama serve
   ```

## Configuration

### Basic Configuration

```python
from tools.ollama import OllamaTool

tool = OllamaTool({
    "url": "http://localhost:11434",  # Ollama API URL
    "model": "llama2",                 # Default model
    "timeout": 300,                    # Timeout in seconds
    "temperature": 0.7,                # Sampling temperature (0.0-2.0)
    "stream": False,                   # Enable streaming (future feature)
    "max_tokens": None                 # Max tokens to generate (optional)
})
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | `http://localhost:11434` | Ollama API base URL |
| `model` | str | `llama2` | Default model to use |
| `timeout` | float | `300` | Request timeout in seconds |
| `temperature` | float | `0.7` | Sampling temperature (0.0-2.0) |
| `stream` | bool | `False` | Enable streaming output |
| `max_tokens` | int | `None` | Maximum tokens to generate |

## Usage

### Basic Text Generation

```python
import asyncio
from tools.ollama import OllamaTool

async def main():
    tool = OllamaTool({
        "url": "http://localhost:11434",
        "model": "llama2"
    })

    result = await tool.execute(
        instructions="Explain the SOLID principles of object-oriented programming."
    )

    if result["success"]:
        print(result["output"])
        print(f"Tokens used: {result['metadata']['total_tokens']}")
    else:
        print(f"Error: {result['error']}")

asyncio.run(main())
```

### Code Generation

```python
tool = OllamaTool({
    "model": "codellama",
    "temperature": 0.3  # Lower temperature for deterministic code
})

result = await tool.execute(
    instructions="Write a Python function to merge two sorted lists."
)
```

### Chat Mode with System Prompt

```python
result = await tool.execute(
    instructions="How do I optimize database queries?",
    context={
        "use_chat": True,
        "system_prompt": "You are a database expert. Provide specific, actionable advice."
    }
)
```

### Runtime Model Override

```python
# Default configuration uses llama2
tool = OllamaTool({"model": "llama2"})

# Override to use a different model for a specific request
result = await tool.execute(
    instructions="Write a Rust function to parse JSON.",
    context={
        "model": "codellama",
        "temperature": 0.2,
        "max_tokens": 500
    }
)
```

### Health Check

```python
tool = OllamaTool({"model": "llama2"})

# Check if Ollama is running and model is available
is_healthy = await tool.health_check()

if is_healthy:
    print("Ollama is ready!")
else:
    print("Ollama is not available or model is not installed")
```

### Configuration Validation

```python
tool = OllamaTool({
    "model": "llama2",
    "temperature": 0.7
})

# Validate configuration
is_valid = await tool.validate_config()

if not is_valid:
    print("Invalid configuration!")
```

## Response Format

The `execute()` method returns a dictionary with the following structure:

```python
{
    "success": bool,           # Whether execution succeeded
    "output": str,             # Generated text (or None on error)
    "error": str,              # Error message (or None on success)
    "metadata": {
        "model": str,          # Model used
        "duration": float,     # Total duration in seconds
        "prompt_tokens": int,  # Number of prompt tokens
        "completion_tokens": int,  # Number of completion tokens
        "total_tokens": int,   # Total tokens
        "load_duration": int,  # Model load duration (nanoseconds)
        "eval_duration": int,  # Evaluation duration (nanoseconds)
        # On error:
        "error_type": str,     # Type of error (connection_error, timeout, etc.)
        "status_code": int     # HTTP status code (if applicable)
    }
}
```

## Supported Models

The tool supports any model available in Ollama. Popular models include:

| Model | Size | Best For |
|-------|------|----------|
| `llama2` | 7B-70B | General purpose text generation |
| `codellama` | 7B-34B | Code generation and understanding |
| `mistral` | 7B | Fast, high-quality text generation |
| `qwen2.5-coder` | 7B-32B | Advanced code generation |
| `llama3` | 8B-70B | Latest Llama model with improved performance |
| `gemma` | 2B-7B | Lightweight, efficient model |
| `phi` | 3B | Microsoft's compact model |
| `neural-chat` | 7B | Conversational AI |
| `starling-lm` | 7B | Instruction-following |

To see all available models on your system:
```bash
ollama list
```

## Error Handling

The tool provides detailed error information for various failure scenarios:

### Connection Errors

```python
{
    "success": False,
    "error": "Failed to connect to Ollama at http://localhost:11434: ...",
    "metadata": {
        "error_type": "connection_error",
        "duration": 0.5
    }
}
```

### Timeout Errors

```python
{
    "success": False,
    "error": "Request timed out after 300s: ...",
    "metadata": {
        "error_type": "timeout",
        "duration": 300.0
    }
}
```

### HTTP Errors

```python
{
    "success": False,
    "error": "HTTP error 404: model not found",
    "metadata": {
        "error_type": "http_error",
        "status_code": 404
    }
}
```

## Best Practices

1. **Model Selection**:
   - Use `codellama` or `qwen2.5-coder` for code-related tasks
   - Use `llama2` or `mistral` for general text generation
   - Use smaller models (7B) for faster responses
   - Use larger models (70B) for better quality (if hardware allows)

2. **Temperature Settings**:
   - Use `0.1-0.3` for deterministic outputs (code, factual answers)
   - Use `0.7-0.9` for creative outputs (writing, brainstorming)
   - Use `1.0+` for highly diverse outputs

3. **Timeout Configuration**:
   - Set longer timeouts for large models or complex prompts
   - Set shorter timeouts for simple queries to fail fast
   - Consider hardware capabilities when setting timeouts

4. **Resource Management**:
   - Monitor system resources (RAM, GPU memory)
   - Use smaller models if running on limited hardware
   - Close other applications to free up resources

5. **Error Handling**:
   - Always check `success` field before using `output`
   - Implement retry logic for connection errors
   - Handle timeouts gracefully with fallback mechanisms

## Integration with Worker-Agent

The OllamaTool integrates seamlessly with the worker-agent system:

```python
from tools.ollama import OllamaTool

# In your agent configuration
agent_config = {
    "tools": {
        "ollama": {
            "enabled": True,
            "config": {
                "url": "http://localhost:11434",
                "model": "codellama",
                "timeout": 300,
                "temperature": 0.5
            }
        }
    }
}

# Initialize and use
tool = OllamaTool(agent_config["tools"]["ollama"]["config"])
result = await tool.execute(instructions="Your task here")
```

## Performance Tips

1. **First Request Latency**: The first request to a model will be slower as Ollama loads the model into memory.

2. **Model Caching**: Keep Ollama running to maintain models in memory for faster subsequent requests.

3. **Hardware Acceleration**: Ensure Ollama is using GPU acceleration if available:
   ```bash
   # Check Ollama is using GPU
   ollama ps
   ```

4. **Concurrent Requests**: Ollama can handle multiple requests, but performance depends on available resources.

5. **Model Size vs Speed**: Smaller models respond faster but may produce lower quality outputs.

## Troubleshooting

### Ollama Not Running

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

### Model Not Found

```bash
# List installed models
ollama list

# Pull missing model
ollama pull llama2
```

### Out of Memory

```bash
# Use a smaller model
ollama pull llama2:7b

# Or set limits in Ollama configuration
```

### Connection Refused

- Check Ollama is running on the correct port
- Verify firewall settings
- Ensure URL in configuration matches Ollama's listen address

## API Endpoints

The tool uses two main Ollama API endpoints:

### Generate Endpoint (`/api/generate`)

Used for simple text generation without conversation context.

### Chat Endpoint (`/api/chat`)

Used for conversational interactions with system prompts and message history.

## Examples

Complete examples are available in `examples/ollama_example.py`. Run them with:

```bash
cd worker-agent
python examples/ollama_example.py
```

## Further Reading

- [Ollama Official Documentation](https://github.com/ollama/ollama)
- [Ollama Model Library](https://ollama.ai/library)
- [Ollama API Reference](https://github.com/ollama/ollama/blob/main/docs/api.md)

## License

This tool is part of the bmad-test project and follows the same license.
