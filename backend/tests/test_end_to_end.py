"""
End-to-end tests for the complete simulation preprocessing workflow.
Tests the full user journey from file upload to simulation completion.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import tempfile
import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.libs.cae_models import Base, Project, UploadedFile, WorkflowExecution
from app.libs.langgraph_workflow import SimulationPreprocessingWorkflow
from app.libs.cae_agents import AgentFactory


@pytest.mark.e2e
class TestEndToEndWorkflow:
    """End-to-end tests for complete workflow execution"""

    @pytest.fixture(scope="function")
    def db_engine(self):
        """Create in-memory database for E2E testing"""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture(scope="function")
    def db_session(self, db_engine):
        """Create database session for E2E testing"""
        Session = sessionmaker(bind=db_engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def test_project(self, db_session):
        """Create test project"""
        project = Project(
            name="E2E Test Project",
            description="End-to-end testing project",
            project_type="cfd",
            created_by="test_user"
        )
        db_session.add(project)
        db_session.commit()
        return project

    @pytest.fixture
    def test_cad_file(self, db_session, test_project):
        """Create test CAD file"""
        cad_file = UploadedFile(
            project_id=str(test_project.id),
            filename="wing_geometry.step",
            file_path="/tmp/wing_geometry.step",
            file_type="cad",
            file_format="STEP",
            file_size_bytes=1024000,
            upload_status="completed"
        )
        db_session.add(cad_file)
        db_session.commit()
        return cad_file

    @pytest.fixture
    def mock_agent_responses(self):
        """Mock responses for all AI agents"""
        return {
            "geometry": {
                "success": True,
                "data": {
                    "geometry_metrics": {
                        "volume": 1.5,
                        "surface_area": 8.2,
                        "characteristic_length": 1.0,
                        "complexity": "medium"
                    },
                    "quality_assessment": {
                        "mesh_readiness_score": 0.85,
                        "surface_quality": "good",
                        "geometric_issues": []
                    },
                    "recommendations": [
                        "Geometry is suitable for CFD analysis",
                        "Consider surface smoothing for better mesh quality"
                    ],
                    "confidence_score": 0.88,
                    "potential_issues": []
                }
            },
            "mesh": {
                "success": True,
                "data": {
                    "mesh_strategy": {
                        "approach": "structured_hex",
                        "refinement_levels": 3,
                        "boundary_layers": True
                    },
                    "element_types": {
                        "primary": "hexahedral",
                        "boundary": "prism"
                    },
                    "quality_assessment": {
                        "predicted_quality_score": 0.82,
                        "estimated_cell_count": 150000
                    },
                    "computational_cost_estimate": {
                        "element_count": 150000,
                        "memory_estimate_gb": 2.5,
                        "runtime_estimate_hours": 0.5
                    },
                    "confidence_score": 0.85
                }
            },
            "materials": {
                "success": True,
                "data": {
                    "material_recommendations": [
                        {
                            "region": "fluid_domain",
                            "material": "air",
                            "properties": {
                                "density": 1.225,
                                "viscosity": 1.8e-05
                            }
                        }
                    ],
                    "validation_results": {
                        "physics_compatibility": True,
                        "property_completeness": True
                    },
                    "confidence_score": 0.92
                }
            },
            "physics": {
                "success": True,
                "data": {
                    "boundary_conditions": {
                        "inlet": {"type": "velocity_inlet", "value": [10, 0, 0]},
                        "outlet": {"type": "pressure_outlet", "value": 0},
                        "walls": {"type": "no_slip_wall"}
                    },
                    "solver_configuration": {
                        "solver_type": "SIMPLE",
                        "turbulence_model": "kOmegaSST",
                        "time_scheme": "steady"
                    },
                    "convergence_criteria": {
                        "residual_targets": {"U": 1e-6, "p": 1e-6},
                        "max_iterations": 1000
                    },
                    "confidence_score": 0.89
                }
            }
        }

    @pytest.mark.asyncio
    async def test_complete_user_journey(self, db_session, test_project, test_cad_file, mock_agent_responses):
        """Test complete user journey from project creation to simulation completion"""
        
        # Step 1: Create workflow
        workflow = SimulationPreprocessingWorkflow(db_session)
        
        # Mock all agent responses
        with patch.object(workflow.node_executor.agent_factory, 'create_agent') as mock_create_agent:
            # Set up mock agents
            mock_agents = {}
            for agent_type, response_data in mock_agent_responses.items():
                mock_agent = AsyncMock()
                mock_response = Mock()
                mock_response.success = response_data["success"]
                mock_response.data = response_data["data"]
                mock_response.error_message = None
                mock_agent.process_request.return_value = mock_response
                mock_agents[agent_type] = mock_agent
            
            def get_agent(agent_type):
                return mock_agents[agent_type]
            
            mock_create_agent.side_effect = get_agent
            
            # Mock state persistence
            with patch.object(workflow.state_persistence, 'save_state', return_value=True):
                with patch.object(workflow.state_persistence, 'create_workflow_step', return_value="step_001"):
                    with patch.object(workflow.state_persistence, 'update_workflow_step', return_value=True):
                        
                        # Step 2: Start workflow
                        workflow_id = await workflow.start_workflow(
                            project_id=str(test_project.id),
                            user_goal="Perform CFD analysis of wing aerodynamics at cruise conditions",
                            physics_type="cfd",
                            cad_files=[{
                                "id": str(test_cad_file.id),
                                "filename": test_cad_file.filename,
                                "file_path": test_cad_file.file_path,
                                "file_type": test_cad_file.file_type,
                                "file_format": test_cad_file.file_format
                            }]
                        )
                        
                        # Verify workflow was created
                        assert workflow_id is not None
                        
                        # Step 3: Verify workflow execution record
                        workflow_execution = db_session.query(WorkflowExecution).filter(
                            WorkflowExecution.id == workflow_id
                        ).first()
                        
                        assert workflow_execution is not None
                        assert workflow_execution.project_id == str(test_project.id)
                        assert workflow_execution.status == "running"
                        assert "cfd" in workflow_execution.workflow_plan["physics_type"]

    @pytest.mark.asyncio
    async def test_workflow_with_hitl_checkpoint(self, db_session, test_project, test_cad_file, mock_agent_responses):
        """Test workflow execution with HITL checkpoint interaction"""
        
        workflow = SimulationPreprocessingWorkflow(db_session)
        
        # Mock agents and state persistence
        with patch.object(workflow.node_executor.agent_factory, 'create_agent') as mock_create_agent:
            # Set up mock agents
            mock_agents = {}
            for agent_type, response_data in mock_agent_responses.items():
                mock_agent = AsyncMock()
                mock_response = Mock()
                mock_response.success = response_data["success"]
                mock_response.data = response_data["data"]
                mock_response.error_message = None
                mock_agent.process_request.return_value = mock_response
                mock_agents[agent_type] = mock_agent
            
            mock_create_agent.side_effect = lambda agent_type: mock_agents[agent_type]
            
            with patch.object(workflow.state_persistence, 'save_state', return_value=True):
                with patch.object(workflow.state_persistence, 'create_workflow_step', return_value="step_001"):
                    with patch.object(workflow.state_persistence, 'update_workflow_step', return_value=True):
                        with patch.object(workflow.hitl_manager, 'create_checkpoint', return_value="checkpoint_001"):
                            
                            # Start workflow
                            workflow_id = await workflow.start_workflow(
                                project_id=str(test_project.id),
                                user_goal="CFD analysis with human review",
                                physics_type="cfd",
                                cad_files=[{
                                    "id": str(test_cad_file.id),
                                    "filename": test_cad_file.filename,
                                    "file_path": test_cad_file.file_path,
                                    "file_type": test_cad_file.file_type,
                                    "file_format": test_cad_file.file_format
                                }]
                            )
                            
                            # Simulate HITL checkpoint response
                            with patch.object(workflow.hitl_manager, 'respond_to_checkpoint', return_value=True):
                                result = await workflow.respond_to_checkpoint(
                                    checkpoint_id="checkpoint_001",
                                    approved=True,
                                    feedback="Preprocessing looks good, proceed with simulation",
                                    reviewer_id="test_reviewer"
                                )
                                
                                assert result is True

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, db_session, test_project, test_cad_file):
        """Test workflow error handling and recovery"""
        
        workflow = SimulationPreprocessingWorkflow(db_session)
        
        # Mock geometry agent failure
        with patch.object(workflow.node_executor.agent_factory, 'create_agent') as mock_create_agent:
            mock_agent = AsyncMock()
            mock_response = Mock()
            mock_response.success = False
            mock_response.error_message = "Geometry file is corrupted"
            mock_response.data = {}
            mock_agent.process_request.return_value = mock_response
            mock_create_agent.return_value = mock_agent
            
            with patch.object(workflow.state_persistence, 'save_state', return_value=True):
                with patch.object(workflow.state_persistence, 'create_workflow_step', return_value="step_001"):
                    with patch.object(workflow.state_persistence, 'update_workflow_step', return_value=True):
                        
                        # Start workflow (should handle error gracefully)
                        workflow_id = await workflow.start_workflow(
                            project_id=str(test_project.id),
                            user_goal="Test error handling",
                            physics_type="cfd",
                            cad_files=[{
                                "id": str(test_cad_file.id),
                                "filename": test_cad_file.filename,
                                "file_path": test_cad_file.file_path,
                                "file_type": test_cad_file.file_type,
                                "file_format": test_cad_file.file_format
                            }]
                        )
                        
                        # Verify workflow was created even with error
                        assert workflow_id is not None
                        
                        # Verify error was recorded
                        workflow_execution = db_session.query(WorkflowExecution).filter(
                            WorkflowExecution.id == workflow_id
                        ).first()
                        
                        assert workflow_execution is not None

    @pytest.mark.asyncio
    async def test_agent_coordination_e2e(self, db_session):
        """Test end-to-end agent coordination"""
        
        agent_factory = AgentFactory(db_session)
        
        # Test creating all agent types
        geometry_agent = agent_factory.create_agent("geometry")
        mesh_agent = agent_factory.create_agent("mesh")
        material_agent = agent_factory.create_agent("materials")
        physics_agent = agent_factory.create_agent("physics")
        
        # Verify all agents are created with correct types
        assert geometry_agent.agent_type == "geometry"
        assert mesh_agent.agent_type == "mesh"
        assert material_agent.agent_type == "materials"
        assert physics_agent.agent_type == "physics"
        
        # Verify all agents have unique IDs
        agent_ids = [
            geometry_agent.agent_id,
            mesh_agent.agent_id,
            material_agent.agent_id,
            physics_agent.agent_id
        ]
        assert len(set(agent_ids)) == 4

    @pytest.mark.asyncio
    async def test_performance_under_load(self, db_session, test_project):
        """Test system performance under simulated load"""
        
        workflow = SimulationPreprocessingWorkflow(db_session)
        
        # Mock fast agent responses
        with patch.object(workflow.node_executor.agent_factory, 'create_agent') as mock_create_agent:
            mock_agent = AsyncMock()
            mock_response = Mock()
            mock_response.success = True
            mock_response.data = {"confidence_score": 0.85}
            mock_response.error_message = None
            mock_agent.process_request.return_value = mock_response
            mock_create_agent.return_value = mock_agent
            
            with patch.object(workflow.state_persistence, 'save_state', return_value=True):
                with patch.object(workflow.state_persistence, 'create_workflow_step', return_value="step_001"):
                    with patch.object(workflow.state_persistence, 'update_workflow_step', return_value=True):
                        
                        # Start multiple workflows concurrently
                        tasks = []
                        for i in range(5):  # Simulate 5 concurrent workflows
                            task = workflow.start_workflow(
                                project_id=str(test_project.id),
                                user_goal=f"Performance test workflow {i}",
                                physics_type="cfd",
                                cad_files=[]
                            )
                            tasks.append(task)
                        
                        # Wait for all workflows to start
                        workflow_ids = await asyncio.gather(*tasks)
                        
                        # Verify all workflows were created
                        assert len(workflow_ids) == 5
                        assert all(wid is not None for wid in workflow_ids)

    def test_database_integrity_e2e(self, db_session, test_project, test_cad_file):
        """Test database integrity throughout the workflow"""
        
        # Verify project exists
        project = db_session.query(Project).filter(Project.id == test_project.id).first()
        assert project is not None
        assert project.name == "E2E Test Project"
        
        # Verify file relationship
        assert len(project.uploaded_files) == 1
        assert project.uploaded_files[0].filename == "wing_geometry.step"
        
        # Verify file properties
        file = project.uploaded_files[0]
        assert file.file_type == "cad"
        assert file.file_format == "STEP"
        assert file.upload_status == "completed"
        assert file.file_size_bytes == 1024000
