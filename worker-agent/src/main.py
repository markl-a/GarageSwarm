"""Worker Agent CLI entry point"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
import structlog

from agent import WorkerAgent
from config import load_config


def setup_logging(debug: bool = False):
    """Setup structured logging

    Args:
        debug: Enable debug level logging
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Multi-Agent Worker Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default config
  python src/main.py

  # Start with custom config
  python src/main.py --config /path/to/config.yaml

  # Start with debug logging
  python src/main.py --debug

For more information, see: README.md
        """
    )

    parser.add_argument(
        "--config",
        default="config/agent.yaml",
        help="Path to configuration file (default: config/agent.yaml)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="GarageSwarm Worker v0.0.1"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(debug=args.debug)
    logger = structlog.get_logger()

    logger.info(
        "Multi-Agent Worker Agent starting",
        version="0.0.1",
        config=args.config
    )

    agent = None

    try:
        # Load configuration
        config = load_config(args.config)

        # Create Worker Agent
        agent = WorkerAgent(config)

        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        agent.setup_signal_handlers(loop)

        # Register AI tools based on config
        # tools can be a list (e.g., ["claude_code", "gemini_cli"]) or a dict
        tools_list = config.get("tools", [])
        if isinstance(tools_list, dict):
            tools_list = list(tools_list.keys())
        registered_tools = []

        # Register Claude Code if configured
        if "claude_code" in tools_list:
            try:
                from tools.claude_code import ClaudeCodeTool
                # Get config from separate 'claude' section
                claude_config = config.get("claude", {})
                claude_tool = ClaudeCodeTool(claude_config)

                # Validate configuration
                if await claude_tool.validate_config():
                    agent.register_tool("claude_code", claude_tool)
                    registered_tools.append("claude_code")
                    logger.info("Claude Code tool registered successfully")
                else:
                    logger.warning("Claude Code tool validation failed, skipping registration")
            except Exception as e:
                logger.error("Failed to register Claude Code tool", error=str(e))

        # Register Gemini CLI if configured
        if "gemini_cli" in tools_list:
            try:
                from tools.gemini_cli import GeminiCLI
                # Get config from separate 'gemini' section
                gemini_config = config.get("gemini", {})
                gemini_tool = GeminiCLI(gemini_config)

                # Validate configuration
                if await gemini_tool.validate_config():
                    agent.register_tool("gemini_cli", gemini_tool)
                    registered_tools.append("gemini_cli")
                    logger.info("Gemini CLI tool registered successfully")
                else:
                    logger.warning("Gemini CLI tool validation failed, skipping registration")
            except Exception as e:
                logger.error("Failed to register Gemini CLI tool", error=str(e))

        # Register Ollama if configured
        if "ollama" in tools_list:
            try:
                from tools.ollama import OllamaTool
                # Get config from separate 'ollama' section
                ollama_config = config.get("ollama", {})
                ollama_tool = OllamaTool(ollama_config)

                # Validate configuration
                if await ollama_tool.validate_config():
                    agent.register_tool("ollama", ollama_tool)
                    registered_tools.append("ollama")
                    logger.info("Ollama tool registered successfully")
                else:
                    logger.warning("Ollama tool validation failed, skipping registration")
            except Exception as e:
                logger.error("Failed to register Ollama tool", error=str(e))

        if not registered_tools:
            logger.warning("No AI tools registered! Worker will not be able to execute tasks.")
        else:
            logger.info("AI tools registered", tools=registered_tools)

        logger.info("Worker Agent initialized", machine_id=agent.machine_id, tools=registered_tools)

        # Start agent
        await agent.start()

        # Keep running until shutdown signal
        logger.info("Worker Agent running. Press Ctrl+C to stop gracefully.")
        await agent.wait_for_shutdown()

    except FileNotFoundError as e:
        logger.error("Configuration file not found", error=str(e))
        sys.exit(1)

    except ValueError as e:
        logger.error("Configuration error", error=str(e))
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        if agent:
            await agent.stop()

    except Exception as e:
        logger.error("Fatal error", error=str(e), exc_info=True)
        if agent:
            await agent.stop()
        sys.exit(1)

    logger.info("Worker Agent shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
