"""
Unified database models for the ensimu-space platform.
Merges best features from ensimu-space, AgentSim, and EnsimuAgent.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON, ARRAY, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from app.libs.database import Base

# ============================================================================
# Core User Management
# ============================================================================

class User(Base):
    """Enhanced user management with role-based access"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="engineer", nullable=False)  # engineer, admin, researcher, student
    organization = Column(String(200))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    preferences = Column(JSON, default=dict)

    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"

# ============================================================================
# Project and Simulation Management
# ============================================================================

class Project(Base):
    """Enhanced project management with simulation goals"""
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Simulation configuration
    simulation_goal = Column(Text)  # Natural language description
    physics_type = Column(String(50), default="cfd", nullable=False)  # cfd, structural, thermal, electromagnetic, multi_physics
    domain = Column(String(50), default="engineering", nullable=False)  # engineering, research, academic, industrial
    status = Column(String(50), default="created", nullable=False)  # created, processing, completed, failed

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Preprocessing progress tracking
    geometry_status = Column(String(50), default="pending")  # pending, processing, completed, failed, requires_review
    mesh_status = Column(String(50), default="pending")
    materials_status = Column(String(50), default="pending")
    physics_status = Column(String(50), default="pending")

    # Metadata
    tags = Column(ARRAY(String), default=list)
    project_metadata = Column(JSON, default=dict)

    # Relationships
    user = relationship("User", back_populates="projects")
    uploaded_files = relationship("UploadedFile", back_populates="project", cascade="all, delete-orphan")
    simulations = relationship("Simulation", back_populates="project", cascade="all, delete-orphan")
    workflow_executions = relationship("WorkflowExecution", back_populates="project", cascade="all, delete-orphan")
    ai_sessions = relationship("AISession", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(name='{self.name}', physics_type='{self.physics_type}')>"

class Simulation(Base):
    """Advanced simulation tracking with HPC integration"""
    __tablename__ = "simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String(200), nullable=False)
    status = Column(String(50), default="pending", nullable=False)  # pending, queued, running, completed, failed, cancelled
    progress = Column(Integer, default=0)  # 0-100

    # HPC Integration
    hpc_queue = Column(String(50))  # standard, large, gpu, multi_gpu
    job_id = Column(String(100))  # HPC job identifier
    gpu_count = Column(Integer, default=1)
    node_count = Column(Integer, default=1)
    compute_hours = Column(Float)
    runtime = Column(Integer)  # in seconds

    # Simulation Configuration
    solver_settings = Column(JSON)
    boundary_conditions = Column(JSON)
    material_properties = Column(JSON)
    mesh_quality = Column(JSON)

    # Results
    results = Column(JSON)  # KPIs and analysis results
    convergence_data = Column(JSON)
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    project = relationship("Project", back_populates="simulations")
    reports = relationship("Report", back_populates="simulation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Simulation(name='{self.name}', status='{self.status}')>"

# ============================================================================
# File Management
# ============================================================================

class UploadedFile(Base):
    """Enhanced file management with analysis results"""
    __tablename__ = "uploaded_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    filename = Column(String(200), nullable=False)
    original_filename = Column(String(200), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # cad, mesh, results, report
    file_format = Column(String(20))  # step, iges, stl, etc.
    file_size = Column(Integer)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Analysis results from AI agents
    analysis_results = Column(JSON)
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed

    # File metadata
    checksum = Column(String(64))
    file_metadata = Column(JSON, default=dict)

    # Relationships
    project = relationship("Project", back_populates="uploaded_files")

    def __repr__(self):
        return f"<UploadedFile(filename='{self.filename}', file_type='{self.file_type}')>"

# ============================================================================
# AI Agent System
# ============================================================================

class AISession(Base):
    """Enhanced AI agent sessions with orchestration"""
    __tablename__ = "ai_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    agent_type = Column(String(100), nullable=False)  # geometry, mesh, materials, physics, knowledge, orchestrator
    session_data = Column(JSON)
    status = Column(String(50), default="active", nullable=False)  # active, completed, failed, paused
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Agent-specific data
    agent_version = Column(String(20))
    capabilities = Column(ARRAY(String))
    performance_metrics = Column(JSON)

    # Relationships
    project = relationship("Project", back_populates="ai_sessions")
    sent_communications = relationship("AgentCommunication", foreign_keys="AgentCommunication.sender_agent_id", back_populates="sender_agent")
    received_communications = relationship("AgentCommunication", foreign_keys="AgentCommunication.receiver_agent_id", back_populates="receiver_agent")

    def __repr__(self):
        return f"<AISession(agent_type='{self.agent_type}', status='{self.status}')>"

class AgentCommunication(Base):
    """Agent communication and coordination"""
    __tablename__ = "agent_communications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_agent_id = Column(UUID(as_uuid=True), ForeignKey("ai_sessions.id"))
    receiver_agent_id = Column(UUID(as_uuid=True), ForeignKey("ai_sessions.id"))
    message_type = Column(String(50), nullable=False)  # request, response, notification, error
    message_content = Column(JSON, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    processed = Column(Boolean, default=False, nullable=False)

    # Relationships
    sender_agent = relationship("AISession", foreign_keys=[sender_agent_id], back_populates="sent_communications")
    receiver_agent = relationship("AISession", foreign_keys=[receiver_agent_id], back_populates="received_communications")

    def __repr__(self):
        return f"<AgentCommunication(message_type='{self.message_type}', processed={self.processed})>"

# ============================================================================
# Workflow Management (LangGraph Integration)
# ============================================================================

class WorkflowExecution(Base):
    """LangGraph workflow execution tracking"""
    __tablename__ = "workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_goal = Column(Text, nullable=False)
    workflow_plan = Column(JSON)  # Serialized LangGraph workflow
    current_step = Column(String(100))
    status = Column(String(50), default="running", nullable=False)  # running, paused, completed, failed
    global_context = Column(JSON)  # Shared state between agents
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)

    # Orchestration metadata
    orchestrator_version = Column(String(20))
    execution_metrics = Column(JSON)

    # Relationships
    project = relationship("Project", back_populates="workflow_executions")
    workflow_steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan")
    hitl_checkpoints = relationship("HITLCheckpoint", back_populates="workflow", cascade="all, delete-orphan")
    orchestrator_metrics = relationship("OrchestratorMetrics", back_populates="workflow", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WorkflowExecution(status='{self.status}', current_step='{self.current_step}')>"

class WorkflowStep(Base):
    """Individual workflow steps"""
    __tablename__ = "workflow_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=False)
    step_name = Column(String(100), nullable=False)
    agent_type = Column(String(50), nullable=False)
    step_order = Column(Integer, nullable=False)
    status = Column(String(50), default="pending", nullable=False)  # pending, running, completed, failed, skipped
    input_data = Column(JSON)
    output_data = Column(JSON)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    error_message = Column(Text)

    # Dependencies
    depends_on = Column(ARRAY(UUID))  # Array of step IDs
    parallel_group = Column(String(50))  # For parallel execution

    # Relationships
    workflow = relationship("WorkflowExecution", back_populates="workflow_steps")
    hitl_checkpoints = relationship("HITLCheckpoint", back_populates="step", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WorkflowStep(step_name='{self.step_name}', status='{self.status}')>"

# ============================================================================
# Human-in-the-Loop (HITL) System
# ============================================================================

class HITLCheckpoint(Base):
    """HITL checkpoint management"""
    __tablename__ = "hitl_checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("workflow_steps.id"), nullable=False)
    checkpoint_type = Column(String(50), nullable=False)  # geometry_validation, mesh_approval, material_review
    description = Column(Text)

    # Checkpoint data
    checkpoint_data = Column(JSON)  # Data requiring human review
    required_fields = Column(JSON)  # Fields that must be provided by human
    agent_recommendations = Column(ARRAY(String))

    # Status tracking
    status = Column(String(50), default="pending", nullable=False)  # pending, approved, rejected, modified
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True))
    timeout_at = Column(DateTime(timezone=True))

    # Human response
    human_response = Column(JSON)
    human_feedback = Column(Text)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    workflow = relationship("WorkflowExecution", back_populates="hitl_checkpoints")
    step = relationship("WorkflowStep", back_populates="hitl_checkpoints")
    reviewer = relationship("User")

    def __repr__(self):
        return f"<HITLCheckpoint(checkpoint_type='{self.checkpoint_type}', status='{self.status}')>"

# ============================================================================
# Material Database
# ============================================================================

class MaterialProperty(Base):
    """Enhanced material properties with validation"""
    __tablename__ = "material_properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    category = Column(String(100))  # metal, polymer, ceramic, composite

    # Physical properties
    density = Column(Float)
    youngs_modulus = Column(Float)
    poissons_ratio = Column(Float)
    yield_strength = Column(Float)
    ultimate_strength = Column(Float)
    thermal_conductivity = Column(Float)
    specific_heat = Column(Float)
    thermal_expansion = Column(Float)

    # Additional properties
    properties = Column(JSON)  # Flexible storage for additional properties

    # Validation and source
    data_source = Column(String(200))
    validated = Column(Boolean, default=False, nullable=False)
    validation_standard = Column(String(50))  # ASTM, ISO, DIN, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<MaterialProperty(name='{self.name}', category='{self.category}')>"

# ============================================================================
# Reports & Analytics
# ============================================================================

class Report(Base):
    """AI-generated reports"""
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)  # Markdown content
    report_type = Column(String(50))  # preprocessing, results, analysis, summary
    generated_by = Column(String(50), default="ai")  # ai, user, hybrid

    # File attachments
    pdf_url = Column(String(500))
    attachments = Column(JSON)  # Array of file references

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    version = Column(Integer, default=1)

    # Relationships
    simulation = relationship("Simulation", back_populates="reports")

    def __repr__(self):
        return f"<Report(title='{self.title}', report_type='{self.report_type}')>"

class OrchestratorMetrics(Base):
    """Performance metrics and analytics"""
    __tablename__ = "orchestrator_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"))
    metric_type = Column(String(50), nullable=False)  # performance, accuracy, efficiency, user_satisfaction
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Context
    agent_type = Column(String(50))
    step_name = Column(String(100))
    metrics_metadata = Column(JSON)

    # Relationships
    workflow = relationship("WorkflowExecution", back_populates="orchestrator_metrics")

    def __repr__(self):
        return f"<OrchestratorMetrics(metric_name='{self.metric_name}', value={self.metric_value})>"

