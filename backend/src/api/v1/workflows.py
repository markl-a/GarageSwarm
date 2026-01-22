"""
Workflow Endpoints

Workflow CRUD, execution management, templates, checkpoints, and human review.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from src.database import get_db
from src.models.workflow import Workflow, WorkflowNode, WorkflowEdge, WorkflowStatus, NodeStatus
from src.models.user import User
from src.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowNodeResponse,
    WorkflowEdgeResponse,
)
from src.auth.dependencies import get_current_active_user
from src.logging_config import get_logger
from src.workflows import WorkflowState, WorkflowContext, WorkflowGraph

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Additional Pydantic Schemas for New Endpoints
# =============================================================================

class WorkflowFromTemplateRequest(BaseModel):
    """Request to create workflow from template."""
    template_id: str = Field(..., description="Template identifier")
    input: Dict[str, Any] = Field(default_factory=dict, description="Input parameters for template")
    name: Optional[str] = Field(None, description="Optional workflow name override")


class WorkflowTemplateMetadata(BaseModel):
    """Template metadata for listing."""
    template_id: str
    name: str
    description: str = ""
    category: str = "general"
    tags: List[str] = Field(default_factory=list)
    required_inputs: List[str] = Field(default_factory=list)
    node_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WorkflowTemplateDetail(WorkflowTemplateMetadata):
    """Detailed template information."""
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    default_context: Dict[str, Any] = Field(default_factory=dict)
    workflow_type: str = "sequential"


class WorkflowTemplateListResponse(BaseModel):
    """List of available templates."""
    templates: List[WorkflowTemplateMetadata]
    total: int


class CheckpointCreate(BaseModel):
    """Request to create a manual checkpoint."""
    name: Optional[str] = Field(None, description="Optional checkpoint name")
    description: Optional[str] = Field(None, description="Optional description")


class CheckpointResponse(BaseModel):
    """Checkpoint information."""
    checkpoint_id: UUID
    workflow_id: UUID
    name: str
    description: Optional[str] = None
    state: Dict[str, Any]
    node_states: Dict[str, Any]
    created_at: datetime
    created_by: Optional[UUID] = None


class CheckpointListResponse(BaseModel):
    """List of checkpoints for a workflow."""
    checkpoints: List[CheckpointResponse]
    total: int


class HumanReviewRequest(BaseModel):
    """Human review submission."""
    decision: Literal["approve", "reject", "modify"] = Field(..., description="Review decision")
    comments: Optional[str] = Field(None, description="Reviewer comments")
    modifications: Optional[Dict[str, Any]] = Field(None, description="State modifications for 'modify' decision")


class HumanReviewResponse(BaseModel):
    """Human review result."""
    node_id: UUID
    workflow_id: UUID
    decision: str
    comments: Optional[str] = None
    reviewer_id: UUID
    reviewed_at: datetime
    workflow_status: str


class ExecutionGraphNode(BaseModel):
    """Node in execution visualization."""
    node_id: str
    name: str
    node_type: str
    status: str
    order_index: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    output_preview: Optional[str] = None


class ExecutionGraphEdge(BaseModel):
    """Edge in execution visualization."""
    edge_id: str
    from_node_id: str
    to_node_id: str
    label: Optional[str] = None
    executed: bool = False


class ExecutionGraphResponse(BaseModel):
    """Complete execution graph for visualization."""
    workflow_id: UUID
    workflow_name: str
    workflow_status: str
    workflow_type: str
    nodes: List[ExecutionGraphNode]
    edges: List[ExecutionGraphEdge]
    entry_node: Optional[str] = None
    exit_nodes: List[str] = Field(default_factory=list)
    progress: int
    total_nodes: int
    completed_nodes: int
    current_node: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# =============================================================================
# In-Memory Storage for Templates and Checkpoints
# (In production, these would be database tables)
# =============================================================================

# Built-in workflow templates
WORKFLOW_TEMPLATES: Dict[str, WorkflowTemplateDetail] = {
    "code-review": WorkflowTemplateDetail(
        template_id="code-review",
        name="Code Review Pipeline",
        description="Automated code review with multiple analysis stages",
        category="development",
        tags=["code", "review", "quality"],
        required_inputs=["repository_url", "branch_name"],
        workflow_type="sequential",
        node_count=4,
        nodes=[
            {"name": "Clone Repository", "node_type": "task", "order_index": 0,
             "agent_config": {"tool": "claude_code", "prompt": "Clone and analyze {repository_url}"}},
            {"name": "Static Analysis", "node_type": "task", "order_index": 1,
             "agent_config": {"tool": "claude_code", "prompt": "Run static analysis on the codebase"}},
            {"name": "Security Scan", "node_type": "task", "order_index": 2,
             "agent_config": {"tool": "claude_code", "prompt": "Perform security vulnerability scan"}},
            {"name": "Generate Report", "node_type": "task", "order_index": 3,
             "agent_config": {"tool": "claude_code", "prompt": "Generate comprehensive code review report"}},
        ],
        edges=[],
        default_context={"scan_depth": "full", "report_format": "markdown"},
    ),
    "data-pipeline": WorkflowTemplateDetail(
        template_id="data-pipeline",
        name="Data Processing Pipeline",
        description="ETL workflow for data extraction, transformation, and loading",
        category="data",
        tags=["etl", "data", "processing"],
        required_inputs=["source_url", "destination"],
        workflow_type="sequential",
        node_count=4,
        nodes=[
            {"name": "Extract Data", "node_type": "task", "order_index": 0,
             "agent_config": {"tool": "claude_code", "prompt": "Extract data from {source_url}"}},
            {"name": "Validate Data", "node_type": "task", "order_index": 1,
             "agent_config": {"tool": "claude_code", "prompt": "Validate extracted data quality"}},
            {"name": "Transform Data", "node_type": "task", "order_index": 2,
             "agent_config": {"tool": "claude_code", "prompt": "Apply data transformations"}},
            {"name": "Load Data", "node_type": "task", "order_index": 3,
             "agent_config": {"tool": "claude_code", "prompt": "Load data to {destination}"}},
        ],
        edges=[],
        default_context={"batch_size": 1000, "validate_schema": True},
    ),
    "content-generation": WorkflowTemplateDetail(
        template_id="content-generation",
        name="Content Generation with Review",
        description="Generate content with human-in-the-loop review",
        category="content",
        tags=["content", "generation", "review"],
        required_inputs=["topic", "content_type"],
        workflow_type="sequential",
        node_count=4,
        nodes=[
            {"name": "Research Topic", "node_type": "task", "order_index": 0,
             "agent_config": {"tool": "gemini_cli", "prompt": "Research {topic} for {content_type}"}},
            {"name": "Generate Draft", "node_type": "task", "order_index": 1,
             "agent_config": {"tool": "claude_code", "prompt": "Generate {content_type} draft about {topic}"}},
            {"name": "Human Review", "node_type": "wait", "order_index": 2,
             "agent_config": {"review_type": "approval", "instructions": "Review and approve generated content"}},
            {"name": "Finalize Content", "node_type": "task", "order_index": 3,
             "agent_config": {"tool": "claude_code", "prompt": "Apply feedback and finalize content"}},
        ],
        edges=[],
        default_context={"tone": "professional", "length": "medium"},
    ),
    "parallel-analysis": WorkflowTemplateDetail(
        template_id="parallel-analysis",
        name="Parallel Multi-Expert Analysis",
        description="Analyze input using multiple AI tools in parallel",
        category="analysis",
        tags=["parallel", "analysis", "multi-expert"],
        required_inputs=["input_data"],
        workflow_type="concurrent",
        node_count=4,
        nodes=[
            {"name": "Claude Analysis", "node_type": "task", "order_index": 0,
             "agent_config": {"tool": "claude_code", "prompt": "Analyze {input_data} from software perspective"}},
            {"name": "Gemini Analysis", "node_type": "task", "order_index": 1,
             "agent_config": {"tool": "gemini_cli", "prompt": "Analyze {input_data} from research perspective"}},
            {"name": "Ollama Analysis", "node_type": "task", "order_index": 2,
             "agent_config": {"tool": "ollama", "prompt": "Analyze {input_data} from local LLM perspective"}},
            {"name": "Aggregate Results", "node_type": "task", "order_index": 3,
             "agent_config": {"tool": "claude_code", "prompt": "Synthesize all analysis results"}},
        ],
        edges=[],
        default_context={"analysis_depth": "comprehensive"},
    ),
}

# In-memory checkpoint storage (would be a database table in production)
WORKFLOW_CHECKPOINTS: Dict[str, List[CheckpointResponse]] = {}


# =============================================================================
# Template Endpoints
# =============================================================================

@router.get("/templates", response_model=WorkflowTemplateListResponse)
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    current_user: User = Depends(get_current_active_user),
):
    """
    List available workflow templates.
    """
    templates = list(WORKFLOW_TEMPLATES.values())

    # Apply filters
    if category:
        templates = [t for t in templates if t.category == category]
    if tag:
        templates = [t for t in templates if tag in t.tags]

    # Convert to metadata (exclude detailed node/edge info)
    metadata_list = [
        WorkflowTemplateMetadata(
            template_id=t.template_id,
            name=t.name,
            description=t.description,
            category=t.category,
            tags=t.tags,
            required_inputs=t.required_inputs,
            node_count=t.node_count,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in templates
    ]

    return WorkflowTemplateListResponse(
        templates=metadata_list,
        total=len(metadata_list),
    )


@router.get("/templates/{template_id}", response_model=WorkflowTemplateDetail)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get detailed information about a specific template.
    """
    if template_id not in WORKFLOW_TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )

    return WORKFLOW_TEMPLATES[template_id]


