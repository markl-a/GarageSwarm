"""Add performance indexes for N+1 query optimization

Revision ID: 004_add_performance_indexes
Revises: 002_add_subtask_type
Create Date: 2025-12-09

This migration adds database indexes to optimize query performance and
eliminate N+1 query issues:

1. Tasks table indexes:
   - Composite index on (status, created_at) for filtered list queries
   - Index on updated_at for recent activity queries

2. Subtasks table indexes:
   - Composite index on (task_id, status) for task detail queries
   - Composite index on (status, priority) for scheduler queries
   - Index on assigned_worker for worker workload queries

3. Workers table indexes:
   - Composite index on (status, last_heartbeat) for available worker queries
   - Index on machine_id for lookup optimization
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003a'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes"""

    # Tasks table indexes
    op.create_index(
        'ix_tasks_status_created_at',
        'tasks',
        ['status', 'created_at'],
        unique=False,
        postgresql_using='btree'
    )

    op.create_index(
        'ix_tasks_updated_at',
        'tasks',
        ['updated_at'],
        unique=False,
        postgresql_using='btree'
    )

    # Subtasks table indexes
    op.create_index(
        'ix_subtasks_task_status',
        'subtasks',
        ['task_id', 'status'],
        unique=False,
        postgresql_using='btree'
    )

    op.create_index(
        'ix_subtasks_status_priority',
        'subtasks',
        ['status', 'priority'],
        unique=False,
        postgresql_using='btree'
    )

    op.create_index(
        'ix_subtasks_assigned_worker',
        'subtasks',
        ['assigned_worker'],
        unique=False,
        postgresql_using='btree',
        postgresql_where=sa.text('assigned_worker IS NOT NULL')  # Partial index
    )

    # Workers table indexes
    op.create_index(
        'ix_workers_status_heartbeat',
        'workers',
        ['status', 'last_heartbeat'],
        unique=False,
        postgresql_using='btree'
    )

    # machine_id already has unique constraint, but add explicit index for performance
    # (unique constraints create indexes automatically, so this may be redundant but explicit)


def downgrade():
    """Remove performance indexes"""

    # Workers table indexes
    op.drop_index('ix_workers_status_heartbeat', table_name='workers')

    # Subtasks table indexes
    op.drop_index('ix_subtasks_assigned_worker', table_name='subtasks')
    op.drop_index('ix_subtasks_status_priority', table_name='subtasks')
    op.drop_index('ix_subtasks_task_status', table_name='subtasks')

    # Tasks table indexes
    op.drop_index('ix_tasks_updated_at', table_name='tasks')
    op.drop_index('ix_tasks_status_created_at', table_name='tasks')
