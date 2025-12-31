"""Ollama Local LLM tool implementation using aiohttp"""

import asyncio
import time
from typing import Any, AsyncIterator, Dict, Optional

import aiohttp

from .base import BaseTool


class OllamaTool(BaseTool):
    """Ollama local LLM integration tool

    Supports running local LLMs through Ollama's HTTP API.
    Supports models: llama2, codellama, mistral, qwen2.5-coder, etc.
    """

    # Default configuration
    DEFAULT_URL = "http://localhost:11434"
    DEFAULT_MODEL = "llama2"
    DEFAULT_TIMEOUT = 300.0  # 5 minutes for LLM generation
    DEFAULT_CONNECT_TIMEOUT = 10.0  # 10 seconds for connection
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0

    # API endpoints
    GENERATE_ENDPOINT = "/api/generate"
    CHAT_ENDPOINT = "/api/chat"
    TAGS_ENDPOINT = "/api/tags"
    PULL_ENDPOINT = "/api/pull"
    DELETE_ENDPOINT = "/api/delete"
    SHOW_ENDPOINT = "/api/show"

    def __init__(self, config: Dict[str, Any]):
        """Initialize Ollama tool

        Args:
            config: Configuration dictionary with:
                - url: Ollama API URL (default: http://localhost:11434)
                - model: Model name (default: llama2)
                - timeout: Request timeout in seconds (default: 300)
                - connect_timeout: Connection timeout in seconds (default: 10)
                - stream: Enable streaming output (default: False)
                - temperature: Sampling temperature (default: 0.7)
                - max_tokens: Maximum tokens to generate (optional)
                - max_retries: Maximum connection retry attempts (default: 3)
                - retry_delay: Delay between retries in seconds (default: 1.0)
                - auto_pull: Auto-pull model if not available (default: False)
        """
        super().__init__(config)
        self.url = config.get("url", self.DEFAULT_URL).rstrip("/")
        self.model = config.get("model", self.DEFAULT_MODEL)
        self.timeout = config.get("timeout", self.DEFAULT_TIMEOUT)
        self.connect_timeout = config.get("connect_timeout", self.DEFAULT_CONNECT_TIMEOUT)
        self.stream = config.get("stream", False)
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens")
        self.max_retries = config.get("max_retries", self.DEFAULT_MAX_RETRIES)
        self.retry_delay = config.get("retry_delay", self.DEFAULT_RETRY_DELAY)
        self.auto_pull = config.get("auto_pull", False)

    async def execute(
        self,
        instructions: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute task with Ollama

        Args:
            instructions: Prompt/instructions for the LLM
            context: Optional context with:
                - system_prompt: System prompt for chat mode
                - use_chat: Use chat endpoint instead of generate
                - model: Override default model
                - temperature: Override default temperature
                - max_tokens: Override default max_tokens
                - stream: Override default stream setting
                - callback: Optional callback for streaming (fn(chunk: str))

        Returns:
            Dictionary with:
                - success: bool - Whether execution succeeded
                - output: str - Generated text
                - error: Optional[str] - Error message if failed
                - metadata: Dict - Metadata (model, tokens, duration, etc.)
        """
        start_time = time.time()
        context = context or {}

        # Extract context parameters
        use_chat = context.get("use_chat", False)
        model = context.get("model", self.model)
        temperature = context.get("temperature", self.temperature)
        max_tokens = context.get("max_tokens", self.max_tokens)
        system_prompt = context.get("system_prompt")
        stream = context.get("stream", self.stream)
        callback = context.get("callback")

        # Ensure model is available
        if self.auto_pull:
            model_check = await self._ensure_model_available(model)
            if not model_check["available"]:
                return {
                    "success": False,
                    "output": None,
                    "error": f"Model '{model}' not available and auto-pull failed: {model_check.get('error', 'Unknown error')}",
                    "metadata": {
                        "model": model,
                        "duration": time.time() - start_time,
                        "error_type": "model_unavailable"
                    }
                }

        try:
            timeout = aiohttp.ClientTimeout(
                total=self.timeout,
                connect=self.connect_timeout
            )

            async with aiohttp.ClientSession(timeout=timeout) as session:
                if use_chat:
                    # Use chat endpoint
                    result = await self._chat_completion(
                        session=session,
                        prompt=instructions,
                        system_prompt=system_prompt,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=stream,
                        callback=callback
                    )
                else:
                    # Use generate endpoint
                    result = await self._generate_completion(
                        session=session,
                        prompt=instructions,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=stream,
                        callback=callback
                    )

                duration = time.time() - start_time

                return {
                    "success": True,
                    "output": result["response"],
                    "error": None,
                    "metadata": {
                        "model": model,
                        "duration": duration,
                        "prompt_tokens": result.get("prompt_eval_count", 0),
                        "completion_tokens": result.get("eval_count", 0),
                        "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
                        "load_duration": result.get("load_duration", 0),
                        "eval_duration": result.get("eval_duration", 0),
                        "streamed": stream
                    }
                }

        except aiohttp.ClientConnectorError as e:
            return {
                "success": False,
                "output": None,
                "error": f"Failed to connect to Ollama at {self.url}: {str(e)}. Is Ollama running?",
                "metadata": {
                    "model": model,
                    "duration": time.time() - start_time,
                    "error_type": "connection_error"
                }
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "output": None,
                "error": f"Request timed out after {self.timeout}s",
                "metadata": {
                    "model": model,
                    "duration": time.time() - start_time,
                    "error_type": "timeout"
                }
            }
        except aiohttp.ClientResponseError as e:
            return {
                "success": False,
                "output": None,
                "error": f"HTTP error {e.status}: {e.message}",
                "metadata": {
                    "model": model,
                    "duration": time.time() - start_time,
                    "error_type": "http_error",
                    "status_code": e.status
                }
            }
        except Exception as e:
            return {
                "success": False,
                "output": None,
                "error": f"Unexpected error: {str(e)}",
                "metadata": {
                    "model": model,
                    "duration": time.time() - start_time,
                    "error_type": "unknown",
                    "exception": type(e).__name__
                }
            }

    async def _generate_completion(
        self,
        session: aiohttp.ClientSession,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Call Ollama generate endpoint

        Args:
            session: aiohttp session
            prompt: Prompt text
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Enable streaming
            callback: Optional callback for streaming chunks

        Returns:
            Response dictionary from Ollama
        """
        url = f"{self.url}{self.GENERATE_ENDPOINT}"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        if stream:
            return await self._handle_streaming_response(session, url, payload, callback)
        else:
            return await self._handle_non_streaming_response(session, url, payload)

    async def _chat_completion(
        self,
        session: aiohttp.ClientSession,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Call Ollama chat endpoint

        Args:
            session: aiohttp session
            prompt: User message
            system_prompt: Optional system prompt
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Enable streaming
            callback: Optional callback for streaming chunks

        Returns:
            Response dictionary from Ollama
        """
        url = f"{self.url}{self.CHAT_ENDPOINT}"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        if stream:
            result = await self._handle_streaming_response(session, url, payload, callback)
            # Extract response from message format for chat
            if "message" in result and "content" in result["message"]:
                result["response"] = result["message"]["content"]
            return result
        else:
            result = await self._handle_non_streaming_response(session, url, payload)
            # Extract response from message format for chat
            if "message" in result and "content" in result["message"]:
                result["response"] = result["message"]["content"]
            return result

    async def _handle_non_streaming_response(
        self,
        session: aiohttp.ClientSession,
        url: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle non-streaming response with retry logic

        Args:
            session: aiohttp session
            url: API endpoint URL
            payload: Request payload

        Returns:
            Response dictionary from Ollama
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                async with session.post(url, json=payload) as response:
                    response.raise_for_status()
                    return await response.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                continue

        # If all retries failed, raise the last error
        if last_error:
            raise last_error
        raise Exception("All retry attempts failed")

    async def _handle_streaming_response(
        self,
        session: aiohttp.ClientSession,
        url: str,
        payload: Dict[str, Any],
        callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Handle streaming response from Ollama

        Args:
            session: aiohttp session
            url: API endpoint URL
            payload: Request payload
            callback: Optional callback for streaming chunks

        Returns:
            Aggregated response dictionary
        """
        import json

        full_response = ""
        metadata = {}

        async with session.post(url, json=payload) as response:
            response.raise_for_status()

            async for line in response.content:
                if not line:
                    continue

                try:
                    chunk_data = json.loads(line.decode('utf-8'))

                    # Extract response text
                    if "response" in chunk_data:
                        chunk_text = chunk_data["response"]
                        full_response += chunk_text

                        # Call callback if provided
                        if callback:
                            await callback(chunk_text)

                    # Extract message content for chat endpoint
                    if "message" in chunk_data and "content" in chunk_data["message"]:
                        chunk_text = chunk_data["message"]["content"]
                        full_response += chunk_text

                        # Call callback if provided
                        if callback:
                            await callback(chunk_text)

                    # Update metadata with final chunk info
                    if chunk_data.get("done", False):
                        metadata.update({
                            "prompt_eval_count": chunk_data.get("prompt_eval_count", 0),
                            "eval_count": chunk_data.get("eval_count", 0),
                            "load_duration": chunk_data.get("load_duration", 0),
                            "eval_duration": chunk_data.get("eval_duration", 0),
                            "total_duration": chunk_data.get("total_duration", 0)
                        })

                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

        result = {
            "response": full_response,
            **metadata
        }

        return result

    async def validate_config(self) -> bool:
        """Validate tool configuration

        Returns:
            True if configuration is valid, False otherwise
        """
        # Check required configuration
        if not self.url:
            return False

        if not self.model:
            return False

        # Validate timeout
        if self.timeout <= 0:
            return False

        if self.connect_timeout <= 0:
            return False

        # Validate temperature
        if not (0.0 <= self.temperature <= 2.0):
            return False

        # Validate max_tokens if provided
        if self.max_tokens is not None and self.max_tokens <= 0:
            return False

        # Validate retry settings
        if self.max_retries < 0:
            return False

        if self.retry_delay < 0:
            return False

        return True

    async def health_check(self) -> bool:
        """Check if Ollama is available and responsive

        Returns:
            True if Ollama is healthy, False otherwise
        """
        try:
            timeout = aiohttp.ClientTimeout(total=10.0, connect=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Try to list available models
                url = f"{self.url}{self.TAGS_ENDPOINT}"
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()

                    # Check if our configured model is available
                    models = data.get("models", [])

                    # Extract model names
                    available_models = [m.get("name", "").split(":")[0] for m in models]

                    # Check if our model is available (exact match or base name match)
                    model_base = self.model.split(":")[0]
                    return model_base in available_models or self.model in [m.get("name", "") for m in models]

        except Exception:
            return False

    async def detailed_health_check(self) -> Dict[str, Any]:
        """Perform detailed health check with structured status

        Returns:
            Dictionary containing detailed health information
        """
        start_time = time.time()

        try:
            timeout = aiohttp.ClientTimeout(total=10.0, connect=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.url}{self.TAGS_ENDPOINT}"
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()

                    latency = (time.time() - start_time) * 1000
                    models = data.get("models", [])
                    available_models = [m.get("name", "") for m in models]

                    model_base = self.model.split(":")[0]
                    model_available = (
                        model_base in [m.split(":")[0] for m in available_models] or
                        self.model in available_models
                    )

                    status = "healthy" if model_available else "degraded"

                    return {
                        "status": status,
                        "available": True,
                        "latency": round(latency, 2),
                        "version": data.get("version"),
                        "error": None if model_available else f"Model '{self.model}' not found",
                        "metadata": {
                            "tool_name": self.name,
                            "url": self.url,
                            "model": self.model,
                            "model_available": model_available,
                            "available_models": available_models
                        }
                    }
        except aiohttp.ClientConnectorError as e:
            latency = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "available": False,
                "latency": round(latency, 2),
                "version": None,
                "error": f"Connection failed: {str(e)}. Is Ollama running?",
                "metadata": {
                    "tool_name": self.name,
                    "url": self.url,
                    "error_type": "connection_error"
                }
            }
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return {
                "status": "unhealthy",
                "available": False,
                "latency": round(latency, 2),
                "version": None,
                "error": f"Health check error: {str(e)}",
                "metadata": {
                    "tool_name": self.name,
                    "url": self.url,
                    "error_type": type(e).__name__
                }
            }

    async def _ensure_model_available(self, model: str) -> Dict[str, bool]:
        """Ensure model is available, pull if necessary

        Args:
            model: Model name to check/pull

        Returns:
            Dictionary with 'available' bool and optional 'error' string
        """
        try:
            # Check if model exists
            timeout = aiohttp.ClientTimeout(total=10.0, connect=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.url}{self.TAGS_ENDPOINT}"
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()

                    models = data.get("models", [])
                    available_models = [m.get("name", "") for m in models]
                    model_base = model.split(":")[0]

                    if model_base in [m.split(":")[0] for m in available_models] or model in available_models:
                        return {"available": True}

                    # Model not found, try to pull
                    if self.auto_pull:
                        await self.pull_model(model)
                        return {"available": True}

                    return {"available": False, "error": f"Model '{model}' not found"}

        except Exception as e:
            return {"available": False, "error": str(e)}

    async def pull_model(self, model: str) -> Dict[str, Any]:
        """Pull a model from Ollama library

        Args:
            model: Model name to pull

        Returns:
            Dictionary with success status and details
        """
        try:
            # Use longer timeout for model pulling (can take several minutes)
            timeout = aiohttp.ClientTimeout(total=600.0, connect=10.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.url}{self.PULL_ENDPOINT}"
                payload = {"name": model, "stream": False}

                async with session.post(url, json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()

                    return {
                        "success": True,
                        "model": model,
                        "status": data.get("status", "pulled"),
                        "error": None
                    }

        except Exception as e:
            return {
                "success": False,
                "model": model,
                "status": "failed",
                "error": str(e)
            }

    async def delete_model(self, model: str) -> Dict[str, Any]:
        """Delete a model from local storage

        Args:
            model: Model name to delete

        Returns:
            Dictionary with success status and details
        """
        try:
            timeout = aiohttp.ClientTimeout(total=30.0, connect=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.url}{self.DELETE_ENDPOINT}"
                payload = {"name": model}

                async with session.delete(url, json=payload) as response:
                    response.raise_for_status()

                    return {
                        "success": True,
                        "model": model,
                        "status": "deleted",
                        "error": None
                    }

        except Exception as e:
            return {
                "success": False,
                "model": model,
                "status": "failed",
                "error": str(e)
            }

    async def list_models(self) -> Dict[str, Any]:
        """List all available models

        Returns:
            Dictionary with list of models and metadata
        """
        try:
            timeout = aiohttp.ClientTimeout(total=10.0, connect=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.url}{self.TAGS_ENDPOINT}"
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()

                    return {
                        "success": True,
                        "models": data.get("models", []),
                        "error": None
                    }

        except Exception as e:
            return {
                "success": False,
                "models": [],
                "error": str(e)
            }

    async def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get detailed information about a model

        Args:
            model: Model name

        Returns:
            Dictionary with model details
        """
        try:
            timeout = aiohttp.ClientTimeout(total=10.0, connect=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.url}{self.SHOW_ENDPOINT}"
                payload = {"name": model}

                async with session.post(url, json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()

                    return {
                        "success": True,
                        "model": model,
                        "info": data,
                        "error": None
                    }

        except Exception as e:
            return {
                "success": False,
                "model": model,
                "info": None,
                "error": str(e)
            }

    async def cancel(self) -> bool:
        """Cancel any ongoing execution

        For HTTP-based operations, cancellation is handled via
        asyncio.CancelledError propagation in the aiohttp session.

        Returns:
            True if cancellation was successful, False otherwise
        """
        # HTTP requests are managed by aiohttp session
        # Cancellation is handled via asyncio.CancelledError propagation
        return True

    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information

        Returns:
            Dictionary with tool name, version, capabilities, etc.
        """
        return {
            "name": self.name,
            "type": "ai_tool",
            "provider": "ollama",
            "url": self.url,
            "model": self.model,
            "capabilities": [
                "text_generation",
                "code_generation",
                "chat_completion",
                "local_execution",
                "streaming_support",
                "model_management"
            ],
            "supported_models": [
                "llama2",
                "llama3",
                "codellama",
                "mistral",
                "mixtral",
                "qwen2.5-coder",
                "gemma",
                "phi",
                "neural-chat",
                "starling-lm",
                "orca-mini",
                "vicuna"
            ],
            "features": {
                "streaming": True,
                "chat": True,
                "retry_logic": True,
                "auto_pull": self.auto_pull,
                "max_retries": self.max_retries,
                "cancellation": True
            }
        }