# ============================================================================
# Sample Cases & Templates
# ============================================================================

class SampleCase(Base):
    """Sample cases for onboarding and demonstrations"""
    __tablename__ = "sample_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)  # cfd, structural, thermal, electromagnetic
    physics_type = Column(String(50), nullable=False)
    complexity_level = Column(String(20), default="beginner", nullable=False)  # beginner, intermediate, advanced, expert

    # Files and templates
    cad_file_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))
    simulation_template = Column(JSON, nullable=False)

    # Metadata
    expected_runtime = Column(Integer)  # in minutes
    gpu_required = Column(Boolean, default=False, nullable=False)
    tags = Column(ARRAY(String))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<SampleCase(name='{self.name}', category='{self.category}')>"

class WorkflowTemplate(Base):
    """Reusable workflow templates"""
    __tablename__ = "workflow_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # structural, thermal, cfd, multi_physics

    # Template configuration
    template_steps = Column(JSON)  # Template workflow steps
    default_parameters = Column(JSON)  # Default parameters for steps
    required_inputs = Column(JSON)  # Required inputs from user

    # Usage tracking
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_public = Column(Boolean, default=False, nullable=False)

    # Relationships
    creator = relationship("User")

    def __repr__(self):
        return f"<WorkflowTemplate(name='{self.name}', category='{self.category}')>"