@router.post("/from-template", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow_from_template(
    data: WorkflowFromTemplateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new workflow from a template.
    """
    if data.template_id not in WORKFLOW_TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {data.template_id}",
        )

    template = WORKFLOW_TEMPLATES[data.template_id]

    # Validate required inputs
    missing_inputs = [inp for inp in template.required_inputs if inp not in data.input]
    if missing_inputs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required inputs: {', '.join(missing_inputs)}",
        )

    # Create workflow from template
    workflow_name = data.name or f"{template.name} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

    # Merge template default context with user input
    context = {**template.default_context, **data.input}

    workflow = Workflow(
        user_id=current_user.user_id,
        name=workflow_name,
        description=template.description,
        workflow_type=template.workflow_type,
        context=context,
        status=WorkflowStatus.DRAFT.value,
        dag_definition={"template_id": data.template_id},
    )

    db.add(workflow)
    await db.flush()

    # Create nodes from template
    for i, node_config in enumerate(template.nodes):
        # Substitute template variables in prompts
        agent_config = node_config.get("agent_config", {}).copy()
        if "prompt" in agent_config:
            prompt = agent_config["prompt"]
            for key, value in data.input.items():
                prompt = prompt.replace(f"{{{key}}}", str(value))
            agent_config["prompt"] = prompt

        node = WorkflowNode(
            workflow_id=workflow.workflow_id,
            name=node_config["name"],
            node_type=node_config.get("node_type", "task"),
            order_index=node_config.get("order_index", i),
            agent_config=agent_config,
            max_retries=node_config.get("max_retries", 3),
            status=NodeStatus.PENDING.value,
        )
        db.add(node)

    workflow.total_nodes = len(template.nodes)

    await db.commit()
    await db.refresh(workflow)

    logger.info(
        "Workflow created from template",
        workflow_id=str(workflow.workflow_id),
        template_id=data.template_id,
        user_id=str(current_user.user_id),
    )

    return WorkflowResponse(
        **workflow.__dict__,
        progress=workflow.progress,
    )


# =============================================================================
# Checkpoint Endpoints
# =============================================================================

@router.post("/{workflow_id}/checkpoint", response_model=CheckpointResponse, status_code=status.HTTP_201_CREATED)
async def create_checkpoint(
    workflow_id: UUID,
    data: CheckpointCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a manual checkpoint for the workflow.
    """
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes))
        .where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Capture current state
    node_states = {}
    for node in workflow.nodes:
        node_states[str(node.node_id)] = {
            "status": node.status,
            "output": node.output,
            "error": node.error,
            "retry_count": node.retry_count,
            "started_at": node.started_at.isoformat() if node.started_at else None,
            "completed_at": node.completed_at.isoformat() if node.completed_at else None,
        }

    checkpoint = CheckpointResponse(
        checkpoint_id=uuid4(),
        workflow_id=workflow_id,
        name=data.name or f"Checkpoint {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
        description=data.description,
        state={
            "status": workflow.status,
            "context": workflow.context,
            "result": workflow.result,
            "error": workflow.error,
            "completed_nodes": workflow.completed_nodes,
            "total_nodes": workflow.total_nodes,
        },
        node_states=node_states,
        created_at=datetime.utcnow(),
        created_by=current_user.user_id,
    )

    # Store checkpoint
    workflow_id_str = str(workflow_id)
    if workflow_id_str not in WORKFLOW_CHECKPOINTS:
        WORKFLOW_CHECKPOINTS[workflow_id_str] = []
    WORKFLOW_CHECKPOINTS[workflow_id_str].append(checkpoint)

    logger.info(
        "Checkpoint created",
        workflow_id=str(workflow_id),
        checkpoint_id=str(checkpoint.checkpoint_id),
    )

    return checkpoint


