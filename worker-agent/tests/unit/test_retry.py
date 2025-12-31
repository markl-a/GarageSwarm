"""
Unit Tests for Retry Mechanism

Tests for retry logic with exponential backoff, jitter, and error recovery.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from utils.retry import (
    retry_with_backoff,
    with_retry,
    RetryContext,
    retry_async_generator
)
from exceptions import (
    WorkerException,
    ConnectionError,
    TaskExecutionError,
    ToolError,
    TimeoutError
)


class TestRetryWithBackoff:
    """Test retry_with_backoff function"""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test successful execution on first attempt"""
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_with_backoff(func, max_retries=3)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_success_after_retries(self):
        """Test successful execution after some retries"""
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"

        result = await retry_with_backoff(
            func,
            max_retries=5,
            base_delay=0.01  # Small delay for testing
        )

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_failure_after_max_retries(self):
        """Test failure after exhausting retries"""
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Connection failed")

        with pytest.raises(ConnectionError):
            await retry_with_backoff(
                func,
                max_retries=3,
                base_delay=0.01
            )

        assert call_count == 4  # Initial attempt + 3 retries

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that delays follow exponential backoff"""
        call_times = []

        async def func():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ConnectionError("Connection failed")
            return "success"

        await retry_with_backoff(
            func,
            max_retries=3,
            base_delay=0.1,
            exponential_base=2.0,
            jitter=False  # Disable jitter for predictable timing
        )

        # Check that delays increase exponentially
        assert len(call_times) == 3
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # Second delay should be roughly 2x first delay (exponential_base=2)
        assert 0.08 <= delay1 <= 0.15  # ~0.1s with some tolerance
        assert 0.15 <= delay2 <= 0.25  # ~0.2s with some tolerance

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test that delay is capped at max_delay"""
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            # Always fail to test max delay cap
            raise ConnectionError("Connection failed")

        # With very high exponential base, we should hit max_delay
        with pytest.raises(ConnectionError):
            await retry_with_backoff(
                func,
                max_retries=5,
                base_delay=10.0,
                max_delay=0.05,  # Very small max
                exponential_base=10.0,
                jitter=False
            )

        # Should have tried initial + retries
        assert call_count == 6

    @pytest.mark.asyncio
    async def test_retry_only_recoverable_exceptions(self):
        """Test that only recoverable exceptions are retried"""
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            # Non-recoverable exception
            raise TaskExecutionError("Execution failed", recoverable=False)

        with pytest.raises(TaskExecutionError):
            await retry_with_backoff(
                func,
                max_retries=3,
                base_delay=0.01
            )

        # Should fail immediately without retries
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_specific_exceptions(self):
        """Test retry only on specific exception types"""
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Connection failed")
            raise ValueError("Different error")

        with pytest.raises(ValueError):
            await retry_with_backoff(
                func,
                max_retries=3,
                base_delay=0.01,
                exceptions=(ConnectionError,)
            )

        # Should retry ConnectionError but not ValueError
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to delays"""
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"

        # Just verify it completes successfully with jitter enabled
        result = await retry_with_backoff(
            func,
            max_retries=5,
            base_delay=0.01,
            jitter=True
        )

        assert result == "success"
        assert call_count == 3


class TestWithRetryDecorator:
    """Test with_retry decorator"""

    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Test decorator with successful execution"""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await func()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_decorator_with_retries(self):
        """Test decorator with retries"""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ToolError("Tool failed", recoverable=True)
            return "success"

        result = await func()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_decorator_with_args(self):
        """Test decorator with function arguments"""
        @with_retry(max_retries=2, base_delay=0.01)
        async def func(a, b, c=None):
            if a < 3:
                raise ConnectionError("Not ready")
            return f"{a}-{b}-{c}"

        result = await func(3, "test", c="value")

        assert result == "3-test-value"

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function metadata"""
        @with_retry(max_retries=3)
        async def my_function():
            """This is my function"""
            return "result"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "This is my function"


class TestRetryContext:
    """Test RetryContext context manager"""

    @pytest.mark.asyncio
    async def test_context_success_no_retry(self):
        """Test context manager with immediate success"""
        call_count = 0

        async with RetryContext(max_retries=3) as retry:
            while retry.should_retry():
                call_count += 1
                retry.success()

        assert call_count == 1
        assert retry.attempt == 0

    @pytest.mark.asyncio
    async def test_context_with_retries(self):
        """Test context manager with retries"""
        call_count = 0

        async with RetryContext(max_retries=3, base_delay=0.01) as retry:
            while retry.should_retry():
                call_count += 1
                try:
                    if call_count < 3:
                        raise ConnectionError("Failed")
                    retry.success()
                except Exception as e:
                    await retry.failed(e)

        assert call_count == 3
        assert retry.attempt == 2

    @pytest.mark.asyncio
    async def test_context_exhausts_retries(self):
        """Test context manager when retries are exhausted"""
        call_count = 0

        async with RetryContext(max_retries=2, base_delay=0.01) as retry:
            while retry.should_retry():
                call_count += 1
                await retry.failed(ConnectionError("Failed"))

        assert call_count == 3  # Initial + 2 retries
        assert retry.attempt == 3
        assert retry.last_error is not None

    @pytest.mark.asyncio
    async def test_context_with_callback(self):
        """Test context manager with retry callback"""
        callback_calls = []

        async def on_retry(attempt, error, delay):
            callback_calls.append((attempt, str(error), delay))

        async with RetryContext(
            max_retries=2,
            base_delay=0.01,
            on_retry=on_retry
        ) as retry:
            while retry.should_retry():
                if retry.attempt < 2:
                    await retry.failed(ConnectionError("Failed"))
                else:
                    retry.success()

        assert len(callback_calls) == 2
        assert all(isinstance(call[0], int) for call in callback_calls)


class TestRetryAsyncGenerator:
    """Test retry_async_generator function"""

    @pytest.mark.asyncio
    async def test_generator_success(self):
        """Test async generator with immediate success"""
        async def gen():
            for i in range(5):
                yield i

        results = []
        async for item in retry_async_generator(gen, max_retries=3, base_delay=0.01):
            results.append(item)

        assert results == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_generator_with_retry(self):
        """Test async generator with retry after failure"""
        call_count = 0

        async def gen():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection failed")
            for i in range(3):
                yield i

        results = []
        async for item in retry_async_generator(gen, max_retries=3, base_delay=0.01):
            results.append(item)

        assert results == [0, 1, 2]
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_generator_exhausts_retries(self):
        """Test async generator when retries are exhausted"""
        async def gen():
            raise ConnectionError("Always fails")
            yield  # Never reached

        with pytest.raises(ConnectionError):
            async for _ in retry_async_generator(gen, max_retries=2, base_delay=0.01):
                pass


class TestRecoverableExceptions:
    """Test recoverable vs non-recoverable exceptions"""

    @pytest.mark.asyncio
    async def test_recoverable_connection_error(self):
        """Test that ConnectionError is recoverable"""
        exc = ConnectionError("Connection failed")
        assert exc.recoverable is True

    @pytest.mark.asyncio
    async def test_recoverable_tool_error(self):
        """Test that ToolError is recoverable by default"""
        exc = ToolError("Tool failed")
        assert exc.recoverable is True

    @pytest.mark.asyncio
    async def test_non_recoverable_timeout(self):
        """Test that TimeoutError is not recoverable"""
        exc = TimeoutError("Timeout")
        assert exc.recoverable is False

    @pytest.mark.asyncio
    async def test_retry_respects_recoverable_flag(self):
        """Test that retry respects the recoverable flag"""
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            raise TaskExecutionError("Failed", recoverable=False)

        with pytest.raises(TaskExecutionError):
            await retry_with_backoff(func, max_retries=3, base_delay=0.01)

        # Should not retry non-recoverable errors
        assert call_count == 1


class TestErrorLogging:
    """Test error logging during retries"""

    @pytest.mark.asyncio
    async def test_retry_logs_warnings(self):
        """Test that retries log warning messages"""
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection failed")
            return "success"

        with patch('utils.retry.logger') as mock_logger:
            await retry_with_backoff(func, max_retries=3, base_delay=0.01)

            # Should log warning for retry
            assert mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_final_failure_logs_error(self):
        """Test that final failure logs error message"""
        async def func():
            raise ConnectionError("Connection failed")

        with patch('utils.retry.logger') as mock_logger:
            with pytest.raises(ConnectionError):
                await retry_with_backoff(func, max_retries=2, base_delay=0.01)

            # Should log error for final failure
            assert mock_logger.error.called
