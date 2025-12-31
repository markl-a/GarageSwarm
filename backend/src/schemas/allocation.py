"""Allocation-related Pydantic schemas"""

from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class AllocationRequest(BaseModel):
    """Request to allocate a subtask"""
    subtask_id: UUID = Field(..., description="Subtask to allocate")
    force: bool = Field(default=False, description="Force reallocation even if already assigned")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subtask_id": "456e7890-e89b-12d3-a456-426614174001",
                "force": False
            }
        }
    )


class AllocationResponse(BaseModel):
    """Response for subtask allocation"""
    subtask_id: UUID
    worker_id: Optional[UUID] = None
    assigned_tool: Optional[str] = None
    status: str = Field(..., description="Allocation status: allocated | queued | failed")
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subtask_id": "456e7890-e89b-12d3-a456-426614174001",
                "worker_id": "789e0123-e89b-12d3-a456-426614174002",
                "assigned_tool": "claude_code",
                "status": "allocated",
                "message": "Subtask allocated to worker dev-machine-1"
            }
        }
    )


class BatchAllocationResponse(BaseModel):
    """Response for batch allocation"""
    task_id: Optional[UUID] = None
    allocations: List[AllocationResponse]
    total_allocated: int
    total_queued: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "allocations": [
                    {
                        "subtask_id": "456e7890-e89b-12d3-a456-426614174001",
                        "worker_id": "789e0123-e89b-12d3-a456-426614174002",
                        "status": "allocated",
                        "message": "Allocated to dev-machine-1"
                    }
                ],
                "total_allocated": 1,
                "total_queued": 0
            }
        }
    )


class WorkerScoreDetail(BaseModel):
    """Detailed worker scoring breakdown"""
    worker_id: UUID
    machine_name: str
    tool_score: float = Field(ge=0, le=1, description="Tool matching score (0-1)")
    resource_score: float = Field(ge=0, le=1, description="Resource availability score (0-1)")
    privacy_score: float = Field(ge=0, le=1, description="Privacy compatibility score (0-1)")
    total_score: float = Field(ge=0, le=1, description="Weighted total score (0-1)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "worker_id": "789e0123-e89b-12d3-a456-426614174002",
                "machine_name": "dev-machine-1",
                "tool_score": 1.0,
                "resource_score": 0.8,
                "privacy_score": 1.0,
                "total_score": 0.94
            }
        }
    )


class AllocationStatsResponse(BaseModel):
    """Allocation statistics response"""
    queue_length: int = Field(..., description="Number of subtasks in Redis queue")
    in_progress_count: int = Field(..., description="Number of subtasks being executed")
    online_workers: int = Field(..., description="Number of online workers")
    queued_subtasks: int = Field(..., description="Number of subtasks in queued status")
    scoring_weights: Dict[str, float] = Field(
        ...,
        description="Current scoring algorithm weights"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "queue_length": 5,
                "in_progress_count": 3,
                "online_workers": 2,
                "queued_subtasks": 5,
                "scoring_weights": {
                    "tool_matching": 0.5,
                    "resource_score": 0.3,
                    "privacy_score": 0.2
                }
            }
        }
    )
