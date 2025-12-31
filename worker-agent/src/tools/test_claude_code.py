"""Unit tests for Claude Code tool"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from claude_code import (
    ClaudeCodeTool,
    ClaudeCodeError,
    ClaudeCodeTimeoutError,
    ClaudeCodeCLINotFoundError,
    ClaudeCodeExecutionError
)


class TestClaudeCodeTool:
    """Test cases for ClaudeCodeTool"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            "cli_path": "claude",
            "default_timeout": 300,
            "working_directory": "/test/dir",
            "env_vars": {"TEST_VAR": "test_value"},
            "max_retries": 3,
            "retry_base_delay": 1.0,
            "enable_json_parsing": True
        }
        self.tool = ClaudeCodeTool(self.config)

    def test_initialization(self):
        """Test tool initialization"""
        assert self.tool.cli_path == "claude"
        assert self.tool.default_timeout == 300
        assert self.tool.default_working_dir == "/test/dir"
        assert self.tool.env_vars == {"TEST_VAR": "test_value"}
        assert self.tool.name == "ClaudeCodeTool"
        assert self.tool.max_retries == 3
        assert self.tool.retry_base_delay == 1.0
        assert self.tool.enable_json_parsing is True

    def test_get_tool_info(self):
        """Test get_tool_info method"""
        info = self.tool.get_tool_info()

        assert info["name"] == "ClaudeCodeTool"
        assert info["type"] == "ai_tool"
        assert info["provider"] == "anthropic"
        assert "code_generation" in info["capabilities"]
        assert "streaming" in info["features"]
        assert info["features"]["json_parsing"] is True
        assert info["features"]["retry_logic"] is True
        assert info["features"]["cancellation"] is True
        assert info["features"]["error_classification"] is True
        assert info["config"]["default_timeout"] == 300
        assert info["config"]["max_retries"] == 3

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful execution"""
        mock_result = {
            "stdout": "Test output",
            "stderr": "",
            "exit_code": 0
        }

        with patch.object(
            self.tool,
            '_run_subprocess',
            return_value=mock_result
        ) as mock_run:
            result = await self.tool.execute(
                instructions="Test prompt",
                context={"timeout": 60, "retry": False}
            )

            assert result["success"] is True
            assert result["output"] == "Test output"
            assert result["error"] is None
            assert result["retryable"] is False
            assert "duration" in result["metadata"]
            assert result["metadata"]["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_execute_with_files(self):
        """Test execution with file context"""
        mock_result = {
            "stdout": "Analysis complete",
            "stderr": "",
            "exit_code": 0
        }

        with patch.object(
            self.tool,
            '_run_subprocess',
            return_value=mock_result
        ) as mock_run:
            with patch('os.path.exists', return_value=True):
                result = await self.tool.execute(
                    instructions="Analyze files",
                    context={
                        "files": ["/test/file1.py", "/test/file2.py"],
                        "timeout": 120,
                        "retry": False
                    }
                )

                assert result["success"] is True
                assert result["metadata"]["files_included"] == 2

    @pytest.mark.asyncio
    async def test_execute_with_json_output(self):
        """Test execution with JSON output parsing"""
        json_output = '{"status": "success", "result": "Task completed"}'
        mock_result = {
            "stdout": json_output,
            "stderr": "",
            "exit_code": 0
        }

        with patch.object(
            self.tool,
            '_run_subprocess',
            return_value=mock_result
        ):
            result = await self.tool.execute(
                instructions="Test prompt",
                context={"parse_json": True, "retry": False}
            )

            assert result["success"] is True
            assert result["parsed_json"] is not None
            assert result["parsed_json"]["status"] == "success"
            assert result["metadata"]["has_json"] is True

    @pytest.mark.asyncio
    async def test_execute_with_json_code_block(self):
        """Test JSON parsing from code block"""
        output_with_code_block = """
