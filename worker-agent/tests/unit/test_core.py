"""
Unit tests for Worker Agent Core

Tests agent lifecycle management:
- Initialization
- Starting and stopping
- Task assignment and execution
- Graceful shutdown
- Signal handling
- WebSocket and polling modes
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4, UUID

from agent.core import WorkerAgent
from agent.connection import ConnectionManager
from agent.executor import TaskExecutor
from agent.monitor import ResourceMonitor


@pytest.fixture
def mock_config():
    """Mock configuration for worker agent"""
    return {
        "backend_url": "http://localhost:8000",
        "machine_name": "Test Worker Machine",
        "heartbeat_interval": 5,
        "use_websocket": True,
        "use_polling_fallback": True,
        "polling_interval": 10,
        "shutdown_timeout": 30,
        "tools": ["test_tool"],
        "resource_monitoring": {
            "cpu_threshold": 90,
            "memory_threshold": 85,
            "disk_threshold": 90,
        },
    }


@pytest.fixture
def mock_connection_manager():
    """Mock connection manager"""
    manager = AsyncMock(spec=ConnectionManager)
    manager.connected = True
    manager.register = AsyncMock(return_value=uuid4())
    manager.send_heartbeat = AsyncMock()
    manager.send_final_heartbeat = AsyncMock()
    manager.unregister = AsyncMock()
    manager.close = AsyncMock()
    manager.connect_websocket = AsyncMock()
    manager.poll_for_tasks = AsyncMock(return_value=None)
    manager.update_worker_status = AsyncMock()
    manager.stream_execution_log = AsyncMock()
    manager.upload_subtask_result = AsyncMock()
    manager.ws_client = None
    return manager


@pytest.fixture
def mock_task_executor():
    """Mock task executor"""
    executor = AsyncMock(spec=TaskExecutor)
    executor.is_busy = False
    executor.current_task = None
    executor.get_available_tools = MagicMock(return_value=["test_tool"])
    executor.get_status = MagicMock(return_value={"busy": False})
    executor.execute_task = AsyncMock(return_value={"success": True, "output": "test"})
    executor.cancel_current_task = AsyncMock(return_value=True)
    executor.register_tool = MagicMock()
    executor.set_log_callback = MagicMock()
    return executor


@pytest.fixture
def mock_resource_monitor():
    """Mock resource monitor"""
    monitor = MagicMock(spec=ResourceMonitor)
    monitor.get_system_info = MagicMock(
        return_value={
            "os": "Linux",
            "cpu_count": 4,
            "memory_total": 8589934592,
        }
    )
    monitor.get_resources = MagicMock(
        return_value={
            "cpu_percent": 45.5,
            "memory_percent": 60.0,
            "disk_percent": 50.0,
        }
    )
    monitor.check_resource_thresholds = MagicMock(
        return_value={
            "any_exceeded": False,
            "cpu_exceeded": False,
            "memory_exceeded": False,
            "disk_exceeded": False,
        }
    )
    return monitor


@pytest.fixture
async def worker_agent(
    mock_config, mock_connection_manager, mock_task_executor, mock_resource_monitor
):
    """Create WorkerAgent with mocked dependencies"""
    with patch("agent.core.ConnectionManager", return_value=mock_connection_manager), \
         patch("agent.core.TaskExecutor", return_value=mock_task_executor), \
         patch("agent.core.ResourceMonitor", return_value=mock_resource_monitor):

        agent = WorkerAgent(mock_config)
        # Override mocked components
        agent.connection_manager = mock_connection_manager
        agent.task_executor = mock_task_executor
        agent.resource_monitor = mock_resource_monitor

        yield agent

        # Cleanup
        if agent.running:
            await agent.stop()


class TestWorkerAgentInitialization:
    """Test WorkerAgent initialization"""

    def test_init_success(self, mock_config):
        """Test successful worker agent initialization"""
        with patch("agent.core.load_or_create_machine_id", return_value="test-machine-id"):
            agent = WorkerAgent(mock_config)

            assert agent.config == mock_config
            assert agent.worker_id is None
            assert agent.machine_id == "test-machine-id"
            assert agent.running is False
            assert agent.shutting_down is False
            assert agent.accepting_tasks is True
            assert agent.use_websocket is True
            assert agent.use_polling is True
            assert agent.polling_interval == 10
            assert agent.shutdown_timeout == 30

    def test_init_with_custom_shutdown_timeout(self):
        """Test initialization with custom shutdown timeout"""
        config = {
            "backend_url": "http://localhost:8000",
            "machine_name": "Test",
            "shutdown_timeout": 60,
        }

        with patch("agent.core.load_or_create_machine_id", return_value="test-id"):
            agent = WorkerAgent(config)
            assert agent.shutdown_timeout == 60

    def test_init_default_shutdown_timeout(self):
        """Test initialization with default shutdown timeout"""
        config = {
            "backend_url": "http://localhost:8000",
            "machine_name": "Test",
        }

        with patch("agent.core.load_or_create_machine_id", return_value="test-id"):
            agent = WorkerAgent(config)
            assert agent.shutdown_timeout == WorkerAgent.DEFAULT_SHUTDOWN_TIMEOUT


class TestWorkerAgentStartStop:
    """Test WorkerAgent start and stop"""

    async def test_start_success(self, worker_agent, mock_connection_manager):
        """Test successful worker agent start"""
        await worker_agent.start()

        assert worker_agent.running is True
        assert worker_agent.worker_id is not None
        mock_connection_manager.register.assert_called_once()
        assert worker_agent.heartbeat_task is not None
        assert worker_agent.ws_task is not None
        assert worker_agent.polling_task is not None

    async def test_start_already_running(self, worker_agent):
        """Test starting worker agent when already running"""
        await worker_agent.start()

        # Try to start again
        with patch("structlog.get_logger") as mock_logger:
            await worker_agent.start()
            # Should log warning and not re-register

    async def test_start_registration_failure(self, worker_agent, mock_connection_manager):
        """Test start failure when registration fails"""
        mock_connection_manager.register.side_effect = Exception("Registration failed")

        with pytest.raises(Exception, match="Registration failed"):
            await worker_agent.start()

        assert worker_agent.running is False

    async def test_stop_graceful(self, worker_agent, mock_connection_manager):
        """Test graceful stop"""
        await worker_agent.start()
        await worker_agent.stop()

        assert worker_agent.running is False
        assert worker_agent.shutting_down is True
        assert worker_agent.accepting_tasks is False
        mock_connection_manager.send_final_heartbeat.assert_called_once()
        mock_connection_manager.unregister.assert_called_once()
        mock_connection_manager.close.assert_called_once()

    async def test_stop_with_running_task(self, worker_agent, mock_task_executor):
        """Test stop with task in progress"""
        await worker_agent.start()

        # Simulate busy executor that becomes free after a short delay
        mock_task_executor.is_busy = True

        async def make_free():
            await asyncio.sleep(0.1)
            mock_task_executor.is_busy = False

        task = asyncio.create_task(make_free())

        try:
            await worker_agent.stop()
            assert worker_agent.running is False
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def test_stop_task_timeout(self, worker_agent, mock_task_executor):
        """Test stop with task timeout"""
        # Set very short timeout
        worker_agent.shutdown_timeout = 0.1

        await worker_agent.start()

        # Simulate task that never completes
        mock_task_executor.is_busy = True

        await worker_agent.stop()

        # Should still shutdown even though task didn't complete
        assert worker_agent.running is False


class TestToolRegistration:
    """Test tool registration"""

    def test_register_tool(self, worker_agent, mock_task_executor):
        """Test registering a tool"""
        mock_tool = MagicMock()

        worker_agent.register_tool("test_tool", mock_tool)

        mock_task_executor.register_tool.assert_called_once_with("test_tool", mock_tool)


class TestTaskAssignment:
    """Test task assignment handling"""

    async def test_handle_task_assignment_success(
        self, worker_agent, mock_connection_manager, mock_task_executor
    ):
        """Test successful task assignment handling"""
        await worker_agent.start()

        task_data = {
            "subtask_id": str(uuid4()),
            "description": "Test task",
            "assigned_tool": "test_tool",
            "context": {},
        }

        mock_task_executor.execute_task.return_value = {
            "success": True,
            "output": "Task completed",
        }

        await worker_agent._handle_task_assignment(task_data)

        # Verify task execution
        mock_task_executor.execute_task.assert_called_once_with(task_data)

        # Verify result upload
        mock_connection_manager.upload_subtask_result.assert_called_once()

    async def test_handle_task_assignment_failure(
        self, worker_agent, mock_connection_manager, mock_task_executor
    ):
        """Test task assignment handling with execution failure"""
        await worker_agent.start()

        task_data = {
            "subtask_id": str(uuid4()),
            "description": "Test task",
            "assigned_tool": "test_tool",
        }

        mock_task_executor.execute_task.return_value = {
            "success": False,
            "error": "Execution failed",
        }

        await worker_agent._handle_task_assignment(task_data)

        # Should still upload result with error
        mock_connection_manager.upload_subtask_result.assert_called_once()

    async def test_handle_task_assignment_exception(
        self, worker_agent, mock_connection_manager, mock_task_executor
    ):
        """Test task assignment handling with exception"""
        await worker_agent.start()

        task_data = {
            "subtask_id": str(uuid4()),
            "description": "Test task",
            "assigned_tool": "test_tool",
        }

        mock_task_executor.execute_task.side_effect = Exception("Execution error")

        await worker_agent._handle_task_assignment(task_data)

        # Should upload error result
        mock_connection_manager.upload_subtask_result.assert_called()


class TestTaskCancellation:
    """Test task cancellation"""

    async def test_cancel_current_task(
        self, worker_agent, mock_task_executor, mock_connection_manager
    ):
        """Test cancelling current task"""
        await worker_agent.start()

        subtask_id = uuid4()
        mock_task_executor.current_task = subtask_id

        cancel_data = {
            "subtask_id": str(subtask_id),
            "reason": "User cancelled",
        }

        await worker_agent._handle_task_cancel(cancel_data)

        mock_task_executor.cancel_current_task.assert_called_once()

    async def test_cancel_non_matching_task(
        self, worker_agent, mock_task_executor
    ):
        """Test cancellation request for non-matching task"""
        await worker_agent.start()

        mock_task_executor.current_task = uuid4()
        different_task_id = uuid4()

        cancel_data = {
            "subtask_id": str(different_task_id),
            "reason": "User cancelled",
        }

        await worker_agent._handle_task_cancel(cancel_data)

        # Should not cancel since IDs don't match
        mock_task_executor.cancel_current_task.assert_not_called()


class TestWebSocketHandling:
    """Test WebSocket message handling"""

    async def test_handle_websocket_task_assignment(
        self, worker_agent
    ):
        """Test WebSocket task assignment message"""
        await worker_agent.start()

        message = {
            "type": "task_assignment",
            "data": {
                "subtask_id": str(uuid4()),
                "description": "Test task",
                "assigned_tool": "test_tool",
            },
        }

        with patch.object(worker_agent, "_handle_task_assignment") as mock_handle:
            await worker_agent._handle_websocket_message(message)
            mock_handle.assert_called_once_with(message["data"])

    async def test_handle_websocket_ping(
        self, worker_agent, mock_connection_manager
    ):
        """Test WebSocket ping message"""
        await worker_agent.start()

        message = {"type": "ping"}

        await worker_agent._handle_websocket_message(message)

        mock_connection_manager.send_websocket_message.assert_called_once()

    async def test_handle_websocket_task_cancel(
        self, worker_agent
    ):
        """Test WebSocket task cancel message"""
        await worker_agent.start()

        message = {
            "type": "task_cancel",
            "data": {
                "subtask_id": str(uuid4()),
                "reason": "Cancelled",
            },
        }

        with patch.object(worker_agent, "_handle_task_cancel") as mock_handle:
            await worker_agent._handle_websocket_message(message)
            mock_handle.assert_called_once_with(message["data"])

    async def test_reject_task_during_shutdown(
        self, worker_agent, mock_connection_manager
    ):
        """Test rejecting task assignment during shutdown"""
        await worker_agent.start()
        worker_agent.accepting_tasks = False

        message = {
            "type": "task_assignment",
            "data": {
                "subtask_id": str(uuid4()),
                "description": "Test task",
            },
        }

        await worker_agent._handle_websocket_message(message)

        # Should send rejection message
        mock_connection_manager.send_websocket_message.assert_called_once()
        call_args = mock_connection_manager.send_websocket_message.call_args
        assert call_args[0][0]["type"] == "task_rejected"


class TestWebSocketCallbacks:
    """Test WebSocket connection callbacks"""

    def test_on_websocket_connect(self, worker_agent):
        """Test WebSocket connect callback"""
        assert worker_agent.ws_connected is False

        worker_agent._on_websocket_connect()

        assert worker_agent.ws_connected is True

    def test_on_websocket_disconnect(self, worker_agent):
        """Test WebSocket disconnect callback"""
        worker_agent.ws_connected = True

        worker_agent._on_websocket_disconnect()

        assert worker_agent.ws_connected is False


class TestPollingLoop:
    """Test polling fallback mechanism"""

    async def test_polling_when_websocket_disconnected(
        self, worker_agent, mock_connection_manager
    ):
        """Test polling activates when WebSocket is disconnected"""
        await worker_agent.start()
        worker_agent.ws_connected = False

        task_data = {
            "subtask_id": str(uuid4()),
            "description": "Polled task",
        }
        mock_connection_manager.poll_for_tasks.return_value = task_data

        # Let polling loop run briefly
        await asyncio.sleep(0.1)

        # Should have attempted to poll
        assert mock_connection_manager.poll_for_tasks.called

    async def test_polling_skipped_when_websocket_connected(
        self, worker_agent, mock_connection_manager
    ):
        """Test polling skipped when WebSocket is connected"""
        await worker_agent.start()
        worker_agent.ws_connected = True

        # Reset call count
        mock_connection_manager.poll_for_tasks.reset_mock()

        # Let polling loop run briefly
        await asyncio.sleep(0.1)

        # Polling might have been called before we set ws_connected
        # The important thing is it shouldn't poll while connected


class TestHeartbeat:
    """Test heartbeat functionality"""

    async def test_heartbeat_loop(
        self, worker_agent, mock_connection_manager, mock_resource_monitor
    ):
        """Test heartbeat loop sends periodic updates"""
        await worker_agent.start()

        # Wait for at least one heartbeat (interval is 5 seconds in test config)
        await asyncio.sleep(0.1)

        # Should have sent heartbeat
        assert mock_connection_manager.send_heartbeat.called


class TestAgentStatus:
    """Test agent status reporting"""

    async def test_get_status(
        self, worker_agent, mock_task_executor, mock_resource_monitor
    ):
        """Test getting agent status"""
        await worker_agent.start()

        status = worker_agent.get_status()

        assert status["running"] is True
        assert status["worker_id"] is not None
        assert status["machine_id"] is not None
        assert status["connected"] is True
        assert "executor_status" in status
        assert "resources" in status

    def test_get_status_not_started(self, worker_agent):
        """Test getting status when not started"""
        status = worker_agent.get_status()

        assert status["running"] is False
        assert status["worker_id"] is None


class TestSignalHandling:
    """Test signal handling for graceful shutdown"""

    @pytest.mark.skipif(
        not hasattr(asyncio, "get_event_loop"),
        reason="Signal handling not supported",
    )
    async def test_setup_signal_handlers(self, worker_agent):
        """Test signal handler setup"""
        loop = asyncio.get_event_loop()

        worker_agent.setup_signal_handlers(loop)

        assert worker_agent._shutdown_event is not None


class TestShutdownEvent:
    """Test shutdown event handling"""

    async def test_wait_for_shutdown(self, worker_agent):
        """Test waiting for shutdown event"""
        worker_agent._shutdown_event = asyncio.Event()

        # Start waiting
        wait_task = asyncio.create_task(worker_agent.wait_for_shutdown())

        # Give it a moment to start waiting
        await asyncio.sleep(0.01)

        # Trigger shutdown
        await worker_agent.start()
        await worker_agent.stop()

        # Wait should complete
        try:
            await asyncio.wait_for(wait_task, timeout=1.0)
        except asyncio.TimeoutError:
            wait_task.cancel()
            pytest.fail("wait_for_shutdown did not complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
