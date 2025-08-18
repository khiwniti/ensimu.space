"""
Integration tests for the complete simulation preprocessing workflow.
Tests end-to-end integration of AI agents, LangGraph workflows, and database persistence.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import tempfile
import json

from app.libs.cae_agents import AgentFactory, WorkflowContext
from app.libs.langgraph_workflow import (
    SimulationPreprocessingWorkflow, SimulationState, 
    DatabaseStatePersistence, HITLCheckpointManager
)
from app.libs.cae_models import (
    Project, WorkflowExecution, WorkflowStep, HITLCheckpoint
)


@pytest.mark.integration
class TestWorkflowIntegration:
    """Integration tests for complete workflow execution"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for integration testing"""
        session = Mock()
        
        # Mock project
        mock_project = Mock()
        mock_project.id = "test_project_001"
        mock_project.name = "Integration Test Project"
        
        # Mock workflow execution
        mock_workflow = Mock()
        mock_workflow.id = "workflow_001"
        mock_workflow.project_id = "test_project_001"
        mock_workflow.status = "running"
        mock_workflow.current_step = "geometry_processing"
        mock_workflow.global_context = {}
        
        # Configure query mocks
        session.query.return_value.filter.return_value.first.return_value = mock_workflow
        session.add.return_value = None
        session.commit.return_value = None
        
        return session

    @pytest.fixture
    def sample_cad_files(self):
        """Sample CAD files for testing"""
        return [
            {
                "id": "file_001",
                "filename": "wing_geometry.step",
                "file_path": "/tmp/wing_geometry.step",
                "file_type": "cad",
                "file_format": "STEP"
            }
        ]

    @pytest.fixture
    def workflow_instance(self, mock_db_session):
        """Create workflow instance for testing"""
        return SimulationPreprocessingWorkflow(mock_db_session)

    @pytest.mark.asyncio
    async def test_complete_workflow_execution(self, workflow_instance, sample_cad_files, mock_db_session):
        """Test complete workflow execution from start to finish"""
        
        # Mock all agent responses
        mock_geometry_response = Mock()
        mock_geometry_response.success = True
        mock_geometry_response.data = {
            "geometry_metrics": {"volume": 1.5, "surface_area": 8.2},
            "quality_assessment": {"mesh_readiness_score": 0.85},
            "confidence_score": 0.88,
            "recommendations": ["Geometry is suitable for CFD analysis"]
        }
        
        mock_mesh_response = Mock()
        mock_mesh_response.success = True
        mock_mesh_response.data = {
            "mesh_strategy": {"approach": "structured_hex"},
            "quality_assessment": {"predicted_quality_score": 0.82},
            "confidence_score": 0.85
        }
        
        mock_material_response = Mock()
        mock_material_response.success = True
        mock_material_response.data = {
            "material_recommendations": [{"region": "fluid", "material": "air"}],
            "confidence_score": 0.92
        }
        
        mock_physics_response = Mock()
        mock_physics_response.success = True
        mock_physics_response.data = {
            "boundary_conditions": {"inlet": {"type": "velocity_inlet"}},
            "solver_configuration": {"solver_type": "SIMPLE"},
            "confidence_score": 0.89
        }
        
        # Mock agent factory
        with patch.object(workflow_instance.node_executor.agent_factory, 'create_agent') as mock_create_agent:
            mock_agents = {
                "geometry": AsyncMock(),
                "mesh": AsyncMock(),
                "materials": AsyncMock(),
                "physics": AsyncMock()
            }
            
            mock_agents["geometry"].process_request.return_value = mock_geometry_response
            mock_agents["mesh"].process_request.return_value = mock_mesh_response
            mock_agents["materials"].process_request.return_value = mock_material_response
            mock_agents["physics"].process_request.return_value = mock_physics_response
            
            def get_agent(agent_type):
                return mock_agents[agent_type]
            
            mock_create_agent.side_effect = get_agent
            
            # Mock state persistence
            with patch.object(workflow_instance.state_persistence, 'save_state', return_value=True):
                with patch.object(workflow_instance.state_persistence, 'create_workflow_step', return_value="step_001"):
                    with patch.object(workflow_instance.state_persistence, 'update_workflow_step', return_value=True):
                        
                        # Start workflow
                        workflow_id = await workflow_instance.start_workflow(
                            project_id="test_project_001",
                            user_goal="Test CFD simulation of wing aerodynamics",
                            physics_type="cfd",
                            cad_files=sample_cad_files
                        )
                        
                        assert workflow_id == "workflow_001"
                        
                        # Verify workflow was created
                        mock_db_session.add.assert_called()
                        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_agent_coordination(self, mock_db_session):
        """Test coordination between different AI agents"""
        
        # Create agent factory
        agent_factory = AgentFactory(mock_db_session)
        
        # Create workflow context
        context = WorkflowContext(
            project_id="test_project_001",
            workflow_id="workflow_001",
            user_goal="Test agent coordination",
            physics_type="cfd",
            current_step="geometry_processing",
            global_state={},
            agent_outputs={}
        )
        
        # Test geometry agent
        geometry_agent = agent_factory.create_agent("geometry")
        assert geometry_agent.agent_type == "geometry"
        
        # Test mesh agent
        mesh_agent = agent_factory.create_agent("mesh")
        assert mesh_agent.agent_type == "mesh"
        
        # Test material agent
        material_agent = agent_factory.create_agent("materials")
        assert material_agent.agent_type == "materials"
        
        # Test physics agent
        physics_agent = agent_factory.create_agent("physics")
        assert physics_agent.agent_type == "physics"
        
        # Verify all agents have unique IDs
        agent_ids = [
            geometry_agent.agent_id,
            mesh_agent.agent_id,
            material_agent.agent_id,
            physics_agent.agent_id
        ]
        assert len(set(agent_ids)) == 4  # All unique

    @pytest.mark.asyncio
    async def test_state_persistence_integration(self, mock_db_session):
        """Test state persistence across workflow execution"""
        
        # Create state persistence manager
        state_persistence = DatabaseStatePersistence(mock_db_session)
        
        # Create sample state
        sample_state = SimulationState(
            project_id="test_project_001",
            workflow_id="workflow_001",
            user_goal="Test state persistence",
            physics_type="cfd",
            cad_files=[],
            current_file=None,
            geometry_status="completed",
            mesh_status="processing",
            materials_status="pending",
            physics_status="pending",
            geometry_analysis={"confidence_score": 0.85},
            mesh_recommendations=None,
            material_assignments=None,
            physics_setup=None,
            current_step="mesh_generation",
            completed_steps=["geometry_processing"],
            failed_steps=[],
            hitl_checkpoints=[],
            mesh_quality_metrics=None,
            convergence_criteria=None,
            validation_results=None,
            errors=[],
            warnings=[],
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            iteration_count=1,
            max_iterations=3
        )
        
        # Test saving state
        result = await state_persistence.save_state(sample_state)
        assert result is True
        
        # Test creating workflow step
        step_id = await state_persistence.create_workflow_step(
            workflow_id="workflow_001",
            step_name="mesh_generation",
            agent_type="mesh",
            step_order=2,
            input_data={"geometry_analysis": {"volume": 1.0}}
        )
        
        assert step_id is not None

    @pytest.mark.asyncio
    async def test_hitl_checkpoint_integration(self, mock_db_session):
        """Test HITL checkpoint creation and response handling"""
        
        # Create HITL manager
        hitl_manager = HITLCheckpointManager(mock_db_session)
        
        # Mock checkpoint
        mock_checkpoint = Mock()
        mock_checkpoint.id = "checkpoint_001"
        mock_checkpoint.workflow_id = "workflow_001"
        mock_checkpoint.checkpoint_type = "preprocessing_review"
        mock_checkpoint.status = "pending"
        mock_checkpoint.created_at = datetime.utcnow()
        mock_checkpoint.timeout_at = None
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_checkpoint
        mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_checkpoint]
        
        # Test creating checkpoint
        checkpoint_id = await hitl_manager.create_checkpoint(
            workflow_id="workflow_001",
            step_id="step_001",
            checkpoint_type="preprocessing_review",
            checkpoint_data={"analysis": "complete"},
            agent_recommendations=["Proceed with simulation"],
            timeout_minutes=60
        )
        
        assert checkpoint_id == "checkpoint_001"
        
        # Test getting pending checkpoints
        pending = await hitl_manager.get_pending_checkpoints("workflow_001")
        assert len(pending) == 1
        
        # Test responding to checkpoint
        result = await hitl_manager.respond_to_checkpoint(
            checkpoint_id="checkpoint_001",
            approved=True,
            human_feedback="Approved for simulation",
            reviewer_id="test_user"
        )
        
        assert result is True
        assert mock_checkpoint.status == "approved"

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, workflow_instance, sample_cad_files):
        """Test error handling across the integrated system"""
        
        # Mock agent failure
        mock_geometry_response = Mock()
        mock_geometry_response.success = False
        mock_geometry_response.error_message = "File processing failed"
        mock_geometry_response.data = {}
        
        with patch.object(workflow_instance.node_executor.agent_factory, 'create_agent') as mock_create_agent:
            mock_agent = AsyncMock()
            mock_agent.process_request.return_value = mock_geometry_response
            mock_create_agent.return_value = mock_agent
            
            with patch.object(workflow_instance.state_persistence, 'save_state', return_value=True):
                with patch.object(workflow_instance.state_persistence, 'create_workflow_step', return_value="step_001"):
                    with patch.object(workflow_instance.state_persistence, 'update_workflow_step', return_value=True):
                        
                        # Create initial state
                        initial_state = SimulationState(
                            project_id="test_project_001",
                            workflow_id="workflow_001",
                            user_goal="Test error handling",
                            physics_type="cfd",
                            cad_files=sample_cad_files,
                            current_file=None,
                            geometry_status="pending",
                            mesh_status="pending",
                            materials_status="pending",
                            physics_status="pending",
                            geometry_analysis=None,
                            mesh_recommendations=None,
                            material_assignments=None,
                            physics_setup=None,
                            current_step="geometry_processing",
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
                        
                        # Execute geometry processing node (should fail)
                        result_state = await workflow_instance.node_executor.geometry_processing_node(initial_state)
                        
                        # Verify error handling
                        assert result_state["geometry_status"] == "failed"
                        assert "geometry_processing" in result_state["failed_steps"]
                        assert len(result_state["errors"]) > 0
                        assert "File processing failed" in result_state["errors"][0]["error"]

    @pytest.mark.asyncio
    async def test_workflow_routing_integration(self, mock_db_session):
        """Test workflow routing logic integration"""
        
        from app.libs.langgraph_workflow import WorkflowRouter
        
        router = WorkflowRouter(mock_db_session)
        
        # Test routing from successful geometry processing
        state_geometry_success = SimulationState(
            project_id="test_project_001",
            workflow_id="workflow_001",
            user_goal="Test routing",
            physics_type="cfd",
            cad_files=[],
            current_file=None,
            geometry_status="completed",
            mesh_status="pending",
            materials_status="pending",
            physics_status="pending",
            geometry_analysis={"quality_metrics": {"mesh_readiness_score": 0.85}},
            mesh_recommendations=None,
            material_assignments=None,
            physics_setup=None,
            current_step="geometry_processing",
            completed_steps=["geometry_processing"],
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
        
        next_step = await router.route_next_step(state_geometry_success)
        assert next_step == "mesh_generation"
        
        # Test routing from validation success
        state_validation_success = state_geometry_success.copy()
        state_validation_success["current_step"] = "validation"
        state_validation_success["validation_results"] = {"overall_status": "passed"}
        
        next_step = await router.route_next_step(state_validation_success)
        assert next_step == "hitl_checkpoint"
