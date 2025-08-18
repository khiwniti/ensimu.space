"""
Unit tests for LangGraph workflow components.
Tests state management, node execution, routing logic, and HITL functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import json

from app.libs.langgraph_workflow import (
    SimulationState, WorkflowStatus, DatabaseStatePersistence,
    HITLCheckpointManager, WorkflowNodeExecutor, WorkflowRouter,
    SimulationPreprocessingWorkflow
)
from app.libs.cae_models import WorkflowExecution, WorkflowStep, HITLCheckpoint


@pytest.mark.unit
class TestSimulationState:
    """Test cases for SimulationState TypedDict"""

    @pytest.fixture
    def sample_simulation_state(self):
        """Sample simulation state for testing"""
        return SimulationState(
            project_id="test_project_001",
            workflow_id="workflow_001",
            user_goal="Test CFD simulation",
            physics_type="cfd",
            cad_files=[
                {
                    "id": "file_001",
                    "filename": "wing.step",
                    "file_type": "cad",
                    "file_format": "STEP"
                }
            ],
            current_file=None,
            geometry_status="pending",
            mesh_status="pending",
            materials_status="pending",
            physics_status="pending",
            geometry_analysis=None,
            mesh_recommendations=None,
            material_assignments=None,
            physics_setup=None,
            current_step="initialization",
            completed_steps=[],
            failed_steps=[],
            hitl_checkpoints=[],
            mesh_quality_metrics=None,
            convergence_criteria=None,
            validation_results=None,
            errors=[],
            warnings=[],
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            iteration_count=0,
            max_iterations=3
        )

    def test_simulation_state_structure(self, sample_simulation_state):
        """Test SimulationState structure and required fields"""
        assert sample_simulation_state["project_id"] == "test_project_001"
        assert sample_simulation_state["physics_type"] == "cfd"
        assert sample_simulation_state["current_step"] == "initialization"
        assert sample_simulation_state["iteration_count"] == 0
        assert isinstance(sample_simulation_state["cad_files"], list)
        assert isinstance(sample_simulation_state["completed_steps"], list)

    def test_simulation_state_status_values(self, sample_simulation_state):
        """Test valid status values for simulation state"""
        valid_statuses = ["pending", "processing", "completed", "failed", "requires_review"]
        
        for status in valid_statuses:
            sample_simulation_state["geometry_status"] = status
            assert sample_simulation_state["geometry_status"] in valid_statuses


@pytest.mark.unit
class TestDatabaseStatePersistence:
    """Test cases for DatabaseStatePersistence"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return Mock()

    @pytest.fixture
    def state_persistence(self, mock_db_session):
        """Create DatabaseStatePersistence instance"""
        return DatabaseStatePersistence(mock_db_session)

    @pytest.fixture
    def sample_state(self, sample_simulation_state):
        """Sample state for testing"""
        return sample_simulation_state

    @pytest.mark.asyncio
    async def test_save_state_success(self, state_persistence, sample_state, mock_db_session):
        """Test successful state saving"""
        # Mock workflow query
        mock_workflow = Mock()
        mock_workflow.id = sample_state["workflow_id"]
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_workflow

        result = await state_persistence.save_state(sample_state)

        assert result is True
        assert mock_workflow.current_step == sample_state["current_step"]
        assert mock_workflow.global_context == dict(sample_state)
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_state_workflow_not_found(self, state_persistence, sample_state, mock_db_session):
        """Test state saving when workflow not found"""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        result = await state_persistence.save_state(sample_state)

        assert result is False
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_state_success(self, state_persistence, sample_state, mock_db_session):
        """Test successful state loading"""
        mock_workflow = Mock()
        mock_workflow.global_context = dict(sample_state)
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_workflow

        loaded_state = await state_persistence.load_state(sample_state["workflow_id"])

        assert loaded_state is not None
        assert loaded_state["project_id"] == sample_state["project_id"]
        assert loaded_state["workflow_id"] == sample_state["workflow_id"]

    @pytest.mark.asyncio
    async def test_create_workflow_step(self, state_persistence, mock_db_session):
        """Test creating workflow step"""
        mock_step = Mock()
        mock_step.id = "step_001"
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None

        with patch('app.libs.langgraph_workflow.WorkflowStep', return_value=mock_step):
            step_id = await state_persistence.create_workflow_step(
                workflow_id="workflow_001",
                step_name="geometry_processing",
                agent_type="geometry",
                step_order=1,
                input_data={"files": ["test.step"]}
            )

        assert step_id == "step_001"
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()


