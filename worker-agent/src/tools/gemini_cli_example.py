"""Example usage of Gemini CLI tool

This example demonstrates how to use the Gemini CLI tool in the worker agent.
"""

import asyncio
import os
from gemini_cli import GeminiCLI


async def basic_example():
    """Basic usage example"""
    print("=== Basic Gemini CLI Example ===\n")

    # Configure the tool
    config = {
        "api_key": os.environ.get("GOOGLE_API_KEY"),
        "model": "gemini-1.5-flash",
        "timeout": 60,
        "temperature": 0.7,
        "max_output_tokens": 1024,
    }

    # Initialize the tool
    tool = GeminiCLI(config)

    # Validate configuration
    if not await tool.validate_config():
        print("Configuration validation failed!")
        return

    # Check health
    if not await tool.health_check():
        print("Health check failed!")
        return

    # Execute a simple task
    result = await tool.execute(
        instructions="Write a Python function to calculate factorial"
    )

    if result["success"]:
        print("Output:")
        print(result["output"])
        print(f"\nMetadata: {result['metadata']}")
    else:
        print(f"Error: {result['error']}")


async def example_with_context():
    """Example with code context"""
    print("\n=== Gemini CLI with Context Example ===\n")

    config = {
        "api_key": os.environ.get("GOOGLE_API_KEY"),
        "model": "gemini-1.5-flash",
    }

    tool = GeminiCLI(config)

    # Provide code context
    context = {
        "code": """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
""",
        "parameters": {
            "language": "python",
            "task": "code_review"
        }
    }

    result = await tool.execute(
        instructions="Review this code and suggest improvements",
        context=context
    )

    if result["success"]:
        print("Review:")
        print(result["output"])
    else:
        print(f"Error: {result['error']}")


async def example_with_files():
    """Example with file context"""
    print("\n=== Gemini CLI with Files Example ===\n")

    config = {
        "api_key": os.environ.get("GOOGLE_API_KEY"),
        "model": "gemini-2.0-flash-exp",
        "temperature": 0.3,
    }

    tool = GeminiCLI(config)

    context = {
        "system_instructions": "You are a helpful code assistant",
        "files": [
            {
                "path": "main.py",
                "content": "print('Hello, World!')"
            },
            {
                "path": "utils.py",
                "content": "def helper(): pass"
            }
        ]
    }

    result = await tool.execute(
        instructions="Explain what these files do",
        context=context
    )

    if result["success"]:
        print("Explanation:")
        print(result["output"])
    else:
        print(f"Error: {result['error']}")


async def example_streaming():
    """Example with streaming output"""
    print("\n=== Gemini CLI Streaming Example ===\n")

    config = {
        "api_key": os.environ.get("GOOGLE_API_KEY"),
        "model": "gemini-1.5-flash",
        "stream": True,  # Enable streaming
    }

    tool = GeminiCLI(config)

    result = await tool.execute(
        instructions="Write a short story about a robot learning to code"
    )

    if result["success"]:
        print("Story:")
        print(result["output"])
    else:
        print(f"Error: {result['error']}")


async def example_different_models():
    """Example using different Gemini models"""
    print("\n=== Testing Different Gemini Models ===\n")

    models = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash-exp",
    ]

    prompt = "Explain what is Python in one sentence"

    for model in models:
        print(f"\nUsing model: {model}")

        config = {
            "api_key": os.environ.get("GOOGLE_API_KEY"),
            "model": model,
            "max_output_tokens": 100,
        }

        tool = GeminiCLI(config)
        result = await tool.execute(prompt)

        if result["success"]:
            print(f"Response: {result['output']}")
            print(f"Duration: {result['metadata']['duration']:.2f}s")
        else:
            print(f"Error: {result['error']}")


async def example_error_handling():
    """Example demonstrating error handling"""
    print("\n=== Error Handling Example ===\n")

    # Try with invalid API key
    config = {
        "api_key": "invalid-key",
        "model": "gemini-1.5-flash",
    }

    tool = GeminiCLI(config)

    result = await tool.execute("Hello")

    if not result["success"]:
        print(f"Expected error occurred: {result['error']}")
        print(f"Error type: {result['metadata'].get('error_type')}")


async def example_tool_info():
    """Example showing tool information"""
    print("\n=== Tool Information Example ===\n")

    config = {
        "api_key": os.environ.get("GOOGLE_API_KEY"),
        "model": "gemini-1.5-flash",
    }

    tool = GeminiCLI(config)

    info = tool.get_tool_info()

    print(f"Tool Name: {info['name']}")
    print(f"Provider: {info['provider']}")
    print(f"Model: {info['model']}")
    print(f"Capabilities: {', '.join(info['capabilities'])}")
    print(f"Supported Models: {', '.join(info['supported_models'])}")


async def main():
    """Run all examples"""
    # Check if API key is set
    if not os.environ.get("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY environment variable not set!")
        print("Please set it before running examples:")
        print("  export GOOGLE_API_KEY='your-api-key'")
        return

    try:
        # Run examples
        await basic_example()
        await example_with_context()
        await example_with_files()
        await example_streaming()
        await example_different_models()
        await example_tool_info()

        # Note: Skipping error example with invalid key to avoid API errors
        # await example_error_handling()

    except Exception as e:
        print(f"\nError running examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())
