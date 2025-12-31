"""
Backpressure Middleware

Implements connection pool backpressure to protect the system from overload.
When connection pools are saturated, requests are rejected with HTTP 503
to prevent cascading failures.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog

from src.services.pool_monitor import get_pool_monitor

logger = structlog.get_logger(__name__)


class BackpressureMiddleware(BaseHTTPMiddleware):
    """
    Middleware that implements backpressure based on connection pool utilization.

    When pools are saturated (above threshold), new requests are rejected with
    HTTP 503 Service Unavailable to allow the system to recover.

    Features:
    - Automatic request shedding when pools are overloaded
    - Configurable excluded paths (health checks, metrics)
    - Retry-After header for client-side retry logic
    - Structured logging for monitoring
    """

    def __init__(
        self,
        app: ASGIApp,
        excluded_paths: list[str] | None = None,
        retry_after_seconds: int = 5
    ):
        """
        Initialize backpressure middleware.

        Args:
            app: ASGI application
            excluded_paths: Paths to exclude from backpressure (e.g., /health)
            retry_after_seconds: Value for Retry-After header
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/api/v1/health",
            "/health",
            "/metrics",
            "/ready",
            "/live"
        ]
        self.retry_after_seconds = retry_after_seconds

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request with backpressure check.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response from handler or 503 if under backpressure
        """
        # Skip backpressure check for excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)

        # Get pool monitor
        pool_monitor = get_pool_monitor()

        if pool_monitor:
            # Check if we should allow this request
            should_allow, reason = await pool_monitor.should_allow_request("database")

            if not should_allow:
                logger.warning(
                    "Request rejected due to backpressure",
                    path=path,
                    method=request.method,
                    client=request.client.host if request.client else None,
                    reason=reason
                )

                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "Service Temporarily Unavailable",
                        "message": reason,
                        "retry_after": self.retry_after_seconds
                    },
                    headers={
                        "Retry-After": str(self.retry_after_seconds),
                        "X-Backpressure": "active"
                    }
                )

        # Proceed with request
        return await call_next(request)
