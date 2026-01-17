"""
Worker Log Sender Example

Demonstrates how workers can send log messages during subtask execution.
"""

import asyncio
import sys
from typing import Optional
from uuid import UUID

try:
    import httpx
except ImportError:
    print("Error: httpx package not installed")
    print("Install with: pip install httpx")
    sys.exit(1)


class WorkerLogger:
    """
    Worker logger for sending logs to the backend

    Example usage:
        logger = WorkerLogger("550e8400-e29b-41d4-a716-446655440001")
        await logger.info("Processing started")
        await logger.error("Failed to load file", metadata={"file": "data.json"})
    """

    def __init__(self, subtask_id: str, base_url: str = "http://localhost:8000"):
        """
        Initialize worker logger

        Args:
            subtask_id: Subtask UUID
            base_url: Backend base URL (default: http://localhost:8000)
        """
        self.subtask_id = subtask_id
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def send_log(
        self,
        level: str,
        message: str,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Send a log message to the backend

        Args:
            level: Log level (debug | info | warning | error)
            message: Log message content
            metadata: Optional metadata dict

        Returns:
            Response from the backend

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.base_url}/api/v1/subtasks/{self.subtask_id}/log"

        payload = {
            "level": level,
            "message": message,
            "metadata": metadata or {}
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"✗ Failed to send log: {e}")
            raise

    async def debug(self, message: str, metadata: Optional[dict] = None):
        """Send debug log"""
        return await self.send_log("debug", message, metadata)

    async def info(self, message: str, metadata: Optional[dict] = None):
        """Send info log"""
        return await self.send_log("info", message, metadata)

    async def warning(self, message: str, metadata: Optional[dict] = None):
        """Send warning log"""
        return await self.send_log("warning", message, metadata)

    async def error(self, message: str, metadata: Optional[dict] = None):
        """Send error log"""
        return await self.send_log("error", message, metadata)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


async def simulate_task_execution(subtask_id: str, base_url: str):
    """
    Simulate a task execution with various log messages

    Args:
        subtask_id: Subtask UUID
        base_url: Backend base URL
    """
    logger = WorkerLogger(subtask_id, base_url)

    try:
        print(f"Simulating task execution for subtask: {subtask_id}\n")

        # Start
        result = await logger.info("Task execution started")
        print(f"✓ Sent: Task execution started (broadcasted to {result['broadcasted']} clients)")
        await asyncio.sleep(1)

        # Loading
        result = await logger.debug("Loading configuration file", metadata={"file": "config.json"})
        print(f"✓ Sent: Loading configuration (broadcasted to {result['broadcasted']} clients)")
        await asyncio.sleep(1)

        # Processing
        result = await logger.info("Processing data batch 1/3", metadata={"batch": 1, "total": 3})
        print(f"✓ Sent: Processing batch 1 (broadcasted to {result['broadcasted']} clients)")
        await asyncio.sleep(1.5)

        result = await logger.info("Processing data batch 2/3", metadata={"batch": 2, "total": 3})
        print(f"✓ Sent: Processing batch 2 (broadcasted to {result['broadcasted']} clients)")
        await asyncio.sleep(1.5)

        # Warning
        result = await logger.warning(
            "High memory usage detected",
            metadata={"memory_percent": 85, "threshold": 80}
        )
        print(f"✓ Sent: High memory warning (broadcasted to {result['broadcasted']} clients)")
        await asyncio.sleep(1)

        result = await logger.info("Processing data batch 3/3", metadata={"batch": 3, "total": 3})
        print(f"✓ Sent: Processing batch 3 (broadcasted to {result['broadcasted']} clients)")
        await asyncio.sleep(1.5)

        # Completion
        result = await logger.info(
            "Task execution completed successfully",
            metadata={"duration_seconds": 8, "records_processed": 1500}
        )
        print(f"✓ Sent: Task completed (broadcasted to {result['broadcasted']} clients)")

        print("\n✓ Simulation completed successfully")

    except Exception as e:
        print(f"\n✗ Simulation failed: {e}")
        try:
            await logger.error(f"Task execution failed: {str(e)}")
        except:
            pass
    finally:
        await logger.close()


async def send_single_log(
    subtask_id: str,
    level: str,
    message: str,
    base_url: str,
    metadata: Optional[dict] = None
):
    """
    Send a single log message

    Args:
        subtask_id: Subtask UUID
        level: Log level
        message: Log message
        base_url: Backend base URL
        metadata: Optional metadata
    """
    logger = WorkerLogger(subtask_id, base_url)

    try:
        result = await logger.send_log(level, message, metadata)
        print(f"✓ Log sent successfully")
        print(f"  Level: {level}")
        print(f"  Message: {message}")
        print(f"  Broadcasted to: {result['broadcasted']} clients")

        if metadata:
            print(f"  Metadata: {metadata}")

    except Exception as e:
        print(f"✗ Failed to send log: {e}")
        sys.exit(1)
    finally:
        await logger.close()


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  1. Simulate task execution with multiple logs:")
        print("     python send_log_example.py simulate <subtask_id> [base_url]")
        print("\n  2. Send a single log message:")
        print("     python send_log_example.py send <subtask_id> <level> <message> [base_url]")
        print("\nExamples:")
        print("  python send_log_example.py simulate 550e8400-e29b-41d4-a716-446655440001")
        print("  python send_log_example.py send 550e8400-e29b-41d4-a716-446655440001 info \"Processing data\"")
        sys.exit(1)

    command = sys.argv[1]

    if command == "simulate":
        if len(sys.argv) < 3:
            print("✗ Error: subtask_id required")
            print("Usage: python send_log_example.py simulate <subtask_id> [base_url]")
            sys.exit(1)

        subtask_id = sys.argv[2]
        base_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"

        # Validate subtask_id
        try:
            UUID(subtask_id)
        except ValueError:
            print(f"✗ Invalid subtask_id format: {subtask_id}")
            sys.exit(1)

        await simulate_task_execution(subtask_id, base_url)

    elif command == "send":
        if len(sys.argv) < 5:
            print("✗ Error: subtask_id, level, and message required")
            print("Usage: python send_log_example.py send <subtask_id> <level> <message> [base_url]")
            sys.exit(1)

        subtask_id = sys.argv[2]
        level = sys.argv[3]
        message = sys.argv[4]
        base_url = sys.argv[5] if len(sys.argv) > 5 else "http://localhost:8000"

        # Validate inputs
        try:
            UUID(subtask_id)
        except ValueError:
            print(f"✗ Invalid subtask_id format: {subtask_id}")
            sys.exit(1)

        if level not in ["debug", "info", "warning", "error"]:
            print(f"✗ Invalid level: {level}")
            print("Valid levels: debug, info, warning, error")
            sys.exit(1)

        await send_single_log(subtask_id, level, message, base_url)

    else:
        print(f"✗ Unknown command: {command}")
        print("Valid commands: simulate, send")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
