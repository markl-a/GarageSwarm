"""
Global Error Handler Middleware

This module provides centralized exception handling for the FastAPI application,
ensuring consistent error responses and proper logging for all exceptions.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

from src.exceptions import AppException
from src.config import settings


logger = structlog.get_logger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle custom application exceptions

    Converts AppException instances to standardized JSON responses
    with appropriate status codes and error details.

    Args:
        request: The incoming request
        exc: The AppException instance

    Returns:
        JSONResponse with error details
    """
    # Log the error with context
    logger.error(
        "Application exception",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        message=exc.message,
        details=exc.details,
        exc_info=exc.status_code >= 500  # Only include stack trace for server errors
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle standard HTTP exceptions

    Converts Starlette HTTPException to standardized JSON responses.

    Args:
        request: The incoming request
        exc: The HTTPException instance

    Returns:
        JSONResponse with error details
    """
    logger.warning(
        "HTTP exception",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "details": {},
            "path": request.url.path
        }
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
    # Extract validation errors
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        "Validation error",
        path=request.url.path,
        method=request.method,
        errors=validation_errors
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Request validation failed",
            "details": {
                "validation_errors": validation_errors
            },
            "path": request.url.path
        }
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
    # Log with full details
    logger.error(
        "Unhandled exception",
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

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "Internal server error",
            "details": error_detail,
            "path": request.url.path
        }
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
