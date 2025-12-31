"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2025-11-12 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for Multi-Agent on the Web platform"""

    # Create users table
    op.create_table(
        "users",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("username", sa.String(50), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_login", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("idx_users_email", "users", ["email"])

    # Create workers table
    op.create_table(
        "workers",
        sa.Column(
            "worker_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("machine_id", sa.String(100), unique=True, nullable=False),
        sa.Column("machine_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="offline"),
        sa.Column("system_info", postgresql.JSONB, nullable=False),
        sa.Column("tools", postgresql.JSONB, nullable=False),
        sa.Column("cpu_percent", sa.Float, nullable=True),
        sa.Column("memory_percent", sa.Float, nullable=True),
        sa.Column("disk_percent", sa.Float, nullable=True),
        sa.Column("last_heartbeat", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "registered_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('online', 'offline', 'busy')", name="chk_worker_status"
        ),
    )
    op.create_index("idx_workers_status", "workers", ["status"])
    op.create_index("idx_workers_last_heartbeat", "workers", ["last_heartbeat"])

    # Create tasks table
    op.create_table(
        "tasks",
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.user_id"),
            nullable=True,
        ),
        sa.Column("description", sa.TEXT, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer, default=0, nullable=False),
        sa.Column(
            "checkpoint_frequency",
            sa.String(20),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "privacy_level", sa.String(20), nullable=False, server_default="normal"
        ),
        sa.Column("tool_preferences", postgresql.JSONB, nullable=True),
        sa.Column("task_metadata", postgresql.JSONB, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'initializing', 'in_progress', 'checkpoint', 'completed', 'failed', 'cancelled')",
            name="chk_task_status",
        ),
        sa.CheckConstraint(
            "progress >= 0 AND progress <= 100", name="chk_task_progress"
        ),
        sa.CheckConstraint(
            "checkpoint_frequency IN ('low', 'medium', 'high')",
            name="chk_checkpoint_frequency",
        ),
        sa.CheckConstraint(
            "privacy_level IN ('normal', 'sensitive')", name="chk_privacy_level"
        ),
    )
    op.create_index("idx_tasks_user", "tasks", ["user_id"])
    op.create_index("idx_tasks_status", "tasks", ["status"])
    op.create_index("idx_tasks_created_at", "tasks", [sa.text("created_at DESC")])
    op.create_index(
        "idx_tasks_status_version", "tasks", ["task_id", "status", "version"]
    )

    # Create subtasks table
    op.create_table(
        "subtasks",
        sa.Column(
            "subtask_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.task_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.TEXT, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Integer, default=0, nullable=False),
        sa.Column(
            "dependencies",
            postgresql.JSONB,
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("recommended_tool", sa.String(50), nullable=True),
        sa.Column(
            "assigned_worker",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workers.worker_id"),
            nullable=True,
        ),
        sa.Column("assigned_tool", sa.String(50), nullable=True),
        sa.Column("complexity", sa.Integer, nullable=True),
        sa.Column("priority", sa.Integer, default=0, nullable=False),
        sa.Column("output", postgresql.JSONB, nullable=True),
        sa.Column("error", sa.TEXT, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'queued', 'in_progress', 'completed', 'failed', 'correcting')",
            name="chk_subtask_status",
        ),
        sa.CheckConstraint(
            "progress >= 0 AND progress <= 100", name="chk_subtask_progress"
        ),
        sa.CheckConstraint(
            "complexity >= 1 AND complexity <= 5", name="chk_subtask_complexity"
        ),
    )
    op.create_index("idx_subtasks_task", "subtasks", ["task_id"])
    op.create_index("idx_subtasks_status", "subtasks", ["status"])
    op.create_index("idx_subtasks_worker", "subtasks", ["assigned_worker"])

    # Create checkpoints table
    op.create_table(
        "checkpoints",
        sa.Column(
            "checkpoint_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.task_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="pending_review"
        ),
        sa.Column("subtasks_completed", postgresql.JSONB, nullable=False),
        sa.Column("user_decision", sa.String(20), nullable=True),
        sa.Column("decision_notes", sa.TEXT, nullable=True),
        sa.Column(
            "triggered_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending_review', 'approved', 'corrected', 'rejected')",
            name="chk_checkpoint_status",
        ),
        sa.CheckConstraint(
            "user_decision IS NULL OR user_decision IN ('approve', 'correct', 'reject')",
            name="chk_user_decision",
        ),
    )
    op.create_index("idx_checkpoints_task", "checkpoints", ["task_id"])
    op.create_index("idx_checkpoints_status", "checkpoints", ["status"])

    # Create corrections table
    op.create_table(
        "corrections",
        sa.Column(
            "correction_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "checkpoint_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("checkpoints.checkpoint_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subtask_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subtasks.subtask_id"),
            nullable=False,
        ),
        sa.Column("correction_type", sa.String(20), nullable=False),
        sa.Column("guidance", sa.TEXT, nullable=False),
        sa.Column(
            "reference_files",
            postgresql.JSONB,
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("result", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer, default=0, nullable=False),
        sa.Column("apply_to_future", sa.Boolean, default=False, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "correction_type IN ('wrong_approach', 'incomplete', 'bug', 'style', 'missing_feature', 'other')",
            name="chk_correction_type",
        ),
        sa.CheckConstraint(
            "result IN ('pending', 'success', 'failed')", name="chk_correction_result"
        ),
    )
    op.create_index("idx_corrections_checkpoint", "corrections", ["checkpoint_id"])
    op.create_index("idx_corrections_subtask", "corrections", ["subtask_id"])

    # Create evaluations table
    op.create_table(
        "evaluations",
        sa.Column(
            "evaluation_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "subtask_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subtasks.subtask_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_quality", sa.Numeric(3, 1), nullable=True),
        sa.Column("completeness", sa.Numeric(3, 1), nullable=True),
        sa.Column("security", sa.Numeric(3, 1), nullable=True),
        sa.Column("architecture", sa.Numeric(3, 1), nullable=True),
        sa.Column("testability", sa.Numeric(3, 1), nullable=True),
        sa.Column("overall_score", sa.Numeric(3, 1), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column(
            "evaluated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "code_quality IS NULL OR (code_quality >= 0 AND code_quality <= 10)",
            name="chk_code_quality",
        ),
        sa.CheckConstraint(
            "completeness IS NULL OR (completeness >= 0 AND completeness <= 10)",
            name="chk_completeness",
        ),
        sa.CheckConstraint(
            "security IS NULL OR (security >= 0 AND security <= 10)",
            name="chk_security",
        ),
        sa.CheckConstraint(
            "architecture IS NULL OR (architecture >= 0 AND architecture <= 10)",
            name="chk_architecture",
        ),
        sa.CheckConstraint(
            "testability IS NULL OR (testability >= 0 AND testability <= 10)",
            name="chk_testability",
        ),
        sa.CheckConstraint(
            "overall_score IS NULL OR (overall_score >= 0 AND overall_score <= 10)",
            name="chk_overall_score",
        ),
    )
    op.create_index("idx_evaluations_subtask", "evaluations", ["subtask_id"])
    op.create_index("idx_evaluations_overall_score", "evaluations", ["overall_score"])

    # Create activity_logs table
    op.create_table(
        "activity_logs",
        sa.Column("log_id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.task_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "subtask_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subtasks.subtask_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "worker_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workers.worker_id"),
            nullable=True,
        ),
        sa.Column("level", sa.String(10), nullable=False),
        sa.Column("message", sa.TEXT, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_activity_logs_task", "activity_logs", ["task_id"])
    op.create_index(
        "idx_activity_logs_created_at", "activity_logs", [sa.text("created_at DESC")]
    )


def downgrade() -> None:
    """Drop all tables"""
    op.drop_table("activity_logs")
    op.drop_table("evaluations")
    op.drop_table("corrections")
    op.drop_table("checkpoints")
    op.drop_table("subtasks")
    op.drop_table("tasks")
    op.drop_table("workers")
    op.drop_table("users")