@pytest.mark.unit
class TestHITLCheckpointManager:
    """Test cases for HITLCheckpointManager"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return Mock()

    @pytest.fixture
    def hitl_manager(self, mock_db_session):
        """Create HITLCheckpointManager instance"""
        return HITLCheckpointManager(mock_db_session)

    @pytest.mark.asyncio
    async def test_create_checkpoint(self, hitl_manager, mock_db_session):
        """Test creating HITL checkpoint"""
        mock_checkpoint = Mock()
        mock_checkpoint.id = "checkpoint_001"
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None

        with patch('app.libs.langgraph_workflow.HITLCheckpoint', return_value=mock_checkpoint):
            checkpoint_id = await hitl_manager.create_checkpoint(
                workflow_id="workflow_001",
                step_id="step_001",
                checkpoint_type="preprocessing_review",
                checkpoint_data={"analysis": "complete"},
                agent_recommendations=["Proceed with simulation"],
                timeout_minutes=60
            )

        assert checkpoint_id == "checkpoint_001"
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pending_checkpoints(self, hitl_manager, mock_db_session):
        """Test getting pending checkpoints"""
        mock_checkpoint = Mock()
        mock_checkpoint.id = "checkpoint_001"
        mock_checkpoint.checkpoint_type = "preprocessing_review"
        mock_checkpoint.description = "Review required"
        mock_checkpoint.checkpoint_data = {"data": "test"}
        mock_checkpoint.agent_recommendations = ["Recommendation 1"]
        mock_checkpoint.created_at = datetime.utcnow()
        mock_checkpoint.timeout_at = datetime.utcnow() + timedelta(hours=1)

        mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_checkpoint]

        checkpoints = await hitl_manager.get_pending_checkpoints("workflow_001")

        assert len(checkpoints) == 1
        assert checkpoints[0]["checkpoint_id"] == "checkpoint_001"
        assert checkpoints[0]["checkpoint_type"] == "preprocessing_review"

    @pytest.mark.asyncio
    async def test_respond_to_checkpoint(self, hitl_manager, mock_db_session):
        """Test responding to HITL checkpoint"""
        mock_checkpoint = Mock()
        mock_checkpoint.id = "checkpoint_001"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_checkpoint

        result = await hitl_manager.respond_to_checkpoint(
            checkpoint_id="checkpoint_001",
            approved=True,
            human_feedback="Looks good",
            reviewer_id="user_001"
        )

        assert result is True
        assert mock_checkpoint.status == "approved"
        assert mock_checkpoint.human_feedback == "Looks good"
        mock_db_session.commit.assert_called_once()


@pytest.mark.unit
class TestWorkflowNodeExecutor:
    """Test cases for WorkflowNodeExecutor"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return Mock()

    @pytest.fixture
    def node_executor(self, mock_db_session):
        """Create WorkflowNodeExecutor instance"""
        return WorkflowNodeExecutor(mock_db_session)

    @pytest.fixture
    def sample_state(self, sample_simulation_state):
        """Sample state for testing"""
        return sample_simulation_state

    @pytest.mark.asyncio
    async def test_geometry_processing_node_success(self, node_executor, sample_state):
        """Test successful geometry processing node execution"""
        # Mock agent factory and geometry agent
        mock_agent = AsyncMock()
        mock_response = Mock()
        mock_response.success = True
        mock_response.data = {
            "geometry_metrics": {"volume": 1.0},
            "confidence_score": 0.85
        }
        mock_agent.process_request.return_value = mock_response

        with patch.object(node_executor.agent_factory, 'create_agent', return_value=mock_agent):
            with patch.object(node_executor.state_persistence, 'create_workflow_step', return_value="step_001"):
                with patch.object(node_executor.state_persistence, 'update_workflow_step', return_value=True):
                    with patch.object(node_executor.state_persistence, 'save_state', return_value=True):
                        result_state = await node_executor.geometry_processing_node(sample_state)

        assert result_state["geometry_status"] == "completed"
        assert result_state["geometry_analysis"] is not None
        assert "geometry_processing" in result_state["completed_steps"]

    @pytest.mark.asyncio
    async def test_geometry_processing_node_failure(self, node_executor, sample_state):
        """Test geometry processing node failure handling"""
        # Mock agent failure
        mock_agent = AsyncMock()
        mock_response = Mock()
        mock_response.success = False
        mock_response.error_message = "Processing failed"
        mock_response.data = {}
        mock_agent.process_request.return_value = mock_response

        with patch.object(node_executor.agent_factory, 'create_agent', return_value=mock_agent):
            with patch.object(node_executor.state_persistence, 'create_workflow_step', return_value="step_001"):
                with patch.object(node_executor.state_persistence, 'update_workflow_step', return_value=True):
                    with patch.object(node_executor.state_persistence, 'save_state', return_value=True):
                        result_state = await node_executor.geometry_processing_node(sample_state)

        assert result_state["geometry_status"] == "failed"
        assert "geometry_processing" in result_state["failed_steps"]
        assert len(result_state["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validation_node(self, node_executor, sample_state):
        """Test validation node execution"""
        # Set up state with completed preprocessing
        sample_state["geometry_analysis"] = {"confidence_score": 0.85}
        sample_state["mesh_recommendations"] = {"confidence_score": 0.80}
        sample_state["material_assignments"] = {"confidence_score": 0.90}
        sample_state["physics_setup"] = {"confidence_score": 0.88}

        with patch.object(node_executor, '_validate_preprocessing_results') as mock_validate:
            mock_validate.return_value = {
                "overall_status": "passed",
                "component_validations": {},
                "warnings": [],
                "errors": []
            }
            with patch.object(node_executor.state_persistence, 'save_state', return_value=True):
                result_state = await node_executor.validation_node(sample_state)

        assert result_state["validation_results"]["overall_status"] == "passed"
        assert "validation" in result_state["completed_steps"]


@pytest.mark.unit
class TestWorkflowRouter:
    """Test cases for WorkflowRouter"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return Mock()

    @pytest.fixture
    def workflow_router(self, mock_db_session):
        """Create WorkflowRouter instance"""
        return WorkflowRouter(mock_db_session)

    @pytest.fixture
    def sample_state(self, sample_simulation_state):
        """Sample state for testing"""
        return sample_simulation_state

    @pytest.mark.asyncio
    async def test_route_from_geometry_success(self, workflow_router, sample_state):
        """Test routing from successful geometry processing"""
        sample_state["current_step"] = "geometry_processing"
        sample_state["geometry_status"] = "completed"
        sample_state["geometry_analysis"] = {
            "quality_metrics": {"mesh_readiness_score": 0.85}
        }

        next_step = await workflow_router.route_next_step(sample_state)
        assert next_step == "mesh_generation"

    @pytest.mark.asyncio
    async def test_route_from_geometry_low_quality(self, workflow_router, sample_state):
        """Test routing from geometry processing with low quality"""
        sample_state["current_step"] = "geometry_processing"
        sample_state["geometry_status"] = "completed"
        sample_state["geometry_analysis"] = {
            "quality_metrics": {"mesh_readiness_score": 0.5}
        }

        next_step = await workflow_router.route_next_step(sample_state)
        assert next_step == "geometry_processing"  # Iterate on geometry

    @pytest.mark.asyncio
    async def test_route_from_validation_success(self, workflow_router, sample_state):
        """Test routing from successful validation"""
        sample_state["current_step"] = "validation"
        sample_state["validation_results"] = {"overall_status": "passed"}

        next_step = await workflow_router.route_next_step(sample_state)
        assert next_step == "hitl_checkpoint"

    @pytest.mark.asyncio
    async def test_route_from_validation_failure(self, workflow_router, sample_state):
        """Test routing from failed validation"""
        sample_state["current_step"] = "validation"
        sample_state["validation_results"] = {
            "overall_status": "failed",
            "component_validations": {
                "geometry": {"passed": False}
            }
        }

        next_step = await workflow_router.route_next_step(sample_state)
        assert next_step == "geometry_processing"  # Cycle back to geometry

    @pytest.mark.asyncio
    async def test_max_iterations_limit(self, workflow_router, sample_state):
        """Test maximum iterations limit"""
        sample_state["current_step"] = "geometry_processing"
        sample_state["iteration_count"] = 3
        sample_state["max_iterations"] = 3

        next_step = await workflow_router.route_next_step(sample_state)
        assert next_step == "hitl_checkpoint"  # Force human intervention


@pytest.mark.unit
class TestSimulationPreprocessingWorkflow:
    """Test cases for SimulationPreprocessingWorkflow"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return Mock()

    @pytest.fixture
    def workflow(self, mock_db_session):
        """Create SimulationPreprocessingWorkflow instance"""
        return SimulationPreprocessingWorkflow(mock_db_session)

    @pytest.mark.asyncio
    async def test_start_workflow(self, workflow, mock_db_session):
        """Test starting a new workflow"""
        mock_workflow_execution = Mock()
        mock_workflow_execution.id = "workflow_001"
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None

        with patch('app.libs.langgraph_workflow.WorkflowExecution', return_value=mock_workflow_execution):
            with patch.object(workflow.state_persistence, 'save_state', return_value=True):
                with patch('asyncio.create_task') as mock_create_task:
                    workflow_id = await workflow.start_workflow(
                        project_id="project_001",
                        user_goal="Test CFD simulation",
                        physics_type="cfd",
                        cad_files=[{"id": "file_001", "filename": "test.step"}]
                    )

        assert workflow_id == "workflow_001"
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_workflow_status(self, workflow, mock_db_session):
        """Test getting workflow status"""
        mock_workflow = Mock()
        mock_workflow.status = "running"
        mock_workflow.current_step = "geometry_processing"
        mock_workflow.created_at = datetime.utcnow()
        mock_workflow.updated_at = datetime.utcnow()
        mock_workflow.completed_at = None
        mock_workflow.error_message = None

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_workflow

        with patch.object(workflow.state_persistence, 'load_state') as mock_load_state:
            mock_load_state.return_value = {"progress": 25, "current_step": "geometry_processing"}
            with patch.object(workflow.hitl_manager, 'get_pending_checkpoints') as mock_checkpoints:
                mock_checkpoints.return_value = []
                
                status = await workflow.get_workflow_status("workflow_001")

        assert status is not None
        assert status["status"] == "running"
        assert status["current_step"] == "geometry_processing"

    @pytest.mark.asyncio
    async def test_respond_to_checkpoint(self, workflow, mock_db_session):
        """Test responding to HITL checkpoint"""
        mock_checkpoint = Mock()
        mock_checkpoint.workflow_id = "workflow_001"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_checkpoint

        with patch.object(workflow.hitl_manager, 'respond_to_checkpoint', return_value=True):
            with patch.object(workflow.state_persistence, 'load_state') as mock_load_state:
                mock_state = {"hitl_checkpoints": [{"checkpoint_id": "checkpoint_001", "status": "pending"}]}
                mock_load_state.return_value = mock_state
                with patch.object(workflow.state_persistence, 'save_state', return_value=True):
                    result = await workflow.respond_to_checkpoint(
                        checkpoint_id="checkpoint_001",
                        approved=True,
                        feedback="Approved",
                        reviewer_id="user_001"
                    )

        assert result is True
