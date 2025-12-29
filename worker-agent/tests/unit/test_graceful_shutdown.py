"""Unit tests for Worker Agent graceful shutdown functionality"""

import asyncio
import signal
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from agent.core import WorkerAgent
from agent.connection import ConnectionManager


class TestGracefulShutdown:
    """Tests for graceful shutdown functionality"""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        return {
            "backend_url": "http://localhost:8000",
            "machine_name": "test-worker",
            "heartbeat_interval": 30,
            "shutdown_timeout": 5,  # Short timeout for tests
            "resource_monitoring": {
                "cpu_threshold": 90,
                "memory_threshold": 85,
                "disk_threshold": 90
            }
        }

    @pytest.fixture
    def mock_agent(self, mock_config):
        """Create mock WorkerAgent"""
        with patch("agent.core.load_or_create_machine_id", return_value="test-machine-id"):
            agent = WorkerAgent(mock_config)
            agent.worker_id = uuid4()
            agent.running = True
            return agent

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_sets_shutting_down_flag(self, mock_agent):
        """Test that stop() sets shutting_down flag"""
        mock_agent.connection_manager = AsyncMock()
        mock_agent.resource_monitor = MagicMock()
        mock_agent.resource_monitor.get_resources.return_value = {
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "disk_percent": 70.0
        }

        assert not mock_agent.shutting_down
        await mock_agent.stop()
        assert mock_agent.shutting_down

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_sets_accepting_tasks_false(self, mock_agent):
        """Test that stop() sets accepting_tasks to False"""
        mock_agent.connection_manager = AsyncMock()
        mock_agent.resource_monitor = MagicMock()
        mock_agent.resource_monitor.get_resources.return_value = {
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "disk_percent": 70.0
        }

        assert mock_agent.accepting_tasks
        await mock_agent.stop()
        assert not mock_agent.accepting_tasks

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_sends_final_heartbeat(self, mock_agent):
        """Test that stop() sends final heartbeat with offline status"""
        mock_agent.connection_manager = AsyncMock()
        mock_agent.connection_manager.send_final_heartbeat = AsyncMock(return_value=True)
        mock_agent.connection_manager.unregister = AsyncMock(return_value=True)
        mock_agent.connection_manager.close = AsyncMock()
        mock_agent.resource_monitor = MagicMock()
        mock_agent.resource_monitor.get_resources.return_value = {
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "disk_percent": 70.0
        }

        await mock_agent.stop()

        mock_agent.connection_manager.send_final_heartbeat.assert_called_once()
        call_args = mock_agent.connection_manager.send_final_heartbeat.call_args
        assert call_args.kwargs["worker_id"] == mock_agent.worker_id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_unregisters_worker(self, mock_agent):
        """Test that stop() unregisters worker from backend"""
        mock_agent.connection_manager = AsyncMock()
        mock_agent.connection_manager.send_final_heartbeat = AsyncMock(return_value=True)
        mock_agent.connection_manager.unregister = AsyncMock(return_value=True)
        mock_agent.connection_manager.close = AsyncMock()
        mock_agent.resource_monitor = MagicMock()
        mock_agent.resource_monitor.get_resources.return_value = {
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "disk_percent": 70.0
        }

        await mock_agent.stop()

        mock_agent.connection_manager.unregister.assert_called_once_with(mock_agent.worker_id)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_waits_for_task_completion(self, mock_agent):
        """Test that stop() waits for current task to complete"""
        mock_agent.connection_manager = AsyncMock()
        mock_agent.connection_manager.send_final_heartbeat = AsyncMock(return_value=True)
        mock_agent.connection_manager.unregister = AsyncMock(return_value=True)
        mock_agent.connection_manager.close = AsyncMock()
        mock_agent.resource_monitor = MagicMock()
        mock_agent.resource_monitor.get_resources.return_value = {
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "disk_percent": 70.0
        }

        # Simulate busy executor that completes after 1 second
        call_count = 0

        def is_busy_side_effect():
            nonlocal call_count
            call_count += 1
            return call_count < 3  # Busy for first 2 checks

        mock_agent.task_executor = MagicMock()
        type(mock_agent.task_executor).is_busy = property(lambda self: is_busy_side_effect())

        await mock_agent.stop()

        # Should have checked is_busy multiple times
        assert call_count >= 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_timeout_on_long_running_task(self, mock_agent):
        """Test that stop() times out if task takes too long"""
        mock_agent.shutdown_timeout = 1  # 1 second timeout
        mock_agent.connection_manager = AsyncMock()
        mock_agent.connection_manager.send_final_heartbeat = AsyncMock(return_value=True)
        mock_agent.connection_manager.unregister = AsyncMock(return_value=True)
        mock_agent.connection_manager.close = AsyncMock()
        mock_agent.resource_monitor = MagicMock()
        mock_agent.resource_monitor.get_resources.return_value = {
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "disk_percent": 70.0
        }

        # Simulate always-busy executor
        mock_agent.task_executor = MagicMock()
        type(mock_agent.task_executor).is_busy = property(lambda self: True)

        # Should complete without hanging (timeout will trigger)
        await asyncio.wait_for(mock_agent.stop(), timeout=5)

        # Should still unregister even after timeout
        mock_agent.connection_manager.unregister.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_closes_connections(self, mock_agent):
        """Test that stop() closes all connections"""
        mock_agent.connection_manager = AsyncMock()
        mock_agent.connection_manager.send_final_heartbeat = AsyncMock(return_value=True)
        mock_agent.connection_manager.unregister = AsyncMock(return_value=True)
        mock_agent.connection_manager.close = AsyncMock()
        mock_agent.resource_monitor = MagicMock()
        mock_agent.resource_monitor.get_resources.return_value = {
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "disk_percent": 70.0
        }

        await mock_agent.stop()

        mock_agent.connection_manager.close.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_double_stop_is_safe(self, mock_agent):
        """Test that calling stop() twice is safe"""
        mock_agent.connection_manager = AsyncMock()
        mock_agent.connection_manager.send_final_heartbeat = AsyncMock(return_value=True)
        mock_agent.connection_manager.unregister = AsyncMock(return_value=True)
        mock_agent.connection_manager.close = AsyncMock()
        mock_agent.resource_monitor = MagicMock()
        mock_agent.resource_monitor.get_resources.return_value = {
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "disk_percent": 70.0
        }

        await mock_agent.stop()
        await mock_agent.stop()  # Should not raise

        # Should only unregister once
        assert mock_agent.connection_manager.unregister.call_count == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_not_running_returns_early(self, mock_agent):
        """Test that stop() returns early if not running"""
        mock_agent.running = False
        mock_agent.connection_manager = AsyncMock()

        await mock_agent.stop()

        # Should not call any connection methods
        mock_agent.connection_manager.unregister.assert_not_called()


