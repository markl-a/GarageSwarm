"""Add workflow templates tables

Revision ID: 005
Revises: 004
Create Date: 2025-12-15

This migration adds tables for workflow templates:
- workflow_templates: Reusable task templates
- template_steps: Individual steps within templates
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """Add workflow templates tables"""

    # Create workflow_templates table
    op.create_table(
        'workflow_templates',
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='Unique template identifier'),
        sa.Column('name', sa.String(255), nullable=False, comment='Template name (unique)'),
        sa.Column('description', sa.TEXT(), nullable=False, comment='Template description'),
        sa.Column('category', sa.String(50), nullable=False, comment='Template category: development | testing | documentation | devops | review'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Whether template is active and available for use'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false', comment='System template (cannot be deleted by users)'),
        sa.Column('default_checkpoint_frequency', sa.String(20), nullable=False, server_default='medium', comment='Default checkpoint frequency: low | medium | high'),
        sa.Column('default_privacy_level', sa.String(20), nullable=False, server_default='normal', comment='Default privacy level: normal | sensitive'),
        sa.Column('default_tool_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Default AI tools: ["claude_code", "gemini_cli"]'),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Template tags: ["api", "backend", "python"]'),
        sa.Column('estimated_duration', sa.Integer(), nullable=True, comment='Estimated completion time in minutes'),
        sa.Column('complexity_level', sa.Integer(), nullable=True, comment='Complexity rating: 1 (simple) to 5 (complex)'),
        sa.Column('template_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Additional template metadata'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0', comment='Number of times template has been used'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True, comment='Template creator (null for system templates)'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), comment='Template creation time'),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), comment='Last update time'),
        sa.PrimaryKeyConstraint('template_id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], name='fk_template_user'),
        sa.UniqueConstraint('name', name='uq_template_name'),
        sa.CheckConstraint("category IN ('development', 'testing', 'documentation', 'devops', 'review')", name='chk_template_category'),
        sa.CheckConstraint("default_checkpoint_frequency IN ('low', 'medium', 'high')", name='chk_template_checkpoint_frequency'),
        sa.CheckConstraint("default_privacy_level IN ('normal', 'sensitive')", name='chk_template_privacy_level'),
        sa.CheckConstraint("complexity_level IS NULL OR (complexity_level >= 1 AND complexity_level <= 5)", name='chk_template_complexity'),
        sa.CheckConstraint("estimated_duration IS NULL OR estimated_duration > 0", name='chk_template_duration'),
    )

    # Create indexes for workflow_templates
    op.create_index('ix_workflow_templates_name', 'workflow_templates', ['name'], unique=True)
    op.create_index('ix_workflow_templates_category', 'workflow_templates', ['category'])
    op.create_index('ix_workflow_templates_is_active', 'workflow_templates', ['is_active'])
    op.create_index('ix_workflow_templates_created_by', 'workflow_templates', ['created_by'])
    op.create_index('ix_workflow_templates_created_at', 'workflow_templates', ['created_at'])

    # Create template_steps table
    op.create_table(
        'template_steps',
        sa.Column('step_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'), comment='Unique step identifier'),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Parent template ID'),
        sa.Column('name', sa.String(255), nullable=False, comment='Step name'),
        sa.Column('description', sa.TEXT(), nullable=False, comment='Step description'),
        sa.Column('step_order', sa.Integer(), nullable=False, comment='Step execution order (1-based)'),
        sa.Column('step_type', sa.String(50), nullable=False, comment='Step type: code_generation | code_review | code_fix | test | documentation | analysis | deployment'),
        sa.Column('depends_on', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Dependency step IDs: [uuid1, uuid2] or step orders: [1, 2]'),
        sa.Column('recommended_tool', sa.String(50), nullable=True, comment='Recommended AI tool: claude_code | gemini_cli | ollama'),
        sa.Column('complexity', sa.Integer(), nullable=True, comment='Complexity rating: 1 (simple) to 5 (complex)'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0', comment='Priority score (higher = more urgent)'),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='true', comment='Whether this step is required or optional'),
        sa.Column('is_parallel', sa.Boolean(), nullable=False, server_default='false', comment='Whether this step can run in parallel with siblings'),
        sa.Column('step_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Additional step configuration and metadata'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), comment='Step creation time'),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), comment='Last update time'),
        sa.PrimaryKeyConstraint('step_id'),
        sa.ForeignKeyConstraint(['template_id'], ['workflow_templates.template_id'], name='fk_step_template', ondelete='CASCADE'),
        sa.CheckConstraint("step_type IN ('code_generation', 'code_review', 'code_fix', 'test', 'documentation', 'analysis', 'deployment')", name='chk_step_type'),
        sa.CheckConstraint("complexity IS NULL OR (complexity >= 1 AND complexity <= 5)", name='chk_step_complexity'),
        sa.CheckConstraint("step_order >= 1", name='chk_step_order'),
    )

    # Create indexes for template_steps
    op.create_index('ix_template_steps_template_id', 'template_steps', ['template_id'])


def downgrade():
    """Remove workflow templates tables"""

    # Drop template_steps indexes and table
    op.drop_index('ix_template_steps_template_id', table_name='template_steps')
    op.drop_table('template_steps')

    # Drop workflow_templates indexes and table
    op.drop_index('ix_workflow_templates_created_at', table_name='workflow_templates')
    op.drop_index('ix_workflow_templates_created_by', table_name='workflow_templates')
    op.drop_index('ix_workflow_templates_is_active', table_name='workflow_templates')
    op.drop_index('ix_workflow_templates_category', table_name='workflow_templates')
    op.drop_index('ix_workflow_templates_name', table_name='workflow_templates')
    op.drop_table('workflow_templates')
