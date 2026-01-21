"""Task result reporter for worker agent

This module provides a dedicated ResultReporter class for reporting
task execution results to the backend with retry logic and error handling.
"""

import asyncio
from typing import Any, Dict, Optional
from uuid import UUID

import httpx
import structlog

from exceptions import ResultSubmissionError

logger = structlog.get_logger(__name__)


class ResultReporter:
    """Report task execution results to backend with retry logic

    This class provides a dedicated mechanism for reporting task results
    to the backend API with automatic retries and exponential backoff
    for transient failures.

    Attributes:
        backend_url: Base URL of the backend API
        api_key: Worker API key for authentication
        client: Async HTTP client instance
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff (seconds)
        max_delay: Maximum delay between retries (seconds)

    Example:
        reporter = ResultReporter(
            backend_url="http://127.0.0.1:8000",
            api_key="worker-api-key-123"
        )

        success = await reporter.report_result(
            worker_id="worker-uuid",
            task_id="task-uuid",
            status="completed",
            result={"output": "Task completed successfully"},
            execution_time_ms=1500
        )

        await reporter.close()
    """

    def __init__(
        self,
        backend_url: str,
        api_key: str,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        timeout: float = 30.0
    ):
        """Initialize ResultReporter

        Args:
            backend_url: Base URL of the backend API
            api_key: Worker API key for X-Worker-API-Key header
            max_retries: Maximum retry attempts (default: 3)
            base_delay: Base delay for exponential backoff in seconds (default: 1.0)
            max_delay: Maximum delay between retries in seconds (default: 30.0)
            timeout: HTTP request timeout in seconds (default: 30.0)
        """
        self.backend_url = backend_url.rstrip("/")
        self.api_key = api_key
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

        # Initialize async HTTP client with authentication header
        self.client = httpx.AsyncClient(
            base_url=self.backend_url,
            headers={
                "X-Worker-API-Key": api_key,
                "Content-Type": "application/json",
                "User-Agent": "GarageSwarm-Worker/1.0"
            },
            timeout=timeout
        )

        logger.info(
            "ResultReporter initialized",
            backend_url=self.backend_url,
            max_retries=max_retries
        )

    async def report_result(
        self,
        worker_id: str,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        execution_time_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Report task execution result to backend with retry logic

        This method reports the result of a task execution to the backend.
        It automatically retries on transient failures with exponential backoff.

        Args:
            worker_id: UUID of the worker (as string)
            task_id: UUID of the task/subtask (as string)
            status: Task status ("completed", "failed", "cancelled")
            result: Optional result data dictionary
            error: Optional error message if task failed
            execution_time_ms: Execution time in milliseconds
            metadata: Optional additional metadata

        Returns:
            True if result was reported successfully, False otherwise

        Raises:
            ResultSubmissionError: If all retry attempts fail
        """
        # Determine success based on status
        success = status == "completed"

        # Build request payload based on success/failure
        if success:
            endpoint = f"/api/v1/workers/{worker_id}/task-complete"
            payload = {
                "task_id": task_id,
                "result": {
                    "output": result.get("output") if result else None,
                    "metadata": metadata or (result.get("metadata", {}) if result else {}),
                    "execution_time": execution_time_ms / 1000.0  # Convert to seconds
                }
            }
        else:
            endpoint = f"/api/v1/workers/{worker_id}/task-failed"
            payload = {
                "task_id": task_id,
                "error": error or (result.get("error") if result else "Unknown error")
            }

        logger.info(
            "Reporting task result",
            worker_id=worker_id,
            task_id=task_id,
            status=status,
            success=success
        )

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.post(endpoint, json=payload)
                response.raise_for_status()

                logger.info(
                    "Task result reported successfully",
                    worker_id=worker_id,
                    task_id=task_id,
                    status=status,
                    attempts=attempt + 1
                )

                return True

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(
                    "Result report timeout",
                    worker_id=worker_id,
                    task_id=task_id,
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(e)
                )

            except httpx.HTTPStatusError as e:
                last_exception = e
                status_code = e.response.status_code

                # Don't retry on client errors (4xx) except for rate limiting (429)
                if 400 <= status_code < 500 and status_code != 429:
                    logger.error(
                        "Result report client error (not retrying)",
                        worker_id=worker_id,
                        task_id=task_id,
                        status_code=status_code,
                        error=str(e)
                    )
                    raise ResultSubmissionError(
                        f"Failed to report task result: HTTP {status_code}",
                        details={
                            "worker_id": worker_id,
                            "task_id": task_id,
                            "status_code": status_code,
                            "response": e.response.text[:500] if e.response.text else None
                        }
                    )

                logger.warning(
                    "Result report HTTP error",
                    worker_id=worker_id,
                    task_id=task_id,
                    status_code=status_code,
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )

            except httpx.RequestError as e:
                last_exception = e
                logger.warning(
                    "Result report network error",
                    worker_id=worker_id,
                    task_id=task_id,
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(e)
                )

            except Exception as e:
                last_exception = e
                logger.error(
                    "Unexpected error reporting result",
                    worker_id=worker_id,
                    task_id=task_id,
                    attempt=attempt + 1,
                    error=str(e),
                    error_type=type(e).__name__
                )

            # Check if we should retry
            if attempt < self.max_retries:
                # Calculate delay with exponential backoff
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)

                # Add jitter (random value between 0.5 and 1.0 of delay)
                import random
                delay = delay * (0.5 + random.random() * 0.5)

                logger.info(
                    "Retrying result report",
                    worker_id=worker_id,
                    task_id=task_id,
                    attempt=attempt + 1,
                    next_attempt=attempt + 2,
                    delay=round(delay, 2)
                )

                await asyncio.sleep(delay)

        # All retries exhausted
        logger.error(
            "Failed to report task result after all retries",
            worker_id=worker_id,
            task_id=task_id,
            attempts=self.max_retries + 1,
            last_error=str(last_exception) if last_exception else None
        )

        raise ResultSubmissionError(
            f"Failed to report task result after {self.max_retries + 1} attempts",
            details={
                "worker_id": worker_id,
                "task_id": task_id,
                "last_error": str(last_exception) if last_exception else None
            }
        )

    async def report_progress(
        self,
        worker_id: str,
        task_id: str,
        progress: int,
        message: Optional[str] = None
    ) -> bool:
        """Report task progress to backend (non-critical, no retries)

        This method reports intermediate progress updates for long-running tasks.
        Unlike report_result, this is non-critical and doesn't use retries.

        Args:
            worker_id: UUID of the worker (as string)
            task_id: UUID of the task/subtask (as string)
            progress: Progress percentage (0-100)
            message: Optional progress message

        Returns:
            True if progress was reported, False on any error
        """
        try:
            endpoint = f"/api/v1/workers/{worker_id}/tasks/{task_id}/progress"
            payload = {
                "progress": min(max(progress, 0), 100),  # Clamp to 0-100
                "message": message
            }

            response = await self.client.post(
                endpoint,
                json=payload,
                timeout=5.0  # Short timeout for progress updates
            )
            response.raise_for_status()

            logger.debug(
                "Task progress reported",
                worker_id=worker_id,
                task_id=task_id,
                progress=progress
            )

            return True

        except Exception as e:
            # Progress reporting is non-critical, just log and continue
            logger.debug(
                "Failed to report task progress",
                worker_id=worker_id,
                task_id=task_id,
                progress=progress,
                error=str(e)
            )
            return False

    async def report_batch_results(
        self,
        worker_id: str,
        results: list[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """Report multiple task results in batch

        This method reports multiple task results, useful when connection
        was lost and results were queued locally.

        Args:
            worker_id: UUID of the worker (as string)
            results: List of result dictionaries, each containing:
                - task_id: Task UUID
                - status: Task status
                - result: Result data (optional)
                - error: Error message (optional)
                - execution_time_ms: Execution time (optional)

        Returns:
            Dictionary mapping task_id to success status
        """
        report_status: Dict[str, bool] = {}

        for task_result in results:
            task_id = task_result.get("task_id")
            if not task_id:
                continue

            try:
                success = await self.report_result(
                    worker_id=worker_id,
                    task_id=task_id,
                    status=task_result.get("status", "failed"),
                    result=task_result.get("result"),
                    error=task_result.get("error"),
                    execution_time_ms=task_result.get("execution_time_ms", 0)
                )
                report_status[task_id] = success

            except ResultSubmissionError:
                report_status[task_id] = False
                logger.error(
                    "Failed to report batch result",
                    worker_id=worker_id,
                    task_id=task_id
                )

        logger.info(
            "Batch result reporting complete",
            worker_id=worker_id,
            total=len(results),
            successful=sum(1 for s in report_status.values() if s),
            failed=sum(1 for s in report_status.values() if not s)
        )

        return report_status

    async def close(self):
        """Close the HTTP client and release resources

        This method should be called when the ResultReporter is no longer needed
        to properly close the underlying HTTP connection pool.
        """
        if self.client:
            await self.client.aclose()
            logger.info("ResultReporter closed")

    async def __aenter__(self) -> "ResultReporter":
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close client"""
        await self.close()
        return False