# ============================================================================
# Database Indexes for Performance
# ============================================================================

# Core performance indexes
Index('idx_projects_user_id', Project.user_id)
Index('idx_projects_status', Project.status)
Index('idx_projects_physics_type', Project.physics_type)
Index('idx_simulations_project_id', Simulation.project_id)
Index('idx_simulations_status', Simulation.status)
Index('idx_uploaded_files_project_id', UploadedFile.project_id)
Index('idx_uploaded_files_file_type', UploadedFile.file_type)
Index('idx_workflow_executions_project_id', WorkflowExecution.project_id)
Index('idx_workflow_executions_status', WorkflowExecution.status)
Index('idx_workflow_steps_workflow_id', WorkflowStep.workflow_id)
Index('idx_workflow_steps_status', WorkflowStep.status)
Index('idx_hitl_checkpoints_workflow_id', HITLCheckpoint.workflow_id)
Index('idx_hitl_checkpoints_status', HITLCheckpoint.status)
Index('idx_ai_sessions_project_id', AISession.project_id)
Index('idx_ai_sessions_agent_type', AISession.agent_type)
Index('idx_agent_communications_sender', AgentCommunication.sender_agent_id)
Index('idx_agent_communications_receiver', AgentCommunication.receiver_agent_id)
Index('idx_agent_communications_processed', AgentCommunication.processed)
Index('idx_material_properties_category', MaterialProperty.category)
Index('idx_material_properties_validated', MaterialProperty.validated)
Index('idx_reports_simulation_id', Report.simulation_id)
Index('idx_reports_report_type', Report.report_type)
Index('idx_orchestrator_metrics_workflow_id', OrchestratorMetrics.workflow_id)
Index('idx_orchestrator_metrics_metric_type', OrchestratorMetrics.metric_type)
Index('idx_sample_cases_category', SampleCase.category)
Index('idx_sample_cases_complexity', SampleCase.complexity_level)
Index('idx_workflow_templates_category', WorkflowTemplate.category)
Index('idx_workflow_templates_public', WorkflowTemplate.is_public)