class TestConnectionManagerUnregister:
    """Tests for ConnectionManager unregister functionality"""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create mock ConnectionManager"""
        config = {"backend_url": "http://localhost:8000"}
        return ConnectionManager(config)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unregister_success(self, mock_connection_manager):
        """Test successful unregistration"""
        worker_id = uuid4()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_connection_manager.client = mock_client

        result = await mock_connection_manager.unregister(worker_id)

        assert result is True
        mock_client.post.assert_called_once_with(
            f"/api/v1/workers/{worker_id}/unregister"
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unregister_failure(self, mock_connection_manager):
        """Test unregistration failure handling"""
        worker_id = uuid4()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection error"))
        mock_connection_manager.client = mock_client

        result = await mock_connection_manager.unregister(worker_id)

        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_final_heartbeat_success(self, mock_connection_manager):
        """Test successful final heartbeat"""
        worker_id = uuid4()
        resources = {"cpu_percent": 50.0, "memory_percent": 60.0}

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_connection_manager.client = mock_client

        result = await mock_connection_manager.send_final_heartbeat(worker_id, resources)

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args.kwargs["json"]["status"] == "offline"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_final_heartbeat_failure(self, mock_connection_manager):
        """Test final heartbeat failure handling"""
        worker_id = uuid4()
        resources = {"cpu_percent": 50.0, "memory_percent": 60.0}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection error"))
        mock_connection_manager.client = mock_client

        result = await mock_connection_manager.send_final_heartbeat(worker_id, resources)

        assert result is False


class TestTaskRejectionDuringShutdown:
    """Tests for task rejection during shutdown"""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        return {
            "backend_url": "http://localhost:8000",
            "machine_name": "test-worker",
            "heartbeat_interval": 30,
            "shutdown_timeout": 60
        }

    @pytest.fixture
    def mock_agent(self, mock_config):
        """Create mock WorkerAgent"""
        with patch("agent.core.load_or_create_machine_id", return_value="test-machine-id"):
            agent = WorkerAgent(mock_config)
            agent.worker_id = uuid4()
            agent.running = True
            return agent

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_task_rejected_during_shutdown(self, mock_agent):
        """Test that tasks are rejected during shutdown"""
        mock_agent.accepting_tasks = False
        mock_agent.connection_manager = AsyncMock()
        mock_agent.connection_manager.send_websocket_message = AsyncMock()

        message = {
            "type": "task_assignment",
            "data": {"subtask_id": str(uuid4())}
        }

        await mock_agent._handle_websocket_message(message)

        # Should send rejection message
        mock_agent.connection_manager.send_websocket_message.assert_called_once()
        call_args = mock_agent.connection_manager.send_websocket_message.call_args
        assert call_args.args[0]["type"] == "task_rejected"
        assert call_args.args[0]["reason"] == "shutdown_in_progress"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_task_accepted_when_running(self, mock_agent):
        """Test that tasks are accepted when running normally"""
        mock_agent.accepting_tasks = True
        mock_agent.connection_manager = AsyncMock()

        # Mock task handler
        mock_agent._handle_task_assignment = AsyncMock()

        message = {
            "type": "task_assignment",
            "data": {"subtask_id": str(uuid4())}
        }

        await mock_agent._handle_websocket_message(message)

        # Should call task handler
        mock_agent._handle_task_assignment.assert_called_once()
