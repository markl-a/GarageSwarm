"""
Workflow Template Models

Reusable workflow templates for common development tasks
"""

from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, TEXT, TIMESTAMP, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class WorkflowTemplate(Base):
    """Workflow template model - reusable task templates"""

    __tablename__ = "workflow_templates"

    # Primary key
    template_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique template identifier",
    )

    # Template details
    name = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Template name (unique)",
    )

    description = Column(
        TEXT,
        nullable=False,
        comment="Template description",
    )

    category = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Template category: development | testing | documentation | devops | review",
    )

    # Template configuration
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether template is active and available for use",
    )

    is_system = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="System template (cannot be deleted by users)",
    )

    # Default task settings
    default_checkpoint_frequency = Column(
        String(20),
        nullable=False,
        default="medium",
        comment="Default checkpoint frequency: low | medium | high",
    )

    default_privacy_level = Column(
        String(20),
        nullable=False,
        default="normal",
        comment="Default privacy level: normal | sensitive",
    )

    default_tool_preferences = Column(
        JSONB,
        nullable=True,
        comment='Default AI tools: ["claude_code", "gemini_cli"]',
    )

    # Template metadata
    tags = Column(
        JSONB,
        nullable=True,
        comment='Template tags: ["api", "backend", "python"]',
    )

    estimated_duration = Column(
        Integer,
        nullable=True,
        comment="Estimated completion time in minutes",
    )

    complexity_level = Column(
        Integer,
        nullable=True,
        comment="Complexity rating: 1 (simple) to 5 (complex)",
    )

    template_metadata = Column(
        JSONB,
        nullable=True,
        comment="Additional template metadata",
    )

    # Usage statistics
    usage_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of times template has been used",
    )

    # Foreign key to user (for custom templates)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=True,
        index=True,
        comment="Template creator (null for system templates)",
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        index=True,
        comment="Template creation time",
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update time",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "category IN ('development', 'testing', 'documentation', 'devops', 'review')",
            name="chk_template_category",
        ),
        CheckConstraint(
            "default_checkpoint_frequency IN ('low', 'medium', 'high')",
            name="chk_template_checkpoint_frequency",
        ),
        CheckConstraint(
            "default_privacy_level IN ('normal', 'sensitive')",
            name="chk_template_privacy_level",
        ),
        CheckConstraint(
            "complexity_level IS NULL OR (complexity_level >= 1 AND complexity_level <= 5)",
            name="chk_template_complexity",
        ),
        CheckConstraint(
            "estimated_duration IS NULL OR estimated_duration > 0",
            name="chk_template_duration",
        ),
    )

    # Relationships
    user = relationship("User", back_populates="templates")
    steps = relationship(
        "TemplateStep",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateStep.step_order",
    )

    def __repr__(self):
        return f"<WorkflowTemplate(template_id={self.template_id}, name={self.name}, category={self.category})>"


class TemplateStep(Base):
    """Template step model - individual steps within a workflow template"""

    __tablename__ = "template_steps"

    # Primary key
    step_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
        comment="Unique step identifier",
    )

    # Foreign key to template
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_templates.template_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent template ID",
    )

    # Step details
    name = Column(
        String(255),
        nullable=False,
        comment="Step name",
    )

    description = Column(
        TEXT,
        nullable=False,
        comment="Step description",
    )

    step_order = Column(
        Integer,
        nullable=False,
        comment="Step execution order (1-based)",
    )

    # Step type
    step_type = Column(
        String(50),
        nullable=False,
        comment="Step type: code_generation | code_review | code_fix | test | documentation | analysis | deployment",
    )

    # Dependencies
    depends_on = Column(
        JSONB,
        nullable=True,
        comment="Dependency step IDs: [uuid1, uuid2] or step orders: [1, 2]",
    )

    # Tool recommendation
    recommended_tool = Column(
        String(50),
        nullable=True,
        comment="Recommended AI tool: claude_code | gemini_cli | ollama",
    )

    # Complexity & Priority
    complexity = Column(
        Integer,
        nullable=True,
        comment="Complexity rating: 1 (simple) to 5 (complex)",
    )

    priority = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Priority score (higher = more urgent)",
    )

    # Step configuration
    is_required = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this step is required or optional",
    )

    is_parallel = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this step can run in parallel with siblings",
    )

    # Step metadata
    step_metadata = Column(
        JSONB,
        nullable=True,
        comment="Additional step configuration and metadata",
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Step creation time",
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update time",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "step_type IN ('code_generation', 'code_review', 'code_fix', 'test', 'documentation', 'analysis', 'deployment')",
            name="chk_step_type",
        ),
        CheckConstraint(
            "complexity IS NULL OR (complexity >= 1 AND complexity <= 5)",
            name="chk_step_complexity",
        ),
        CheckConstraint(
            "step_order >= 1",
            name="chk_step_order",
        ),
    )

    # Relationships
    template = relationship("WorkflowTemplate", back_populates="steps")

    def __repr__(self):
        return f"<TemplateStep(step_id={self.step_id}, name={self.name}, step_order={self.step_order})>"
