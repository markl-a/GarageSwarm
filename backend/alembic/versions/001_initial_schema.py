"""Initial schema - Users, Workers, Tasks, Workflows

Revision ID: 001
Revises:
Create Date: 2026-01-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_login', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_username', 'users', ['username'])

    # Workers table
    op.create_table(
        'workers',
        sa.Column('worker_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('machine_id', sa.String(100), nullable=False),
        sa.Column('machine_name', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='offline'),
        sa.Column('system_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tools', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('cpu_percent', sa.Float(), nullable=True),
        sa.Column('memory_percent', sa.Float(), nullable=True),
        sa.Column('disk_percent', sa.Float(), nullable=True),
        sa.Column('last_heartbeat', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('registered_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint("status IN ('online', 'offline', 'busy', 'idle')", name='chk_worker_status'),
        sa.PrimaryKeyConstraint('worker_id'),
        sa.UniqueConstraint('machine_id'),
    )
    op.create_index('ix_workers_status', 'workers', ['status'])
    op.create_index('ix_workers_last_heartbeat', 'workers', ['last_heartbeat'])

    # User-Worker relationship table
    op.create_table(
        'user_workers',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('worker_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('added_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['worker_id'], ['workers.worker_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_workers_user_id', 'user_workers', ['user_id'])
    op.create_index('ix_user_workers_worker_id', 'user_workers', ['worker_id'])

    # Workflows table
    op.create_table(
        'workflows',
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('workflow_type', sa.String(20), nullable=False, server_default='sequential'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('dag_definition', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('total_nodes', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('completed_nodes', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("workflow_type IN ('sequential', 'concurrent', 'graph', 'hierarchical', 'mixture')", name='chk_workflow_type'),
        sa.CheckConstraint("status IN ('draft', 'pending', 'running', 'paused', 'completed', 'failed', 'cancelled')", name='chk_workflow_status'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workflow_id'),
    )
    op.create_index('ix_workflows_user_id', 'workflows', ['user_id'])
    op.create_index('ix_workflows_status', 'workflows', ['status'])

    # Workflow nodes table
    op.create_table(
        'workflow_nodes',
        sa.Column('node_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('node_type', sa.String(20), nullable=False, server_default='task'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('agent_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('condition_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('dependencies', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=True, server_default='3'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("node_type IN ('task', 'condition', 'parallel_start', 'parallel_end', 'wait', 'router', 'director')", name='chk_node_type'),
        sa.CheckConstraint("status IN ('pending', 'ready', 'running', 'completed', 'failed', 'skipped')", name='chk_node_status'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.workflow_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('node_id'),
    )
    op.create_index('ix_workflow_nodes_workflow_id', 'workflow_nodes', ['workflow_id'])
    op.create_index('ix_workflow_nodes_status', 'workflow_nodes', ['status'])

    # Workflow edges table
    op.create_table(
        'workflow_edges',
        sa.Column('edge_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('to_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('condition', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('label', sa.String(100), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.workflow_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_node_id'], ['workflow_nodes.node_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_node_id'], ['workflow_nodes.node_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('edge_id'),
    )
    op.create_index('ix_workflow_edges_workflow_id', 'workflow_edges', ['workflow_id'])

    # Tasks table
    op.create_table(
        'tasks',
        sa.Column('task_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('worker_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tool_preference', sa.String(50), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('task_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'queued', 'assigned', 'running', 'completed', 'failed', 'cancelled')", name='chk_task_status'),
        sa.CheckConstraint('progress >= 0 AND progress <= 100', name='chk_task_progress'),
        sa.CheckConstraint('priority >= 1 AND priority <= 10', name='chk_task_priority'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['worker_id'], ['workers.worker_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.workflow_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('task_id'),
    )
    op.create_index('ix_tasks_user_id', 'tasks', ['user_id'])
    op.create_index('ix_tasks_worker_id', 'tasks', ['worker_id'])
    op.create_index('ix_tasks_workflow_id', 'tasks', ['workflow_id'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])
    op.create_index('ix_tasks_created_at', 'tasks', ['created_at'])


def downgrade() -> None:
    op.drop_table('tasks')
    op.drop_table('workflow_edges')
    op.drop_table('workflow_nodes')
    op.drop_table('workflows')
    op.drop_table('user_workers')
    op.drop_table('workers')
    op.drop_table('users')
