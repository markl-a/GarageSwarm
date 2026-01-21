"""Add api_key and is_active fields to workers table

Revision ID: 002_add_worker_api_key
Revises: 001_initial_schema
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_worker_api_key'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add api_key column to workers table
    op.add_column(
        'workers',
        sa.Column('api_key', sa.String(64), unique=True, nullable=True)
    )

    # Add is_active column to workers table
    op.add_column(
        'workers',
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False)
    )

    # Create index on api_key for faster lookups
    op.create_index('ix_workers_api_key', 'workers', ['api_key'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_workers_api_key', table_name='workers')
    op.drop_column('workers', 'is_active')
    op.drop_column('workers', 'api_key')
