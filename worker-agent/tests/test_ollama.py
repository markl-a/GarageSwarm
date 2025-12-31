"""Tests for OllamaTool"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from aiohttp import ClientResponseError, ClientConnectorError
import asyncio

from src.tools.ollama import OllamaTool


class TestOllamaTool:
    """Test suite for OllamaTool"""

    def test_init_default_config(self):
        """Test initialization with default configuration"""
        tool = OllamaTool({})

        assert tool.url == "http://localhost:11434"
        assert tool.model == "llama2"
        assert tool.timeout == 300.0
        assert tool.connect_timeout == 10.0
        assert tool.stream is False
        assert tool.temperature == 0.7
        assert tool.max_tokens is None
        assert tool.max_retries == 3
        assert tool.retry_delay == 1.0
        assert tool.auto_pull is False

    def test_init_custom_config(self):
        """Test initialization with custom configuration"""
        config = {
            "url": "http://custom:8080",
            "model": "codellama",
            "timeout": 600,
            "connect_timeout": 15,
            "stream": True,
            "temperature": 0.5,
            "max_tokens": 1000,
            "max_retries": 5,
            "retry_delay": 2.0,
            "auto_pull": True
        }
        tool = OllamaTool(config)

        assert tool.url == "http://custom:8080"
        assert tool.model == "codellama"
        assert tool.timeout == 600
        assert tool.connect_timeout == 15
        assert tool.stream is True
        assert tool.temperature == 0.5
        assert tool.max_tokens == 1000
        assert tool.max_retries == 5
        assert tool.retry_delay == 2.0
        assert tool.auto_pull is True

    def test_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from URL"""
        tool = OllamaTool({"url": "http://localhost:11434/"})
        assert tool.url == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_validate_config_valid(self):
        """Test configuration validation with valid config"""
        tool = OllamaTool({
            "model": "llama2",
            "temperature": 0.7,
            "timeout": 300
        })

        is_valid = await tool.validate_config()
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_config_invalid_temperature(self):
        """Test configuration validation with invalid temperature"""
        tool = OllamaTool({
            "model": "llama2",
            "temperature": 3.0,  # Invalid: > 2.0
            "timeout": 300
        })

        is_valid = await tool.validate_config()
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_config_invalid_timeout(self):
        """Test configuration validation with invalid timeout"""
        tool = OllamaTool({
            "model": "llama2",
            "temperature": 0.7,
            "timeout": -1  # Invalid: <= 0
        })

        is_valid = await tool.validate_config()
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_config_invalid_max_tokens(self):
        """Test configuration validation with invalid max_tokens"""
        tool = OllamaTool({
            "model": "llama2",
            "temperature": 0.7,
            "timeout": 300,
            "max_tokens": 0  # Invalid: <= 0
        })

        is_valid = await tool.validate_config()
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_config_invalid_retries(self):
        """Test configuration validation with invalid retry settings"""
        tool = OllamaTool({
            "model": "llama2",
            "max_retries": -1  # Invalid: < 0
        })

        is_valid = await tool.validate_config()
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_execute_generate_success(self):
        """Test successful text generation"""
        tool = OllamaTool({"model": "llama2"})

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "response": "Generated text",
            "prompt_eval_count": 10,
            "eval_count": 50,
            "load_duration": 1000000,
            "eval_duration": 5000000
        })
        mock_response.raise_for_status = Mock()

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await tool.execute("Test prompt")

            assert result["success"] is True
            assert result["output"] == "Generated text"
            assert result["error"] is None
            assert result["metadata"]["model"] == "llama2"
            assert result["metadata"]["prompt_tokens"] == 10
            assert result["metadata"]["completion_tokens"] == 50
            assert result["metadata"]["total_tokens"] == 60

    @pytest.mark.asyncio
    async def test_execute_chat_success(self):
        """Test successful chat completion"""
        tool = OllamaTool({"model": "llama2"})

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "message": {
                "role": "assistant",
                "content": "Chat response"
            },
            "prompt_eval_count": 15,
            "eval_count": 40
        })
        mock_response.raise_for_status = Mock()

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await tool.execute(
                "Test prompt",
                context={
                    "use_chat": True,
                    "system_prompt": "You are a helpful assistant"
                }
            )

            assert result["success"] is True
            assert result["output"] == "Chat response"
            assert result["metadata"]["prompt_tokens"] == 15
            assert result["metadata"]["completion_tokens"] == 40

    @pytest.mark.asyncio
    async def test_execute_connection_error(self):
        """Test handling of connection error"""
        tool = OllamaTool({"model": "llama2"})

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(
            side_effect=ClientConnectorError(Mock(), Mock())
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await tool.execute("Test prompt")

            assert result["success"] is False
            assert result["output"] is None
            assert "Failed to connect" in result["error"]
            assert "Is Ollama running?" in result["error"]
            assert result["metadata"]["error_type"] == "connection_error"

    @pytest.mark.asyncio
    async def test_execute_timeout_error(self):
        """Test handling of timeout error"""
        tool = OllamaTool({"model": "llama2", "timeout": 5})

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await tool.execute("Test prompt")

            assert result["success"] is False
            assert result["output"] is None
            assert "timed out" in result["error"]
            assert result["metadata"]["error_type"] == "timeout"

    @pytest.mark.asyncio
    async def test_execute_http_error(self):
        """Test handling of HTTP error"""
        tool = OllamaTool({"model": "llama2"})

        # Create proper error
        error = ClientResponseError(
            request_info=Mock(),
            history=(),
            status=404,
            message="Model not found"
        )

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(side_effect=error)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await tool.execute("Test prompt")

            assert result["success"] is False
            assert result["output"] is None
            assert "HTTP error 404" in result["error"]
            assert result["metadata"]["error_type"] == "http_error"
            assert result["metadata"]["status_code"] == 404

    @pytest.mark.asyncio
    async def test_execute_model_override(self):
        """Test model override in context"""
        tool = OllamaTool({"model": "llama2"})

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "response": "Generated text",
            "prompt_eval_count": 10,
            "eval_count": 50
        })
        mock_response.raise_for_status = Mock()

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await tool.execute(
                "Test prompt",
                context={"model": "codellama"}
            )

            assert result["success"] is True
            assert result["metadata"]["model"] == "codellama"

            # Verify the correct model was sent in the request
            call_args = mock_session.post.call_args
            assert call_args[1]["json"]["model"] == "codellama"

    @pytest.mark.asyncio
    async def test_execute_streaming(self):
        """Test streaming response handling"""
        tool = OllamaTool({"model": "llama2"})

        # Simulate streaming response chunks
        chunks = [
            b'{"response":"Hello","done":false}\n',
            b'{"response":" world","done":false}\n',
            b'{"response":"!","done":true,"prompt_eval_count":5,"eval_count":10}\n'
        ]

        mock_content = AsyncMock()
        mock_content.__aiter__ = AsyncMock(return_value=iter(chunks))

        mock_response = AsyncMock()
        mock_response.content = mock_content
        mock_response.raise_for_status = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await tool.execute(
                "Test prompt",
                context={"stream": True}
            )

            assert result["success"] is True
            assert result["output"] == "Hello world!"
            assert result["metadata"]["streamed"] is True

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check"""
        tool = OllamaTool({"model": "llama2"})

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "models": [
                {"name": "llama2:latest"},
                {"name": "codellama:latest"}
            ]
        })
        mock_response.raise_for_status = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            is_healthy = await tool.health_check()
            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_model_not_found(self):
        """Test health check when model is not available"""
        tool = OllamaTool({"model": "nonexistent"})

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "models": [
                {"name": "llama2:latest"}
            ]
        })
        mock_response.raise_for_status = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            is_healthy = await tool.health_check()
            assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self):
        """Test health check with connection error"""
        tool = OllamaTool({"model": "llama2"})

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(
            side_effect=ClientConnectorError(Mock(), Mock())
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            is_healthy = await tool.health_check()
            assert is_healthy is False

    @pytest.mark.asyncio
    async def test_detailed_health_check_success(self):
        """Test detailed health check"""
        tool = OllamaTool({"model": "llama2"})

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "models": [
                {"name": "llama2:latest"},
                {"name": "codellama:latest"}
            ],
            "version": "0.1.0"
        })
        mock_response.raise_for_status = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await tool.detailed_health_check()

            assert result["status"] == "healthy"
            assert result["available"] is True
            assert result["error"] is None
            assert result["version"] == "0.1.0"
            assert "latency" in result
            assert result["metadata"]["model_available"] is True

    @pytest.mark.asyncio
    async def test_list_models(self):
        """Test listing available models"""
        tool = OllamaTool({})

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "models": [
                {"name": "llama2:latest", "size": 3800000000},
                {"name": "codellama:latest", "size": 3800000000}
            ]
        })
        mock_response.raise_for_status = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await tool.list_models()

            assert result["success"] is True
            assert len(result["models"]) == 2
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_pull_model(self):
        """Test pulling a model"""
        tool = OllamaTool({})

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "status": "success"
        })
        mock_response.raise_for_status = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await tool.pull_model("llama2")

            assert result["success"] is True
            assert result["model"] == "llama2"
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_delete_model(self):
        """Test deleting a model"""
        tool = OllamaTool({})

        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.delete = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await tool.delete_model("llama2")

            assert result["success"] is True
            assert result["model"] == "llama2"
            assert result["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_get_model_info(self):
        """Test getting model info"""
        tool = OllamaTool({})

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "modelfile": "FROM llama2:latest",
            "parameters": {"num_ctx": 2048}
        })
        mock_response.raise_for_status = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await tool.get_model_info("llama2")

            assert result["success"] is True
            assert result["model"] == "llama2"
            assert result["info"] is not None

    def test_get_tool_info(self):
        """Test get_tool_info method"""
        tool = OllamaTool({
            "url": "http://localhost:11434",
            "model": "codellama",
            "auto_pull": True,
            "max_retries": 5
        })

        info = tool.get_tool_info()

        assert info["name"] == "OllamaTool"
        assert info["type"] == "ai_tool"
        assert info["provider"] == "ollama"
        assert info["url"] == "http://localhost:11434"
        assert info["model"] == "codellama"
        assert "text_generation" in info["capabilities"]
        assert "code_generation" in info["capabilities"]
        assert "streaming_support" in info["capabilities"]
        assert "model_management" in info["capabilities"]
        assert "llama2" in info["supported_models"]
        assert "codellama" in info["supported_models"]
        assert info["features"]["streaming"] is True
        assert info["features"]["chat"] is True
        assert info["features"]["retry_logic"] is True
        assert info["features"]["auto_pull"] is True
        assert info["features"]["max_retries"] == 5
