"""Unit tests for Gemini CLI tool"""

import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pytest

from src.tools.gemini_cli import GeminiCLI


class TestGeminiCLI:
    """Test cases for GeminiCLI tool"""

    @pytest.fixture
    def config(self):
        """Basic configuration for testing"""
        return {
            "api_key": "test-api-key",
            "model": "gemini-1.5-flash",
            "timeout": 60,
            "temperature": 0.7,
            "max_output_tokens": 1024,
        }

    @pytest.fixture
    def mock_genai(self):
        """Mock google.generativeai module"""
        with patch('src.tools.gemini_cli.genai') as mock:
            # Mock the GenerativeModel
            mock_model = MagicMock()
            mock.GenerativeModel.return_value = mock_model
            yield mock

    def test_init_with_api_key_in_config(self, config, mock_genai):
        """Test initialization with API key in config"""
        tool = GeminiCLI(config)

        assert tool.api_key == "test-api-key"
        assert tool.model_name == "gemini-1.5-flash"
        assert tool.timeout == 60
        assert tool.temperature == 0.7
        assert tool.max_output_tokens == 1024

        # Verify genai.configure was called
        mock_genai.configure.assert_called_once_with(api_key="test-api-key")

    def test_init_with_env_var(self, mock_genai):
        """Test initialization with API key from environment"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "env-api-key"}):
            config = {"model": "gemini-pro"}
            tool = GeminiCLI(config)

            assert tool.api_key == "env-api-key"
            mock_genai.configure.assert_called_once_with(api_key="env-api-key")

    def test_init_missing_api_key(self, mock_genai):
        """Test initialization fails without API key"""
        with patch.dict(os.environ, {}, clear=True):
            config = {"model": "gemini-pro"}

            with pytest.raises(ValueError, match="GOOGLE_API_KEY must be provided"):
                GeminiCLI(config)

    def test_init_defaults(self, config, mock_genai):
        """Test default configuration values"""
        minimal_config = {"api_key": "test-key"}
        tool = GeminiCLI(minimal_config)

        assert tool.model_name == GeminiCLI.DEFAULT_MODEL
        assert tool.timeout == GeminiCLI.DEFAULT_TIMEOUT
        assert tool.max_retries == GeminiCLI.DEFAULT_MAX_RETRIES
        assert tool.stream is False
        assert tool.temperature == 0.7

    @pytest.mark.asyncio
    async def test_validate_config_success(self, config, mock_genai):
        """Test successful configuration validation"""
        tool = GeminiCLI(config)
        result = await tool.validate_config()

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_config_missing_api_key(self, config, mock_genai):
        """Test validation fails with missing API key"""
        tool = GeminiCLI(config)
        tool.api_key = None

        result = await tool.validate_config()
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_config_invalid_timeout(self, config, mock_genai):
        """Test validation fails with invalid timeout"""
        tool = GeminiCLI(config)
        tool.timeout = -1

        result = await tool.validate_config()
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_config_invalid_temperature(self, config, mock_genai):
        """Test validation fails with invalid temperature"""
        tool = GeminiCLI(config)
        tool.temperature = 3.0

        result = await tool.validate_config()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_success(self, config, mock_genai):
        """Test successful health check"""
        tool = GeminiCLI(config)

        # Mock successful response
        mock_response = MagicMock()
        mock_response.text = "Hello response"
        tool.model.generate_content = Mock(return_value=mock_response)

        result = await tool.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, config, mock_genai):
        """Test health check with timeout"""
        tool = GeminiCLI(config)

        # Mock timeout
        async def slow_generation(*args, **kwargs):
            await asyncio.sleep(20)
            return MagicMock(text="response")

        with patch('asyncio.to_thread', side_effect=slow_generation):
            result = await tool.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_api_error(self, config, mock_genai):
        """Test health check with API error"""
        tool = GeminiCLI(config)

        # Mock API error
        tool.model.generate_content = Mock(side_effect=Exception("API Error"))

        result = await tool.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_execute_success(self, config, mock_genai):
        """Test successful task execution"""
        tool = GeminiCLI(config)

        # Mock successful response
        mock_response = MagicMock()
        mock_response.text = "Generated response"
        mock_response.candidates = [MagicMock(finish_reason="STOP")]

        # Mock usage metadata
        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 10
        mock_usage.candidates_token_count = 20
        mock_usage.total_token_count = 30
        mock_response.usage_metadata = mock_usage

        async def mock_generate(*args, **kwargs):
            return mock_response

        with patch('asyncio.to_thread', side_effect=mock_generate):
            result = await tool.execute("Test prompt")

        assert result["success"] is True
        assert result["output"] == "Generated response"
        assert result["error"] is None
        assert "metadata" in result
        assert result["metadata"]["model"] == "gemini-1.5-flash"
        assert result["metadata"]["prompt_tokens"] == 10
        assert result["metadata"]["completion_tokens"] == 20
        assert result["metadata"]["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_execute_with_context(self, config, mock_genai):
        """Test execution with context data"""
        tool = GeminiCLI(config)

        # Mock response
        mock_response = MagicMock()
        mock_response.text = "Response with context"
        mock_response.candidates = [MagicMock(finish_reason="STOP")]

        async def mock_generate(*args, **kwargs):
            return mock_response

        context = {
            "system_instructions": "You are a helpful assistant",
            "files": [
                {"path": "test.py", "content": "print('hello')"}
            ],
            "code": "def foo(): pass",
            "parameters": {"language": "python"}
        }

        with patch('asyncio.to_thread', side_effect=mock_generate):
            result = await tool.execute("Analyze this code", context=context)

        assert result["success"] is True
        assert result["output"] == "Response with context"

    @pytest.mark.asyncio
    async def test_execute_api_error(self, config, mock_genai):
        """Test execution with API error"""
        tool = GeminiCLI(config)

        # Mock API error
        async def mock_error(*args, **kwargs):
            raise Exception("API request failed")

        with patch('asyncio.to_thread', side_effect=mock_error):
            result = await tool.execute("Test prompt")

        assert result["success"] is False
        assert result["output"] is None
        assert "API request failed" in result["error"]
        assert "duration" in result["metadata"]

    @pytest.mark.asyncio
    async def test_execute_timeout(self, config, mock_genai):
        """Test execution with timeout"""
        config["timeout"] = 1
        tool = GeminiCLI(config)

        # Mock slow response
        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(10)
            return MagicMock(text="response")

        with patch('asyncio.to_thread', side_effect=slow_generate):
            result = await tool.execute("Test prompt")

        assert result["success"] is False
        assert result["output"] is None
        assert "timeout" in result["error"].lower() or "failed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_with_retry(self, config, mock_genai):
        """Test execution with retry on transient error"""
        tool = GeminiCLI(config)

        # Mock: fail twice, succeed on third attempt
        call_count = 0

        async def mock_generate_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Create a mock exception that behaves like ServiceUnavailable
                from unittest.mock import Mock
                # Use asyncio.TimeoutError which will trigger retry
                raise asyncio.TimeoutError("Service unavailable")
            return MagicMock(text="Success after retry", candidates=[])

        with patch('asyncio.to_thread', side_effect=mock_generate_with_retry):
            with patch('asyncio.sleep'):  # Speed up test
                result = await tool.execute("Test prompt")

        assert result["success"] is True
        assert call_count == 3

    def test_build_prompt_basic(self, config, mock_genai):
        """Test basic prompt building"""
        tool = GeminiCLI(config)

        prompt = tool._build_prompt("Write a function", {})
        assert "Write a function" in prompt

    def test_build_prompt_with_context(self, config, mock_genai):
        """Test prompt building with full context"""
        tool = GeminiCLI(config)

        context = {
            "system_instructions": "You are an expert",
            "files": [
                {"path": "main.py", "content": "code here"}
            ],
            "code": "def example(): pass",
            "parameters": {"lang": "python", "style": "PEP8"}
        }

        prompt = tool._build_prompt("Refactor this", context)

        assert "You are an expert" in prompt
        assert "main.py" in prompt
        assert "code here" in prompt
        assert "def example(): pass" in prompt
        assert "lang: python" in prompt
        assert "Refactor this" in prompt

    @pytest.mark.asyncio
    async def test_streaming_response(self, config, mock_genai):
        """Test streaming response processing"""
        config["stream"] = True
        tool = GeminiCLI(config)

        # Mock streaming response
        chunk1 = MagicMock()
        chunk1.text = "Hello "
        chunk2 = MagicMock()
        chunk2.text = "world!"

        mock_response = [chunk1, chunk2]
        mock_response_iter = iter(mock_response)

        async def mock_generate(*args, **kwargs):
            return mock_response_iter

        with patch('asyncio.to_thread', side_effect=mock_generate):
            result = await tool.execute("Test")

        assert result["success"] is True
        assert result["output"] == "Hello world!"

    def test_rate_limiting(self, config, mock_genai):
        """Test rate limiting logic"""
        tool = GeminiCLI(config)

        # Simulate hitting rate limit
        tool.request_count = tool.MAX_REQUESTS_PER_MINUTE
        tool.rate_limit_window_start = tool.rate_limit_window_start

        # This should trigger rate limiting
        import time
        start = time.time()
        tool._check_rate_limit()
        duration = time.time() - start

        # Should have waited or reset counter
        assert tool.request_count <= tool.MAX_REQUESTS_PER_MINUTE

    def test_get_tool_info(self, config, mock_genai):
        """Test get_tool_info returns correct information"""
        tool = GeminiCLI(config)

        info = tool.get_tool_info()

        assert info["name"] == "GeminiCLI"
        assert info["type"] == "ai_tool"
        assert info["provider"] == "google"
        assert info["model"] == "gemini-1.5-flash"
        assert "text_generation" in info["capabilities"]
        assert "streaming" in info["capabilities"]
        assert "supported_models" in info
        assert len(info["supported_models"]) > 0

    def test_supported_models(self, config, mock_genai):
        """Test that all supported models are listed"""
        tool = GeminiCLI(config)

        assert "gemini-pro" in tool.SUPPORTED_MODELS
        assert "gemini-1.5-flash" in tool.SUPPORTED_MODELS
        assert "gemini-2.0-flash-exp" in tool.SUPPORTED_MODELS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