Here's the result:
```json
{
    "status": "completed",
    "files_created": 5
}
```
        """
        mock_result = {
            "stdout": output_with_code_block,
            "stderr": "",
            "exit_code": 0
        }

        with patch.object(
            self.tool,
            '_run_subprocess',
            return_value=mock_result
        ):
            result = await self.tool.execute(
                instructions="Test prompt",
                context={"parse_json": True, "retry": False}
            )

            assert result["success"] is True
            assert result["parsed_json"] is not None
            assert result["parsed_json"]["status"] == "completed"
            assert result["parsed_json"]["files_created"] == 5

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        """Test execution timeout handling"""
        async def mock_timeout(*args, **kwargs):
            raise asyncio.TimeoutError()

        with patch.object(
            self.tool,
            '_run_subprocess',
            side_effect=mock_timeout
        ):
            result = await self.tool.execute(
                instructions="Test prompt",
                context={"timeout": 10, "retry": False}
            )

            assert result["success"] is False
            assert "timeout" in result["error"].lower()
            assert result["retryable"] is False

    @pytest.mark.asyncio
    async def test_execute_error_retryable(self):
        """Test execution with retryable error"""
        mock_result = {
            "stdout": "",
            "stderr": "Rate limit exceeded, try again later",
            "exit_code": 1
        }

        with patch.object(
            self.tool,
            '_run_subprocess',
            return_value=mock_result
        ):
            result = await self.tool.execute(
                instructions="Test prompt",
                context={"retry": False}  # Disable retry to test error classification
            )

            assert result["success"] is False
            assert result["retryable"] is True
            assert "error_details" in result["metadata"]

    @pytest.mark.asyncio
    async def test_execute_error_non_retryable(self):
        """Test execution with non-retryable error"""
        mock_result = {
            "stdout": "",
            "stderr": "Invalid syntax in prompt",
            "exit_code": 2
        }

        with patch.object(
            self.tool,
            '_run_subprocess',
            return_value=mock_result
        ):
            result = await self.tool.execute(
                instructions="Test prompt",
                context={"retry": False}
            )

            assert result["success"] is False
            assert result["retryable"] is False

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_after_failure(self):
        """Test retry logic succeeds after initial failure"""
        # First call fails, second succeeds
        call_count = 0

        async def mock_subprocess(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "stdout": "",
                    "stderr": "Temporary network error",
                    "exit_code": 1
                }
            else:
                return {
                    "stdout": "Success",
                    "stderr": "",
                    "exit_code": 0
                }

        with patch.object(
            self.tool,
            '_run_subprocess',
            side_effect=mock_subprocess
        ):
            result = await self.tool.execute(
                instructions="Test prompt",
                context={"retry": True, "max_retries": 2}
            )

            assert call_count == 2
            assert result["success"] is True
            assert result["output"] == "Success"

    @pytest.mark.asyncio
    async def test_cancellation(self):
        """Test execution cancellation"""
        # Create a mock process
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.stderr.readline = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock()
        mock_process.terminate = AsyncMock()
        mock_process.kill = AsyncMock()

        # Set the current process
        self.tool._current_process = mock_process

        # Cancel execution
        await self.tool.cancel()

        assert self.tool._cancelled is True
        mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_retryable_error_by_exit_code(self):
        """Test error classification by exit code"""
        # Retryable exit codes
        assert self.tool._is_retryable_error(124, "") is True  # Timeout
        assert self.tool._is_retryable_error(137, "") is True  # SIGKILL
        assert self.tool._is_retryable_error(143, "") is True  # SIGTERM

        # Non-retryable exit code
        assert self.tool._is_retryable_error(1, "Invalid input") is False

    @pytest.mark.asyncio
    async def test_is_retryable_error_by_stderr(self):
        """Test error classification by stderr patterns"""
        # Retryable patterns
        assert self.tool._is_retryable_error(1, "Rate limit exceeded") is True
        assert self.tool._is_retryable_error(1, "Connection timeout") is True
        assert self.tool._is_retryable_error(1, "Network error") is True
        assert self.tool._is_retryable_error(1, "Service temporarily unavailable") is True

        # Non-retryable
        assert self.tool._is_retryable_error(1, "Invalid syntax") is False

    def test_parse_json_output_plain_json(self):
        """Test JSON parsing from plain JSON output"""
        json_str = '{"key": "value", "count": 42}'
        result = self.tool._parse_json_output(json_str)

        assert result is not None
        assert result["key"] == "value"
        assert result["count"] == 42

    def test_parse_json_output_code_block(self):
        """Test JSON parsing from code block"""
        output = """
Some text before
```json
{"status": "ok", "data": [1, 2, 3]}
```
Some text after
        """
        result = self.tool._parse_json_output(output)

        assert result is not None
        assert result["status"] == "ok"
        assert result["data"] == [1, 2, 3]

    def test_parse_json_output_embedded(self):
        """Test JSON parsing from embedded JSON in text"""
        output = """
