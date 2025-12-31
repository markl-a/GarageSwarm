"""
Authentication Schemas

Pydantic models for authentication request/response validation.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserRegisterRequest(BaseModel):
    """User registration request"""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_-]+$",
        description="Username (alphanumeric, hyphens, underscores)",
        examples=["john_doe"],
    )
    email: EmailStr = Field(
        ...,
        description="Valid email address",
        examples=["john@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password (minimum 8 characters)",
        examples=["SecurePass123!"],
    )


class UserLoginRequest(BaseModel):
    """User login request"""

    username: str = Field(
        ...,
        description="Username or email",
        examples=["john_doe"],
    )
    password: str = Field(
        ...,
        description="User password",
        examples=["SecurePass123!"],
    )


class TokenResponse(BaseModel):
    """Token response"""

    access_token: str = Field(
        ...,
        description="JWT access token (15 min expiry)",
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token (7 day expiry)",
    )
    token_type: str = Field(
        default="bearer",
        description="Token type",
    )
    expires_in: int = Field(
        default=900,
        description="Access token expiry in seconds (15 minutes)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 900,
            }
        }
    )


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
    )


class LogoutRequest(BaseModel):
    """Logout request"""

    access_token: Optional[str] = Field(
        None,
        description="Access token to blacklist (optional)",
    )
    refresh_token: Optional[str] = Field(
        None,
        description="Refresh token to blacklist (optional)",
    )


class UserResponse(BaseModel):
    """User profile response"""

    user_id: UUID = Field(
        ...,
        description="User's unique identifier",
    )
    username: str = Field(
        ...,
        description="Username",
    )
    email: EmailStr = Field(
        ...,
        description="Email address",
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp",
    )
    last_login: Optional[datetime] = Field(
        None,
        description="Last login timestamp",
    )
    is_active: bool = Field(
        default=True,
        description="Whether user account is active",
    )

    model_config = ConfigDict(from_attributes=True)


class RegisterResponse(BaseModel):
    """User registration response"""

    user: UserResponse
    message: str = Field(
        default="User registered successfully",
        description="Success message",
    )


class LoginResponse(BaseModel):
    """User login response"""

    user: UserResponse
    tokens: TokenResponse
    message: str = Field(
        default="Login successful",
        description="Success message",
    )


class LogoutResponse(BaseModel):
    """Logout response"""

    message: str = Field(
        default="Logout successful",
        description="Success message",
    )


class PasswordChangeRequest(BaseModel):
    """Password change request"""

    current_password: str = Field(
        ...,
        description="Current password",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (minimum 8 characters)",
    )


class PasswordChangeResponse(BaseModel):
    """Password change response"""

    message: str = Field(
        default="Password changed successfully",
        description="Success message",
    )


class TokenValidationResponse(BaseModel):
    """Token validation response"""

    valid: bool = Field(
        ...,
        description="Whether token is valid",
    )
    user_id: Optional[UUID] = Field(
        None,
        description="User ID if token is valid",
    )
    username: Optional[str] = Field(
        None,
        description="Username if token is valid",
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Token expiration timestamp",
    )
