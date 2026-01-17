"""
Request ID Middleware

Adds unique request IDs for distributed tracing and log correlation.
Each request gets a unique ID that propagates through all logs and responses.
"""

import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
import structlog

# Context variable for request ID - accessible throughout the request lifecycle
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# Header names
REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"

logger = structlog.get_logger()


def get_request_id() -> Optional[str]:
    """
    Get the current request ID from context.

    Can be called from anywhere in the request lifecycle to get the
    current request's unique identifier for logging or tracing.

    Returns:
        Request ID string, or None if not in a request context
    """
    return request_id_ctx.get()


def generate_request_id() -> str:
    """Generate a new unique request ID"""
    return str(uuid.uuid4())


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a unique ID to each request.

    Features:
    - Generates UUID for each request if not provided
    - Accepts existing X-Request-ID header (for distributed tracing)
    - Adds X-Request-ID to response headers
    - Stores ID in context variable for access throughout request
    - Adds request_id to all structlog entries automatically

    Usage:
        app.add_middleware(RequestIDMiddleware)

        # Access in any handler or service:
        from src.middleware.request_id import get_request_id
        request_id = get_request_id()
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Check for existing request ID (from upstream service or client)
        request_id = request.headers.get(REQUEST_ID_HEADER)
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)

        # Generate new ID if not provided
        if not request_id:
            request_id = generate_request_id()

        # Use correlation ID if provided (for tracing across services)
        if correlation_id and not request_id:
            request_id = correlation_id

        # Store in context variable
        token = request_id_ctx.set(request_id)

        # Add to request state for easy access in handlers
        request.state.request_id = request_id

        try:
            # Bind request_id to all logs in this context
            with structlog.contextvars.bound_contextvars(request_id=request_id):
                # Log request start
                logger.info(
                    "Request started",
                    method=request.method,
                    path=request.url.path,
                    client_ip=request.client.host if request.client else None
                )

                # Process request
                response = await call_next(request)

                # Log request completion
                logger.info(
                    "Request completed",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code
                )

                # Add request ID to response headers
                response.headers[REQUEST_ID_HEADER] = request_id

                return response

        except Exception as e:
            # Log exception with request context
            logger.exception(
                "Request failed with exception",
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
        finally:
            # Reset context variable
            request_id_ctx.reset(token)


class RequestContextProcessor:
    """
    Structlog processor that adds request context to all log entries.

    Add this to structlog configuration to automatically include
    request_id in all log messages.
    """

    def __call__(self, logger, method_name, event_dict):
        request_id = get_request_id()
        if request_id:
            event_dict["request_id"] = request_id
        return event_dict


def configure_structlog_with_request_id():
    """
    Configure structlog to include request ID in all log entries.

    Call this during application startup to enable request ID tracking
    in all logs.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            RequestContextProcessor(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
        cache_logger_on_first_use=True,
    )
