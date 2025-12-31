"""
Retry Mechanism with Exponential Backoff

This module provides retry decorators and functions for handling transient failures
with configurable backoff strategies.
"""

import asyncio
import functools
from typing import Callable, Optional, Tuple, Type, Union
import structlog

from ..exceptions import WorkerException


logger = structlog.get_logger(__name__)


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Optional[Tuple[Type[Exception], ...]] = None
):
    """
    Retry a coroutine function with exponential backoff

    Implements exponential backoff with optional jitter to avoid thundering herd.
    Only retries on specified exceptions or WorkerException with recoverable=True.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Add random jitter to delay (default: True)
        exceptions: Tuple of exception types to retry on (default: None, retries on all)

    Returns:
        Result of the function call

    Raises:
        The last exception if all retries fail

    Example:
        async def fetch_data():
            # Some operation that may fail
            pass

        result = await retry_with_backoff(
            fetch_data,
            max_retries=5,
            base_delay=2.0
        )
    """
    last_exception = None

    for attempt in range(max_retries + 1):  # +1 to include initial attempt
        try:
            return await func()

        except Exception as e:
            last_exception = e

            # Check if we should retry this exception
            should_retry = False

            if exceptions:
                # If specific exceptions are specified, only retry those
                if isinstance(e, exceptions):
                    should_retry = True
            elif isinstance(e, WorkerException):
                # For WorkerExceptions, check recoverable flag
                should_retry = e.recoverable
            else:
                # For other exceptions (when no specific exceptions specified), retry all
                should_retry = True

            if not should_retry or attempt == max_retries:
                # Don't retry or max retries reached
                logger.error(
                    "Operation failed after retries",
                    function=func.__name__,
                    attempts=attempt + 1,
                    error=str(e),
                    recoverable=getattr(e, 'recoverable', False)
                )
                raise

            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** attempt), max_delay)

            # Add jitter if enabled (random value between 0 and delay)
            if jitter:
                import random
                delay = delay * (0.5 + random.random() * 0.5)

            logger.warning(
                "Operation failed, retrying",
                function=func.__name__,
                attempt=attempt + 1,
                max_retries=max_retries,
                delay=round(delay, 2),
                error=str(e)
            )

            await asyncio.sleep(delay)

    # This should never be reached, but just in case
    if last_exception:
        raise last_exception


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Optional[Tuple[Type[Exception], ...]] = None
):
    """
    Decorator for retrying async functions with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to delay
        exceptions: Tuple of exception types to retry on

    Example:
        @with_retry(max_retries=5, base_delay=2.0)
        async def fetch_subtask(worker_id: str):
            # API call that may fail
            pass
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            async def call_func():
                return await func(*args, **kwargs)

            return await retry_with_backoff(
                call_func,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                exceptions=exceptions
            )

        return wrapper
    return decorator


class RetryContext:
    """
    Context manager for retry operations with tracking

    Provides a context manager that tracks retry attempts and provides
    callback hooks for monitoring.

    Example:
        async with RetryContext(max_retries=3) as retry:
            while retry.should_retry():
                try:
                    result = await some_operation()
                    retry.success()
                    return result
                except Exception as e:
                    retry.failed(e)
    """
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        on_retry: Optional[Callable] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.on_retry = on_retry

        self.attempt = 0
        self.last_error = None
        self._success = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Suppress exception if we haven't exceeded max retries
        return False

    def should_retry(self) -> bool:
        """Check if we should attempt another retry"""
        return self.attempt <= self.max_retries and not self._success

    async def failed(self, error: Exception):
        """
        Mark current attempt as failed

        Args:
            error: The exception that caused the failure
        """
        self.last_error = error
        self.attempt += 1

        if self.attempt <= self.max_retries:
            # Calculate delay
            delay = min(
                self.base_delay * (self.exponential_base ** (self.attempt - 1)),
                self.max_delay
            )

            logger.warning(
                "Retry attempt failed",
                attempt=self.attempt,
                max_retries=self.max_retries,
                delay=round(delay, 2),
                error=str(error)
            )

            # Call callback if provided
            if self.on_retry:
                await self.on_retry(self.attempt, error, delay)

            await asyncio.sleep(delay)

    def success(self):
        """Mark operation as successful"""
        self._success = True

        if self.attempt > 0:
            logger.info(
                "Operation succeeded after retries",
                attempts=self.attempt + 1
            )


async def retry_async_generator(
    generator_func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0
):
    """
    Retry an async generator function

    Args:
        generator_func: Async generator function to retry
        max_retries: Maximum retry attempts
        base_delay: Base delay between retries

    Yields:
        Items from the generator

    Example:
        async def fetch_items():
            async for item in api.stream_items():
                yield item

        async for item in retry_async_generator(fetch_items):
            process(item)
    """
    for attempt in range(max_retries + 1):
        try:
            async for item in generator_func():
                yield item
            return  # Success

        except Exception as e:
            if attempt == max_retries:
                logger.error(
                    "Async generator failed after retries",
                    attempts=attempt + 1,
                    error=str(e)
                )
                raise

            delay = base_delay * (2 ** attempt)
            logger.warning(
                "Async generator failed, retrying",
                attempt=attempt + 1,
                delay=delay,
                error=str(e)
            )
            await asyncio.sleep(delay)
