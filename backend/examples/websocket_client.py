"""
WebSocket Client Example

Demonstrates how to connect to the WebSocket log streaming API and receive real-time logs.
"""

import asyncio
import json
import sys
from typing import Optional
from uuid import UUID

try:
    import websockets
except ImportError:
    print("Error: websockets package not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


class LogStreamClient:
    """
    WebSocket client for real-time log streaming

    Example usage:
        client = LogStreamClient("550e8400-e29b-41d4-a716-446655440000")
        await client.connect()
        await client.listen()
    """

    def __init__(self, task_id: str, base_url: str = "ws://localhost:8000"):
        """
        Initialize log stream client

        Args:
            task_id: Task UUID to subscribe to
            base_url: WebSocket base URL (default: ws://localhost:8000)
        """
        self.task_id = task_id
        self.base_url = base_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None

    async def connect(self):
        """Establish WebSocket connection"""
        uri = f"{self.base_url}/api/v1/ws/tasks/{self.task_id}/logs"
        print(f"Connecting to {uri}...")

        try:
            self.websocket = await websockets.connect(uri)
            print("✓ Connected successfully")
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            raise

    async def listen(self):
        """
        Listen for incoming messages

        Continuously receives and processes messages until connection is closed.
        """
        if not self.websocket:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            print("\n✗ Connection closed by server")
        except KeyboardInterrupt:
            print("\n✓ Disconnected by user")
        finally:
            await self.close()

    async def send_ping(self):
        """Send ping message to check connection"""
        if not self.websocket:
            raise RuntimeError("Not connected")

        await self.websocket.send(json.dumps({"action": "ping"}))

    async def subscribe_to_task(self, task_id: str):
        """
        Subscribe to additional task

        Args:
            task_id: Task UUID to subscribe to
        """
        if not self.websocket:
            raise RuntimeError("Not connected")

        message = {
            "action": "subscribe",
            "task_id": task_id
        }
        await self.websocket.send(json.dumps(message))
        print(f"→ Subscribing to task {task_id}")

    async def unsubscribe_from_task(self, task_id: str):
        """
        Unsubscribe from task

        Args:
            task_id: Task UUID to unsubscribe from
        """
        if not self.websocket:
            raise RuntimeError("Not connected")

        message = {
            "action": "unsubscribe",
            "task_id": task_id
        }
        await self.websocket.send(json.dumps(message))
        print(f"→ Unsubscribing from task {task_id}")

    async def _handle_message(self, message: str):
        """
        Handle incoming WebSocket message

        Args:
            message: Raw message string
        """
        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "subscribed":
                self._handle_subscribed(data)
            elif message_type == "unsubscribed":
                self._handle_unsubscribed(data)
            elif message_type == "log":
                self._handle_log(data)
            elif message_type == "pong":
                self._handle_pong(data)
            elif message_type == "error":
                self._handle_error(data)
            else:
                print(f"⚠ Unknown message type: {message_type}")

        except json.JSONDecodeError:
            print(f"⚠ Failed to parse message: {message}")

    def _handle_subscribed(self, data: dict):
        """Handle subscription confirmation"""
        task_id = data.get("data", {}).get("task_id")
        print(f"✓ Subscribed to task: {task_id}")

    def _handle_unsubscribed(self, data: dict):
        """Handle unsubscription confirmation"""
        task_id = data.get("data", {}).get("task_id")
        print(f"✓ Unsubscribed from task: {task_id}")

    def _handle_log(self, data: dict):
        """Handle log message"""
        log = data.get("data", {})

        # Extract log details
        level = log.get("level", "info").upper()
        message = log.get("message", "")
        timestamp = log.get("timestamp", "")
        worker_name = log.get("worker_name", "unknown")
        subtask_id = log.get("subtask_id", "")

        # Color codes for log levels
        colors = {
            "DEBUG": "\033[36m",    # Cyan
            "INFO": "\033[32m",     # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",    # Red
        }
        reset = "\033[0m"

        color = colors.get(level, "")

        # Format and print log
        print(f"{color}[{level}]{reset} [{timestamp[:19]}] [{worker_name}] {message}")

        # Print metadata if present
        metadata = log.get("metadata")
        if metadata:
            print(f"       Metadata: {json.dumps(metadata, indent=2)}")

    def _handle_pong(self, data: dict):
        """Handle pong response"""
        timestamp = data.get("timestamp", "")
        print(f"✓ Pong received at {timestamp}")

    def _handle_error(self, data: dict):
        """Handle error message"""
        error = data.get("data", {}).get("message", "Unknown error")
        print(f"✗ Error: {error}")

    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            print("✓ Connection closed")


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python websocket_client.py <task_id> [base_url]")
        print("\nExample:")
        print("  python websocket_client.py 550e8400-e29b-41d4-a716-446655440000")
        print("  python websocket_client.py 550e8400-e29b-41d4-a716-446655440000 ws://localhost:8000")
        sys.exit(1)

    task_id = sys.argv[1]
    base_url = sys.argv[2] if len(sys.argv) > 2 else "ws://localhost:8000"

    # Validate task_id format
    try:
        UUID(task_id)
    except ValueError:
        print(f"✗ Invalid task_id format: {task_id}")
        print("Task ID must be a valid UUID")
        sys.exit(1)

    # Create and connect client
    client = LogStreamClient(task_id, base_url)

    try:
        await client.connect()
        print("\nListening for logs... (Press Ctrl+C to stop)\n")
        print("-" * 80)
        await client.listen()
    except KeyboardInterrupt:
        print("\n✓ Shutting down...")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
