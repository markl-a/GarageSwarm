"""
Global Error Handler Middleware

This module provides centralized exception handling for the FastAPI application,
ensuring consistent error responses and proper logging for all exceptions.

Features:
- Request ID tracking in error responses
- Structured error codes for client-side handling
- Retry information for transient errors
- Consistent JSON error format
"""

from datetime import datetime
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

from src.exceptions import AppException, ErrorCode
from src.config import settings
from src.middleware.request_id import get_request_id


logger = structlog.get_logger(__name__)


def _build_error_response(
    status_code: int,
    error_code: str,
    message: str,
    path: str,
    details: dict = None,
    retryable: bool = False,
    retry_after: int = None
) -> dict:
    """Build standardized error response"""
    request_id = get_request_id()

    response = {
        "status": "error",
        "error_code": error_code,
        "message": message,
        "details": details or {},
        "path": path,
        "timestamp": datetime.utcnow().isoformat(),
        "retryable": retryable
    }

    if request_id:
        response["request_id"] = request_id

    if retry_after:
        response["retry_after"] = retry_after

    return response


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle custom application exceptions

    Converts AppException instances to standardized JSON responses
    with appropriate status codes, error codes, and retry information.

    Args:
        request: The incoming request
        exc: The AppException instance

    Returns:
        JSONResponse with error details
    """
    request_id = get_request_id()

    # Log the error with context
    logger.error(
        "Application exception",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        error_code=exc.error_code.value,
        message=exc.message,
        details=exc.details,
        retryable=exc.retryable,
        exc_info=exc.status_code >= 500  # Only include stack trace for server errors
    )

    response_content = _build_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code.value,
        message=exc.message,
        path=request.url.path,
        details=exc.details,
        retryable=exc.retryable,
        retry_after=exc.retry_after
    )

    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=exc.status_code,
        content=response_content,
        headers=headers if headers else None
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle standard HTTP exceptions

    Converts Starlette HTTPException to standardized JSON responses
    with appropriate error codes.

    Args:
        request: The incoming request
        exc: The HTTPException instance

    Returns:
        JSONResponse with error details
    """
    request_id = get_request_id()

    # Map HTTP status codes to error codes
    error_code_map = {
        400: ErrorCode.VALIDATION_FAILED.value,
        401: ErrorCode.AUTH_UNAUTHORIZED.value,
        403: ErrorCode.AUTH_FORBIDDEN.value,
        404: ErrorCode.RESOURCE_NOT_FOUND.value,
        409: ErrorCode.RESOURCE_CONFLICT.value,
        429: ErrorCode.RATE_LIMIT_EXCEEDED.value,
        500: ErrorCode.INTERNAL_ERROR.value,
        503: ErrorCode.SERVICE_UNAVAILABLE.value,
        504: ErrorCode.TIMEOUT_EXCEEDED.value,
    }
    error_code = error_code_map.get(exc.status_code, ErrorCode.UNKNOWN_ERROR.value)

    logger.warning(
        "HTTP exception",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        error_code=error_code,
        detail=exc.detail
    )

    response_content = _build_error_response(
        status_code=exc.status_code,
        error_code=error_code,
        message=str(exc.detail),
        path=request.url.path
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response_content
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation errors

    Converts Pydantic validation errors to standardized JSON responses
    with detailed field-level error information.

    Args:
        request: The incoming request
        exc: The RequestValidationError instance

    Returns:
        JSONResponse with validation error details
    """
    request_id = get_request_id()

    # Extract validation errors with improved formatting
    validation_errors = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        validation_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")  # Include actual input value for debugging
        })

    logger.warning(
        "Validation error",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        error_count=len(validation_errors),
        errors=validation_errors
    )

    response_content = _build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code=ErrorCode.VALIDATION_FAILED.value,
        message="Request validation failed",
        path=request.url.path,
        details={"validation_errors": validation_errors}
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_content
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unhandled exceptions

    Catches any exceptions not handled by other handlers and returns
    a generic error response. In production, hides internal error details.

    Args:
        request: The incoming request
        exc: The unhandled exception

    Returns:
        JSONResponse with generic error message
    """
    request_id = get_request_id()

    # Log with full details
    logger.error(
        "Unhandled exception",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        error=str(exc),
        exc_info=True  # Include full stack trace
    )

    # In production, hide internal error details
    if settings.DEBUG:
        error_detail = {
            "type": type(exc).__name__,
            "message": str(exc)
        }
    else:
        error_detail = {}

    response_content = _build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=ErrorCode.INTERNAL_ERROR.value,
        message="Internal server error" if not settings.DEBUG else str(exc),
        path=request.url.path,
        details=error_detail
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_content
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app

    This function should be called during app initialization to register
    all custom exception handlers.

    Args:
        app: FastAPI application instance

    Example:
        from src.middleware.error_handler import register_exception_handlers
        register_exception_handlers(app)
    """
    # Custom application exceptions
    app.add_exception_handler(AppException, app_exception_handler)

    # Standard HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Catch-all for unhandled exceptions
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Exception handlers registered")
