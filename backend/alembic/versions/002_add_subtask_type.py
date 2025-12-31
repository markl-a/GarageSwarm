"""Add subtask_type field for review/fix workflows

Revision ID: 002
Revises: 001
Create Date: 2025-12-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add subtask_type column to subtasks table"""

    # Add subtask_type column
    op.add_column(
        "subtasks",
        sa.Column(
            "subtask_type",
            sa.String(50),
            nullable=True,
            comment="Subtask type: code_generation | code_review | code_fix | test | documentation"
        )
    )

    # Add index for subtask_type
    op.create_index(
        "idx_subtasks_type",
        "subtasks",
        ["subtask_type"]
    )

    # Add check constraint for valid subtask types
    op.create_check_constraint(
        "chk_subtask_type",
        "subtasks",
        "subtask_type IS NULL OR subtask_type IN ('code_generation', 'code_review', 'code_fix', 'test', 'documentation', 'analysis', 'deployment')"
    )

    # Set default value for existing records (they are all code_generation by default)
    op.execute(
        """
        UPDATE subtasks
        SET subtask_type = 'code_generation'
        WHERE subtask_type IS NULL
        """
    )


def downgrade() -> None:
    """Remove subtask_type column from subtasks table"""

    # Drop check constraint
    op.drop_constraint("chk_subtask_type", "subtasks", type_="check")

    # Drop index
    op.drop_index("idx_subtasks_type", table_name="subtasks")

    # Drop column
    op.drop_column("subtasks", "subtask_type")
