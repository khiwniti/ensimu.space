"""
Unit tests for AI agents in the simulation preprocessing workflow.
Tests GeometryAgent, MeshAgent, MaterialAgent, and PhysicsAgent classes.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import json

from app.libs.cae_agents import (
    GeometryAgent, MeshAgent, MaterialAgent, PhysicsAgent,
    AgentFactory, WorkflowContext, AgentResponse
)


@pytest.mark.unit
@pytest.mark.agents
class TestGeometryAgent:
    """Test cases for GeometryAgent"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return Mock()

    @pytest.fixture
    def geometry_agent(self, mock_db_session):
        """Create GeometryAgent instance for testing"""
        return GeometryAgent(mock_db_session)

    @pytest.fixture
    def sample_geometry_request(self):
        """Sample geometry analysis request"""
        return {
            "cad_files": [
                {
                    "id": "file_001",
                    "filename": "test_geometry.step",
                    "file_path": "/tmp/test_geometry.step",
                    "file_type": "cad",
                    "file_format": "STEP"
                }
            ],
            "analysis_requirements": {
                "physics_type": "cfd",
                "user_goal": "External aerodynamics analysis of a wing"
            }
        }

    @pytest.fixture
    def workflow_context(self):
        """Sample workflow context"""
        return WorkflowContext(
            project_id="test_project_001",
            workflow_id="workflow_001",
            user_goal="Test aerodynamics simulation",
            physics_type="cfd",
            current_step="geometry_processing",
            global_state={},
            agent_outputs={}
        )

    def test_geometry_agent_initialization(self, geometry_agent):
        """Test GeometryAgent initialization"""
        assert geometry_agent.agent_type == "geometry"
        assert geometry_agent.agent_id is not None
        assert geometry_agent.db_session is not None
        assert hasattr(geometry_agent, 'llm_client')

    @pytest.mark.asyncio
    async def test_geometry_agent_process_request_success(
        self, geometry_agent, sample_geometry_request, workflow_context
    ):
        """Test successful geometry processing"""
        # Mock the geometry analysis
        with patch.object(geometry_agent, '_analyze_geometry') as mock_analyze:
            mock_analyze.return_value = {
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

            response = await geometry_agent.process_request(
                sample_geometry_request, workflow_context
            )

            assert isinstance(response, AgentResponse)
            assert response.success is True
            assert response.agent_type == "geometry"
            assert response.data is not None
            assert "geometry_metrics" in response.data
            assert "confidence_score" in response.data
            assert response.data["confidence_score"] == 0.88

    @pytest.mark.asyncio
    async def test_geometry_agent_process_request_failure(
        self, geometry_agent, sample_geometry_request, workflow_context
    ):
        """Test geometry processing failure handling"""
        # Mock analysis failure
        with patch.object(geometry_agent, '_analyze_geometry') as mock_analyze:
            mock_analyze.side_effect = Exception("File not found")

            response = await geometry_agent.process_request(
                sample_geometry_request, workflow_context
            )

            assert isinstance(response, AgentResponse)
            assert response.success is False
            assert response.error_message is not None
            assert "File not found" in response.error_message

    def test_geometry_agent_validate_request_valid(self, geometry_agent, sample_geometry_request):
        """Test request validation with valid data"""
        is_valid, error = geometry_agent._validate_request(sample_geometry_request)
        assert is_valid is True
        assert error is None

    def test_geometry_agent_validate_request_invalid(self, geometry_agent):
        """Test request validation with invalid data"""
        invalid_request = {"invalid": "data"}
        is_valid, error = geometry_agent._validate_request(invalid_request)
        assert is_valid is False
        assert error is not None

    @pytest.mark.asyncio
    async def test_geometry_agent_confidence_scoring(self, geometry_agent):
        """Test confidence scoring logic"""
        # Test high confidence scenario
        analysis_result = {
            "geometry_metrics": {"volume": 1.0, "surface_area": 6.0},
            "quality_assessment": {"mesh_readiness_score": 0.9},
            "potential_issues": []
        }
        
        confidence = await geometry_agent._calculate_confidence(analysis_result)
        assert 0.8 <= confidence <= 1.0

        # Test low confidence scenario
        analysis_result_low = {
            "geometry_metrics": {"volume": 0.0, "surface_area": 0.0},
            "quality_assessment": {"mesh_readiness_score": 0.3},
            "potential_issues": ["Invalid geometry", "Self-intersections"]
        }
        
        confidence_low = await geometry_agent._calculate_confidence(analysis_result_low)
        assert 0.0 <= confidence_low <= 0.5


@pytest.mark.unit
@pytest.mark.agents
class TestMeshAgent:
    """Test cases for MeshAgent"""

    @pytest.fixture
    def mesh_agent(self, mock_db_session):
        """Create MeshAgent instance for testing"""
        return MeshAgent(mock_db_session)

    @pytest.fixture
    def sample_mesh_request(self):
        """Sample mesh generation request"""
        return {
            "geometry_analysis": {
                "geometry_metrics": {
                    "volume": 1.5,
                    "surface_area": 8.2,
                    "characteristic_length": 1.0
                },
                "quality_assessment": {
                    "mesh_readiness_score": 0.85
                }
            },
            "computational_resources": {
                "cpu_cores": 8,
                "memory_gb": 32
            },
            "quality_requirements": {
                "target_quality": 0.8,
                "max_aspect_ratio": 10
            }
        }

    def test_mesh_agent_initialization(self, mesh_agent):
        """Test MeshAgent initialization"""
        assert mesh_agent.agent_type == "mesh"
        assert mesh_agent.agent_id is not None

    @pytest.mark.asyncio
    async def test_mesh_agent_process_request_success(
        self, mesh_agent, sample_mesh_request, workflow_context
    ):
        """Test successful mesh generation"""
        with patch.object(mesh_agent, '_generate_mesh_strategy') as mock_strategy:
            mock_strategy.return_value = {
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

            response = await mesh_agent.process_request(
                sample_mesh_request, workflow_context
            )

            assert response.success is True
            assert "mesh_strategy" in response.data
            assert "quality_assessment" in response.data
            assert response.data["confidence_score"] == 0.85

    def test_mesh_agent_quality_prediction(self, mesh_agent):
        """Test mesh quality prediction logic"""
        geometry_metrics = {
            "volume": 1.0,
            "surface_area": 6.0,
            "characteristic_length": 1.0,
            "complexity": "medium"
        }
        
        predicted_quality = mesh_agent._predict_mesh_quality(geometry_metrics)
        assert 0.0 <= predicted_quality <= 1.0

    def test_mesh_agent_resource_estimation(self, mesh_agent):
        """Test computational resource estimation"""
        mesh_config = {
            "element_count": 100000,
            "element_type": "hexahedral",
            "refinement_levels": 2
        }
        
        resources = mesh_agent._estimate_computational_resources(mesh_config)
        assert "memory_estimate_gb" in resources
        assert "runtime_estimate_hours" in resources
        assert resources["memory_estimate_gb"] > 0


@pytest.mark.unit
@pytest.mark.agents
class TestMaterialAgent:
    """Test cases for MaterialAgent"""

    @pytest.fixture
    def material_agent(self, mock_db_session):
        """Create MaterialAgent instance for testing"""
        return MaterialAgent(mock_db_session)

    @pytest.fixture
    def sample_material_request(self):
        """Sample material assignment request"""
        return {
            "geometry_analysis": {
                "geometry_metrics": {"volume": 1.0}
            },
            "physics_requirements": {
                "physics_type": "cfd"
            },
            "application_context": {
                "user_goal": "External aerodynamics analysis"
            }
        }

    def test_material_agent_initialization(self, material_agent):
        """Test MaterialAgent initialization"""
        assert material_agent.agent_type == "materials"
        assert material_agent.agent_id is not None

    @pytest.mark.asyncio
    async def test_material_agent_process_request_success(
        self, material_agent, sample_material_request, workflow_context
    ):
        """Test successful material assignment"""
        with patch.object(material_agent, '_assign_materials') as mock_assign:
            mock_assign.return_value = {
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

            response = await material_agent.process_request(
                sample_material_request, workflow_context
            )

            assert response.success is True
            assert "material_recommendations" in response.data
            assert response.data["confidence_score"] == 0.92

    def test_material_agent_property_validation(self, material_agent):
        """Test material property validation"""
        material_props = {
            "density": 1.225,
            "viscosity": 1.8e-05,
            "specific_heat": 1005
        }
        
        is_valid = material_agent._validate_material_properties(
            material_props, "cfd"
        )
        assert is_valid is True


@pytest.mark.unit
@pytest.mark.agents
class TestPhysicsAgent:
    """Test cases for PhysicsAgent"""

    @pytest.fixture
    def physics_agent(self, mock_db_session):
        """Create PhysicsAgent instance for testing"""
        return PhysicsAgent(mock_db_session)

    @pytest.fixture
    def sample_physics_request(self):
        """Sample physics setup request"""
        return {
            "geometry_analysis": {"geometry_metrics": {"volume": 1.0}},
            "mesh_strategy": {"approach": "structured_hex"},
            "material_assignment": {
                "material_recommendations": [
                    {"region": "fluid_domain", "material": "air"}
                ]
            },
            "operating_conditions": {"physics_type": "cfd"}
        }

    def test_physics_agent_initialization(self, physics_agent):
        """Test PhysicsAgent initialization"""
        assert physics_agent.agent_type == "physics"
        assert physics_agent.agent_id is not None

    @pytest.mark.asyncio
    async def test_physics_agent_process_request_success(
        self, physics_agent, sample_physics_request, workflow_context
    ):
        """Test successful physics setup"""
        with patch.object(physics_agent, '_setup_physics') as mock_setup:
            mock_setup.return_value = {
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

            response = await physics_agent.process_request(
                sample_physics_request, workflow_context
            )

            assert response.success is True
            assert "boundary_conditions" in response.data
            assert "solver_configuration" in response.data
            assert response.data["confidence_score"] == 0.89


@pytest.mark.unit
@pytest.mark.agents
class TestAgentFactory:
    """Test cases for AgentFactory"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return Mock()

    @pytest.fixture
    def agent_factory(self, mock_db_session):
        """Create AgentFactory instance for testing"""
        return AgentFactory(mock_db_session)

    def test_agent_factory_create_geometry_agent(self, agent_factory):
        """Test creating GeometryAgent through factory"""
        agent = agent_factory.create_agent("geometry")
        assert isinstance(agent, GeometryAgent)
        assert agent.agent_type == "geometry"

    def test_agent_factory_create_mesh_agent(self, agent_factory):
        """Test creating MeshAgent through factory"""
        agent = agent_factory.create_agent("mesh")
        assert isinstance(agent, MeshAgent)
        assert agent.agent_type == "mesh"

    def test_agent_factory_create_material_agent(self, agent_factory):
        """Test creating MaterialAgent through factory"""
        agent = agent_factory.create_agent("materials")
        assert isinstance(agent, MaterialAgent)
        assert agent.agent_type == "materials"

    def test_agent_factory_create_physics_agent(self, agent_factory):
        """Test creating PhysicsAgent through factory"""
        agent = agent_factory.create_agent("physics")
        assert isinstance(agent, PhysicsAgent)
        assert agent.agent_type == "physics"

    def test_agent_factory_invalid_agent_type(self, agent_factory):
        """Test creating agent with invalid type"""
        with pytest.raises(ValueError):
            agent_factory.create_agent("invalid_type")


@pytest.mark.unit
@pytest.mark.agents
class TestAgentResponse:
    """Test cases for AgentResponse class"""

    def test_agent_response_success(self):
        """Test successful AgentResponse creation"""
        response = AgentResponse(
            success=True,
            agent_type="geometry",
            agent_id="agent_001",
            data={"result": "success"},
            processing_time=1.5
        )
        
        assert response.success is True
        assert response.agent_type == "geometry"
        assert response.data["result"] == "success"
        assert response.error_message is None

    def test_agent_response_failure(self):
        """Test failed AgentResponse creation"""
        response = AgentResponse(
            success=False,
            agent_type="mesh",
            agent_id="agent_002",
            error_message="Processing failed",
            processing_time=0.5
        )
        
        assert response.success is False
        assert response.error_message == "Processing failed"
        assert response.data is None

    def test_agent_response_to_dict(self):
        """Test AgentResponse serialization"""
        response = AgentResponse(
            success=True,
            agent_type="materials",
            agent_id="agent_003",
            data={"materials": ["steel", "aluminum"]},
            processing_time=2.0
        )
        
        response_dict = response.to_dict()
        assert isinstance(response_dict, dict)
        assert response_dict["success"] is True
        assert response_dict["agent_type"] == "materials"
        assert "materials" in response_dict["data"]
