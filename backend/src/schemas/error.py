"""
Error Response Schemas

Pydantic models for standardized error responses across the API.
All error responses follow the same structure for consistency.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ValidationErrorDetail(BaseModel):
    """
    Single validation error detail

    Attributes:
        field: The field that failed validation
        message: Human-readable error message
        type: Type of validation error
    """
    field: str = Field(..., description="Field name that failed validation")
    message: str = Field(..., description="Validation error message")
    type: str = Field(..., description="Type of validation error")


class ErrorResponse(BaseModel):
    """
    Standard error response format

    All API errors return this format for consistency.

    Attributes:
        status: Always "error" for error responses
        message: Human-readable error message
        details: Additional error details (empty dict if none)
        path: Request path that generated the error (optional)

    Example:
        {
            "status": "error",
            "message": "Task with id 123 not found",
            "details": {
                "resource": "Task",
                "identifier": "123"
            },
            "path": "/api/v1/tasks/123"
        }
    """
    status: str = Field(default="error", description="Response status (always 'error')")
    message: str = Field(..., description="Human-readable error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    path: Optional[str] = Field(None, description="Request path that generated the error")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "message": "Task with id 123e4567-e89b-12d3-a456-426614174000 not found",
                "details": {
                    "resource": "Task",
                    "identifier": "123e4567-e89b-12d3-a456-426614174000"
                },
                "path": "/api/v1/tasks/123e4567-e89b-12d3-a456-426614174000"
            }
        }


class ValidationErrorResponse(BaseModel):
    """
    Validation error response format

    Returned when request validation fails (422 status code).

    Attributes:
        status: Always "error"
        message: Generic validation error message
        details: Contains list of validation errors
        path: Request path that generated the error

    Example:
        {
            "status": "error",
            "message": "Request validation failed",
            "details": {
                "validation_errors": [
                    {
                        "field": "description",
                        "message": "String should have at least 10 characters",
                        "type": "string_too_short"
                    }
                ]
            },
            "path": "/api/v1/tasks"
        }
    """
    status: str = Field(default="error", description="Response status")
    message: str = Field(default="Request validation failed", description="Error message")
    details: Dict[str, List[ValidationErrorDetail]] = Field(..., description="Validation error details")
    path: Optional[str] = Field(None, description="Request path")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "message": "Request validation failed",
                "details": {
                    "validation_errors": [
                        {
                            "field": "description",
                            "message": "String should have at least 10 characters",
                            "type": "string_too_short"
                        }
                    ]
                },
                "path": "/api/v1/tasks"
            }
        }


class ServiceErrorResponse(BaseModel):
    """
    Service unavailable error response

    Returned when external services are unavailable (503 status code).

    Attributes:
        status: Always "error"
        message: Service unavailable message
        details: Service-specific details
        path: Request path

    Example:
        {
            "status": "error",
            "message": "Service Redis is unavailable",
            "details": {
                "service": "Redis",
                "host": "localhost:6379"
            },
            "path": "/api/v1/tasks"
        }
    """
    status: str = Field(default="error", description="Response status")
    message: str = Field(..., description="Service error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Service error details")
    path: Optional[str] = Field(None, description="Request path")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "message": "Service Redis is unavailable",
                "details": {
                    "service": "Redis",
                    "host": "localhost:6379"
                },
                "path": "/api/v1/tasks"
            }
        }
