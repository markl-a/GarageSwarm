"""
Prometheus Metrics Middleware

Collects application metrics for monitoring and observability:
- HTTP request metrics (count, latency, errors)
- Active workers gauge
- Tasks by status gauge
- Error rates
"""

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, Info
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog

from src.config import settings


logger = structlog.get_logger(__name__)


# Application info
app_info = Info("app", "Application information")
app_info.info({
    "name": settings.APP_NAME,
    "version": settings.APP_VERSION,
    "environment": settings.ENVIRONMENT,
})


# HTTP Request Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests by method, endpoint, and status",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency by method and endpoint",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
)

http_errors_total = Counter(
    "http_errors_total",
    "Total HTTP errors by method, endpoint, and status code",
    ["method", "endpoint", "status_code"],
)


# Worker Metrics
workers_active = Gauge(
    "workers_active",
    "Number of active workers by status",
    ["status"],
)

workers_total = Gauge(
    "workers_total",
    "Total number of registered workers",
)

workers_cpu_percent = Gauge(
    "workers_cpu_percent",
    "Worker CPU usage percentage",
    ["worker_id", "machine_name"],
)

workers_memory_percent = Gauge(
    "workers_memory_percent",
    "Worker memory usage percentage",
    ["worker_id", "machine_name"],
)

workers_disk_percent = Gauge(
    "workers_disk_percent",
    "Worker disk usage percentage",
    ["worker_id", "machine_name"],
)


# Task Metrics
tasks_total = Gauge(
    "tasks_total",
    "Total number of tasks by status",
    ["status"],
)

tasks_created_total = Counter(
    "tasks_created_total",
    "Total number of tasks created",
)

tasks_completed_total = Counter(
    "tasks_completed_total",
    "Total number of tasks completed",
)

tasks_failed_total = Counter(
    "tasks_failed_total",
    "Total number of tasks failed",
)

task_duration_seconds = Histogram(
    "task_duration_seconds",
    "Task execution duration in seconds",
    ["status"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
)


# Subtask Metrics
subtasks_total = Gauge(
    "subtasks_total",
    "Total number of subtasks by status",
    ["status"],
)

subtasks_by_tool = Gauge(
    "subtasks_by_tool",
    "Number of subtasks by AI tool",
    ["tool"],
)

subtask_duration_seconds = Histogram(
    "subtask_duration_seconds",
    "Subtask execution duration in seconds",
    ["tool", "status"],
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600),
)


# Checkpoint Metrics
checkpoints_total = Counter(
    "checkpoints_total",
    "Total number of checkpoints created",
    ["trigger_reason"],
)

checkpoint_approval_duration_seconds = Histogram(
    "checkpoint_approval_duration_seconds",
    "Time taken for checkpoint approval",
    buckets=(1, 5, 10, 30, 60, 300, 600, 1800, 3600),
)


# Evaluation Metrics
evaluations_total = Counter(
    "evaluations_total",
    "Total number of evaluations performed",
    ["evaluator_type"],
)

evaluation_score = Histogram(
    "evaluation_score",
    "Evaluation scores by evaluator type",
    ["evaluator_type"],
    buckets=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
)

evaluation_duration_seconds = Histogram(
    "evaluation_duration_seconds",
    "Evaluation execution duration",
    ["evaluator_type"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60),
)


# WebSocket Metrics
websocket_connections_active = Gauge(
    "websocket_connections_active",
    "Number of active WebSocket connections",
)

websocket_messages_sent_total = Counter(
    "websocket_messages_sent_total",
    "Total number of WebSocket messages sent",
    ["message_type"],
)

websocket_messages_received_total = Counter(
    "websocket_messages_received_total",
    "Total number of WebSocket messages received",
    ["message_type"],
)


# Database Metrics
database_connections_active = Gauge(
    "database_connections_active",
    "Number of active database connections",
)

