"""Add proposals and proposal_votes tables for multi-agent voting

Revision ID: 003
Revises: 002
Create Date: 2025-12-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create proposals and proposal_votes tables for multi-agent voting system"""

    # Create proposals table
    op.create_table(
        "proposals",
        sa.Column(
            "proposal_id",
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
        sa.Column(
            "worker_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workers.worker_id"),
            nullable=False,
        ),
        sa.Column("content", sa.TEXT, nullable=False),
        sa.Column("evaluation_score", sa.Float, nullable=True),
        sa.Column("votes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
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
        sa.CheckConstraint(
            "status IN ('pending', 'selected', 'rejected')",
            name="chk_proposal_status",
        ),
        sa.CheckConstraint(
            "evaluation_score IS NULL OR (evaluation_score >= 0 AND evaluation_score <= 10)",
            name="chk_evaluation_score",
        ),
        sa.CheckConstraint(
            "votes >= 0",
            name="chk_votes_non_negative",
        ),
    )
    op.create_index("idx_proposals_subtask", "proposals", ["subtask_id"])
    op.create_index("idx_proposals_worker", "proposals", ["worker_id"])
    op.create_index("idx_proposals_status", "proposals", ["status"])
    op.create_index("idx_proposals_created_at", "proposals", [sa.text("created_at DESC")])

    # Create proposal_votes table
    op.create_table(
        "proposal_votes",
        sa.Column(
            "vote_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "proposal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("proposals.proposal_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "voter_worker_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workers.worker_id"),
            nullable=False,
        ),
        sa.Column("vote_value", sa.Integer, nullable=False, server_default="1"),
        sa.Column("reasoning", sa.TEXT, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "vote_value IN (-1, 0, 1)",
            name="chk_vote_value",
        ),
    )
    op.create_index("idx_proposal_votes_proposal", "proposal_votes", ["proposal_id"])
    op.create_index("idx_proposal_votes_voter", "proposal_votes", ["voter_worker_id"])
    op.create_index("idx_proposal_votes_created_at", "proposal_votes", [sa.text("created_at DESC")])

    # Create unique constraint to ensure one vote per worker per proposal
    op.create_unique_constraint(
        "uq_proposal_votes_proposal_worker",
        "proposal_votes",
        ["proposal_id", "voter_worker_id"],
    )


def downgrade() -> None:
    """Drop proposals and proposal_votes tables"""
    op.drop_table("proposal_votes")
    op.drop_table("proposals")
