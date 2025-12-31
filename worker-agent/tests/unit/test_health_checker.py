"""Tests for AI tool health checker"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import pytest

from tools.health_checker import (
    ToolHealthChecker,
    HealthStatus,
    quick_health_check
)


class TestToolHealthChecker:
    """Test suite for ToolHealthChecker"""

    @pytest.fixture
    def checker(self):
        """Create health checker instance"""
        return ToolHealthChecker(timeout=5.0)

    @pytest.fixture
    def quick_checker(self):
        """Create health checker with quick timeout"""
        return ToolHealthChecker(timeout=2.0)

    # Claude Code Health Check Tests

    @pytest.mark.asyncio
    async def test_claude_code_healthy(self, checker):
        """Test Claude Code health check when CLI is available"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock successful version check
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(b"Claude Code v1.0.0\n", b"")
            )
            mock_subprocess.return_value = mock_process

            result = await checker.check_claude_code({"cli_path": "claude"})

            assert result["status"] == HealthStatus.HEALTHY
            assert result["available"] is True
            assert result["version"] == "Claude Code v1.0.0"
            assert result["error"] is None
            assert result["latency"] is not None
            assert result["latency"] >= 0  # Can be 0 in mocked tests

    @pytest.mark.asyncio
    async def test_claude_code_not_found(self, checker):
        """Test Claude Code health check when CLI not found"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_subprocess.side_effect = FileNotFoundError()

            result = await checker.check_claude_code({"cli_path": "claude"})

            assert result["status"] == HealthStatus.UNHEALTHY
            assert result["available"] is False
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_claude_code_timeout(self, quick_checker):
        """Test Claude Code health check timeout"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock process that times out
            async def slow_process(*args, **kwargs):
                await asyncio.sleep(10)  # Longer than timeout
                return AsyncMock()

            mock_subprocess.side_effect = slow_process

            result = await quick_checker.check_claude_code({"cli_path": "claude"})

            assert result["status"] == HealthStatus.UNHEALTHY
            assert result["available"] is False
            assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_claude_code_degraded(self, checker):
        """Test Claude Code health check with non-zero exit code"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(
                return_value=(b"", b"Error message")
            )
            mock_subprocess.return_value = mock_process

            result = await checker.check_claude_code({"cli_path": "claude"})

            assert result["status"] == HealthStatus.DEGRADED
            assert "exit code" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_claude_code_custom_path(self, checker):
        """Test Claude Code with custom CLI path"""
        custom_path = "/custom/path/to/claude"

        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"v1.0", b""))
            mock_subprocess.return_value = mock_process

            result = await checker.check_claude_code({"cli_path": custom_path})

            assert result["path"] == custom_path
            mock_subprocess.assert_called_once()
            assert mock_subprocess.call_args[0][0] == custom_path

    # Gemini Health Check Tests

    @pytest.mark.asyncio
    async def test_gemini_healthy(self, checker):
        """Test Gemini health check when API is available"""
        with patch('tools.health_checker.GENAI_AVAILABLE', True):
            with patch('tools.health_checker.genai') as mock_genai:
                # Mock successful API call
                mock_response = MagicMock()
                mock_response.text = "Hello back!"

                mock_model = MagicMock()
                mock_model.generate_content = MagicMock(return_value=mock_response)
                mock_genai.GenerativeModel.return_value = mock_model

                config = {
                    "api_key": "test-api-key",
                    "model": "gemini-1.5-flash"
                }

                result = await checker.check_gemini(config)

                assert result["status"] == HealthStatus.HEALTHY
                assert result["available"] is True
                assert result["configured"] is True
                assert result["error"] is None
                assert result["latency"] is not None

    @pytest.mark.asyncio
    async def test_gemini_sdk_not_available(self, checker):
        """Test Gemini when SDK is not installed"""
        with patch('tools.health_checker.GENAI_AVAILABLE', False):
            result = await checker.check_gemini({})

            assert result["status"] == HealthStatus.UNHEALTHY
            assert result["available"] is False
            assert "package not installed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_gemini_no_api_key(self, checker):
        """Test Gemini without API key"""
        with patch('tools.health_checker.GENAI_AVAILABLE', True):
            with patch.dict(os.environ, {}, clear=True):
                result = await checker.check_gemini({})

                assert result["status"] == HealthStatus.UNHEALTHY
                assert result["configured"] is False
                assert "not configured" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_gemini_api_key_from_env(self, checker):
        """Test Gemini with API key from environment"""
        with patch('tools.health_checker.GENAI_AVAILABLE', True):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "env-api-key"}):
                with patch('tools.health_checker.genai') as mock_genai:
                    mock_response = MagicMock()
                    mock_response.text = "Hello"
                    mock_model = MagicMock()
                    mock_model.generate_content = MagicMock(return_value=mock_response)
                    mock_genai.GenerativeModel.return_value = mock_model

                    result = await checker.check_gemini({})

                    assert result["configured"] is True
                    mock_genai.configure.assert_called_once_with(api_key="env-api-key")

    @pytest.mark.asyncio
    async def test_gemini_timeout(self, quick_checker):
        """Test Gemini API timeout"""
        with patch('tools.health_checker.GENAI_AVAILABLE', True):
            with patch('tools.health_checker.genai') as mock_genai:
                async def slow_call(*args, **kwargs):
                    await asyncio.sleep(10)
                    return MagicMock()

                mock_model = MagicMock()
                mock_genai.GenerativeModel.return_value = mock_model

                with patch('asyncio.to_thread', side_effect=slow_call):
                    result = await quick_checker.check_gemini({"api_key": "test"})

                    assert result["status"] == HealthStatus.UNHEALTHY
                    assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_gemini_empty_response(self, checker):
        """Test Gemini with empty response"""
        with patch('tools.health_checker.GENAI_AVAILABLE', True):
            with patch('tools.health_checker.genai') as mock_genai:
                mock_response = MagicMock()
                mock_response.text = ""

                mock_model = MagicMock()
                mock_model.generate_content = MagicMock(return_value=mock_response)
                mock_genai.GenerativeModel.return_value = mock_model

                result = await checker.check_gemini({"api_key": "test"})

                assert result["status"] == HealthStatus.DEGRADED
                assert "empty response" in result["error"].lower()

    # Ollama Health Check Tests

    @pytest.mark.asyncio
    async def test_ollama_healthy(self, checker):
        """Test Ollama health check when service is available"""
        with patch('tools.health_checker.HTTPX_AVAILABLE', True):
            with patch('tools.health_checker.httpx') as mock_httpx:
                # Mock successful API response
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "models": [
                        {"name": "llama2:latest"},
                        {"name": "codellama:latest"}
                    ]
                }

                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.get = AsyncMock(return_value=mock_response)

                mock_httpx.AsyncClient.return_value = mock_client

                result = await checker.check_ollama({
                    "url": "http://localhost:11434",
                    "model": "llama2"
                })

                assert result["status"] == HealthStatus.HEALTHY
                assert result["available"] is True
                assert "llama2" in result["models_available"]
                assert result["error"] is None

    @pytest.mark.asyncio
    async def test_ollama_httpx_not_available(self, checker):
        """Test Ollama when httpx is not installed"""
        with patch('tools.health_checker.HTTPX_AVAILABLE', False):
            result = await checker.check_ollama({})

            assert result["status"] == HealthStatus.UNHEALTHY
            assert "httpx package not installed" in result["error"]

    @pytest.mark.asyncio
    async def test_ollama_connection_error(self, checker):
        """Test Ollama connection error"""
        with patch('tools.health_checker.HTTPX_AVAILABLE', True):
            with patch('tools.health_checker.httpx') as mock_httpx:
                # Create custom exception class
                class MockConnectError(Exception):
                    pass

                mock_httpx.ConnectError = MockConnectError

                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.get = AsyncMock(
                    side_effect=MockConnectError("Connection refused")
                )

                mock_httpx.AsyncClient.return_value = mock_client

                result = await checker.check_ollama({})

                assert result["status"] == HealthStatus.UNHEALTHY
                assert "cannot connect" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_ollama_model_not_available(self, checker):
        """Test Ollama when specific model is not available"""
        with patch('tools.health_checker.HTTPX_AVAILABLE', True):
            with patch('tools.health_checker.httpx') as mock_httpx:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "models": [{"name": "llama2:latest"}]
                }

                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.get = AsyncMock(return_value=mock_response)

                mock_httpx.AsyncClient.return_value = mock_client

                result = await checker.check_ollama({
                    "model": "mistral"  # Model not in list
                })

                assert result["status"] == HealthStatus.DEGRADED
                assert "not available" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_ollama_no_models(self, checker):
        """Test Ollama when no models are available"""
        with patch('tools.health_checker.HTTPX_AVAILABLE', True):
            with patch('tools.health_checker.httpx') as mock_httpx:
                mock_response = MagicMock()
                mock_response.json.return_value = {"models": []}

                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.get = AsyncMock(return_value=mock_response)

                mock_httpx.AsyncClient.return_value = mock_client

                result = await checker.check_ollama({})

                assert result["status"] == HealthStatus.DEGRADED
                assert "no models" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_ollama_with_version(self, checker):
        """Test Ollama version detection"""
        with patch('tools.health_checker.HTTPX_AVAILABLE', True):
            with patch('tools.health_checker.httpx') as mock_httpx:
                # Mock tags response
                mock_tags_response = MagicMock()
                mock_tags_response.json.return_value = {
                    "models": [{"name": "llama2:latest"}]
                }

                # Mock version response
                mock_version_response = MagicMock()
                mock_version_response.status_code = 200
                mock_version_response.json.return_value = {"version": "0.1.25"}

                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.get = AsyncMock(
                    side_effect=[mock_tags_response, mock_version_response]
                )

                mock_httpx.AsyncClient.return_value = mock_client

                result = await checker.check_ollama({"model": "llama2"})

                assert result["version"] == "0.1.25"

    # Overall Health Check Tests

    @pytest.mark.asyncio
    async def test_check_all_tools(self, checker):
        """Test checking all tools together"""
        with patch.object(checker, 'check_claude_code', return_value={
            "name": "Claude Code",
            "status": HealthStatus.HEALTHY,
            "available": True,
            "error": None
        }):
            with patch.object(checker, 'check_gemini', return_value={
                "name": "Gemini",
                "status": HealthStatus.HEALTHY,
                "available": True,
                "error": None
            }):
                with patch.object(checker, 'check_ollama', return_value={
                    "name": "Ollama",
                    "status": HealthStatus.UNHEALTHY,
                    "available": False,
                    "error": "Connection failed"
                }):
                    result = await checker.check_all_tools()

                    assert "timestamp" in result
                    assert "duration" in result
                    assert "overall_status" in result
                    assert "tools" in result
                    assert "summary" in result

                    # Check that all tools were checked
                    assert "claude_code" in result["tools"]
                    assert "gemini" in result["tools"]
                    assert "ollama" in result["tools"]

                    # Overall status should be unhealthy (one tool is unhealthy)
                    assert result["overall_status"] == HealthStatus.UNHEALTHY

                    # Check summary
                    summary = result["summary"]
                    assert summary["total_count"] == 3
                    assert summary["healthy_count"] == 2
                    assert summary["unhealthy_count"] == 1

    @pytest.mark.asyncio
    async def test_overall_status_all_healthy(self, checker):
        """Test overall status when all tools are healthy"""
        tools_status = {
            "tool1": {"status": HealthStatus.HEALTHY},
            "tool2": {"status": HealthStatus.HEALTHY},
            "tool3": {"status": HealthStatus.HEALTHY}
        }

        status = checker._calculate_overall_status(tools_status)
        assert status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_overall_status_one_degraded(self, checker):
        """Test overall status with one degraded tool"""
        tools_status = {
            "tool1": {"status": HealthStatus.HEALTHY},
            "tool2": {"status": HealthStatus.DEGRADED},
            "tool3": {"status": HealthStatus.HEALTHY}
        }

        status = checker._calculate_overall_status(tools_status)
        assert status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_overall_status_one_unhealthy(self, checker):
        """Test overall status with one unhealthy tool"""
        tools_status = {
            "tool1": {"status": HealthStatus.HEALTHY},
            "tool2": {"status": HealthStatus.UNHEALTHY},
            "tool3": {"status": HealthStatus.DEGRADED}
        }

        status = checker._calculate_overall_status(tools_status)
        assert status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_summary_generation(self, checker):
        """Test summary statistics generation"""
        tools_status = {
            "claude_code": {"status": HealthStatus.HEALTHY},
            "gemini": {"status": HealthStatus.DEGRADED},
            "ollama": {"status": HealthStatus.UNHEALTHY}
        }

        summary = checker._generate_summary(tools_status)

        assert summary["total_count"] == 3
        assert summary["healthy_count"] == 1
        assert summary["degraded_count"] == 1
        assert summary["unhealthy_count"] == 1
        assert "claude_code" in summary["healthy_tools"]
        assert "gemini" in summary["degraded_tools"]
        assert "ollama" in summary["unhealthy_tools"]

    @pytest.mark.asyncio
    async def test_exception_handling_in_check_all(self, checker):
        """Test exception handling during check_all_tools"""
        with patch.object(checker, 'check_claude_code', side_effect=Exception("Test error")):
            with patch.object(checker, 'check_gemini', return_value={
                "name": "Gemini",
                "status": HealthStatus.HEALTHY,
                "available": True
            }):
                with patch.object(checker, 'check_ollama', return_value={
                    "name": "Ollama",
                    "status": HealthStatus.HEALTHY,
                    "available": True
                }):
                    result = await checker.check_all_tools()

                    # Check that exception was handled gracefully
                    assert result["tools"]["claude_code"]["status"] == HealthStatus.UNHEALTHY
                    assert "exception" in result["tools"]["claude_code"]["error"].lower() or \
                           "failed" in result["tools"]["claude_code"]["error"].lower()

    # Quick Health Check Tests

    @pytest.mark.asyncio
    async def test_quick_health_check_all_tools(self):
        """Test quick health check convenience function"""
        with patch('tools.health_checker.ToolHealthChecker') as MockChecker:
            mock_instance = MagicMock()
            mock_instance.check_all_tools = AsyncMock(return_value={
                "timestamp": 123456,
                "tools": {}
            })
            MockChecker.return_value = mock_instance

            result = await quick_health_check()

            assert "timestamp" in result or "tools" in result
            MockChecker.assert_called_once()

    @pytest.mark.asyncio
    async def test_quick_health_check_specific_tools(self):
        """Test quick health check for specific tools"""
        with patch('tools.health_checker.ToolHealthChecker') as MockChecker:
            mock_instance = MagicMock()
            mock_instance.check_claude_code = AsyncMock(return_value={
                "status": HealthStatus.HEALTHY
            })
            mock_instance.check_gemini = AsyncMock(return_value={
                "status": HealthStatus.HEALTHY
            })
            MockChecker.return_value = mock_instance

            result = await quick_health_check(
                tools=["claude_code", "gemini"],
                config={"claude_code": {}, "gemini": {"api_key": "test"}}
            )

            assert "tools" in result
            assert "claude_code" in result["tools"]
            assert "gemini" in result["tools"]
            assert "ollama" not in result["tools"]

    # Custom Timeout Tests

    @pytest.mark.asyncio
    async def test_custom_timeout(self):
        """Test health checker with custom timeout"""
        custom_timeout = 15.0
        checker = ToolHealthChecker(timeout=custom_timeout)

        assert checker.timeout == custom_timeout

    @pytest.mark.asyncio
    async def test_latency_measurement(self, checker):
        """Test that latency is properly measured"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"v1.0", b""))
            mock_subprocess.return_value = mock_process

            result = await checker.check_claude_code({})

            assert "latency" in result
            assert result["latency"] is not None
            assert result["latency"] >= 0

    # Edge Cases

    @pytest.mark.asyncio
    async def test_empty_config(self, checker):
        """Test with empty configuration"""
        # Should use defaults
        result = await checker.check_claude_code({})

        assert result["path"] == "claude"  # Default path
        assert "status" in result

    @pytest.mark.asyncio
    async def test_handle_check_exception(self, checker):
        """Test exception handling in health checks"""
        test_exception = ValueError("Test error")
        result = checker._handle_check_exception(test_exception, "TestTool")

        assert result["status"] == HealthStatus.UNHEALTHY
        assert result["available"] is False
        assert "Test error" in result["error"]

    @pytest.mark.asyncio
    async def test_concurrent_checks(self, checker):
        """Test that concurrent checks work properly"""
        # Run multiple checks concurrently
        tasks = [
            checker.check_claude_code({}),
            checker.check_claude_code({}),
            checker.check_claude_code({})
        ]

        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"v1.0", b""))
            mock_subprocess.return_value = mock_process

            results = await asyncio.gather(*tasks)

            assert len(results) == 3
            for result in results:
                assert "status" in result