@router.get("/{workflow_id}/checkpoints", response_model=CheckpointListResponse)
async def list_checkpoints(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all checkpoints for a workflow.
    """
    # Verify workflow ownership
    result = await db.execute(
        select(Workflow).where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    workflow_id_str = str(workflow_id)
    checkpoints = WORKFLOW_CHECKPOINTS.get(workflow_id_str, [])

    return CheckpointListResponse(
        checkpoints=checkpoints,
        total=len(checkpoints),
    )


@router.post("/{workflow_id}/restore/{checkpoint_id}", response_model=WorkflowResponse)
async def restore_from_checkpoint(
    workflow_id: UUID,
    checkpoint_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Restore workflow state from a checkpoint.
    """
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes))
        .where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Only allow restore on paused or failed workflows
    if workflow.status not in (WorkflowStatus.PAUSED.value, WorkflowStatus.FAILED.value, WorkflowStatus.CANCELLED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot restore workflow with status: {workflow.status}. Must be paused, failed, or cancelled.",
        )

    # Find checkpoint
    workflow_id_str = str(workflow_id)
    checkpoints = WORKFLOW_CHECKPOINTS.get(workflow_id_str, [])
    checkpoint = next((cp for cp in checkpoints if cp.checkpoint_id == checkpoint_id), None)

    if not checkpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkpoint not found",
        )

    # Restore workflow state
    workflow.status = checkpoint.state.get("status", WorkflowStatus.PAUSED.value)
    workflow.context = checkpoint.state.get("context")
    workflow.result = checkpoint.state.get("result")
    workflow.error = checkpoint.state.get("error")
    workflow.completed_nodes = checkpoint.state.get("completed_nodes", 0)

    # Restore node states
    for node in workflow.nodes:
        node_id_str = str(node.node_id)
        if node_id_str in checkpoint.node_states:
            node_state = checkpoint.node_states[node_id_str]
            node.status = node_state.get("status", NodeStatus.PENDING.value)
            node.output = node_state.get("output")
            node.error = node_state.get("error")
            node.retry_count = node_state.get("retry_count", 0)
            # Parse timestamps if present
            if node_state.get("started_at"):
                node.started_at = datetime.fromisoformat(node_state["started_at"])
            if node_state.get("completed_at"):
                node.completed_at = datetime.fromisoformat(node_state["completed_at"])

    await db.commit()
    await db.refresh(workflow)

    logger.info(
        "Workflow restored from checkpoint",
        workflow_id=str(workflow_id),
        checkpoint_id=str(checkpoint_id),
    )

    return WorkflowResponse(
        **workflow.__dict__,
        progress=workflow.progress,
    )


