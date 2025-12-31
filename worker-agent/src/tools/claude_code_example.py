"""Example usage of Claude Code tool"""

import asyncio
from claude_code import ClaudeCodeTool


async def main():
    """Example of using Claude Code tool"""

    # Initialize the tool with configuration
    config = {
        "cli_path": "claude",  # Or full path like "C:\\Program Files\\Claude\\claude.exe"
        "default_timeout": 300,  # 5 minutes
        "working_directory": "C:\\Users\\m4932\\OneDrive\\Documents\\Gitlab\\bmad-test",
        "env_vars": {
            # Add any additional environment variables if needed
        }
    }

    tool = ClaudeCodeTool(config)

    # Validate configuration
    print("Validating Claude Code configuration...")
    is_valid = await tool.validate_config()
    print(f"Configuration valid: {is_valid}")

    if not is_valid:
        print("Claude Code CLI not available or configuration invalid")
        return

    # Health check
    print("\nPerforming health check...")
    is_healthy = await tool.health_check()
    print(f"Health check passed: {is_healthy}")

    # Get tool info
    print("\nTool information:")
    info = tool.get_tool_info()
    print(f"Name: {info['name']}")
    print(f"Provider: {info['provider']}")
    print(f"Capabilities: {', '.join(info['capabilities'])}")

    # Example 1: Simple code generation
    print("\n" + "=" * 60)
    print("Example 1: Simple code generation")
    print("=" * 60)

    instructions = "Create a Python function that calculates the factorial of a number"

    result = await tool.execute(
        instructions=instructions,
        context={
            "timeout": 60,
            "stream": True
        }
    )

    print(f"Success: {result['success']}")
    print(f"Duration: {result['metadata']['duration']:.2f}s")
    if result['success']:
        print(f"Output:\n{result['output']}")
    else:
        print(f"Error: {result['error']}")

    # Example 2: Code analysis with file context
    print("\n" + "=" * 60)
    print("Example 2: Code analysis with file context")
    print("=" * 60)

    instructions = "Review this code for potential improvements and bugs"

    result = await tool.execute(
        instructions=instructions,
        context={
            "working_directory": "C:\\Users\\m4932\\OneDrive\\Documents\\Gitlab\\bmad-test\\worker-agent",
            "files": [
                "C:\\Users\\m4932\\OneDrive\\Documents\\Gitlab\\bmad-test\\worker-agent\\src\\tools\\base.py"
            ],
            "timeout": 120,
            "stream": True
        }
    )

    print(f"Success: {result['success']}")
    print(f"Duration: {result['metadata']['duration']:.2f}s")
    print(f"Files included: {result['metadata']['files_included']}")
    if result['success']:
        print(f"Output:\n{result['output']}")
    else:
        print(f"Error: {result['error']}")

    # Example 3: Debugging assistance
    print("\n" + "=" * 60)
    print("Example 3: Debugging assistance")
    print("=" * 60)

    instructions = """
    I have a function that's throwing an error. Help me debug it:

    def divide_numbers(a, b):
        return a / b

    # This crashes when b is 0
    result = divide_numbers(10, 0)
    """

    result = await tool.execute(
        instructions=instructions,
        context={
            "timeout": 60
        }
    )

    print(f"Success: {result['success']}")
    print(f"Duration: {result['metadata']['duration']:.2f}s")
    if result['success']:
        print(f"Output:\n{result['output']}")
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
