"""
Unit tests for Circuit Breaker implementation
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import time

from src.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
    CircuitBreakerRegistry,
    get_circuit_registry,
    get_circuit_breaker,
)


@pytest.fixture
def circuit_config():
    """Create a test circuit breaker config with short timeouts"""
    return CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=1.0,  # Short timeout for testing
        success_threshold=2,
        expected_exceptions=(ValueError, ConnectionError),
    )


@pytest.fixture
def circuit_breaker(circuit_config):
    """Create a circuit breaker for testing"""
    return CircuitBreaker("test_circuit", circuit_config)


class TestCircuitBreakerStates:
    """Test circuit breaker state transitions"""

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, circuit_breaker):
        """Circuit breaker starts in closed state"""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.is_closed
        assert not circuit_breaker.is_open
        assert not circuit_breaker.is_half_open

    @pytest.mark.asyncio
    async def test_opens_after_failure_threshold(self, circuit_breaker):
        """Circuit opens after reaching failure threshold"""
        # Record failures up to threshold
        for _ in range(3):
            await circuit_breaker.record_failure(ValueError("test error"))

        assert circuit_breaker.is_open
        assert circuit_breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_stays_closed_below_threshold(self, circuit_breaker):
        """Circuit stays closed below failure threshold"""
        # Record failures below threshold
        for _ in range(2):
            await circuit_breaker.record_failure(ValueError("test error"))

        assert circuit_breaker.is_closed

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, circuit_breaker):
        """Success resets consecutive failure count"""
        # Record some failures
        await circuit_breaker.record_failure(ValueError("test error"))
        await circuit_breaker.record_failure(ValueError("test error"))

        # Record success
        await circuit_breaker.record_success()

        # Record more failures - should not open because count was reset
        await circuit_breaker.record_failure(ValueError("test error"))
        await circuit_breaker.record_failure(ValueError("test error"))

        assert circuit_breaker.is_closed

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self, circuit_breaker):
        """Circuit transitions to half-open after recovery timeout"""
        # Open the circuit
        for _ in range(3):
            await circuit_breaker.record_failure(ValueError("test error"))
        assert circuit_breaker.is_open

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Check if can execute - should transition to half-open
        can_execute = await circuit_breaker.can_execute()
        assert can_execute
        assert circuit_breaker.is_half_open

    @pytest.mark.asyncio
    async def test_closes_after_success_in_half_open(self, circuit_breaker):
        """Circuit closes after success threshold in half-open state"""
        # Open the circuit
        for _ in range(3):
            await circuit_breaker.record_failure(ValueError("test error"))

        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        await circuit_breaker.can_execute()  # Transition to half-open

        # Record successes up to threshold
        for _ in range(2):
            await circuit_breaker.record_success()

        assert circuit_breaker.is_closed

    @pytest.mark.asyncio
    async def test_reopens_on_failure_in_half_open(self, circuit_breaker):
        """Circuit reopens on any failure in half-open state"""
        # Open the circuit
        for _ in range(3):
            await circuit_breaker.record_failure(ValueError("test error"))

        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        await circuit_breaker.can_execute()  # Transition to half-open

        # Record a failure
        await circuit_breaker.record_failure(ValueError("test error"))

        assert circuit_breaker.is_open


class TestCircuitBreakerExecution:
    """Test circuit breaker execution control"""

    @pytest.mark.asyncio
    async def test_allows_execution_when_closed(self, circuit_breaker):
        """Allows execution when circuit is closed"""
        can_execute = await circuit_breaker.can_execute()
        assert can_execute

    @pytest.mark.asyncio
    async def test_blocks_execution_when_open(self, circuit_breaker):
        """Blocks execution when circuit is open"""
        # Open the circuit
        for _ in range(3):
            await circuit_breaker.record_failure(ValueError("test error"))

        can_execute = await circuit_breaker.can_execute()
        assert not can_execute

    @pytest.mark.asyncio
    async def test_context_manager_success(self, circuit_breaker):
        """Context manager records success on normal exit"""
        async with circuit_breaker:
            pass  # Simulate successful operation

        stats = circuit_breaker.get_stats()
        assert stats["total_successes"] == 1

    @pytest.mark.asyncio
    async def test_context_manager_failure(self, circuit_breaker):
        """Context manager records failure on exception"""
        with pytest.raises(ValueError):
            async with circuit_breaker:
                raise ValueError("test error")

        stats = circuit_breaker.get_stats()
        assert stats["total_failures"] == 1

    @pytest.mark.asyncio
    async def test_context_manager_raises_when_open(self, circuit_breaker):
        """Context manager raises CircuitBreakerError when open"""
        # Open the circuit
        for _ in range(3):
            await circuit_breaker.record_failure(ValueError("test error"))

        with pytest.raises(CircuitBreakerError) as exc_info:
            async with circuit_breaker:
                pass

        assert "test_circuit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_decorator_success(self, circuit_breaker):
        """Decorator records success on successful function call"""

        @circuit_breaker
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

        stats = circuit_breaker.get_stats()
        assert stats["total_successes"] == 1

    @pytest.mark.asyncio
    async def test_decorator_failure(self, circuit_breaker):
        """Decorator records failure on exception"""

        @circuit_breaker
        async def test_func():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await test_func()

        stats = circuit_breaker.get_stats()
        assert stats["total_failures"] == 1

    @pytest.mark.asyncio
    async def test_decorator_raises_when_open(self, circuit_breaker):
        """Decorator raises CircuitBreakerError when open"""
        # Open the circuit
        for _ in range(3):
            await circuit_breaker.record_failure(ValueError("test error"))

        @circuit_breaker
        async def test_func():
            return "success"

        with pytest.raises(CircuitBreakerError):
            await test_func()


class TestCircuitBreakerStats:
    """Test circuit breaker statistics"""

    @pytest.mark.asyncio
    async def test_get_stats(self, circuit_breaker):
        """Get stats returns correct values"""
        await circuit_breaker.record_success()
        await circuit_breaker.record_failure(ValueError("test error"))

        stats = circuit_breaker.get_stats()

        assert stats["name"] == "test_circuit"
        assert stats["state"] == "closed"
        assert stats["total_successes"] == 1
        assert stats["total_failures"] == 1
        assert "config" in stats

    @pytest.mark.asyncio
    async def test_reset_clears_state(self, circuit_breaker):
        """Reset clears all state"""
        # Record some activity
        await circuit_breaker.record_success()
        await circuit_breaker.record_failure(ValueError("test error"))

        # Reset
        await circuit_breaker.reset()

        stats = circuit_breaker.get_stats()
        assert stats["state"] == "closed"
        assert stats["total_successes"] == 0
        assert stats["total_failures"] == 0


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry"""

    @pytest.mark.asyncio
    async def test_get_or_create_new(self):
        """Creates new circuit breaker if not exists"""
        registry = CircuitBreakerRegistry()
        breaker = await registry.get_or_create("new_circuit")

        assert breaker is not None
        assert breaker.name == "new_circuit"

    @pytest.mark.asyncio
    async def test_get_or_create_existing(self):
        """Returns existing circuit breaker"""
        registry = CircuitBreakerRegistry()
        breaker1 = await registry.get_or_create("test_circuit")
        breaker2 = await registry.get_or_create("test_circuit")

        assert breaker1 is breaker2

    @pytest.mark.asyncio
    async def test_get_existing(self):
        """Get returns existing circuit breaker"""
        registry = CircuitBreakerRegistry()
        await registry.get_or_create("test_circuit")
        breaker = registry.get("test_circuit")

        assert breaker is not None
        assert breaker.name == "test_circuit"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        """Get returns None for nonexistent circuit"""
        registry = CircuitBreakerRegistry()
        breaker = registry.get("nonexistent")

        assert breaker is None

    @pytest.mark.asyncio
    async def test_reset_all(self):
        """Reset all resets all circuits"""
        registry = CircuitBreakerRegistry()
        breaker1 = await registry.get_or_create("circuit1")
        breaker2 = await registry.get_or_create("circuit2")

        # Record some activity
        await breaker1.record_failure(ValueError("test"))
        await breaker2.record_failure(ValueError("test"))

        # Reset all
        await registry.reset_all()

        assert breaker1.stats.total_failures == 0
        assert breaker2.stats.total_failures == 0

    @pytest.mark.asyncio
    async def test_get_all_stats(self):
        """Get all stats returns stats for all circuits"""
        registry = CircuitBreakerRegistry()
        await registry.get_or_create("circuit1")
        await registry.get_or_create("circuit2")

        all_stats = registry.get_all_stats()

        assert "circuit1" in all_stats
        assert "circuit2" in all_stats

    @pytest.mark.asyncio
    async def test_list_circuits(self):
        """List circuits returns all circuit states"""
        registry = CircuitBreakerRegistry()
        await registry.get_or_create("circuit1")
        await registry.get_or_create("circuit2")

        circuits = registry.list_circuits()

        assert len(circuits) == 2
        assert all(state == CircuitState.CLOSED for state in circuits.values())


class TestGlobalRegistry:
    """Test global registry functions"""

    @pytest.mark.asyncio
    async def test_get_circuit_registry(self):
        """Get circuit registry returns singleton"""
        registry1 = get_circuit_registry()
        registry2 = get_circuit_registry()

        assert registry1 is registry2

    @pytest.mark.asyncio
    async def test_get_circuit_breaker(self):
        """Get circuit breaker creates or returns circuit"""
        breaker = await get_circuit_breaker("global_test_circuit")

        assert breaker is not None
        assert breaker.name == "global_test_circuit"
