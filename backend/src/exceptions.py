"""
Custom Exception Classes

This module defines custom exceptions for the BMAD application,
providing clear, specific error types with standardized status codes,
error codes for client-side handling, and detailed error information.
"""

from typing import Dict, Optional, Any
from enum import Enum


class ErrorCode(str, Enum):
    """
    Standardized error codes for client-side handling.

    Format: CATEGORY_SPECIFIC_ERROR
    Categories: AUTH, RESOURCE, VALIDATION, SERVICE, TASK, RATE, TIMEOUT, DATA
    """
    # Authentication errors (1xxx)
    AUTH_UNAUTHORIZED = "AUTH_001"
    AUTH_FORBIDDEN = "AUTH_002"
    AUTH_TOKEN_EXPIRED = "AUTH_003"
    AUTH_TOKEN_INVALID = "AUTH_004"

    # Resource errors (2xxx)
    RESOURCE_NOT_FOUND = "RESOURCE_001"
    RESOURCE_CONFLICT = "RESOURCE_002"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_003"
    RESOURCE_VERSION_CONFLICT = "RESOURCE_004"

    # Data integrity errors (25xx)
    DATA_CYCLE_DETECTED = "DATA_025"

    # Validation errors (3xxx)
    VALIDATION_FAILED = "VALIDATION_001"
    VALIDATION_FIELD_REQUIRED = "VALIDATION_002"
    VALIDATION_FIELD_INVALID = "VALIDATION_003"

    # Service errors (4xxx)
    SERVICE_UNAVAILABLE = "SERVICE_001"
    SERVICE_REDIS_ERROR = "SERVICE_002"
    SERVICE_DATABASE_ERROR = "SERVICE_003"
    SERVICE_EXTERNAL_ERROR = "SERVICE_004"

    # Task execution errors (5xxx)
    TASK_EXECUTION_FAILED = "TASK_001"
    TASK_WORKER_ERROR = "TASK_002"
    TASK_TIMEOUT = "TASK_003"
    TASK_CANCELLED = "TASK_004"
    TASK_INVALID_STATE = "TASK_005"

    # Rate limiting errors (6xxx)
    RATE_LIMIT_EXCEEDED = "RATE_001"

    # Timeout errors (7xxx)
    TIMEOUT_EXCEEDED = "TIMEOUT_001"

    # Internal errors (9xxx)
    INTERNAL_ERROR = "INTERNAL_001"
    UNKNOWN_ERROR = "INTERNAL_999"


