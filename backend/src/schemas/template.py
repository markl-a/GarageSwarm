"""Template-related Pydantic schemas"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class TemplateCategory(str, Enum):
    """Template category enum"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DEVOPS = "devops"
    REVIEW = "review"


class StepType(str, Enum):
    """Step type enum"""

    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    CODE_FIX = "code_fix"
    TEST = "test"
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"
    DEPLOYMENT = "deployment"


class TemplateStepCreate(BaseModel):
    """Template step creation request"""

    name: str = Field(..., min_length=1, max_length=255, description="Step name")
    description: str = Field(..., min_length=1, description="Step description")
    step_order: int = Field(..., ge=1, description="Step execution order (1-based)")
    step_type: StepType = Field(..., description="Step type")
    depends_on: Optional[List[int]] = Field(
        None, description="Dependency step orders (e.g., [1, 2])"
    )
    recommended_tool: Optional[str] = Field(
        None, description="Recommended AI tool (claude_code, gemini_cli, ollama)"
    )
    complexity: Optional[int] = Field(
        None, ge=1, le=5, description="Complexity rating (1-5)"
    )
    priority: int = Field(default=0, description="Priority score")
    is_required: bool = Field(default=True, description="Whether step is required")
    is_parallel: bool = Field(
        default=False, description="Whether step can run in parallel"
    )
    step_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional step metadata"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Generate API endpoint",
                "description": "Create REST API endpoint with proper error handling",
                "step_order": 1,
                "step_type": "code_generation",
                "depends_on": None,
                "recommended_tool": "claude_code",
                "complexity": 3,
                "priority": 100,
                "is_required": True,
                "is_parallel": False,
            }
        }
    )


class TemplateStepResponse(BaseModel):
    """Template step response"""

    step_id: UUID
    template_id: UUID
    name: str
    description: str
    step_order: int
    step_type: StepType
    depends_on: Optional[List[int]] = None
    recommended_tool: Optional[str] = None
    complexity: Optional[int] = None
    priority: int
    is_required: bool
    is_parallel: bool
    step_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TemplateCreateRequest(BaseModel):
    """Template creation request"""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Template name (unique)"
    )
    description: str = Field(..., min_length=1, description="Template description")
    category: TemplateCategory = Field(..., description="Template category")
    steps: List[TemplateStepCreate] = Field(
        ..., min_items=1, description="Template steps (at least one required)"
    )
    is_active: bool = Field(default=True, description="Whether template is active")
    default_checkpoint_frequency: str = Field(
        default="medium", description="Default checkpoint frequency (low, medium, high)"
    )
    default_privacy_level: str = Field(
        default="normal", description="Default privacy level (normal, sensitive)"
    )
    default_tool_preferences: Optional[List[str]] = Field(
        None, description="Default AI tools"
    )
    tags: Optional[List[str]] = Field(None, description="Template tags")
    estimated_duration: Optional[int] = Field(
        None, gt=0, description="Estimated completion time in minutes"
    )
    complexity_level: Optional[int] = Field(
        None, ge=1, le=5, description="Overall complexity (1-5)"
    )
    template_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional template metadata"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "REST API Development",
                "description": "Complete REST API development workflow",
                "category": "development",
                "steps": [
                    {
                        "name": "API Design",
                        "description": "Design API endpoints and data models",
                        "step_order": 1,
                        "step_type": "analysis",
                        "complexity": 2,
                        "priority": 100,
                    }
                ],
                "tags": ["api", "backend", "rest"],
                "estimated_duration": 120,
                "complexity_level": 3,
            }
        }
    )


class TemplateUpdateRequest(BaseModel):
    """Template update request"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    category: Optional[TemplateCategory] = None
    is_active: Optional[bool] = None
    default_checkpoint_frequency: Optional[str] = None
    default_privacy_level: Optional[str] = None
    default_tool_preferences: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    estimated_duration: Optional[int] = Field(None, gt=0)
    complexity_level: Optional[int] = Field(None, ge=1, le=5)
    template_metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Updated description",
                "is_active": True,
                "tags": ["api", "backend", "rest", "updated"],
            }
        }
    )


class TemplateDetailResponse(BaseModel):
    """Template detail response"""

    template_id: UUID
    name: str
    description: str
    category: TemplateCategory
    is_active: bool
    is_system: bool
    default_checkpoint_frequency: str
    default_privacy_level: str
    default_tool_preferences: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    estimated_duration: Optional[int] = None
    complexity_level: Optional[int] = None
    template_metadata: Optional[Dict[str, Any]] = None
    usage_count: int
    created_by: Optional[UUID] = None
    steps: List[TemplateStepResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "template_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "REST API Development",
                "description": "Complete REST API workflow",
                "category": "development",
                "is_active": True,
                "is_system": True,
                "usage_count": 42,
                "steps": [],
                "created_at": "2025-11-12T10:00:00Z",
                "updated_at": "2025-11-12T10:00:00Z",
            }
        },
    )


class TemplateSummary(BaseModel):
    """Template summary for list view"""

    template_id: UUID
    name: str
    description: str = Field(max_length=200)
    category: TemplateCategory
    is_active: bool
    is_system: bool
    tags: Optional[List[str]] = None
    estimated_duration: Optional[int] = None
    complexity_level: Optional[int] = None
    usage_count: int
    step_count: int = Field(..., description="Number of steps in template")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TemplateListResponse(BaseModel):
    """Template list response with pagination"""

    templates: List[TemplateSummary]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "templates": [
                    {
                        "template_id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "REST API Development",
                        "description": "Complete REST API workflow",
                        "category": "development",
                        "is_active": True,
                        "is_system": True,
                        "usage_count": 42,
                        "step_count": 5,
                        "created_at": "2025-11-12T10:00:00Z",
                        "updated_at": "2025-11-12T10:00:00Z",
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0,
            }
        }
    )


class TemplateCreateResponse(BaseModel):
    """Template creation response"""

    template_id: UUID
    name: str
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "template_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "REST API Development",
                "message": "Template created successfully",
            }
        }
    )


class TemplateApplyRequest(BaseModel):
    """Template apply request"""

    template_id: UUID = Field(..., description="Template UUID to apply")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"template_id": "123e4567-e89b-12d3-a456-426614174000"}
        }
    )


class TemplateApplyResponse(BaseModel):
    """Template apply response"""

    task_id: UUID
    template_id: UUID
    template_name: str
    subtask_count: int
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "456e7890-e89b-12d3-a456-426614174001",
                "template_id": "123e4567-e89b-12d3-a456-426614174000",
                "template_name": "REST API Development",
                "subtask_count": 5,
                "message": "Template applied successfully",
            }
        }
    )
