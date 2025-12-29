"""Pytest configuration and fixtures for worker agent tests"""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    return {
        "backend_url": "http://localhost:8000",
        "machine_name": "Test Machine",
        "heartbeat_interval": 30,
        "tools": ["test_tool"],
        "resource_monitoring": {
            "cpu_threshold": 90,
            "memory_threshold": 85,
            "disk_threshold": 90
        }
    }


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient"""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"worker_id": "test-worker-id-123"}
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_subtask():
    """Sample subtask for testing"""
    return {
        "subtask_id": "test-subtask-123",
        "description": "Test task description",
        "assigned_tool": "test_tool",
        "context": {
            "test_key": "test_value"
        }
    }