database_query_duration_seconds = Histogram(
    "database_query_duration_seconds",
    "Database query duration",
    ["query_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)


# Redis Metrics
redis_operations_total = Counter(
    "redis_operations_total",
    "Total number of Redis operations",
    ["operation"],
)

redis_operation_duration_seconds = Histogram(
    "redis_operation_duration_seconds",
    "Redis operation duration",
    ["operation"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect Prometheus metrics for HTTP requests

    Tracks:
    - Request count by endpoint, method, and status code
    - Request latency histogram
    - Requests in progress gauge
    - Error rate counter
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        logger.info("PrometheusMiddleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and collect metrics

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            Response from the application
        """
        # Skip metrics collection for the metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        # Extract endpoint pattern (without query params)
        endpoint = self._get_endpoint_pattern(request)
        method = request.method

        # Track requests in progress
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        # Start timing
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code

            # Record metrics
            duration = time.time() - start_time

            # Request count
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
            ).inc()

            # Request duration
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            # Track errors (4xx and 5xx)
            if status_code >= 400:
                http_errors_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                ).inc()

            return response

        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time

            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=500,
            ).inc()

            http_errors_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=500,
            ).inc()

            logger.error(
                "Request processing error",
                method=method,
                endpoint=endpoint,
                duration=duration,
                error=str(e),
            )

            raise

        finally:
            # Always decrement in-progress counter
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()

    def _get_endpoint_pattern(self, request: Request) -> str:
        """
        Extract the endpoint pattern from the request

        Converts paths like /api/v1/tasks/123 to /api/v1/tasks/{task_id}
        to avoid high cardinality in metrics.

        Args:
            request: The incoming request

        Returns:
            Normalized endpoint pattern
        """
        # Try to get the matched route pattern
        if request.scope.get("route"):
            return request.scope["route"].path

        # Fallback to raw path
        return request.url.path


def update_worker_metrics(workers_data: list[dict]) -> None:
    """
    Update worker-related metrics

    Args:
        workers_data: List of worker data dictionaries with keys:
            - worker_id: UUID
            - machine_name: str
            - status: str
            - cpu_percent: float
            - memory_percent: float
            - disk_percent: float
    """
    # Count workers by status
    status_counts = {}
    total_workers = len(workers_data)

    for worker in workers_data:
        status = worker.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

        # Update resource metrics
        worker_id = str(worker.get("worker_id", "unknown"))
        machine_name = worker.get("machine_name", "unknown")

        if worker.get("cpu_percent") is not None:
            workers_cpu_percent.labels(
                worker_id=worker_id,
                machine_name=machine_name,
            ).set(worker["cpu_percent"])

        if worker.get("memory_percent") is not None:
            workers_memory_percent.labels(
                worker_id=worker_id,
                machine_name=machine_name,
            ).set(worker["memory_percent"])

        if worker.get("disk_percent") is not None:
            workers_disk_percent.labels(
                worker_id=worker_id,
                machine_name=machine_name,
            ).set(worker["disk_percent"])

    # Update status gauges
    for status, count in status_counts.items():
        workers_active.labels(status=status).set(count)

    # Update total workers
    workers_total.set(total_workers)


def update_task_metrics(tasks_data: list[dict]) -> None:
    """
    Update task-related metrics

    Args:
        tasks_data: List of task data dictionaries with keys:
            - status: str
    """
    # Count tasks by status
    status_counts = {}

    for task in tasks_data:
        status = task.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    # Update status gauges
    for status, count in status_counts.items():
        tasks_total.labels(status=status).set(count)


def update_subtask_metrics(subtasks_data: list[dict]) -> None:
    """
    Update subtask-related metrics

    Args:
        subtasks_data: List of subtask data dictionaries with keys:
            - status: str
            - assigned_tool: str
    """
    # Count subtasks by status
    status_counts = {}
    tool_counts = {}

    for subtask in subtasks_data:
        status = subtask.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

        tool = subtask.get("assigned_tool")
        if tool:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

    # Update status gauges
    for status, count in status_counts.items():
        subtasks_total.labels(status=status).set(count)

    # Update tool gauges
    for tool, count in tool_counts.items():
        subtasks_by_tool.labels(tool=tool).set(count)


def record_task_created() -> None:
    """Record a new task creation"""
    tasks_created_total.inc()


def record_task_completed(duration_seconds: float) -> None:
    """
    Record a task completion

    Args:
        duration_seconds: Task execution duration in seconds
    """
    tasks_completed_total.inc()
    task_duration_seconds.labels(status="completed").observe(duration_seconds)


def record_task_failed(duration_seconds: float) -> None:
    """
    Record a task failure

    Args:
        duration_seconds: Task execution duration in seconds
    """
    tasks_failed_total.inc()
    task_duration_seconds.labels(status="failed").observe(duration_seconds)


def record_subtask_completed(tool: str, duration_seconds: float) -> None:
    """
    Record a subtask completion

    Args:
        tool: The AI tool used
        duration_seconds: Subtask execution duration in seconds
    """
    subtask_duration_seconds.labels(tool=tool, status="completed").observe(duration_seconds)


def record_subtask_failed(tool: str, duration_seconds: float) -> None:
    """
    Record a subtask failure

    Args:
        tool: The AI tool used
        duration_seconds: Subtask execution duration in seconds
    """
    subtask_duration_seconds.labels(tool=tool, status="failed").observe(duration_seconds)


def record_checkpoint_created(trigger_reason: str) -> None:
    """
    Record a checkpoint creation

    Args:
        trigger_reason: Reason for checkpoint (e.g., 'low_score', 'error', 'manual')
    """
    checkpoints_total.labels(trigger_reason=trigger_reason).inc()


def record_checkpoint_approval_duration(duration_seconds: float) -> None:
    """
    Record checkpoint approval duration

    Args:
        duration_seconds: Time taken for checkpoint approval
    """
    checkpoint_approval_duration_seconds.observe(duration_seconds)


def record_evaluation(evaluator_type: str, score: float, duration_seconds: float) -> None:
    """
    Record an evaluation

    Args:
        evaluator_type: Type of evaluator (e.g., 'completeness', 'code_quality')
        score: Evaluation score (0-10)
        duration_seconds: Evaluation execution duration
    """
    evaluations_total.labels(evaluator_type=evaluator_type).inc()
    evaluation_score.labels(evaluator_type=evaluator_type).observe(score)
    evaluation_duration_seconds.labels(evaluator_type=evaluator_type).observe(duration_seconds)


def record_websocket_connection(connected: bool) -> None:
    """
    Record WebSocket connection state change

    Args:
        connected: True if connection established, False if disconnected
    """
    if connected:
        websocket_connections_active.inc()
    else:
        websocket_connections_active.dec()


def record_websocket_message(message_type: str, sent: bool = True) -> None:
    """
    Record WebSocket message

    Args:
        message_type: Type of message (e.g., 'task_update', 'heartbeat')
        sent: True if message was sent, False if received
    """
    if sent:
        websocket_messages_sent_total.labels(message_type=message_type).inc()
    else:
        websocket_messages_received_total.labels(message_type=message_type).inc()


def record_database_query(query_type: str, duration_seconds: float) -> None:
    """
    Record database query metrics

    Args:
        query_type: Type of query (e.g., 'select', 'insert', 'update')
        duration_seconds: Query execution duration
    """
    database_query_duration_seconds.labels(query_type=query_type).observe(duration_seconds)


def record_redis_operation(operation: str, duration_seconds: float) -> None:
    """
    Record Redis operation metrics

    Args:
        operation: Operation type (e.g., 'get', 'set', 'publish')
        duration_seconds: Operation duration
    """
    redis_operations_total.labels(operation=operation).inc()
    redis_operation_duration_seconds.labels(operation=operation).observe(duration_seconds)
