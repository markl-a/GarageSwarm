"""Example usage of AI Tool Health Checker

This script demonstrates how to use the health checker to monitor AI tool availability.
"""

import asyncio
import json
import os
from health_checker import ToolHealthChecker, HealthStatus, quick_health_check


async def example_basic_check():
    """Basic health check example"""
    print("=" * 60)
    print("BASIC HEALTH CHECK")
    print("=" * 60)

    checker = ToolHealthChecker(timeout=10.0)

    # Check all tools
    result = await checker.check_all_tools()

    print(f"\nTimestamp: {result['timestamp']}")
    print(f"Duration: {result['duration']:.2f}s")
    print(f"Overall Status: {result['overall_status']}")
    print("\n" + "-" * 60)

    # Display each tool status
    for tool_name, status in result['tools'].items():
        print(f"\n{status['name']}:")
        print(f"  Status: {status['status']}")
        print(f"  Available: {status['available']}")

        if status.get('version'):
            print(f"  Version: {status['version']}")

        if status.get('latency') is not None:
            print(f"  Latency: {status['latency']:.2f}ms")

        if status.get('error'):
            print(f"  Error: {status['error']}")

    # Display summary
    print("\n" + "-" * 60)
    print("SUMMARY:")
    summary = result['summary']
    print(f"  Total tools: {summary['total_count']}")
    print(f"  Healthy: {summary['healthy_count']}")
    print(f"  Degraded: {summary['degraded_count']}")
    print(f"  Unhealthy: {summary['unhealthy_count']}")


async def example_individual_checks():
    """Individual tool check examples"""
    print("\n\n" + "=" * 60)
    print("INDIVIDUAL TOOL CHECKS")
    print("=" * 60)

    checker = ToolHealthChecker()

    # Check Claude Code
    print("\nChecking Claude Code...")
    claude_status = await checker.check_claude_code({
        "cli_path": "claude"  # Or custom path
    })
    print(f"  Status: {claude_status['status']}")
    print(f"  Available: {claude_status['available']}")

    # Check Gemini
    print("\nChecking Gemini...")
    gemini_status = await checker.check_gemini({
        "api_key": os.environ.get("GOOGLE_API_KEY"),
        "model": "gemini-1.5-flash"
    })
    print(f"  Status: {gemini_status['status']}")
    print(f"  Configured: {gemini_status['configured']}")
    print(f"  Available: {gemini_status['available']}")

    # Check Ollama
    print("\nChecking Ollama...")
    ollama_status = await checker.check_ollama({
        "url": "http://localhost:11434",
        "model": "llama2"
    })
    print(f"  Status: {ollama_status['status']}")
    print(f"  Available: {ollama_status['available']}")
    if ollama_status['models_available']:
        print(f"  Models: {', '.join(ollama_status['models_available'])}")


async def example_quick_check():
    """Quick health check example"""
    print("\n\n" + "=" * 60)
    print("QUICK HEALTH CHECK")
    print("=" * 60)

    # Check all tools with quick timeout
    result = await quick_health_check()

    print(f"\nOverall Status: {result.get('overall_status', 'N/A')}")
    print(f"Duration: {result.get('duration', 0):.2f}s")


async def example_specific_tools():
    """Check specific tools only"""
    print("\n\n" + "=" * 60)
    print("SPECIFIC TOOLS CHECK")
    print("=" * 60)

    # Only check Claude Code and Gemini
    result = await quick_health_check(
        tools=["claude_code", "gemini"],
        config={
            "claude_code": {"cli_path": "claude"},
            "gemini": {"api_key": os.environ.get("GOOGLE_API_KEY")}
        }
    )

    print("\nChecked tools:")
    for tool_name, status in result['tools'].items():
        print(f"  {tool_name}: {status['status']}")


async def example_with_config():
    """Health check with custom configuration"""
    print("\n\n" + "=" * 60)
    print("HEALTH CHECK WITH CUSTOM CONFIG")
    print("=" * 60)

    checker = ToolHealthChecker(timeout=15.0)

    config = {
        "claude_code": {
            "cli_path": "claude"
        },
        "gemini": {
            "api_key": os.environ.get("GOOGLE_API_KEY"),
            "model": "gemini-1.5-pro"  # Use pro model
        },
        "ollama": {
            "url": "http://localhost:11434",
            "model": "codellama"  # Check for specific model
        }
    }

    result = await checker.check_all_tools(config)

    print(f"\nOverall Status: {result['overall_status']}")

    for tool_name, status in result['tools'].items():
        print(f"\n{status['name']}:")
        print(f"  Status: {status['status']}")

        if tool_name == "gemini" and status.get('model'):
            print(f"  Model: {status['model']}")

        if tool_name == "ollama" and status.get('models_available'):
            print(f"  Available Models: {status['models_available']}")


async def example_json_output():
    """Output health check as JSON"""
    print("\n\n" + "=" * 60)
    print("JSON OUTPUT")
    print("=" * 60)

    checker = ToolHealthChecker()
    result = await checker.check_all_tools()

    # Convert to JSON for API responses or logging
    json_output = json.dumps(result, indent=2, default=str)
    print("\n" + json_output)


async def example_graceful_degradation():
    """Example of handling degraded tools gracefully"""
    print("\n\n" + "=" * 60)
    print("GRACEFUL DEGRADATION EXAMPLE")
    print("=" * 60)

    checker = ToolHealthChecker()
    result = await checker.check_all_tools()

    # Determine available tools
    available_tools = []
    for tool_name, status in result['tools'].items():
        if status['status'] in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
            available_tools.append(tool_name)

    print(f"\nAvailable tools for use: {', '.join(available_tools)}")

    # Example: Select best available tool
    if "claude_code" in available_tools:
        print("\nRecommendation: Use Claude Code (primary choice)")
    elif "gemini" in available_tools:
        print("\nRecommendation: Use Gemini (fallback)")
    elif "ollama" in available_tools:
        print("\nRecommendation: Use Ollama (local fallback)")
    else:
        print("\nWarning: No AI tools available!")


async def example_continuous_monitoring():
    """Example of continuous health monitoring"""
    print("\n\n" + "=" * 60)
    print("CONTINUOUS MONITORING (3 checks)")
    print("=" * 60)

    checker = ToolHealthChecker(timeout=5.0)

    for i in range(3):
        print(f"\n--- Check #{i+1} ---")

        result = await checker.check_all_tools()

        print(f"Overall Status: {result['overall_status']}")
        print(f"Healthy: {result['summary']['healthy_count']}/{result['summary']['total_count']}")

        # Wait before next check
        if i < 2:
            await asyncio.sleep(2)


async def main():
    """Run all examples"""
    print("AI TOOL HEALTH CHECKER - EXAMPLES")
    print("=" * 60)

    try:
        # Run examples
        await example_basic_check()
        await example_individual_checks()
        await example_quick_check()
        await example_specific_tools()
        await example_with_config()
        await example_json_output()
        await example_graceful_degradation()
        await example_continuous_monitoring()

        print("\n\n" + "=" * 60)
        print("ALL EXAMPLES COMPLETED")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
