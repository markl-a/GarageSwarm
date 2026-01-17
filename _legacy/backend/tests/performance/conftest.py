"""
Performance Test Fixtures

Fixtures and utilities for performance testing including timing,
concurrent execution, and performance assertions.
"""

import time
import asyncio
from typing import Callable, List, Any, Dict
from dataclasses import dataclass
from statistics import mean, stdev, median

import pytest


@dataclass
class PerformanceMetrics:
    """Performance metrics for an operation"""
    operation: str
    duration_ms: float
    success: bool
    timestamp: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PerformanceReport:
    """Aggregated performance report"""
    operation: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    median_duration_ms: float
    std_deviation_ms: float
    p95_duration_ms: float
    p99_duration_ms: float

    def meets_requirement(self, max_duration_ms: float) -> bool:
        """Check if performance meets requirement"""
        return self.p95_duration_ms <= max_duration_ms

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "operation": self.operation,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "min_duration_ms": round(self.min_duration_ms, 2),
            "max_duration_ms": round(self.max_duration_ms, 2),
            "median_duration_ms": round(self.median_duration_ms, 2),
            "std_deviation_ms": round(self.std_deviation_ms, 2),
            "p95_duration_ms": round(self.p95_duration_ms, 2),
            "p99_duration_ms": round(self.p99_duration_ms, 2),
        }


class PerformanceTimer:
    """Context manager for timing operations"""

    def __init__(self, operation: str = "operation"):
        self.operation = operation
        self.start_time: float = 0
        self.end_time: float = 0
        self.duration_ms: float = 0
        self.success: bool = False

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = exc_type is None
        return False  # Don't suppress exceptions

    def get_metrics(self) -> PerformanceMetrics:
        """Get performance metrics"""
        return PerformanceMetrics(
            operation=self.operation,
            duration_ms=self.duration_ms,
            success=self.success,
            timestamp=self.start_time
        )


class PerformanceAnalyzer:
    """Analyze and report on performance metrics"""

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []

    def add_metric(self, metric: PerformanceMetrics):
        """Add a performance metric"""
        self.metrics.append(metric)

    def generate_report(self, operation: str = None) -> PerformanceReport:
        """Generate performance report"""
        # Filter metrics by operation if specified
        metrics = self.metrics if operation is None else [
            m for m in self.metrics if m.operation == operation
        ]

        if not metrics:
            raise ValueError(f"No metrics found for operation: {operation}")

        durations = [m.duration_ms for m in metrics]
        successful = [m for m in metrics if m.success]

        # Calculate percentiles
        sorted_durations = sorted(durations)
        p95_index = int(len(sorted_durations) * 0.95)
        p99_index = int(len(sorted_durations) * 0.99)

        return PerformanceReport(
            operation=operation or "all",
            total_runs=len(metrics),
            successful_runs=len(successful),
            failed_runs=len(metrics) - len(successful),
            avg_duration_ms=mean(durations),
            min_duration_ms=min(durations),
            max_duration_ms=max(durations),
            median_duration_ms=median(durations),
            std_deviation_ms=stdev(durations) if len(durations) > 1 else 0,
            p95_duration_ms=sorted_durations[p95_index] if sorted_durations else 0,
            p99_duration_ms=sorted_durations[p99_index] if sorted_durations else 0,
        )

    def clear(self):
        """Clear all metrics"""
        self.metrics.clear()


@pytest.fixture
def perf_timer():
    """Fixture for timing operations"""
    def _timer(operation: str = "operation"):
        return PerformanceTimer(operation)
    return _timer


@pytest.fixture
def perf_analyzer():
    """Fixture for analyzing performance metrics"""
    analyzer = PerformanceAnalyzer()
    yield analyzer
    analyzer.clear()


