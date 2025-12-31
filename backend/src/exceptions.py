"""
Custom Exception Classes

This module defines custom exceptions for the BMAD application,
providing clear, specific error types with standardized status codes
and detailed error information.
"""

from typing import Dict, Optional, Any


class AppException(Exception):
    """
    Base application exception

    All custom exceptions should inherit from this class to ensure
    consistent error handling across the application.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 500)
        details: Additional error details as a dictionary
    """
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    """
    Resource not found error

    Raised when a requested resource (task, worker, subtask, etc.) is not found.
    Returns HTTP 404.

    Example:
        raise NotFoundError("Task", "123e4567-e89b-12d3-a456-426614174000")
    """
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            f"{resource} with id {identifier} not found",
            status_code=404,
            details={"resource": resource, "identifier": identifier}
        )


class ValidationError(AppException):
    """
    Validation error

    Raised when input validation fails (invalid parameters, missing fields, etc.).
    Returns HTTP 400.

    Example:
        raise ValidationError(
            "Invalid task description",
            details={"field": "description", "error": "Too short"}
        )
    """
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, details=details)


class ConflictError(AppException):
    """
    Resource conflict error

    Raised when an operation conflicts with the current state
    (e.g., trying to cancel a completed task).
    Returns HTTP 409.

    Example:
        raise ConflictError("Cannot cancel a completed task")
    """
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=409, details=details)


class ServiceUnavailableError(AppException):
    """
    External service unavailable error

    Raised when an external service (Redis, database, AI service) is unavailable.
    Returns HTTP 503.

    Example:
        raise ServiceUnavailableError("Redis", details={"host": "localhost:6379"})
    """
    def __init__(self, service: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Service {service} is unavailable",
            status_code=503,
            details={**(details or {}), "service": service}
        )


class UnauthorizedError(AppException):
    """
    Unauthorized access error

    Raised when authentication is required or has failed.
    Returns HTTP 401.

    Example:
        raise UnauthorizedError("Invalid API key")
    """
    def __init__(self, message: str = "Unauthorized access", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, details=details)


class ForbiddenError(AppException):
    """
    Forbidden access error

    Raised when user doesn't have permission to access a resource.
    Returns HTTP 403.

    Example:
        raise ForbiddenError("Insufficient permissions to delete this task")
    """
    def __init__(self, message: str = "Access forbidden", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=403, details=details)


class TaskExecutionError(AppException):
    """
    Task execution error

    Raised when task execution fails (subtask failure, worker error, etc.).
    Returns HTTP 500.

    Example:
        raise TaskExecutionError(
            "Subtask execution failed",
            details={"subtask_id": "123", "error": "Worker timeout"}
        )
    """
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class DatabaseError(AppException):
    """
    Database operation error

    Raised when database operations fail (connection, query, transaction).
    Returns HTTP 500.

    Example:
        raise DatabaseError("Failed to save task", details={"operation": "INSERT"})
    """
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class RateLimitError(AppException):
    """
    Rate limit exceeded error

    Raised when rate limits are exceeded.
    Returns HTTP 429.

    Example:
        raise RateLimitError("Too many requests", details={"retry_after": 60})
    """
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=429, details=details)


class TimeoutError(AppException):
    """
    Operation timeout error

    Raised when an operation exceeds its timeout limit.
    Returns HTTP 504.

    Example:
        raise TimeoutError("Task execution timeout", details={"timeout": 300})
    """
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=504, details=details)