# =============================================================================
# Human Review Endpoint
# =============================================================================

@router.post("/{workflow_id}/nodes/{node_id}/review", response_model=HumanReviewResponse)
async def submit_human_review(
    workflow_id: UUID,
    node_id: UUID,
    data: HumanReviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit human review decision for a node waiting for approval.
    """
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes))
        .where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Find the node
    node = next((n for n in workflow.nodes if n.node_id == node_id), None)

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found in workflow",
        )

    # Verify node is waiting for review
    if node.node_type not in ("wait", "human_review"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Node is not a review node. Type: {node.node_type}",
        )

    if node.status not in (NodeStatus.RUNNING.value, NodeStatus.PENDING.value, "waiting"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Node is not waiting for review. Status: {node.status}",
        )

    # Process review decision
    review_output = {
        "decision": data.decision,
        "comments": data.comments,
        "reviewer_id": str(current_user.user_id),
        "reviewed_at": datetime.utcnow().isoformat(),
    }

    if data.decision == "approve":
        node.status = NodeStatus.COMPLETED.value
        node.completed_at = datetime.utcnow()
        node.output = review_output
        workflow.completed_nodes = (workflow.completed_nodes or 0) + 1

        # If workflow was paused for this review, resume it
        if workflow.status == WorkflowStatus.PAUSED.value:
            workflow.status = WorkflowStatus.RUNNING.value

    elif data.decision == "reject":
        node.status = NodeStatus.FAILED.value
        node.completed_at = datetime.utcnow()
        node.error = data.comments or "Review rejected"
        node.output = review_output

        # Mark workflow as failed or cancelled
        workflow.status = WorkflowStatus.FAILED.value
        workflow.error = f"Review rejected at node: {node.name}"
        workflow.completed_at = datetime.utcnow()

    elif data.decision == "modify":
        if data.modifications:
            # Apply modifications to workflow context
            current_context = workflow.context or {}
            current_context.update(data.modifications)
            workflow.context = current_context

        node.status = NodeStatus.COMPLETED.value
        node.completed_at = datetime.utcnow()
        review_output["modifications"] = data.modifications
        node.output = review_output
        workflow.completed_nodes = (workflow.completed_nodes or 0) + 1

        # Resume workflow if paused
        if workflow.status == WorkflowStatus.PAUSED.value:
            workflow.status = WorkflowStatus.RUNNING.value

    await db.commit()

    logger.info(
        "Human review submitted",
        workflow_id=str(workflow_id),
        node_id=str(node_id),
        decision=data.decision,
        reviewer_id=str(current_user.user_id),
    )

    return HumanReviewResponse(
        node_id=node_id,
        workflow_id=workflow_id,
        decision=data.decision,
        comments=data.comments,
        reviewer_id=current_user.user_id,
        reviewed_at=datetime.utcnow(),
        workflow_status=workflow.status,
    )


# =============================================================================
# Execution Graph Visualization Endpoint
# =============================================================================

@router.get("/{workflow_id}/execution-graph", response_model=ExecutionGraphResponse)
async def get_execution_graph(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get execution graph data for visualization.

    Returns node and edge data formatted for graph visualization libraries.
    """
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Build nodes for visualization
    graph_nodes = []
    current_node = None

    for node in sorted(workflow.nodes, key=lambda n: n.order_index or 0):
        duration = None
        if node.started_at and node.completed_at:
            duration = (node.completed_at - node.started_at).total_seconds()

        # Determine output preview
        output_preview = None
        if node.output:
            output_str = str(node.output)
            output_preview = output_str[:100] + "..." if len(output_str) > 100 else output_str

        graph_node = ExecutionGraphNode(
            node_id=str(node.node_id),
            name=node.name,
            node_type=node.node_type,
            status=node.status,
            order_index=node.order_index or 0,
            started_at=node.started_at,
            completed_at=node.completed_at,
            duration_seconds=duration,
            error=node.error,
            output_preview=output_preview,
        )
        graph_nodes.append(graph_node)

        # Track current running node
        if node.status == NodeStatus.RUNNING.value:
            current_node = str(node.node_id)

    # Build edges for visualization
    graph_edges = []
    completed_node_ids = {str(n.node_id) for n in workflow.nodes if n.status == NodeStatus.COMPLETED.value}

    for edge in workflow.edges:
        executed = str(edge.from_node_id) in completed_node_ids

        graph_edge = ExecutionGraphEdge(
            edge_id=str(edge.edge_id),
            from_node_id=str(edge.from_node_id),
            to_node_id=str(edge.to_node_id),
            label=edge.label,
            executed=executed,
        )
        graph_edges.append(graph_edge)

    # If no explicit edges, create implicit sequential edges
    if not graph_edges and len(graph_nodes) > 1:
        sorted_nodes = sorted(graph_nodes, key=lambda n: n.order_index)
        for i in range(len(sorted_nodes) - 1):
            from_node = sorted_nodes[i]
            to_node = sorted_nodes[i + 1]
            executed = from_node.status == NodeStatus.COMPLETED.value

            graph_edge = ExecutionGraphEdge(
                edge_id=f"implicit-{from_node.node_id}-{to_node.node_id}",
                from_node_id=from_node.node_id,
                to_node_id=to_node.node_id,
                label=None,
                executed=executed,
            )
            graph_edges.append(graph_edge)

    # Determine entry and exit nodes
    entry_node = None
    exit_nodes = []

    if graph_nodes:
        sorted_nodes = sorted(graph_nodes, key=lambda n: n.order_index)
        entry_node = sorted_nodes[0].node_id
        exit_nodes = [sorted_nodes[-1].node_id]

    return ExecutionGraphResponse(
        workflow_id=workflow_id,
        workflow_name=workflow.name,
        workflow_status=workflow.status,
        workflow_type=workflow.workflow_type,
        nodes=graph_nodes,
        edges=graph_edges,
        entry_node=entry_node,
        exit_nodes=exit_nodes,
        progress=workflow.progress,
        total_nodes=workflow.total_nodes or len(graph_nodes),
        completed_nodes=workflow.completed_nodes or 0,
        current_node=current_node,
        started_at=workflow.started_at,
        completed_at=workflow.completed_at,
    )


# =============================================================================
# Existing CRUD Endpoints
# =============================================================================

@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List workflows for the current user.
    """
    query = select(Workflow).where(Workflow.user_id == current_user.user_id)

    if status:
        query = query.where(Workflow.status == status)

    query = query.order_by(Workflow.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    workflows = result.scalars().all()

    # Get total count
    count_query = select(func.count()).select_from(Workflow).where(
        Workflow.user_id == current_user.user_id
    )
    if status:
        count_query = count_query.where(Workflow.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return WorkflowListResponse(
        workflows=[
            WorkflowResponse(
                **w.__dict__,
                progress=w.progress,
            )
            for w in workflows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new workflow.
    """
    workflow = Workflow(
        user_id=current_user.user_id,
        name=data.name,
        description=data.description,
        workflow_type=data.workflow_type,
        context=data.context,
        status=WorkflowStatus.DRAFT.value,
    )

    db.add(workflow)
    await db.flush()

    # Create nodes if provided
    if data.nodes:
        for node_data in data.nodes:
            node = WorkflowNode(
                workflow_id=workflow.workflow_id,
                name=node_data.name,
                node_type=node_data.node_type,
                order_index=node_data.order_index,
                agent_config=node_data.agent_config,
                condition_config=node_data.condition_config,
                dependencies=node_data.dependencies,
                max_retries=node_data.max_retries,
                status=NodeStatus.PENDING.value,
            )
            db.add(node)

        workflow.total_nodes = len(data.nodes)

    # Create edges if provided
    if data.edges:
        for edge_data in data.edges:
            edge = WorkflowEdge(
                workflow_id=workflow.workflow_id,
                from_node_id=edge_data.from_node_id,
                to_node_id=edge_data.to_node_id,
                condition=edge_data.condition,
                label=edge_data.label,
            )
            db.add(edge)

    await db.commit()
    await db.refresh(workflow)

    logger.info(
        "Workflow created",
        workflow_id=str(workflow.workflow_id),
        user_id=str(current_user.user_id),
    )

    return WorkflowResponse(
        **workflow.__dict__,
        progress=workflow.progress,
    )


@router.get("/test/{workflow_id}")
async def get_workflow_test(workflow_id: str):
    """Simple test endpoint."""
    return {"test": "ok", "workflow_id": workflow_id}


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific workflow with nodes and edges.
    """
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Build response dict directly
    response = {
        "workflow_id": str(workflow.workflow_id),
        "user_id": str(workflow.user_id),
        "name": workflow.name,
        "description": workflow.description,
        "workflow_type": workflow.workflow_type,
        "status": workflow.status,
        "dag_definition": workflow.dag_definition,
        "context": workflow.context,
        "result": workflow.result,
        "error": workflow.error,
        "total_nodes": workflow.total_nodes or 0,
        "completed_nodes": workflow.completed_nodes or 0,
        "progress": workflow.progress,
        "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
        "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
        "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
        "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
        "nodes": [],
        "edges": [],
    }

    # Add nodes
    for n in workflow.nodes:
        response["nodes"].append({
            "node_id": str(n.node_id),
            "workflow_id": str(n.workflow_id),
            "name": n.name,
            "node_type": n.node_type,
            "status": n.status,
            "order_index": n.order_index or 0,
            "retry_count": n.retry_count or 0,
            "max_retries": n.max_retries or 3,
        })

    # Add edges
    for e in workflow.edges:
        response["edges"].append({
            "edge_id": str(e.edge_id),
            "from_node_id": str(e.from_node_id),
            "to_node_id": str(e.to_node_id),
        })

    return response


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    data: WorkflowUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a workflow.
    """
    result = await db.execute(
        select(Workflow).where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Only allow updates if workflow is in draft or failed state
    if workflow.status not in (WorkflowStatus.DRAFT.value, WorkflowStatus.FAILED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update workflow with status: {workflow.status}",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workflow, field, value)

    await db.commit()
    await db.refresh(workflow)

    logger.info("Workflow updated", workflow_id=str(workflow_id))

    return WorkflowResponse(
        **workflow.__dict__,
        progress=workflow.progress,
    )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a workflow.
    """
    result = await db.execute(
        select(Workflow).where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    # Don't allow deletion of running workflows
    if workflow.status == WorkflowStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete running workflow",
        )

    # Clean up checkpoints
    workflow_id_str = str(workflow_id)
    if workflow_id_str in WORKFLOW_CHECKPOINTS:
        del WORKFLOW_CHECKPOINTS[workflow_id_str]

    await db.delete(workflow)
    await db.commit()

    logger.info("Workflow deleted", workflow_id=str(workflow_id))

    return None


@router.post("/{workflow_id}/execute", response_model=WorkflowResponse)
async def execute_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start workflow execution.
    """
    from src.services.workflow_engine import get_workflow_engine

    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes))
        .where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    if workflow.status not in (WorkflowStatus.DRAFT.value, WorkflowStatus.FAILED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot execute workflow with status: {workflow.status}",
        )

    if not workflow.nodes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow has no nodes",
        )

    # Reset node statuses
    for node in workflow.nodes:
        node.status = NodeStatus.PENDING.value
        node.started_at = None
        node.completed_at = None
        node.output = None
        node.error = None
        node.retry_count = 0

    workflow.completed_nodes = 0
    workflow.error = None
    workflow.result = None

    await db.commit()

    # Start workflow execution via engine
    engine = get_workflow_engine(db)
    try:
        workflow = await engine.start_workflow(workflow_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    await db.refresh(workflow)

    logger.info("Workflow execution started", workflow_id=str(workflow_id))

    return WorkflowResponse(
        **workflow.__dict__,
        progress=workflow.progress,
    )


@router.post("/{workflow_id}/pause", response_model=WorkflowResponse)
async def pause_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Pause a running workflow.
    """
    result = await db.execute(
        select(Workflow).where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    if workflow.status != WorkflowStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only running workflows can be paused",
        )

    workflow.status = WorkflowStatus.PAUSED.value
    await db.commit()
    await db.refresh(workflow)

    logger.info("Workflow paused", workflow_id=str(workflow_id))

    return WorkflowResponse(
        **workflow.__dict__,
        progress=workflow.progress,
    )


@router.post("/{workflow_id}/resume", response_model=WorkflowResponse)
async def resume_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Resume a paused workflow.
    """
    result = await db.execute(
        select(Workflow).where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    if workflow.status != WorkflowStatus.PAUSED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only paused workflows can be resumed",
        )

    workflow.status = WorkflowStatus.RUNNING.value
    await db.commit()
    await db.refresh(workflow)

    logger.info("Workflow resumed", workflow_id=str(workflow_id))

    # TODO: Trigger async workflow execution via background task or message queue

    return WorkflowResponse(
        **workflow.__dict__,
        progress=workflow.progress,
    )


@router.post("/{workflow_id}/cancel", response_model=WorkflowResponse)
async def cancel_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a workflow.
    """
    result = await db.execute(
        select(Workflow).where(
            Workflow.workflow_id == workflow_id,
            Workflow.user_id == current_user.user_id,
        )
    )
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    if workflow.status in (WorkflowStatus.COMPLETED.value, WorkflowStatus.CANCELLED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel workflow with status: {workflow.status}",
        )

    workflow.status = WorkflowStatus.CANCELLED.value
    workflow.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(workflow)

    logger.info("Workflow cancelled", workflow_id=str(workflow_id))

    return WorkflowResponse(
        **workflow.__dict__,
        progress=workflow.progress,
    )
