"""Scheduler-related Pydantic schemas"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class SchedulingCycleResult(BaseModel):
    """Result of a scheduling cycle"""
    cycle_start: str = Field(..., description="Cycle start timestamp")
    cycle_end: Optional[str] = Field(None, description="Cycle end timestamp")
    tasks_processed: int = Field(ge=0, description="Number of tasks processed")
    subtasks_allocated: int = Field(ge=0, description="Number of subtasks allocated")
    subtasks_queued: int = Field(ge=0, description="Number of subtasks queued")
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    message: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cycle_start": "2025-11-12T10:00:00Z",
                "cycle_end": "2025-11-12T10:00:01Z",
                "tasks_processed": 3,
                "subtasks_allocated": 5,
                "subtasks_queued": 2,
                "errors": []
            }
        }
    )


class SubtaskCompletionResult(BaseModel):
    """Result of handling subtask completion"""
    subtask_id: str
    newly_allocated: int = Field(ge=0, description="Number of newly allocated subtasks")
    task_completed: bool = Field(description="Whether the parent task is now complete")
    error: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subtask_id": "456e7890-e89b-12d3-a456-426614174001",
                "newly_allocated": 2,
                "task_completed": False
            }
        }
    )


class TaskScheduleResult(BaseModel):
    """Result of scheduling a specific task"""
    task_id: str
    subtasks_allocated: int = Field(ge=0)
    subtasks_queued: int = Field(ge=0)
    error: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "subtasks_allocated": 1,
                "subtasks_queued": 3
            }
        }
    )


class SchedulerStatsResponse(BaseModel):
    """Scheduler statistics response"""
    active_tasks: int = Field(ge=0, description="Number of active tasks")
    available_workers: int = Field(ge=0, description="Number of available workers")
    subtask_status_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Subtask counts by status"
    )
    queue_length: int = Field(ge=0, description="Number of subtasks in Redis queue")
    in_progress_count: int = Field(ge=0, description="Number of in-progress subtasks")
    max_concurrent_subtasks: int = Field(ge=1, description="System-wide concurrency limit")
    max_subtasks_per_worker: int = Field(ge=1, description="Per-worker concurrency limit")
    scheduler_interval_seconds: int = Field(ge=1, description="Scheduling interval")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "active_tasks": 5,
                "available_workers": 3,
                "subtask_status_counts": {
                    "pending": 10,
                    "queued": 5,
                    "in_progress": 3,
                    "completed": 20
                },
                "queue_length": 5,
                "in_progress_count": 3,
                "max_concurrent_subtasks": 20,
                "max_subtasks_per_worker": 1,
                "scheduler_interval_seconds": 30
            }
        }
    )


class SchedulerStatusResponse(BaseModel):
    """Scheduler status response"""
    running: bool = Field(description="Whether scheduler is running")
    interval_seconds: int = Field(description="Scheduling interval")
    last_cycle: Optional[str] = Field(None, description="Last cycle timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "running": True,
                "interval_seconds": 30,
                "last_cycle": "2025-11-12T10:00:00Z"
            }
        }
    )
