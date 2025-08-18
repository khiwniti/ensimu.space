"""unified_database_schema

Revision ID: 002
Revises: 001
Create Date: 2025-01-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create unified database schema for ensimu-space platform"""
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('organization', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('preferences', sa.JSON(), nullable=True),
        sa.CheckConstraint("role IN ('engineer', 'admin', 'researcher', 'student')", name='check_user_role'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_index('idx_users_username', 'users', ['username'], unique=False)
    op.create_index('idx_users_email', 'users', ['email'], unique=False)
    
    # Create projects table
    op.create_table('projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('simulation_goal', sa.Text(), nullable=True),
        sa.Column('physics_type', sa.String(length=50), nullable=False),
        sa.Column('domain', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('geometry_status', sa.String(length=50), nullable=True),
        sa.Column('mesh_status', sa.String(length=50), nullable=True),
        sa.Column('materials_status', sa.String(length=50), nullable=True),
        sa.Column('physics_status', sa.String(length=50), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('project_metadata', sa.JSON(), nullable=True),
        sa.CheckConstraint("physics_type IN ('cfd', 'structural', 'thermal', 'electromagnetic', 'multi_physics')", name='check_physics_type'),
        sa.CheckConstraint("domain IN ('engineering', 'research', 'academic', 'industrial')", name='check_domain'),
        sa.CheckConstraint("status IN ('created', 'processing', 'completed', 'failed')", name='check_project_status'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_projects_user_id', 'projects', ['user_id'], unique=False)
    op.create_index('idx_projects_status', 'projects', ['status'], unique=False)
    op.create_index('idx_projects_physics_type', 'projects', ['physics_type'], unique=False)
    op.create_index('idx_projects_user_status', 'projects', ['user_id', 'status'], unique=False)
    op.create_index('idx_projects_created_at', 'projects', ['created_at'], unique=False)
    
    # Create simulations table
    op.create_table('simulations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('hpc_queue', sa.String(length=50), nullable=True),
        sa.Column('job_id', sa.String(length=100), nullable=True),
        sa.Column('gpu_count', sa.Integer(), nullable=True),
        sa.Column('node_count', sa.Integer(), nullable=True),
        sa.Column('compute_hours', sa.Float(), nullable=True),
        sa.Column('runtime', sa.Integer(), nullable=True),
        sa.Column('solver_settings', sa.JSON(), nullable=True),
        sa.Column('boundary_conditions', sa.JSON(), nullable=True),
        sa.Column('material_properties', sa.JSON(), nullable=True),
        sa.Column('mesh_quality', sa.JSON(), nullable=True),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('convergence_data', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'queued', 'running', 'completed', 'failed', 'cancelled')", name='check_simulation_status'),
        sa.CheckConstraint('progress >= 0 AND progress <= 100', name='check_progress_range'),
        sa.CheckConstraint('gpu_count > 0', name='check_gpu_count'),
        sa.CheckConstraint('node_count > 0', name='check_node_count'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_simulations_project_id', 'simulations', ['project_id'], unique=False)
    op.create_index('idx_simulations_status', 'simulations', ['status'], unique=False)
    op.create_index('idx_simulations_project_status', 'simulations', ['project_id', 'status'], unique=False)
    op.create_index('idx_simulations_created_at', 'simulations', ['created_at'], unique=False)
    
    # Create uploaded_files table
    op.create_table('uploaded_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=200), nullable=False),
        sa.Column('original_filename', sa.String(length=200), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_format', sa.String(length=20), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('analysis_results', sa.JSON(), nullable=True),
        sa.Column('processing_status', sa.String(length=50), nullable=True),
        sa.Column('checksum', sa.String(length=64), nullable=True),
        sa.Column('file_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_uploaded_files_project_id', 'uploaded_files', ['project_id'], unique=False)
    op.create_index('idx_uploaded_files_file_type', 'uploaded_files', ['file_type'], unique=False)
    
    # Create ai_sessions table
    op.create_table('ai_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.String(length=100), nullable=False),
        sa.Column('session_data', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('agent_version', sa.String(length=20), nullable=True),
        sa.Column('capabilities', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('performance_metrics', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_ai_sessions_project_id', 'ai_sessions', ['project_id'], unique=False)
    op.create_index('idx_ai_sessions_agent_type', 'ai_sessions', ['agent_type'], unique=False)
    
    # Create workflow_executions table
    op.create_table('workflow_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_goal', sa.Text(), nullable=False),
        sa.Column('workflow_plan', sa.JSON(), nullable=True),
        sa.Column('current_step', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('global_context', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('orchestrator_version', sa.String(length=20), nullable=True),
        sa.Column('execution_metrics', sa.JSON(), nullable=True),
        sa.CheckConstraint("status IN ('running', 'paused', 'completed', 'failed')", name='check_workflow_status'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_workflow_executions_project_id', 'workflow_executions', ['project_id'], unique=False)
    op.create_index('idx_workflow_executions_status', 'workflow_executions', ['status'], unique=False)
    op.create_index('idx_workflow_executions_created_at', 'workflow_executions', ['created_at'], unique=False)

    # Create workflow_steps table
    op.create_table('workflow_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_name', sa.String(length=100), nullable=False),
        sa.Column('agent_type', sa.String(length=50), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('output_data', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('depends_on', postgresql.ARRAY(postgresql.UUID()), nullable=True),
        sa.Column('parallel_group', sa.String(length=50), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'running', 'completed', 'failed', 'skipped')", name='check_step_status'),
        sa.CheckConstraint('step_order > 0', name='check_step_order'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflow_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_workflow_steps_workflow_id', 'workflow_steps', ['workflow_id'], unique=False)
    op.create_index('idx_workflow_steps_status', 'workflow_steps', ['status'], unique=False)
    op.create_index('idx_workflow_steps_workflow_status', 'workflow_steps', ['workflow_id', 'status'], unique=False)

    # Create hitl_checkpoints table
    op.create_table('hitl_checkpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('checkpoint_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('checkpoint_data', sa.JSON(), nullable=True),
        sa.Column('required_fields', sa.JSON(), nullable=True),
        sa.Column('agent_recommendations', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timeout_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('human_response', sa.JSON(), nullable=True),
        sa.Column('human_feedback', sa.Text(), nullable=True),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'modified')", name='check_checkpoint_status'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['step_id'], ['workflow_steps.id'], ),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflow_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_hitl_checkpoints_workflow_id', 'hitl_checkpoints', ['workflow_id'], unique=False)
    op.create_index('idx_hitl_checkpoints_status', 'hitl_checkpoints', ['status'], unique=False)
    op.create_index('idx_hitl_checkpoints_workflow_status', 'hitl_checkpoints', ['workflow_id', 'status'], unique=False)
    op.create_index('idx_hitl_checkpoints_created_at', 'hitl_checkpoints', ['created_at'], unique=False)

    # Create agent_communications table
    op.create_table('agent_communications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('receiver_agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('message_type', sa.String(length=50), nullable=False),
        sa.Column('message_content', sa.JSON(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('processed', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['receiver_agent_id'], ['ai_sessions.id'], ),
        sa.ForeignKeyConstraint(['sender_agent_id'], ['ai_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_agent_communications_sender', 'agent_communications', ['sender_agent_id'], unique=False)
    op.create_index('idx_agent_communications_receiver', 'agent_communications', ['receiver_agent_id'], unique=False)
    op.create_index('idx_agent_communications_processed', 'agent_communications', ['processed'], unique=False)

    # Create material_properties table
    op.create_table('material_properties',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('density', sa.Float(), nullable=True),
        sa.Column('youngs_modulus', sa.Float(), nullable=True),
        sa.Column('poissons_ratio', sa.Float(), nullable=True),
        sa.Column('yield_strength', sa.Float(), nullable=True),
        sa.Column('ultimate_strength', sa.Float(), nullable=True),
        sa.Column('thermal_conductivity', sa.Float(), nullable=True),
        sa.Column('specific_heat', sa.Float(), nullable=True),
        sa.Column('thermal_expansion', sa.Float(), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('data_source', sa.String(length=200), nullable=True),
        sa.Column('validated', sa.Boolean(), nullable=False),
        sa.Column('validation_standard', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_material_properties_category', 'material_properties', ['category'], unique=False)
    op.create_index('idx_material_properties_validated', 'material_properties', ['validated'], unique=False)

    # Create reports table
    op.create_table('reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('report_type', sa.String(length=50), nullable=True),
        sa.Column('generated_by', sa.String(length=50), nullable=True),
        sa.Column('pdf_url', sa.String(length=500), nullable=True),
        sa.Column('attachments', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_reports_simulation_id', 'reports', ['simulation_id'], unique=False)
    op.create_index('idx_reports_report_type', 'reports', ['report_type'], unique=False)

    # Create orchestrator_metrics table
    op.create_table('orchestrator_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('metric_unit', sa.String(length=20), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('agent_type', sa.String(length=50), nullable=True),
        sa.Column('step_name', sa.String(length=100), nullable=True),
        sa.Column('metrics_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflow_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_orchestrator_metrics_workflow_id', 'orchestrator_metrics', ['workflow_id'], unique=False)
    op.create_index('idx_orchestrator_metrics_metric_type', 'orchestrator_metrics', ['metric_type'], unique=False)

    # Create sample_cases table
    op.create_table('sample_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('physics_type', sa.String(length=50), nullable=False),
        sa.Column('complexity_level', sa.String(length=20), nullable=False),
        sa.Column('cad_file_url', sa.String(length=500), nullable=False),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('simulation_template', sa.JSON(), nullable=False),
        sa.Column('expected_runtime', sa.Integer(), nullable=True),
        sa.Column('gpu_required', sa.Boolean(), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.CheckConstraint("complexity_level IN ('beginner', 'intermediate', 'advanced', 'expert')", name='check_complexity_level'),
        sa.CheckConstraint('expected_runtime > 0', name='check_expected_runtime'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sample_cases_category', 'sample_cases', ['category'], unique=False)
    op.create_index('idx_sample_cases_complexity', 'sample_cases', ['complexity_level'], unique=False)

    # Create workflow_templates table
    op.create_table('workflow_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('template_steps', sa.JSON(), nullable=True),
        sa.Column('default_parameters', sa.JSON(), nullable=True),
        sa.Column('required_inputs', sa.JSON(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_workflow_templates_category', 'workflow_templates', ['category'], unique=False)
    op.create_index('idx_workflow_templates_public', 'workflow_templates', ['is_public'], unique=False)


def downgrade() -> None:
    """Drop unified database schema"""
    # Drop tables in reverse order of creation (respecting foreign key constraints)
    op.drop_table('workflow_templates')
    op.drop_table('sample_cases')
    op.drop_table('orchestrator_metrics')
    op.drop_table('reports')
    op.drop_table('material_properties')
    op.drop_table('agent_communications')
    op.drop_table('hitl_checkpoints')
    op.drop_table('workflow_steps')
    op.drop_table('workflow_executions')
    op.drop_table('ai_sessions')
    op.drop_table('uploaded_files')
    op.drop_table('simulations')
    op.drop_table('projects')
    op.drop_table('users')
