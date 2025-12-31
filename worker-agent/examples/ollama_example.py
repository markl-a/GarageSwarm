"""Example usage of OllamaTool

This example demonstrates how to use the OllamaTool for local LLM inference.
Make sure Ollama is running locally before running this example.

Installation:
    1. Install Ollama from https://ollama.ai/
    2. Pull a model: ollama pull llama2
    3. Run this example

Usage:
    python examples/ollama_example.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tools.ollama import OllamaTool


async def example_basic_generation():
    """Example 1: Basic text generation"""
    print("\n=== Example 1: Basic Text Generation ===\n")

    # Initialize tool
    tool = OllamaTool({
        "url": "http://localhost:11434",
        "model": "llama2",
        "timeout": 300,
        "temperature": 0.7
    })

    # Check if tool is healthy
    is_healthy = await tool.health_check()
    print(f"Tool health check: {'OK' if is_healthy else 'FAILED'}")

    if not is_healthy:
        print("Ollama is not running or model is not available.")
        print("Please install Ollama and run: ollama pull llama2")
        return

    # Execute a simple prompt
    result = await tool.execute(
        instructions="Write a short poem about programming in Python.",
    )

    print(f"Success: {result['success']}")
    if result['success']:
        print(f"\nOutput:\n{result['output']}")
        print(f"\nMetadata:")
        print(f"  Model: {result['metadata']['model']}")
        print(f"  Duration: {result['metadata']['duration']:.2f}s")
        print(f"  Tokens: {result['metadata']['total_tokens']}")
    else:
        print(f"Error: {result['error']}")


async def example_code_generation():
    """Example 2: Code generation with codellama"""
    print("\n=== Example 2: Code Generation ===\n")

    # Initialize tool with codellama model
    tool = OllamaTool({
        "url": "http://localhost:11434",
        "model": "codellama",
        "timeout": 300,
        "temperature": 0.3  # Lower temperature for more deterministic code
    })

    # Check if codellama is available
    is_healthy = await tool.health_check()
    if not is_healthy:
        print("CodeLlama model is not available.")
        print("Please run: ollama pull codellama")
        return

    # Generate code
    result = await tool.execute(
        instructions="Write a Python function to calculate the Fibonacci sequence recursively.",
    )

    print(f"Success: {result['success']}")
    if result['success']:
        print(f"\nGenerated Code:\n{result['output']}")
        print(f"\nDuration: {result['metadata']['duration']:.2f}s")
    else:
        print(f"Error: {result['error']}")


async def example_chat_mode():
    """Example 3: Chat mode with system prompt"""
    print("\n=== Example 3: Chat Mode with System Prompt ===\n")

    tool = OllamaTool({
        "url": "http://localhost:11434",
        "model": "llama2",
        "timeout": 300,
        "temperature": 0.8
    })

    # Use chat endpoint with system prompt
    result = await tool.execute(
        instructions="What are the best practices for writing clean code?",
        context={
            "use_chat": True,
            "system_prompt": "You are a senior software engineer with 20 years of experience. Provide concise, practical advice."
        }
    )

    print(f"Success: {result['success']}")
    if result['success']:
        print(f"\nResponse:\n{result['output']}")
        print(f"\nTokens used: {result['metadata']['total_tokens']}")
    else:
        print(f"Error: {result['error']}")


async def example_model_override():
    """Example 4: Override model at runtime"""
    print("\n=== Example 4: Runtime Model Override ===\n")

    # Default configuration uses llama2
    tool = OllamaTool({
        "url": "http://localhost:11434",
        "model": "llama2",
        "timeout": 300
    })

    # But we can override to use mistral for this specific request
    result = await tool.execute(
        instructions="Explain quantum computing in one paragraph.",
        context={
            "model": "mistral",  # Override to use mistral
            "temperature": 0.5,
            "max_tokens": 200
        }
    )

    print(f"Success: {result['success']}")
    if result['success']:
        print(f"\nOutput:\n{result['output']}")
        print(f"Model used: {result['metadata']['model']}")
    else:
        print(f"Error: {result['error']}")
        if "error_type" in result["metadata"]:
            print(f"Error type: {result['metadata']['error_type']}")


async def example_error_handling():
    """Example 5: Error handling"""
    print("\n=== Example 5: Error Handling ===\n")

    # Try to connect to wrong port
    tool = OllamaTool({
        "url": "http://localhost:99999",  # Wrong port
        "model": "llama2",
        "timeout": 5
    })

    result = await tool.execute(
        instructions="This should fail.",
    )

    print(f"Success: {result['success']}")
    print(f"Error: {result['error']}")
    print(f"Error type: {result['metadata'].get('error_type', 'N/A')}")


async def example_tool_info():
    """Example 6: Get tool information"""
    print("\n=== Example 6: Tool Information ===\n")

    tool = OllamaTool({
        "url": "http://localhost:11434",
        "model": "llama2"
    })

    info = tool.get_tool_info()
    print(f"Tool name: {info['name']}")
    print(f"Provider: {info['provider']}")
    print(f"Model: {info['model']}")
    print(f"Capabilities: {', '.join(info['capabilities'])}")
    print(f"\nSupported models:")
    for model in info['supported_models']:
        print(f"  - {model}")


async def main():
    """Run all examples"""
    print("=" * 60)
    print("Ollama Tool Examples")
    print("=" * 60)

    # Run examples
    await example_basic_generation()
    await example_code_generation()
    await example_chat_mode()
    await example_model_override()
    await example_error_handling()
    await example_tool_info()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
