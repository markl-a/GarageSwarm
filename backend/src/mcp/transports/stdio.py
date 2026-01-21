"""
STDIO Transport for MCP

Implements the STDIO transport layer for MCP communication.
This transport spawns a subprocess and communicates via stdin/stdout
using newline-delimited JSON-RPC messages.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from typing import Any, Dict, List, Optional, Union

from .base import (
    JsonRpcNotification,
    JsonRpcRequest,
    JsonRpcResponse,
    Transport,
    TransportConfig,
    TransportConnectionError,
    TransportError,
    TransportProtocolError,
    TransportTimeoutError,
    TransportType,
)

logger = logging.getLogger(__name__)


class STDIOTransport(Transport):
    """
    STDIO Transport for MCP servers.

    This transport spawns an MCP server as a subprocess and communicates
    with it via stdin (for sending) and stdout (for receiving) using
    newline-delimited JSON-RPC messages.

    Example:
        config = TransportConfig(
            transport_type=TransportType.STDIO,
            command="node",
            args=["mcp-server.js"],
            env={"NODE_ENV": "production"},
        )
        async with STDIOTransport(config) as transport:
            response = await transport.request("initialize", {"capabilities": {}})
    """

    def __init__(
        self,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        timeout: float = 30.0,
        read_timeout: float = 60.0,
        config: Optional[TransportConfig] = None,
    ):
        """
        Initialize STDIO transport.

        Can be initialized either with individual parameters or a TransportConfig.

        Args:
            command: Command to execute
            args: Command arguments
            env: Environment variables for subprocess
            cwd: Working directory for subprocess
            timeout: Default timeout for operations
            read_timeout: Timeout for read operations
            config: Full transport configuration (overrides other params if provided)
        """
        if config is None:
            config = TransportConfig(
                transport_type=TransportType.STDIO,
                command=command,
                args=args or [],
                env=env,
                cwd=cwd,
                timeout=timeout,
                read_timeout=read_timeout,
            )

        super().__init__(config)

        self._process: Optional[asyncio.subprocess.Process] = None
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._pending_responses: Dict[Union[int, str], asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self._stderr_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    @property
    def process(self) -> Optional[asyncio.subprocess.Process]:
        """Get the subprocess if connected."""
        return self._process

    def _build_env(self) -> Dict[str, str]:
        """Build environment variables for the subprocess."""
        # Start with current environment
        env = os.environ.copy()

        # Override/add configured environment variables
        if self._config.env:
            env.update(self._config.env)

        return env

    async def connect(self) -> None:
        """
        Start the MCP server subprocess.

        Raises:
            TransportConnectionError: If the subprocess fails to start
        """
        if self._connected:
            logger.warning("Transport already connected")
            return

        if not self._config.command:
            raise TransportConnectionError("No command specified for STDIO transport")

        command = self._config.command
        args = self._config.args or []
        env = self._build_env()
        cwd = self._config.cwd

        logger.info(f"Starting MCP server: {command} {' '.join(args)}")

        try:
            # Build the full command
            full_command = [command] + args

            # Create subprocess with pipes for stdin, stdout, stderr
            self._process = await asyncio.create_subprocess_exec(
                *full_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd,
                # On Windows, we need to avoid creating a new console window
                creationflags=getattr(asyncio.subprocess, "CREATE_NO_WINDOW", 0)
                if sys.platform == "win32"
                else 0,
            )

            self._connected = True
            self._shutdown_event.clear()

            # Start background reader task
            self._reader_task = asyncio.create_task(
                self._read_loop(), name="mcp-stdio-reader"
            )

            # Start stderr reader task for logging
            self._stderr_task = asyncio.create_task(
                self._stderr_loop(), name="mcp-stdio-stderr"
            )

            logger.info(f"MCP server started with PID: {self._process.pid}")

        except FileNotFoundError as e:
            raise TransportConnectionError(
                f"Command not found: {command}", cause=e
            )
        except PermissionError as e:
            raise TransportConnectionError(
                f"Permission denied executing: {command}", cause=e
            )
        except Exception as e:
            raise TransportConnectionError(
                f"Failed to start subprocess: {e}", cause=e
            )

    async def _read_loop(self) -> None:
        """
        Background task that continuously reads from stdout.

        Parses JSON-RPC messages and dispatches responses to waiting futures.
        """
        if not self._process or not self._process.stdout:
            return

        try:
            while not self._shutdown_event.is_set():
                try:
                    # Read a line from stdout
                    line = await asyncio.wait_for(
                        self._process.stdout.readline(),
                        timeout=1.0,  # Short timeout to check shutdown event
                    )

                    if not line:
                        # EOF - process has closed stdout
                        logger.warning("MCP server closed stdout")
                        break

                    # Decode and parse the JSON-RPC message
                    try:
                        line_str = line.decode("utf-8").strip()
                        if not line_str:
                            continue

                        logger.debug(f"Received: {line_str[:200]}...")
                        data = json.loads(line_str)

                        # Create response object
                        response = JsonRpcResponse(
                            jsonrpc=data.get("jsonrpc", "2.0"),
                            id=data.get("id"),
                            result=data.get("result"),
                            error=data.get("error"),
                        )

                        # Dispatch to waiting future if there's an ID
                        if response.id is not None:
                            future = self._pending_responses.pop(response.id, None)
                            if future and not future.done():
                                future.set_result(response)
                            else:
                                logger.warning(
                                    f"Received response for unknown request ID: {response.id}"
                                )
                        else:
                            # This is a notification from the server
                            logger.debug(f"Received server notification: {data}")

                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON from MCP server: {e}")
                        logger.debug(f"Raw line: {line}")

                except asyncio.TimeoutError:
                    # Normal timeout, just continue the loop
                    continue

        except asyncio.CancelledError:
            logger.debug("Read loop cancelled")
        except Exception as e:
            logger.error(f"Error in read loop: {e}")
        finally:
            # Cancel any pending futures
            for request_id, future in self._pending_responses.items():
                if not future.done():
                    future.set_exception(
                        TransportConnectionError("Connection closed")
                    )
            self._pending_responses.clear()

    async def _stderr_loop(self) -> None:
        """Background task that reads and logs stderr output."""
        if not self._process or not self._process.stderr:
            return

        try:
            while not self._shutdown_event.is_set():
                try:
                    line = await asyncio.wait_for(
                        self._process.stderr.readline(),
                        timeout=1.0,
                    )

                    if not line:
                        break

                    line_str = line.decode("utf-8").strip()
                    if line_str:
                        logger.debug(f"MCP server stderr: {line_str}")

                except asyncio.TimeoutError:
                    continue

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error reading stderr: {e}")

    async def send(self, message: Union[JsonRpcRequest, JsonRpcNotification]) -> None:
        """
        Send a JSON-RPC message to the MCP server via stdin.

        Args:
            message: The JSON-RPC request or notification to send

        Raises:
            TransportConnectionError: If not connected
            TransportError: If send fails
        """
        if not self._connected or not self._process or not self._process.stdin:
            raise TransportConnectionError("Transport not connected")

        # Serialize message to JSON
        message_dict = message.model_dump(exclude_none=True)
        message_json = json.dumps(message_dict, separators=(",", ":"))
        message_bytes = (message_json + "\n").encode("utf-8")

        logger.debug(f"Sending: {message_json[:200]}...")

        async with self._write_lock:
            try:
                self._process.stdin.write(message_bytes)
                await self._process.stdin.drain()
            except (BrokenPipeError, ConnectionError) as e:
                self._connected = False
                raise TransportConnectionError("Pipe to MCP server broken", cause=e)
            except Exception as e:
                raise TransportError(f"Failed to send message: {e}", cause=e)

    async def receive(self, timeout: Optional[float] = None) -> JsonRpcResponse:
        """
        Receive a JSON-RPC response from the MCP server.

        Note: This method is typically used internally by the request() method.
        Direct use is discouraged as responses are dispatched by the read loop.

        Args:
            timeout: Optional timeout override

        Returns:
            The JSON-RPC response

        Raises:
            TransportTimeoutError: If receive times out
            TransportConnectionError: If not connected
        """
        if not self._connected:
            raise TransportConnectionError("Transport not connected")

        # This is a fallback method - normally responses come through the read loop
        # and are matched by request ID
        raise TransportProtocolError(
            "Direct receive() not supported. Use request() method instead."
        )

    async def _wait_for_response(
        self, request_id: Union[int, str], timeout: Optional[float] = None
    ) -> JsonRpcResponse:
        """
        Wait for a response with the given request ID.

        Args:
            request_id: The request ID to wait for
            timeout: Timeout in seconds

        Returns:
            The JSON-RPC response

        Raises:
            TransportTimeoutError: If the wait times out
        """
        timeout = timeout or self._config.read_timeout

        # Create a future for this request
        future: asyncio.Future[JsonRpcResponse] = asyncio.get_event_loop().create_future()
        self._pending_responses[request_id] = future

        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            # Remove the pending future
            self._pending_responses.pop(request_id, None)
            raise TransportTimeoutError(
                f"Timeout waiting for response to request {request_id}"
            )

    async def request(
        self, method: str, params: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None
    ) -> JsonRpcResponse:
        """
        Send a request and wait for the response.

        Args:
            method: The method name to invoke
            params: Optional method parameters
            timeout: Optional timeout override

        Returns:
            The JSON-RPC response

        Raises:
            TransportError: If the request fails
            TransportTimeoutError: If the request times out
        """
        if not self._connected:
            raise TransportConnectionError("Transport not connected")

        request_id = self._next_message_id()
        request = JsonRpcRequest(
            id=request_id,
            method=method,
            params=params,
        )

        # Send the request
        await self.send(request)

        # Wait for the response
        return await self._wait_for_response(request_id, timeout)

    async def close(self) -> None:
        """
        Close the transport and terminate the subprocess.

        This method is safe to call multiple times.
        """
        if not self._connected:
            return

        logger.info("Closing STDIO transport")
        self._connected = False
        self._shutdown_event.set()

        # Cancel background tasks
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        if self._stderr_task and not self._stderr_task.done():
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass

        # Close stdin to signal the subprocess
        if self._process and self._process.stdin:
            try:
                self._process.stdin.close()
                await self._process.stdin.wait_closed()
            except Exception as e:
                logger.debug(f"Error closing stdin: {e}")

        # Wait for process to terminate gracefully
        if self._process:
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
                logger.info(f"MCP server exited with code: {self._process.returncode}")
            except asyncio.TimeoutError:
                # Force terminate if it doesn't exit gracefully
                logger.warning("MCP server did not exit gracefully, terminating")
                try:
                    if sys.platform == "win32":
                        self._process.terminate()
                    else:
                        self._process.send_signal(signal.SIGTERM)

                    await asyncio.wait_for(self._process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    logger.warning("MCP server did not respond to SIGTERM, killing")
                    self._process.kill()
                    await self._process.wait()
                except Exception as e:
                    logger.error(f"Error terminating process: {e}")

        self._process = None
        self._reader_task = None
        self._stderr_task = None

        logger.info("STDIO transport closed")

    async def health_check(self) -> bool:
        """
        Check if the transport and subprocess are healthy.

        Returns:
            True if the transport is connected and subprocess is running
        """
        if not self._connected or not self._process:
            return False

        # Check if process is still running
        if self._process.returncode is not None:
            logger.warning(f"MCP server has exited with code: {self._process.returncode}")
            self._connected = False
            return False

        return True

    def __repr__(self) -> str:
        """String representation of the transport."""
        status = "connected" if self._connected else "disconnected"
        pid = self._process.pid if self._process else "N/A"
        return (
            f"STDIOTransport(command={self._config.command}, "
            f"status={status}, pid={pid})"
        )