@pytest.fixture
def assert_performance():
    """Fixture for asserting performance requirements"""
    def _assert(duration_ms: float, max_ms: float, operation: str = "operation"):
        """Assert that operation meets performance requirement"""
        assert duration_ms <= max_ms, (
            f"{operation} took {duration_ms:.2f}ms, "
            f"exceeds requirement of {max_ms}ms"
        )
    return _assert


@pytest.fixture
def run_concurrent():
    """Fixture for running concurrent operations"""
    async def _run_concurrent(
        coro_func: Callable,
        args_list: List[tuple],
        max_concurrent: int = None
    ) -> List[Any]:
        """
        Run coroutines concurrently

        Args:
            coro_func: Async function to call
            args_list: List of argument tuples for each call
            max_concurrent: Maximum concurrent operations (None = unlimited)

        Returns:
            List of results
        """
        if max_concurrent:
            # Use semaphore to limit concurrency
            semaphore = asyncio.Semaphore(max_concurrent)

            async def limited_coro(args):
                async with semaphore:
                    return await coro_func(*args)

            tasks = [limited_coro(args) for args in args_list]
        else:
            # Unlimited concurrency
            tasks = [coro_func(*args) for args in args_list]

        return await asyncio.gather(*tasks, return_exceptions=True)

    return _run_concurrent


@pytest.fixture
def run_concurrent_timed(perf_analyzer):
    """Fixture for running and timing concurrent operations"""
    async def _run_concurrent_timed(
        coro_func: Callable,
        args_list: List[tuple],
        operation: str = "operation",
        max_concurrent: int = None
    ) -> tuple[List[Any], PerformanceReport]:
        """
        Run coroutines concurrently and collect timing metrics

        Returns:
            Tuple of (results, performance_report)
        """
        async def timed_coro(args, idx):
            """Wrap coroutine with timing"""
            with PerformanceTimer(f"{operation}_{idx}") as timer:
                result = await coro_func(*args)

            perf_analyzer.add_metric(timer.get_metrics())
            return result

        if max_concurrent:
            # Use semaphore to limit concurrency
            semaphore = asyncio.Semaphore(max_concurrent)

            async def limited_timed_coro(args, idx):
                async with semaphore:
                    return await timed_coro(args, idx)

            tasks = [limited_timed_coro(args, i) for i, args in enumerate(args_list)]
        else:
            tasks = [timed_coro(args, i) for i, args in enumerate(args_list)]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        report = perf_analyzer.generate_report()

        return results, report

    return _run_concurrent_timed


@pytest.fixture
def sample_worker_data_factory():
    """Factory for generating worker test data"""
    def _factory(index: int) -> dict:
        return {
            "machine_id": f"perf-test-machine-{index:03d}",
            "machine_name": f"Performance Test Machine {index}",
            "system_info": {
                "os": "Linux",
                "cpu_count": 8,
                "memory_total": 16000000000
            },
            "tools": ["claude_code", "gemini_cli"]
        }
    return _factory


@pytest.fixture
def sample_task_data_factory():
    """Factory for generating task test data"""
    def _factory(index: int) -> dict:
        return {
            "description": f"Performance test task {index}: Implement feature X with comprehensive testing",
            "task_type": "develop_feature",
            "requirements": {
                "complexity": "medium",
                "estimated_time": "30m"
            },
            "checkpoint_frequency": "medium",
            "privacy_level": "normal",
            "tool_preferences": ["claude_code"]
        }
    return _factory


# Performance thresholds as per NFR requirements
PERFORMANCE_THRESHOLDS = {
    "task_submission_ms": 2000,      # Task submission < 2s
    "websocket_latency_ms": 500,     # WebSocket latency < 500ms
    "worker_registration_ms": 5000,  # Worker registration < 5s
    "max_concurrent_workers": 10,     # Support 10 workers
    "max_concurrent_tasks": 20,       # Support 20 tasks
    "max_websocket_connections": 50,  # Support 50 WS connections
}


@pytest.fixture
def performance_thresholds():
    """Fixture providing performance thresholds"""
    return PERFORMANCE_THRESHOLDS.copy()
