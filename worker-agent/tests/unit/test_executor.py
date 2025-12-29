"""Unit tests for TaskExecutor"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.agent.executor import TaskExecutor
from src.tools.base import BaseTool


class MockTool(BaseTool):
    """Mock tool for testing"""

    async def execute(self, instructions: str, context=None):
        return {
            "success": True,
            "output": f"Executed: {instructions}",
            "error": None,
            "metadata": {}
        }

    async def validate_config(self):
        return True

    async def health_check(self):
        return True


@pytest.mark.unit
def test_executor_initialization():
    """Test TaskExecutor can be initialized"""
    executor = TaskExecutor()
    assert executor is not None
    assert executor.is_busy is False
    assert executor.current_task is None


@pytest.mark.unit
def test_register_tool():
    """Test registering a tool"""
    executor = TaskExecutor()
    tool = MockTool({})

    executor.register_tool("test_tool", tool)

    assert "test_tool" in executor.tools
    assert executor.tools["test_tool"] == tool


@pytest.mark.unit
def test_get_available_tools():
    """Test getting available tools"""
    executor = TaskExecutor()
    tool1 = MockTool({})
    tool2 = MockTool({})

    executor.register_tool("tool1", tool1)
    executor.register_tool("tool2", tool2)

    tools = executor.get_available_tools()
    assert len(tools) == 2
    assert "tool1" in tools
    assert "tool2" in tools


@pytest.mark.unit
def test_has_tool():
    """Test checking if tool exists"""
    executor = TaskExecutor()
    tool = MockTool({})

    executor.register_tool("test_tool", tool)

    assert executor.has_tool("test_tool") is True
    assert executor.has_tool("nonexistent_tool") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_task_success():
    """Test successful task execution"""
    executor = TaskExecutor()
    tool = MockTool({})
    executor.register_tool("test_tool", tool)

    subtask = {
        "subtask_id": str(uuid4()),
        "description": "Test task",
        "assigned_tool": "test_tool",
        "context": {}
    }

    result = await executor.execute_task(subtask)

    assert result["success"] is True
    assert "Executed: Test task" in result["output"]
    assert result["error"] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_task_no_tool_assigned():
    """Test task execution with no tool assigned"""
    executor = TaskExecutor()

    subtask = {
        "subtask_id": str(uuid4()),
        "description": "Test task",
        "assigned_tool": None,
        "context": {}
    }

    result = await executor.execute_task(subtask)

    assert result["success"] is False
    assert "No tool assigned" in result["error"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_task_tool_not_available():
    """Test task execution with unavailable tool"""
    executor = TaskExecutor()

    subtask = {
        "subtask_id": str(uuid4()),
        "description": "Test task",
        "assigned_tool": "nonexistent_tool",
        "context": {}
    }

    result = await executor.execute_task(subtask)

    assert result["success"] is False
    assert "not available" in result["error"]


@pytest.mark.unit
def test_get_status():
    """Test getting executor status"""
    executor = TaskExecutor()
    tool = MockTool({})
    executor.register_tool("test_tool", tool)

    status = executor.get_status()

    assert "is_busy" in status
    assert "current_task" in status
    assert "available_tools" in status
    assert "tool_count" in status

    assert status["is_busy"] is False
    assert status["current_task"] is None
    assert "test_tool" in status["available_tools"]
    assert status["tool_count"] == 1