class AppException(Exception):
    """
    Base application exception

    All custom exceptions should inherit from this class to ensure
    consistent error handling across the application.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code (default: 500)
        error_code: Standardized error code for client handling
        details: Additional error details as a dictionary
        retryable: Whether the operation can be retried
        retry_after: Suggested retry delay in seconds (if retryable)
    """
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = False,
        retry_after: Optional[int] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        self.retryable = retryable
        self.retry_after = retry_after
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response"""
        result = {
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable
        }
        if self.retry_after:
            result["retry_after"] = self.retry_after
        return result


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
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
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
        super().__init__(
            message,
            status_code=400,
            error_code=ErrorCode.VALIDATION_FAILED,
            details=details
        )


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
        super().__init__(
            message,
            status_code=409,
            error_code=ErrorCode.RESOURCE_CONFLICT,
            details=details
        )


class ServiceUnavailableError(AppException):
    """
    External service unavailable error

    Raised when an external service (Redis, database, AI service) is unavailable.
    Returns HTTP 503. This is a retryable error.

    Example:
        raise ServiceUnavailableError("Redis", details={"host": "localhost:6379"})
    """
    def __init__(
        self,
        service: str,
        details: Optional[Dict[str, Any]] = None,
        retry_after: int = 5
    ):
        error_code = ErrorCode.SERVICE_UNAVAILABLE
        if service.lower() == "redis":
            error_code = ErrorCode.SERVICE_REDIS_ERROR
        elif service.lower() in ["database", "postgresql", "db"]:
            error_code = ErrorCode.SERVICE_DATABASE_ERROR

        super().__init__(
            f"Service {service} is unavailable",
            status_code=503,
            error_code=error_code,
            details={**(details or {}), "service": service},
            retryable=True,
            retry_after=retry_after
        )


class UnauthorizedError(AppException):
    """
    Unauthorized access error

    Raised when authentication is required or has failed.
    Returns HTTP 401.

    Example:
        raise UnauthorizedError("Invalid API key")
    """
    def __init__(
        self,
        message: str = "Unauthorized access",
        details: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.AUTH_UNAUTHORIZED
    ):
        super().__init__(
            message,
            status_code=401,
            error_code=error_code,
            details=details
        )


class ForbiddenError(AppException):
    """
    Forbidden access error

    Raised when user doesn't have permission to access a resource.
    Returns HTTP 403.

    Example:
        raise ForbiddenError("Insufficient permissions to delete this task")
    """
    def __init__(self, message: str = "Access forbidden", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            status_code=403,
            error_code=ErrorCode.AUTH_FORBIDDEN,
            details=details
        )


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
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: ErrorCode = ErrorCode.TASK_EXECUTION_FAILED,
        retryable: bool = False
    ):
        super().__init__(
            message,
            status_code=500,
            error_code=error_code,
            details=details,
            retryable=retryable
        )


class DatabaseError(AppException):
    """
    Database operation error

    Raised when database operations fail (connection, query, transaction).
    Returns HTTP 500. This is typically a retryable error.

    Example:
        raise DatabaseError("Failed to save task", details={"operation": "INSERT"})
    """
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = True,
        retry_after: int = 3
    ):
        super().__init__(
            message,
            status_code=500,
            error_code=ErrorCode.SERVICE_DATABASE_ERROR,
            details=details,
            retryable=retryable,
            retry_after=retry_after
        )


class RateLimitError(AppException):
    """
    Rate limit exceeded error

    Raised when rate limits are exceeded.
    Returns HTTP 429. This is a retryable error.

    Example:
        raise RateLimitError("Too many requests", retry_after=60)
    """
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        details: Optional[Dict[str, Any]] = None,
        retry_after: int = 60
    ):
        super().__init__(
            message,
            status_code=429,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            details=details,
            retryable=True,
            retry_after=retry_after
        )


class OperationTimeoutError(AppException):
    """
    Operation timeout error

    Raised when an operation exceeds its timeout limit.
    Returns HTTP 504. This is typically a retryable error.

    Example:
        raise OperationTimeoutError("Task execution timeout", details={"timeout": 300})
    """
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = True,
        retry_after: int = 10
    ):
        super().__init__(
            message,
            status_code=504,
            error_code=ErrorCode.TIMEOUT_EXCEEDED,
            details=details,
            retryable=retryable,
            retry_after=retry_after
        )


class TaskInvalidStateError(AppException):
    """
    Task invalid state error

    Raised when a task operation cannot be performed due to invalid state
    (e.g., trying to rollback a completed task).
    Returns HTTP 400.

    Example:
        raise TaskInvalidStateError("Cannot rollback completed task", current_state="completed")
    """
    def __init__(
        self,
        message: str,
        current_state: Optional[str] = None,
        allowed_states: Optional[list] = None
    ):
        details = {}
        if current_state:
            details["current_state"] = current_state
        if allowed_states:
            details["allowed_states"] = allowed_states

        super().__init__(
            message,
            status_code=400,
            error_code=ErrorCode.TASK_INVALID_STATE,
            details=details
        )


class OptimisticLockError(AppException):
    """
    Optimistic lock conflict error

    Raised when a concurrent modification is detected during update.
    The resource was modified by another process between read and write.
    Returns HTTP 409. This is a retryable error.

    Example:
        raise OptimisticLockError(
            "Task",
            task_id="123e4567-e89b-12d3-a456-426614174000",
            expected_version=1,
            current_version=2
        )
    """
    def __init__(
        self,
        resource: str,
        resource_id: str = None,
        expected_version: int = None,
        current_version: int = None
    ):
        details = {"resource": resource}
        if resource_id:
            details["resource_id"] = resource_id
        if expected_version is not None:
            details["expected_version"] = expected_version
        if current_version is not None:
            details["current_version"] = current_version

        super().__init__(
            f"{resource} was modified by another process. Please refresh and retry.",
            status_code=409,
            error_code=ErrorCode.RESOURCE_VERSION_CONFLICT,
            details=details,
            retryable=True,
            retry_after=1
        )


class CycleDetectedError(AppException):
    """
    Dependency cycle detected error

    Raised when a circular dependency is detected in task/subtask DAG.
    Returns HTTP 400.

    Example:
        raise CycleDetectedError(
            cycle_path=["subtask_a", "subtask_b", "subtask_c", "subtask_a"]
        )
    """
    def __init__(
        self,
        message: str = "Circular dependency detected",
        cycle_path: list = None
    ):
        details = {}
        if cycle_path:
            details["cycle_path"] = cycle_path

        super().__init__(
            message,
            status_code=400,
            error_code=ErrorCode.DATA_CYCLE_DETECTED,
            details=details
        )


# Alias for backward compatibility
TimeoutError = OperationTimeoutError


# ==================== Error Message Utilities ====================

# Generic error messages for production (don't expose internal details)
GENERIC_ERROR_MESSAGES = {
    "create": "Failed to create resource. Please try again.",
    "read": "Failed to retrieve resource. Please try again.",
    "update": "Failed to update resource. Please try again.",
    "delete": "Failed to delete resource. Please try again.",
    "list": "Failed to list resources. Please try again.",
    "allocate": "Failed to allocate resource. Please try again.",
    "schedule": "Failed to schedule operation. Please try again.",
    "evaluate": "Failed to evaluate. Please try again.",
    "upload": "Failed to upload data. Please try again.",
    "operation": "Operation failed. Please try again.",
}


def safe_error_message(
    operation: str,
    error: Exception,
    include_details: bool = False
) -> str:
    """
    Get a safe error message for HTTP responses.

    In production, returns a generic message.
    In debug mode (or when include_details=True), includes the actual error.

    Args:
        operation: Type of operation (create, read, update, delete, etc.)
        error: The caught exception
        include_details: Whether to include actual error details

    Returns:
        Safe error message string
    """
    from src.config import settings

    # Get generic message for operation type
    generic_msg = GENERIC_ERROR_MESSAGES.get(
        operation.lower(),
        GENERIC_ERROR_MESSAGES["operation"]
    )

    # In DEBUG mode or when explicitly requested, include details
    if settings.DEBUG or include_details:
        return f"{generic_msg} Details: {str(error)}"

    return generic_msg


def create_http_exception(
    status_code: int,
    operation: str,
    error: Exception,
    logger=None
) -> 'HTTPException':
    """
    Create an HTTPException with safe error message.

    Logs the full error details server-side, but returns a safe message to client.

    Args:
        status_code: HTTP status code
        operation: Type of operation (for generic message selection)
        error: The caught exception
        logger: Optional logger for server-side logging

    Returns:
        HTTPException with safe detail message
    """
    from fastapi import HTTPException

    # Log full error server-side
    if logger:
        logger.error(
            f"{operation} failed",
            error=str(error),
            error_type=type(error).__name__
        )

    return HTTPException(
        status_code=status_code,
        detail=safe_error_message(operation, error)
    )
