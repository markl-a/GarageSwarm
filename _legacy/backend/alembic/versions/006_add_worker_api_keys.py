"""Add worker_api_keys table

Revision ID: 006
Revises: 005
Create Date: 2026-01-08

Adds the worker_api_keys table for worker authentication.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    """Add worker_api_keys table"""
    op.create_table(
        'worker_api_keys',
        sa.Column(
            'key_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text('gen_random_uuid()'),
            comment='Unique API key identifier'
        ),
        sa.Column(
            'worker_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Associated worker ID'
        ),
        sa.Column(
            'api_key_hash',
            sa.String(255),
            nullable=False,
            comment='Bcrypt-hashed API key'
        ),
        sa.Column(
            'key_prefix',
            sa.String(12),
            nullable=False,
            comment='Key prefix for identification (e.g., wk_a1b2c3d4)'
        ),
        sa.Column(
            'description',
            sa.TEXT(),
            nullable=True,
            comment='Optional description'
        ),
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default='true',
            comment='Whether key is active'
        ),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text('now()'),
            comment='Key creation time'
        ),
        sa.Column(
            'expires_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Key expiration time (null = never expires)'
        ),
        sa.Column(
            'last_used_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Last usage time'
        ),
        sa.Column(
            'revoked_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment='Revocation time'
        ),
        sa.Column(
            'created_by',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='User who created this key'
        ),
        sa.PrimaryKeyConstraint('key_id'),
        sa.ForeignKeyConstraint(
            ['worker_id'],
            ['workers.worker_id'],
            name='fk_api_key_worker',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['created_by'],
            ['users.user_id'],
            name='fk_api_key_creator',
            ondelete='SET NULL'
        ),
    )

    # Create indexes for faster lookups
    op.create_index(
        'ix_worker_api_keys_worker_id',
        'worker_api_keys',
        ['worker_id']
    )
    op.create_index(
        'ix_worker_api_keys_key_prefix',
        'worker_api_keys',
        ['key_prefix']
    )
    op.create_index(
        'ix_worker_api_keys_is_active',
        'worker_api_keys',
        ['is_active']
    )


def downgrade():
    """Remove worker_api_keys table"""
    op.drop_index('ix_worker_api_keys_is_active', table_name='worker_api_keys')
    op.drop_index('ix_worker_api_keys_key_prefix', table_name='worker_api_keys')
    op.drop_index('ix_worker_api_keys_worker_id', table_name='worker_api_keys')
    op.drop_table('worker_api_keys')