# Composite indexes for common queries
Index('idx_projects_user_status', Project.user_id, Project.status)
Index('idx_simulations_project_status', Simulation.project_id, Simulation.status)
Index('idx_workflow_steps_workflow_status', WorkflowStep.workflow_id, WorkflowStep.status)
Index('idx_hitl_checkpoints_workflow_status', HITLCheckpoint.workflow_id, HITLCheckpoint.status)

# Timestamp indexes for time-based queries
Index('idx_projects_created_at', Project.created_at)
Index('idx_simulations_created_at', Simulation.created_at)
Index('idx_workflow_executions_created_at', WorkflowExecution.created_at)
Index('idx_hitl_checkpoints_created_at', HITLCheckpoint.created_at)

# ============================================================================
# Model Validation and Constraints
# ============================================================================

# Add table constraints
Project.__table_args__ = (
    CheckConstraint("physics_type IN ('cfd', 'structural', 'thermal', 'electromagnetic', 'multi_physics')", name='check_physics_type'),
    CheckConstraint("domain IN ('engineering', 'research', 'academic', 'industrial')", name='check_domain'),
    CheckConstraint("status IN ('created', 'processing', 'completed', 'failed')", name='check_project_status'),
)

Simulation.__table_args__ = (
    CheckConstraint("status IN ('pending', 'queued', 'running', 'completed', 'failed', 'cancelled')", name='check_simulation_status'),
    CheckConstraint("progress >= 0 AND progress <= 100", name='check_progress_range'),
    CheckConstraint("gpu_count > 0", name='check_gpu_count'),
    CheckConstraint("node_count > 0", name='check_node_count'),
)

User.__table_args__ = (
    CheckConstraint("role IN ('engineer', 'admin', 'researcher', 'student')", name='check_user_role'),
)

WorkflowExecution.__table_args__ = (
    CheckConstraint("status IN ('running', 'paused', 'completed', 'failed')", name='check_workflow_status'),
)

WorkflowStep.__table_args__ = (
    CheckConstraint("status IN ('pending', 'running', 'completed', 'failed', 'skipped')", name='check_step_status'),
    CheckConstraint("step_order > 0", name='check_step_order'),
)

HITLCheckpoint.__table_args__ = (
    CheckConstraint("status IN ('pending', 'approved', 'rejected', 'modified')", name='check_checkpoint_status'),
)

SampleCase.__table_args__ = (
    CheckConstraint("complexity_level IN ('beginner', 'intermediate', 'advanced', 'expert')", name='check_complexity_level'),
    CheckConstraint("expected_runtime > 0", name='check_expected_runtime'),
)