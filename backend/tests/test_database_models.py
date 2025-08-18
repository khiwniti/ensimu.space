"""
Unit tests for SQLAlchemy database models.
Tests model creation, validation, relationships, and constraints.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import uuid

from app.libs.cae_models import (
    Base, Project, UploadedFile, WorkflowExecution, WorkflowStep,
    HITLCheckpoint, OrchestratorMetrics, AgentMetrics
)


@pytest.mark.unit
class TestDatabaseModels:
    """Test cases for database models"""

    @pytest.fixture(scope="function")
    def db_engine(self):
        """Create in-memory SQLite database for testing"""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture(scope="function")
    def db_session(self, db_engine):
        """Create database session for testing"""
        Session = sessionmaker(bind=db_engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def sample_project_data(self):
        """Sample project data for testing"""
        return {
            "name": "Test Aerodynamics Project",
            "description": "Testing external aerodynamics simulation",
            "project_type": "cfd",
            "created_by": "test_user_001"
        }

    @pytest.fixture
    def sample_workflow_data(self):
        """Sample workflow data for testing"""
        return {
            "user_goal": "Analyze airflow over wing geometry",
            "workflow_plan": {
                "steps": ["geometry", "mesh", "materials", "physics"],
                "physics_type": "cfd"
            },
            "current_step": "geometry_processing",
            "status": "running",
            "global_context": {"iteration": 1},
            "orchestrator_version": "2.0"
        }


@pytest.mark.unit
class TestProjectModel:
    """Test cases for Project model"""

    def test_project_creation(self, db_session, sample_project_data):
        """Test creating a new project"""
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()

        assert project.id is not None
        assert project.name == sample_project_data["name"]
        assert project.created_at is not None
        assert project.updated_at is not None

    def test_project_required_fields(self, db_session):
        """Test project creation with missing required fields"""
        # Missing name should raise error
        with pytest.raises(IntegrityError):
            project = Project(description="Test project")
            db_session.add(project)
            db_session.commit()

    def test_project_relationships(self, db_session, sample_project_data):
        """Test project relationships with other models"""
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()

        # Test uploaded files relationship
        uploaded_file = UploadedFile(
            project_id=str(project.id),
            filename="test.step",
            file_path="/tmp/test.step",
            file_type="cad",
            file_format="STEP",
            file_size_bytes=1024
        )
        db_session.add(uploaded_file)
        db_session.commit()

        # Refresh project to load relationships
        db_session.refresh(project)
        assert len(project.uploaded_files) == 1
        assert project.uploaded_files[0].filename == "test.step"

    def test_project_update_timestamp(self, db_session, sample_project_data):
        """Test that updated_at timestamp changes on modification"""
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()
        
        original_updated_at = project.updated_at
        
        # Update project
        project.description = "Updated description"
        db_session.commit()
        
        assert project.updated_at > original_updated_at


@pytest.mark.unit
class TestUploadedFileModel:
    """Test cases for UploadedFile model"""

    def test_uploaded_file_creation(self, db_session, sample_project_data):
        """Test creating an uploaded file"""
        # Create project first
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()

        # Create uploaded file
        file_data = {
            "project_id": str(project.id),
            "filename": "wing_geometry.step",
            "file_path": "/uploads/wing_geometry.step",
            "file_type": "cad",
            "file_format": "STEP",
            "file_size_bytes": 2048576
        }
        
        uploaded_file = UploadedFile(**file_data)
        db_session.add(uploaded_file)
        db_session.commit()

        assert uploaded_file.id is not None
        assert uploaded_file.filename == "wing_geometry.step"
        assert uploaded_file.upload_status == "pending"  # Default value

    def test_uploaded_file_status_validation(self, db_session, sample_project_data):
        """Test file status validation"""
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()

        uploaded_file = UploadedFile(
            project_id=str(project.id),
            filename="test.step",
            file_path="/tmp/test.step",
            file_type="cad",
            file_format="STEP",
            file_size_bytes=1024,
            upload_status="completed"
        )
        db_session.add(uploaded_file)
        db_session.commit()

        assert uploaded_file.upload_status == "completed"

    def test_uploaded_file_foreign_key_constraint(self, db_session):
        """Test foreign key constraint for project_id"""
        # Try to create file with non-existent project_id
        uploaded_file = UploadedFile(
            project_id="non-existent-id",
            filename="test.step",
            file_path="/tmp/test.step",
            file_type="cad",
            file_format="STEP",
            file_size_bytes=1024
        )
        db_session.add(uploaded_file)
        
        # This should raise an integrity error due to foreign key constraint
        with pytest.raises(IntegrityError):
            db_session.commit()


@pytest.mark.unit
class TestWorkflowExecutionModel:
    """Test cases for WorkflowExecution model"""

    def test_workflow_execution_creation(self, db_session, sample_project_data, sample_workflow_data):
        """Test creating a workflow execution"""
        # Create project first
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()

        # Create workflow execution
        workflow_data = {
            **sample_workflow_data,
            "project_id": str(project.id)
        }
        
        workflow = WorkflowExecution(**workflow_data)
        db_session.add(workflow)
        db_session.commit()

        assert workflow.id is not None
        assert workflow.project_id == str(project.id)
        assert workflow.status == "running"
        assert workflow.created_at is not None

    def test_workflow_execution_json_fields(self, db_session, sample_project_data):
        """Test JSON field storage and retrieval"""
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()

        complex_plan = {
            "steps": ["geometry", "mesh", "materials", "physics"],
            "physics_type": "cfd",
            "advanced_settings": {
                "parallel_execution": True,
                "error_recovery": True,
                "quality_thresholds": {"mesh": 0.8, "geometry": 0.9}
            }
        }

        workflow = WorkflowExecution(
            project_id=str(project.id),
            user_goal="Complex CFD analysis",
            workflow_plan=complex_plan,
            current_step="geometry_processing",
            status="running",
            orchestrator_version="2.0"
        )
        db_session.add(workflow)
        db_session.commit()

        # Refresh and verify JSON data
        db_session.refresh(workflow)
        assert workflow.workflow_plan["physics_type"] == "cfd"
        assert workflow.workflow_plan["advanced_settings"]["parallel_execution"] is True

    def test_workflow_execution_relationships(self, db_session, sample_project_data, sample_workflow_data):
        """Test workflow execution relationships"""
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()

        workflow = WorkflowExecution(
            project_id=str(project.id),
            **sample_workflow_data
        )
        db_session.add(workflow)
        db_session.commit()

        # Add workflow steps
        step1 = WorkflowStep(
            workflow_id=str(workflow.id),
            step_name="geometry_processing",
            agent_type="geometry",
            step_order=1,
            status="completed",
            input_data={"files": ["test.step"]},
            output_data={"analysis": "completed"},
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=120
        )
        db_session.add(step1)
        db_session.commit()

        # Refresh workflow and check relationships
        db_session.refresh(workflow)
        assert len(workflow.workflow_steps) == 1
        assert workflow.workflow_steps[0].step_name == "geometry_processing"


@pytest.mark.unit
class TestWorkflowStepModel:
    """Test cases for WorkflowStep model"""

    def test_workflow_step_creation(self, db_session, sample_project_data, sample_workflow_data):
        """Test creating a workflow step"""
        # Create project and workflow
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()

        workflow = WorkflowExecution(
            project_id=str(project.id),
            **sample_workflow_data
        )
        db_session.add(workflow)
        db_session.commit()

        # Create workflow step
        step = WorkflowStep(
            workflow_id=str(workflow.id),
            step_name="mesh_generation",
            agent_type="mesh",
            step_order=2,
            status="running",
            input_data={"geometry_analysis": {"volume": 1.0}},
            started_at=datetime.utcnow()
        )
        db_session.add(step)
        db_session.commit()

        assert step.id is not None
        assert step.workflow_id == str(workflow.id)
        assert step.step_name == "mesh_generation"
        assert step.status == "running"

    def test_workflow_step_duration_calculation(self, db_session, sample_project_data, sample_workflow_data):
        """Test duration calculation for workflow steps"""
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()

        workflow = WorkflowExecution(
            project_id=str(project.id),
            **sample_workflow_data
        )
        db_session.add(workflow)
        db_session.commit()

        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=5)

        step = WorkflowStep(
            workflow_id=str(workflow.id),
            step_name="physics_setup",
            agent_type="physics",
            step_order=4,
            status="completed",
            input_data={},
            output_data={"setup": "complete"},
            started_at=start_time,
            completed_at=end_time,
            duration_seconds=300
        )
        db_session.add(step)
        db_session.commit()

        assert step.duration_seconds == 300


@pytest.mark.unit
class TestHITLCheckpointModel:
    """Test cases for HITLCheckpoint model"""

    def test_hitl_checkpoint_creation(self, db_session, sample_project_data, sample_workflow_data):
        """Test creating a HITL checkpoint"""
        # Create project and workflow
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()

        workflow = WorkflowExecution(
            project_id=str(project.id),
            **sample_workflow_data
        )
        db_session.add(workflow)
        db_session.commit()

        # Create HITL checkpoint
        checkpoint = HITLCheckpoint(
            workflow_id=str(workflow.id),
            step_id="step_001",
            checkpoint_type="preprocessing_review",
            description="Review preprocessing results before simulation",
            checkpoint_data={
                "geometry_analysis": {"quality": "good"},
                "mesh_recommendations": {"elements": 100000}
            },
            agent_recommendations=[
                "Geometry quality is acceptable",
                "Mesh density is appropriate for CFD analysis"
            ],
            status="pending",
            timeout_at=datetime.utcnow() + timedelta(hours=1)
        )
        db_session.add(checkpoint)
        db_session.commit()

        assert checkpoint.id is not None
        assert checkpoint.status == "pending"
        assert len(checkpoint.agent_recommendations) == 2

    def test_hitl_checkpoint_response(self, db_session, sample_project_data, sample_workflow_data):
        """Test HITL checkpoint response handling"""
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()

        workflow = WorkflowExecution(
            project_id=str(project.id),
            **sample_workflow_data
        )
        db_session.add(workflow)
        db_session.commit()

        checkpoint = HITLCheckpoint(
            workflow_id=str(workflow.id),
            step_id="step_001",
            checkpoint_type="mesh_approval",
            description="Approve mesh quality",
            checkpoint_data={"mesh_quality": 0.85},
            agent_recommendations=["Mesh quality is good"],
            status="pending"
        )
        db_session.add(checkpoint)
        db_session.commit()

        # Simulate human response
        checkpoint.status = "approved"
        checkpoint.human_feedback = "Mesh looks good, proceed with simulation"
        checkpoint.human_response = {"approved": True}
        checkpoint.reviewer_id = "user_001"
        checkpoint.responded_at = datetime.utcnow()
        db_session.commit()

        assert checkpoint.status == "approved"
        assert checkpoint.human_feedback is not None
        assert checkpoint.responded_at is not None


@pytest.mark.unit
class TestMetricsModels:
    """Test cases for metrics models"""

    def test_orchestrator_metrics_creation(self, db_session, sample_project_data, sample_workflow_data):
        """Test creating orchestrator metrics"""
        project = Project(**sample_project_data)
        db_session.add(project)
        db_session.commit()

        workflow = WorkflowExecution(
            project_id=str(project.id),
            **sample_workflow_data
        )
        db_session.add(workflow)
        db_session.commit()

        metrics = OrchestratorMetrics(
            workflow_id=str(workflow.id),
            total_execution_time=3600.5,
            agent_coordination_time=120.0,
            hitl_wait_time=1800.0,
            iteration_count=2,
            error_count=1,
            performance_metrics={
                "memory_usage_mb": 512,
                "cpu_utilization": 0.75,
                "network_io_mb": 10.5
            }
        )
        db_session.add(metrics)
        db_session.commit()

        assert metrics.id is not None
        assert metrics.total_execution_time == 3600.5
        assert metrics.performance_metrics["memory_usage_mb"] == 512

    def test_agent_metrics_creation(self, db_session):
        """Test creating agent metrics"""
        metrics = AgentMetrics(
            agent_id="geometry_agent_001",
            agent_type="geometry",
            execution_time=45.2,
            confidence_score=0.88,
            success_rate=0.95,
            error_count=1,
            performance_data={
                "files_processed": 3,
                "analysis_accuracy": 0.92,
                "processing_speed": "fast"
            }
        )
        db_session.add(metrics)
        db_session.commit()

        assert metrics.id is not None
        assert metrics.agent_type == "geometry"
        assert metrics.confidence_score == 0.88
