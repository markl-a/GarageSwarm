"""Worker API Key Pydantic schemas"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APIKeyCreateRequest(BaseModel):
    """Request to create a new API key for a worker"""

    worker_id: UUID = Field(..., description="Worker ID to create key for")
    description: Optional[str] = Field(
        None, max_length=500, description="Optional key description"
    )
    expires_in_days: Optional[int] = Field(
        None, ge=1, le=365, description="Days until expiration (null = never expires)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "worker_id": "123e4567-e89b-12d3-a456-426614174000",
                "description": "Production worker key",
                "expires_in_days": 90,
            }
        }
    )


class APIKeyCreateResponse(BaseModel):
    """Response after creating an API key - contains the plain key ONCE"""

    key_id: UUID = Field(..., description="Unique key identifier")
    worker_id: UUID = Field(..., description="Associated worker ID")
    api_key: str = Field(
        ..., description="Plain API key - SAVE THIS, it will not be shown again!"
    )
    key_prefix: str = Field(..., description="Key prefix for identification")
    description: Optional[str] = Field(None, description="Key description")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")
    created_at: datetime = Field(..., description="Creation time")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key_id": "abc12345-e89b-12d3-a456-426614174000",
                "worker_id": "123e4567-e89b-12d3-a456-426614174000",
                "api_key": "wk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
                "key_prefix": "wk_a1b2c3d4",
                "description": "Production worker key",
                "expires_at": "2026-04-08T00:00:00Z",
                "created_at": "2026-01-08T10:00:00Z",
            }
        }
    )


class APIKeySummary(BaseModel):
    """API key summary (without the actual key value)"""

    key_id: UUID = Field(..., description="Unique key identifier")
    worker_id: UUID = Field(..., description="Associated worker ID")
    key_prefix: str = Field(..., description="Key prefix for identification")
    description: Optional[str] = Field(None, description="Key description")
    is_active: bool = Field(..., description="Whether the key is active")
    created_at: datetime = Field(..., description="Creation time")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")
    last_used_at: Optional[datetime] = Field(None, description="Last usage time")
    revoked_at: Optional[datetime] = Field(None, description="Revocation time")

    model_config = ConfigDict(from_attributes=True)


class APIKeyListResponse(BaseModel):
    """List of API keys for a worker"""

    keys: List[APIKeySummary] = Field(..., description="List of API keys")
    total: int = Field(..., description="Total number of keys")


class APIKeyRevokeResponse(BaseModel):
    """Response after revoking an API key"""

    key_id: UUID = Field(..., description="Revoked key ID")
    revoked_at: datetime = Field(..., description="Revocation time")
    message: str = Field(
        default="API key revoked successfully", description="Status message"
    )
