"""
Workflow Schemas

Request and response models for workflow endpoints.
"""

from datetime import datetime
from typing import Optional, Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowNodeCreate(BaseModel):
    """Workflow node creation request."""

    name: str = Field(..., min_length=1, max_length=200)
    node_type: str = Field(default="task")
    order_index: int = Field(default=0)
    agent_config: Optional[Dict[str, Any]] = None
    condition_config: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[UUID]] = None
    max_retries: int = Field(default=3, ge=0, le=10)


class WorkflowEdgeCreate(BaseModel):
    """Workflow edge creation request."""

    from_node_id: UUID
    to_node_id: UUID
    condition: Optional[Dict[str, Any]] = None
    label: Optional[str] = Field(None, max_length=100)


class WorkflowCreate(BaseModel):
    """Workflow creation request."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    workflow_type: str = Field(default="sequential")
    nodes: Optional[List[WorkflowNodeCreate]] = None
    edges: Optional[List[WorkflowEdgeCreate]] = None
    context: Optional[Dict[str, Any]] = None


class WorkflowUpdate(BaseModel):
    """Workflow update request."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class WorkflowNodeResponse(BaseModel):
    """Workflow node response."""

    node_id: UUID
    workflow_id: UUID
    name: str
    node_type: str
    status: str
    order_index: int = 0
    agent_config: Optional[Dict[str, Any]] = None
    condition_config: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[UUID]] = None
    input_data: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WorkflowEdgeResponse(BaseModel):
    """Workflow edge response."""

    edge_id: UUID
    workflow_id: UUID
    from_node_id: UUID
    to_node_id: UUID
    condition: Optional[Dict[str, Any]] = None
    label: Optional[str] = None

    model_config = {"from_attributes": True}


class WorkflowResponse(BaseModel):
    """Workflow response."""

    workflow_id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = None
    workflow_type: str
    status: str
    dag_definition: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    total_nodes: int
    completed_nodes: int
    progress: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    nodes: Optional[List[WorkflowNodeResponse]] = None
    edges: Optional[List[WorkflowEdgeResponse]] = None

    model_config = {"from_attributes": True}


class WorkflowListResponse(BaseModel):
    """Paginated workflow list response."""

    workflows: List[WorkflowResponse]
    total: int
    limit: int
    offset: int
