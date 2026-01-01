"""
Circuit Breaker Pattern Implementation

Provides fault tolerance for external service calls by preventing
cascading failures through automatic service isolation.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is unavailable, requests fail fast
- HALF_OPEN: Testing if service has recovered
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Union
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    # Number of failures before opening circuit
    failure_threshold: int = 5
    # Time in seconds to wait before attempting recovery
    recovery_timeout: float = 30.0
    # Number of successful calls needed to close circuit from half-open
    success_threshold: int = 2
    # Exceptions that should trigger the circuit breaker
    expected_exceptions: tuple = field(default_factory=lambda: (Exception,))
    # Maximum number of concurrent half-open requests
    half_open_max_calls: int = 1


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker"""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    total_failures: int = 0
    total_successes: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    def __init__(self, circuit_name: str, time_remaining: float):
        self.circuit_name = circuit_name
        self.time_remaining = time_remaining
        super().__init__(
            f"Circuit breaker '{circuit_name}' is open. "
            f"Retry after {time_remaining:.1f} seconds."
        )


class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.

    Usage:
        breaker = CircuitBreaker("redis_service")

        # As decorator
        @breaker
        async def call_redis():
            ...

        # As context manager
        async with breaker:
            await redis.get("key")

        # Manual usage
        if breaker.can_execute():
            try:
                result = await some_operation()
                breaker.record_success()
            except Exception as e:
                breaker.record_failure()
                raise
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Identifier for this circuit breaker
            config: Configuration options
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitStats()
        self._lock = asyncio.Lock()
        self._half_open_semaphore = asyncio.Semaphore(
            self.config.half_open_max_calls
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self.stats.state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)"""
        return self.stats.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)"""
        return self.stats.state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)"""
        return self.stats.state == CircuitState.HALF_OPEN

    def _get_time_remaining(self) -> float:
        """Get time remaining before circuit can transition to half-open"""
        if not self.stats.last_failure_time:
            return 0.0
        elapsed = time.time() - self.stats.last_failure_time
        remaining = self.config.recovery_timeout - elapsed
        return max(0.0, remaining)

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if not self.stats.last_failure_time:
            return True
        elapsed = time.time() - self.stats.last_failure_time
        return elapsed >= self.config.recovery_timeout

    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state"""
        old_state = self.stats.state
        self.stats.state = new_state

        if new_state == CircuitState.CLOSED:
            self.stats.failure_count = 0
            self.stats.consecutive_failures = 0
        elif new_state == CircuitState.OPEN:
            self.stats.success_count = 0
            self.stats.consecutive_successes = 0
        elif new_state == CircuitState.HALF_OPEN:
            self.stats.success_count = 0
            self.stats.consecutive_successes = 0

        logger.info(
            "Circuit breaker state changed",
            circuit=self.name,
            old_state=old_state.value,
            new_state=new_state.value,
            consecutive_failures=self.stats.consecutive_failures,
            consecutive_successes=self.stats.consecutive_successes
        )

    async def can_execute(self) -> bool:
        """
        Check if a request can be executed.

        Returns:
            True if request should proceed, False otherwise
        """
        async with self._lock:
            if self.stats.state == CircuitState.CLOSED:
                return True

            if self.stats.state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    await self._transition_to(CircuitState.HALF_OPEN)
                    return True
                return False

            # Half-open: only allow limited concurrent requests
            return True

    async def record_success(self) -> None:
        """Record a successful operation"""
        async with self._lock:
            self.stats.success_count += 1
            self.stats.total_successes += 1
            self.stats.consecutive_successes += 1
            self.stats.consecutive_failures = 0
            self.stats.last_success_time = time.time()

            if self.stats.state == CircuitState.HALF_OPEN:
                if self.stats.consecutive_successes >= self.config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)

    async def record_failure(self, exception: Optional[Exception] = None) -> None:
        """Record a failed operation"""
        async with self._lock:
            self.stats.failure_count += 1
            self.stats.total_failures += 1
            self.stats.consecutive_failures += 1
            self.stats.consecutive_successes = 0
            self.stats.last_failure_time = time.time()

            logger.warning(
                "Circuit breaker recorded failure",
                circuit=self.name,
                failure_count=self.stats.failure_count,
                consecutive_failures=self.stats.consecutive_failures,
                exception=str(exception) if exception else None
            )

            if self.stats.state == CircuitState.HALF_OPEN:
                # Any failure in half-open state opens the circuit
                await self._transition_to(CircuitState.OPEN)
            elif self.stats.state == CircuitState.CLOSED:
                if self.stats.consecutive_failures >= self.config.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)

    async def reset(self) -> None:
        """Reset circuit breaker to closed state"""
        async with self._lock:
            self.stats = CircuitStats()
            logger.info("Circuit breaker reset", circuit=self.name)

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.stats.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "consecutive_failures": self.stats.consecutive_failures,
            "consecutive_successes": self.stats.consecutive_successes,
            "total_failures": self.stats.total_failures,
            "total_successes": self.stats.total_successes,
            "last_failure_time": self.stats.last_failure_time,
            "last_success_time": self.stats.last_success_time,
            "time_until_recovery": self._get_time_remaining() if self.is_open else 0,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold
            }
        }

    async def __aenter__(self) -> "CircuitBreaker":
        """Async context manager entry"""
        if not await self.can_execute():
            raise CircuitBreakerError(
                self.name,
                self._get_time_remaining()
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Async context manager exit"""
        if exc_type is None:
            await self.record_success()
        elif isinstance(exc_val, self.config.expected_exceptions):
            await self.record_failure(exc_val)
        return False  # Don't suppress exceptions

    def __call__(self, func: Callable) -> Callable:
        """Decorator for protecting async functions"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not await self.can_execute():
                raise CircuitBreakerError(
                    self.name,
                    self._get_time_remaining()
                )

            try:
                result = await func(*args, **kwargs)
                await self.record_success()
                return result
            except self.config.expected_exceptions as e:
                await self.record_failure(e)
                raise

        return wrapper


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Provides centralized access to circuit breakers for different services.
    """

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Get existing circuit breaker or create new one.

        Args:
            name: Circuit breaker name
            config: Configuration (only used if creating new)

        Returns:
            CircuitBreaker instance
        """
        async with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
                logger.info("Created circuit breaker", circuit=name)
            return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        return self._breakers.get(name)

    async def reset_all(self) -> None:
        """Reset all circuit breakers"""
        async with self._lock:
            for breaker in self._breakers.values():
                await breaker.reset()

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }

    def list_circuits(self) -> Dict[str, CircuitState]:
        """List all circuits and their states"""
        return {
            name: breaker.state
            for name, breaker in self._breakers.items()
        }


# Global registry instance
_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry"""
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry


async def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """
    Get or create a circuit breaker.

    Args:
        name: Circuit breaker name (e.g., "redis", "database", "external_api")
        config: Optional configuration

    Returns:
        CircuitBreaker instance
    """
    registry = get_circuit_registry()
    return await registry.get_or_create(name, config)


# Pre-configured circuit breakers for common services
REDIS_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=15.0,
    success_threshold=2,
    expected_exceptions=(ConnectionError, TimeoutError, Exception)
)

DATABASE_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=30.0,
    success_threshold=3,
    expected_exceptions=(ConnectionError, TimeoutError, Exception)
)

EXTERNAL_API_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=60.0,
    success_threshold=2,
    expected_exceptions=(ConnectionError, TimeoutError, Exception)
)
