"""
Worker Agent Custom Exceptions

Exception classes for the Worker Agent component, covering connection errors,
task execution failures, tool errors, and timeout scenarios.
"""

from typing import Dict, Optional, Any


class WorkerException(Exception):
    """
    Base exception for Worker Agent

    All worker-related exceptions inherit from this class.

    Attributes:
        message: Human-readable error message
        details: Additional error context
        recoverable: Whether the error is recoverable with retry
    """
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = False
    ):
        self.message = message
        self.details = details or {}
        self.recoverable = recoverable
        super().__init__(self.message)


class ConnectionError(WorkerException):
    """
    Connection failure error

    Raised when the worker cannot connect to the backend API or other services.
    This is typically recoverable with retry.

    Example:
        raise ConnectionError(
            "Failed to connect to backend API",
            details={"url": "http://localhost:8000", "attempt": 1},
            recoverable=True
        )
    """
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, recoverable=True)


class TaskExecutionError(WorkerException):
    """
    Task execution failure error

    Raised when a subtask execution fails during processing.
    May be recoverable depending on the failure reason.

    Example:
        raise TaskExecutionError(
            "Failed to execute subtask",
            details={
                "subtask_id": "123",
                "error": "Command failed",
                "exit_code": 1
            },
            recoverable=False
        )
    """
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = False
    ):
        super().__init__(message, details, recoverable)


class ToolError(WorkerException):
    """
    Tool invocation error

    Raised when an AI tool (Claude Code, Gemini CLI, etc.) fails to execute
    or returns an error. May be recoverable with retry.

    Example:
        raise ToolError(
            "Claude Code execution failed",
            details={
                "tool": "claude_code",
                "error": "API rate limit exceeded"
            },
            recoverable=True
        )
    """
    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        details = details or {}
        if tool_name:
            details["tool"] = tool_name
        super().__init__(message, details, recoverable)


class TimeoutError(WorkerException):
    """
    Operation timeout error

    Raised when an operation exceeds its timeout limit.
    Usually not recoverable with simple retry.

    Example:
        raise TimeoutError(
            "Subtask execution timeout",
            details={
                "subtask_id": "123",
                "timeout": 300,
                "elapsed": 305
            }
        )
    """
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, recoverable=False)


class ConfigurationError(WorkerException):
    """
    Configuration error

    Raised when worker configuration is invalid or missing.
    Not recoverable without fixing configuration.

    Example:
        raise ConfigurationError(
            "Missing required configuration",
            details={"missing_field": "backend_url"}
        )
    """
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, recoverable=False)


class RegistrationError(WorkerException):
    """
    Worker registration error

    Raised when worker fails to register with the backend.
    May be recoverable with retry.

    Example:
        raise RegistrationError(
            "Failed to register worker with backend",
            details={"machine_id": "worker-001", "attempt": 3}
        )
    """
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        super().__init__(message, details, recoverable)


class HeartbeatError(WorkerException):
    """
    Heartbeat failure error

    Raised when worker fails to send heartbeat to backend.
    Usually recoverable with retry.

    Example:
        raise HeartbeatError(
            "Failed to send heartbeat",
            details={"worker_id": "123", "consecutive_failures": 2}
        )
    """
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, recoverable=True)


class SubtaskFetchError(WorkerException):
    """
    Subtask fetch error

    Raised when worker fails to fetch subtasks from backend.
    Usually recoverable with retry.

    Example:
        raise SubtaskFetchError(
            "Failed to fetch subtasks",
            details={"worker_id": "123", "error": "API timeout"}
        )
    """
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, recoverable=True)


class ResultSubmissionError(WorkerException):
    """
    Result submission error

    Raised when worker fails to submit subtask results to backend.
    Usually recoverable with retry.

    Example:
        raise ResultSubmissionError(
            "Failed to submit subtask result",
            details={
                "subtask_id": "123",
                "status_code": 500
            }
        )
    """
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, recoverable=True)


class ShutdownError(WorkerException):
    """
    Graceful shutdown error

    Raised when worker encounters errors during shutdown.
    Not recoverable as it occurs during cleanup.

    Example:
        raise ShutdownError(
            "Error during worker shutdown",
            details={"stage": "cleanup", "error": "Failed to close connections"}
        )
    """
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, recoverable=False)