The result is:
{"result": "success", "code": 200}
End of output
        """
        result = self.tool._parse_json_output(output)

        assert result is not None
        assert result["result"] == "success"
        assert result["code"] == 200

    def test_parse_json_output_array(self):
        """Test JSON parsing for array output"""
        output = '[{"id": 1}, {"id": 2}, {"id": 3}]'
        result = self.tool._parse_json_output(output)

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["id"] == 1

    def test_parse_json_output_no_json(self):
        """Test JSON parsing when no JSON present"""
        output = "This is plain text without any JSON"
        result = self.tool._parse_json_output(output)

        assert result is None

    def test_parse_json_output_empty(self):
        """Test JSON parsing with empty output"""
        assert self.tool._parse_json_output("") is None
        assert self.tool._parse_json_output(None) is None

    @pytest.mark.asyncio
    async def test_validate_config_success(self):
        """Test successful config validation"""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.wait = AsyncMock()

        with patch(
            'asyncio.create_subprocess_exec',
            return_value=mock_process
        ):
            result = await self.tool.validate_config()
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_config_not_found(self):
        """Test config validation when CLI not found"""
        with patch(
            'asyncio.create_subprocess_exec',
            side_effect=FileNotFoundError()
        ):
            result = await self.tool.validate_config()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check"""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.wait = AsyncMock()

        with patch(
            'asyncio.create_subprocess_exec',
            return_value=mock_process
        ):
            result = await self.tool.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_timeout(self):
        """Test health check timeout"""
        with patch(
            'asyncio.wait_for',
            side_effect=asyncio.TimeoutError()
        ):
            result = await self.tool.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_detailed_health_check_success(self):
        """Test detailed health check with version info"""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(
            return_value=(b"Claude Code v1.0.0\n", b"")
        )

        with patch('asyncio.wait_for', return_value=mock_process):
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                result = await self.tool.detailed_health_check()

                assert result["status"] == "healthy"
                assert result["available"] is True
                assert result["version"] == "Claude Code v1.0.0"
                assert result["error"] is None
                assert "latency" in result

    @pytest.mark.asyncio
    async def test_detailed_health_check_timeout(self):
        """Test detailed health check timeout"""
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
            result = await self.tool.detailed_health_check()

            assert result["status"] == "unhealthy"
            assert result["available"] is False
            assert result["error"] == "Health check timeout"


class TestClaudeCodeExceptions:
    """Test custom exceptions"""

    def test_claude_code_error(self):
        """Test ClaudeCodeError"""
        error = ClaudeCodeError(
            "Test error",
            retryable=True,
            details={"key": "value"}
        )

        assert str(error) == "Test error"
        assert error.retryable is True
        assert error.details["key"] == "value"

    def test_claude_code_timeout_error(self):
        """Test ClaudeCodeTimeoutError"""
        error = ClaudeCodeTimeoutError(timeout=300)

        assert "300 seconds" in str(error)
        assert error.retryable is False

    def test_claude_code_cli_not_found_error(self):
        """Test ClaudeCodeCLINotFoundError"""
        error = ClaudeCodeCLINotFoundError(cli_path="/usr/bin/claude")

        assert "/usr/bin/claude" in str(error)
        assert error.retryable is False

    def test_claude_code_execution_error(self):
        """Test ClaudeCodeExecutionError"""
        error = ClaudeCodeExecutionError(
            message="Execution failed",
            exit_code=1,
            stderr="Error message",
            retryable=True
        )

        assert "Execution failed" in str(error)
        assert error.retryable is True
        assert error.details["exit_code"] == 1
        assert error.details["stderr"] == "Error message"


def test_basic_imports():
    """Test that all imports work correctly"""
    from claude_code import (
        ClaudeCodeTool,
        ClaudeCodeError,
        ClaudeCodeTimeoutError,
        ClaudeCodeCLINotFoundError,
        ClaudeCodeExecutionError
    )

    assert ClaudeCodeTool is not None
    assert ClaudeCodeError is not None
    assert ClaudeCodeTimeoutError is not None
    assert ClaudeCodeCLINotFoundError is not None
    assert ClaudeCodeExecutionError is not None


if __name__ == "__main__":
    # Run basic tests
    print("Running basic tests...")

    # Test initialization
    config = {
        "cli_path": "claude",
        "default_timeout": 60,
        "working_directory": "/test",
        "max_retries": 3,
        "enable_json_parsing": True
    }

    tool = ClaudeCodeTool(config)
    print(f"✓ Tool initialized: {tool.name}")

    # Test tool info
    info = tool.get_tool_info()
    print(f"✓ Tool info retrieved: {info['name']}")
    print(f"  Capabilities: {len(info['capabilities'])}")
    print(f"  Features: {list(info['features'].keys())}")

    # Test JSON parsing
    json_output = '{"status": "ok", "value": 123}'
    parsed = tool._parse_json_output(json_output)
    print(f"✓ JSON parsing works: {parsed}")

    # Test error classification
    is_retryable = tool._is_retryable_error(1, "Rate limit exceeded")
    print(f"✓ Error classification works: retryable={is_retryable}")

    print("\nBasic tests passed!")
    print("\nTo run full test suite:")
    print("  pytest test_claude_code.py -v")
