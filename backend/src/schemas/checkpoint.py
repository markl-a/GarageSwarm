"""Checkpoint-related Pydantic schemas"""

from datetime import datetime
from typing import List, Optional, Any, Dict
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class CheckpointStatus(str, Enum):
    """Checkpoint status enum"""
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    CORRECTED = "corrected"
    REJECTED = "rejected"


class UserDecision(str, Enum):
    """User decision enum"""
    ACCEPT = "accept"
    CORRECT = "correct"
    REJECT = "reject"


class CheckpointTriggerReason(str, Enum):
    """Checkpoint trigger reason enum"""
    CODE_GENERATION_COMPLETE = "code_generation_complete"
    REVIEW_ISSUES_FOUND = "review_issues_found"
    LOW_EVALUATION_SCORE = "low_evaluation_score"
    CHECKPOINT_FREQUENCY = "checkpoint_frequency"
    MANUAL_TRIGGER = "manual_trigger"


class CheckpointCreate(BaseModel):
    """Checkpoint creation request (internal)"""
    task_id: UUID = Field(..., description="Task ID for the checkpoint")
    subtasks_completed: List[UUID] = Field(..., description="List of completed subtask IDs")
    trigger_reason: CheckpointTriggerReason = Field(..., description="Reason for checkpoint trigger")
    context_info: Optional[Dict[str, Any]] = Field(None, description="Additional context information")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "subtasks_completed": ["456e7890-e89b-12d3-a456-426614174001"],
                "trigger_reason": "code_generation_complete",
                "context_info": {
                    "subtask_count": 3,
                    "completed_count": 1
                }
            }
        }
    )


class SubtaskInfo(BaseModel):
    """Subtask information in checkpoint"""
    subtask_id: UUID
    name: str
    status: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EvaluationInfo(BaseModel):
    """Evaluation information in checkpoint"""
    evaluation_id: UUID
    subtask_id: UUID
    overall_score: Optional[float] = Field(None, ge=0, le=10)
    code_quality: Optional[float] = Field(None, ge=0, le=10)
    completeness: Optional[float] = Field(None, ge=0, le=10)
    security: Optional[float] = Field(None, ge=0, le=10)
    architecture: Optional[float] = Field(None, ge=0, le=10)
    testability: Optional[float] = Field(None, ge=0, le=10)
    details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class CheckpointResponse(BaseModel):
    """Checkpoint detail response"""
    checkpoint_id: UUID
    task_id: UUID
    status: CheckpointStatus
    subtasks_completed: List[UUID]
    user_decision: Optional[UserDecision] = None
    decision_notes: Optional[str] = None
    triggered_at: datetime
    reviewed_at: Optional[datetime] = None

    # Additional context
    context_info: Optional[Dict[str, Any]] = Field(None, description="Context about checkpoint trigger")
    subtask_details: List[SubtaskInfo] = Field(default_factory=list, description="Details of completed subtasks")
    evaluations: List[EvaluationInfo] = Field(default_factory=list, description="Evaluation results")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "checkpoint_id": "789e0123-e89b-12d3-a456-426614174002",
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "pending_review",
                "subtasks_completed": ["456e7890-e89b-12d3-a456-426614174001"],
                "user_decision": None,
                "decision_notes": None,
                "triggered_at": "2025-11-12T10:30:00Z",
                "reviewed_at": None,
                "context_info": {
                    "trigger_reason": "code_generation_complete",
                    "subtask_count": 3
                },
                "subtask_details": [
                    {
                        "subtask_id": "456e7890-e89b-12d3-a456-426614174001",
                        "name": "Code Generation",
                        "status": "completed",
                        "output": {"files_created": ["main.py"]}
                    }
                ],
                "evaluations": [
                    {
                        "evaluation_id": "abc12345-e89b-12d3-a456-426614174003",
                        "subtask_id": "456e7890-e89b-12d3-a456-426614174001",
                        "overall_score": 8.5,
                        "code_quality": 9.0,
                        "completeness": 8.0,
                        "security": 9.0
                    }
                ]
            }
        }
    )


class CheckpointListResponse(BaseModel):
    """Checkpoint list response"""
    checkpoints: List[CheckpointResponse]
    total: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "checkpoints": [
                    {
                        "checkpoint_id": "789e0123-e89b-12d3-a456-426614174002",
                        "task_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "pending_review",
                        "subtasks_completed": ["456e7890-e89b-12d3-a456-426614174001"],
                        "triggered_at": "2025-11-12T10:30:00Z"
                    }
                ],
                "total": 1
            }
        }
    )


class CheckpointDecisionRequest(BaseModel):
    """Checkpoint decision request"""
    decision: UserDecision = Field(..., description="User decision: accept, correct, or reject")
    feedback: Optional[str] = Field(None, max_length=5000, description="User feedback or correction instructions")
    correction_type: Optional[str] = Field(None, description="Type of correction if decision is 'correct'")
    reference_files: Optional[List[str]] = Field(default_factory=list, description="Reference files or links for correction")
    apply_to_future: bool = Field(default=False, description="Apply this correction pattern to future tasks")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "decision": "correct",
                "feedback": "The error handling needs improvement. Add try-catch blocks around database operations.",
                "correction_type": "incomplete",
                "reference_files": ["docs/error_handling.md"],
                "apply_to_future": False
            }
        }
    )


class CheckpointDecisionResponse(BaseModel):
    """Checkpoint decision response"""
    checkpoint_id: UUID
    status: CheckpointStatus
    message: str
    task_status: str = Field(..., description="Updated task status")
    corrections_created: int = Field(default=0, description="Number of corrections created")
    next_action: str = Field(..., description="Description of next action")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "checkpoint_id": "789e0123-e89b-12d3-a456-426614174002",
                "status": "corrected",
                "message": "Checkpoint decision processed successfully",
                "task_status": "in_progress",
                "corrections_created": 2,
                "next_action": "Corrections created for 2 subtasks. Task will continue after corrections are applied."
            }
        }
    )


class CheckpointHistoryItem(BaseModel):
    """Individual checkpoint history item"""
    checkpoint_id: UUID
    status: CheckpointStatus
    subtasks_completed: List[UUID]
    user_decision: Optional[UserDecision] = None
    decision_notes: Optional[str] = None
    triggered_at: datetime
    reviewed_at: Optional[datetime] = None
    trigger_reason: Optional[str] = Field(None, description="Reason why checkpoint was triggered")

    model_config = ConfigDict(from_attributes=True)


class CheckpointHistoryResponse(BaseModel):
    """Checkpoint history response"""
    task_id: UUID
    checkpoints: List[CheckpointHistoryItem]
    total: int
    statistics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Statistics about checkpoints (total, approved, corrected, rejected)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "checkpoints": [
                    {
                        "checkpoint_id": "789e0123-e89b-12d3-a456-426614174002",
                        "status": "approved",
                        "subtasks_completed": ["456e7890-e89b-12d3-a456-426614174001"],
                        "user_decision": "accept",
                        "triggered_at": "2025-11-12T10:30:00Z",
                        "reviewed_at": "2025-11-12T10:35:00Z",
                        "trigger_reason": "code_generation_complete"
                    }
                ],
                "total": 1,
                "statistics": {
                    "total": 1,
                    "approved": 1,
                    "corrected": 0,
                    "rejected": 0,
                    "pending": 0
                }
            }
        }
    )
