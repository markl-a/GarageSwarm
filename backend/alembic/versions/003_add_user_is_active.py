"""Add is_active field to users table

Revision ID: 003_add_user_is_active
Revises: 002_add_subtask_type
Create Date: 2025-01-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003a'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_active column to users table"""
    # Add is_active column with default True
    op.add_column('users', sa.Column('is_active', sa.Boolean(),
                                     nullable=False,
                                     server_default='true',
                                     comment='Whether user account is active'))


def downgrade() -> None:
    """Remove is_active column from users table"""
    op.drop_column('users', 'is_active')
