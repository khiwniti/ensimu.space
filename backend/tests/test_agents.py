"""
Unit tests for AI agents in the simulation preprocessing system.
Tests individual agent functionality, prompt engineering, and response handling.
"""

import pytest
import json
import uuid
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.libs.cae_agents import (
    AgentFactory, GeometryAgent, MeshAgent, MaterialsAgent, PhysicsAgent,
    WorkflowContext, AgentResponse, PromptTemplate
)

@pytest.fixture
def mock_openai():
    """Mock OpenAI API responses"""
    with patch('openai.ChatCompletion.acreate') as mock:
        mock.return_value = AsyncMock()
        yield mock

@pytest.fixture
def sample_context():
    """Create sample workflow context"""
    return WorkflowContext(
        project_id=str(uuid.uuid4()),
        workflow_id=str(uuid.uuid4()),
        user_goal="Test CFD analysis of airflow around a car",
        physics_type="cfd",
        current_step="test_step",
        global_state={},
        agent_outputs={}
    )

@pytest.fixture
def mock_db_session():
    """Mock database session"""
    return Mock()

class TestAgentFactory:
    """Test agent factory functionality"""
    
    def test_create_geometry_agent(self, mock_db_session):
        """Test creating geometry agent"""
        factory = AgentFactory(mock_db_session)
        agent = factory.create_agent("geometry")
        
        assert isinstance(agent, GeometryAgent)
        assert agent.agent_type == "geometry"
    
    def test_create_mesh_agent(self, mock_db_session):
        """Test creating mesh agent"""
        factory = AgentFactory(mock_db_session)
        agent = factory.create_agent("mesh")
        
        assert isinstance(agent, MeshAgent)
        assert agent.agent_type == "mesh"
    
    def test_create_materials_agent(self, mock_db_session):
        """Test creating materials agent"""
        factory = AgentFactory(mock_db_session)
        agent = factory.create_agent("materials")
        
        assert isinstance(agent, MaterialsAgent)
        assert agent.agent_type == "materials"
    
    def test_create_physics_agent(self, mock_db_session):
        """Test creating physics agent"""
        factory = AgentFactory(mock_db_session)
        agent = factory.create_agent("physics")
        
        assert isinstance(agent, PhysicsAgent)
        assert agent.agent_type == "physics"
    
    def test_invalid_agent_type(self, mock_db_session):
        """Test creating invalid agent type"""
        factory = AgentFactory(mock_db_session)
        
        with pytest.raises(ValueError):
            factory.create_agent("invalid_type")

class TestGeometryAgent:
    """Test geometry analysis agent"""
    
    @pytest.mark.asyncio
    async def test_process_cfd_geometry(self, mock_db_session, sample_context, mock_openai):
        """Test geometry analysis for CFD"""
        # Mock OpenAI response
        mock_response = {
            "geometry_analysis": {
                "complexity": "medium",
                "surface_area": 15.2,
                "volume": 8.5,
                "characteristic_length": 2.1
            },
            "flow_regions": [
                {"name": "inlet", "type": "boundary", "area": 1.2},
                {"name": "outlet", "type": "boundary", "area": 1.1},
                {"name": "walls", "type": "boundary", "area": 12.9}
            ],
            "recommendations": [
                "Consider simplifying small features for better mesh quality",
                "Ensure inlet and outlet are properly defined"
            ],
            "confidence": 0.85
        }
        
        mock_openai.return_value.choices = [
            Mock(message=Mock(content=json.dumps(mock_response)))
        ]
        
        agent = GeometryAgent(mock_db_session)
        request_data = {
            "cad_files": ["car_body.step"],
            "physics_type": "cfd",
            "user_requirements": "Analyze airflow around car body"
        }
        
        result = await agent.process_request(request_data, sample_context)
        
        assert result.success
        assert result.confidence_score == 0.85
        assert "geometry_analysis" in result.data
        assert "flow_regions" in result.data
        assert len(result.data["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_process_structural_geometry(self, mock_db_session, sample_context, mock_openai):
        """Test geometry analysis for structural analysis"""
        sample_context.physics_type = "structural"
        
        mock_response = {
            "geometry_analysis": {
                "complexity": "high",
                "volume": 12.3,
                "mass_properties": {
                    "center_of_mass": [0.5, 0.2, 1.1],
                    "moments_of_inertia": [2.1, 3.4, 1.8]
                }
            },
            "structural_features": [
                {"name": "mounting_holes", "type": "constraint_region", "count": 4},
                {"name": "load_points", "type": "load_region", "count": 2}
            ],
            "recommendations": [
                "Identify stress concentration areas",
                "Define appropriate boundary conditions"
            ],
            "confidence": 0.78
        }
        
        mock_openai.return_value.choices = [
            Mock(message=Mock(content=json.dumps(mock_response)))
        ]
        
        agent = GeometryAgent(mock_db_session)
        request_data = {
            "cad_files": ["bracket.step"],
            "physics_type": "structural",
            "user_requirements": "Structural analysis of mounting bracket"
        }
        
        result = await agent.process_request(request_data, sample_context)
        
        assert result.success
        assert result.confidence_score == 0.78
        assert "structural_features" in result.data
    
    @pytest.mark.asyncio
    async def test_invalid_cad_files(self, mock_db_session, sample_context):
        """Test handling of invalid CAD files"""
        agent = GeometryAgent(mock_db_session)
        request_data = {
            "cad_files": [],  # Empty CAD files
            "physics_type": "cfd"
        }
        
        result = await agent.process_request(request_data, sample_context)
        
        assert not result.success
        assert "No CAD files provided" in result.error_message

class TestMeshAgent:
    """Test mesh generation agent"""
    
    @pytest.mark.asyncio
    async def test_generate_cfd_mesh_strategy(self, mock_db_session, sample_context, mock_openai):
        """Test mesh strategy generation for CFD"""
        mock_response = {
            "mesh_strategy": {
                "element_type": "tetrahedral",
                "base_size": 0.1,
                "refinement_regions": [
                    {"region": "near_walls", "size": 0.02, "layers": 5},
                    {"region": "wake", "size": 0.05, "adaptive": True}
                ]
            },
            "quality_targets": {
                "min_angle": 15,
                "max_aspect_ratio": 100,
                "skewness_threshold": 0.8
            },
            "estimated_elements": 2500000,
            "recommendations": [
                "Use boundary layer mesh near walls",
                "Consider adaptive refinement in wake region"
            ],
            "confidence": 0.82
        }
        
        mock_openai.return_value.choices = [
            Mock(message=Mock(content=json.dumps(mock_response)))
        ]
        
        agent = MeshAgent(mock_db_session)
        request_data = {
            "geometry_data": {
                "complexity": "medium",
                "characteristic_length": 2.1,
                "flow_regions": [{"name": "inlet"}, {"name": "outlet"}]
            },
            "physics_type": "cfd",
            "quality_requirements": {"accuracy": "high"}
        }
        
        result = await agent.process_request(request_data, sample_context)
        
        assert result.success
        assert result.confidence_score == 0.82
        assert "mesh_strategy" in result.data
        assert "quality_targets" in result.data
        assert result.data["estimated_elements"] > 0
    
    @pytest.mark.asyncio
    async def test_structural_mesh_strategy(self, mock_db_session, sample_context, mock_openai):
        """Test mesh strategy for structural analysis"""
        sample_context.physics_type = "structural"
        
        mock_response = {
            "mesh_strategy": {
                "element_type": "hexahedral",
                "base_size": 0.05,
                "refinement_regions": [
                    {"region": "stress_concentrations", "size": 0.01},
                    {"region": "contact_areas", "size": 0.02}
                ]
            },
            "quality_targets": {
                "min_angle": 20,
                "max_aspect_ratio": 50,
                "jacobian_threshold": 0.1
            },
            "estimated_elements": 850000,
            "recommendations": [
                "Use fine mesh at stress concentration points",
                "Ensure proper element connectivity at interfaces"
            ],
            "confidence": 0.88
        }
        
        mock_openai.return_value.choices = [
            Mock(message=Mock(content=json.dumps(mock_response)))
        ]
        
        agent = MeshAgent(mock_db_session)
        request_data = {
            "geometry_data": {
                "complexity": "high",
                "structural_features": [{"name": "mounting_holes"}]
            },
            "physics_type": "structural"
        }
        
        result = await agent.process_request(request_data, sample_context)
        
        assert result.success
        assert "hexahedral" in result.data["mesh_strategy"]["element_type"]

class TestMaterialsAgent:
    """Test materials assignment agent"""
    
    @pytest.mark.asyncio
    async def test_assign_cfd_materials(self, mock_db_session, sample_context, mock_openai):
        """Test material assignment for CFD"""
        mock_response = {
            "material_assignments": [
                {
                    "region": "fluid_domain",
                    "material": "air",
                    "properties": {
                        "density": 1.225,
                        "dynamic_viscosity": 1.81e-5,
                        "thermal_conductivity": 0.0242
                    }
                },
                {
                    "region": "solid_walls",
                    "material": "aluminum",
                    "properties": {
                        "density": 2700,
                        "thermal_conductivity": 237
                    }
                }
            ],
            "material_database": {
                "air": {"type": "fluid", "compressible": False},
                "aluminum": {"type": "solid", "thermal_expansion": 2.31e-5}
            },
            "recommendations": [
                "Consider temperature-dependent properties for high-speed flows",
                "Verify material properties match operating conditions"
            ],
            "confidence": 0.91
        }
        
        mock_openai.return_value.choices = [
            Mock(message=Mock(content=json.dumps(mock_response)))
        ]
        
        agent = MaterialsAgent(mock_db_session)
        request_data = {
            "geometry_data": {"flow_regions": [{"name": "inlet"}]},
            "mesh_data": {"element_type": "tetrahedral"},
            "physics_type": "cfd",
            "operating_conditions": {"temperature": 293, "pressure": 101325}
        }
        
        result = await agent.process_request(request_data, sample_context)
        
        assert result.success
        assert result.confidence_score == 0.91
        assert "material_assignments" in result.data
        assert len(result.data["material_assignments"]) > 0
    
    @pytest.mark.asyncio
    async def test_structural_materials(self, mock_db_session, sample_context, mock_openai):
        """Test material assignment for structural analysis"""
        sample_context.physics_type = "structural"
        
        mock_response = {
            "material_assignments": [
                {
                    "region": "main_body",
                    "material": "steel",
                    "properties": {
                        "density": 7850,
                        "elastic_modulus": 200e9,
                        "poisson_ratio": 0.3,
                        "yield_strength": 250e6
                    }
                }
            ],
            "material_database": {
                "steel": {
                    "type": "isotropic",
                    "fatigue_limit": 120e6,
                    "ultimate_strength": 400e6
                }
            },
            "recommendations": [
                "Consider material nonlinearity for high stress regions",
                "Verify safety factors meet design requirements"
            ],
            "confidence": 0.86
        }
        
        mock_openai.return_value.choices = [
            Mock(message=Mock(content=json.dumps(mock_response)))
        ]
        
        agent = MaterialsAgent(mock_db_session)
        request_data = {
            "geometry_data": {"structural_features": [{"name": "mounting_holes"}]},
            "physics_type": "structural",
            "load_conditions": {"max_force": 5000}
        }
        
        result = await agent.process_request(request_data, sample_context)
        
        assert result.success
        assert "elastic_modulus" in result.data["material_assignments"][0]["properties"]

class TestPhysicsAgent:
    """Test physics setup agent"""
    
    @pytest.mark.asyncio
    async def test_setup_cfd_physics(self, mock_db_session, sample_context, mock_openai):
        """Test physics setup for CFD"""
        mock_response = {
            "physics_models": {
                "turbulence": {
                    "model": "k-epsilon",
                    "wall_treatment": "enhanced_wall_treatment"
                },
                "heat_transfer": {
                    "enabled": True,
                    "model": "energy_equation"
                }
            },
            "boundary_conditions": [
                {
                    "region": "inlet",
                    "type": "velocity_inlet",
                    "velocity": 30,
                    "temperature": 293
                },
                {
                    "region": "outlet",
                    "type": "pressure_outlet",
                    "pressure": 0
                },
                {
                    "region": "walls",
                    "type": "wall",
                    "heat_flux": 0
                }
            ],
            "solver_settings": {
                "pressure_velocity_coupling": "SIMPLE",
                "discretization": "second_order",
                "convergence_criteria": 1e-6
            },
            "recommendations": [
                "Monitor residuals for convergence",
                "Consider mesh independence study"
            ],
            "confidence": 0.89
        }
        
        mock_openai.return_value.choices = [
            Mock(message=Mock(content=json.dumps(mock_response)))
        ]
        
        agent = PhysicsAgent(mock_db_session)
        request_data = {
            "geometry_data": {"flow_regions": [{"name": "inlet"}]},
            "mesh_data": {"estimated_elements": 2500000},
            "materials_data": {"material_assignments": [{"material": "air"}]},
            "physics_type": "cfd",
            "operating_conditions": {"velocity": 30, "temperature": 293}
        }
        
        result = await agent.process_request(request_data, sample_context)
        
        assert result.success
        assert result.confidence_score == 0.89
        assert "physics_models" in result.data
        assert "boundary_conditions" in result.data
        assert "solver_settings" in result.data
    
    @pytest.mark.asyncio
    async def test_structural_physics_setup(self, mock_db_session, sample_context, mock_openai):
        """Test physics setup for structural analysis"""
        sample_context.physics_type = "structural"
        
        mock_response = {
            "physics_models": {
                "analysis_type": "static",
                "nonlinearity": {
                    "geometric": False,
                    "material": False
                }
            },
            "boundary_conditions": [
                {
                    "region": "mounting_holes",
                    "type": "fixed_support"
                },
                {
                    "region": "load_points",
                    "type": "force",
                    "magnitude": 5000,
                    "direction": [0, 0, -1]
                }
            ],
            "solver_settings": {
                "solver_type": "direct",
                "convergence_tolerance": 1e-8,
                "max_iterations": 1000
            },
            "recommendations": [
                "Verify boundary conditions represent actual constraints",
                "Check for rigid body modes"
            ],
            "confidence": 0.84
        }
        
        mock_openai.return_value.choices = [
            Mock(message=Mock(content=json.dumps(mock_response)))
        ]
        
        agent = PhysicsAgent(mock_db_session)
        request_data = {
            "geometry_data": {"structural_features": [{"name": "mounting_holes"}]},
            "materials_data": {"material_assignments": [{"material": "steel"}]},
            "physics_type": "structural",
            "load_conditions": {"max_force": 5000}
        }
        
        result = await agent.process_request(request_data, sample_context)
        
        assert result.success
        assert "analysis_type" in result.data["physics_models"]

class TestPromptTemplate:
    """Test prompt template functionality"""
    
    def test_geometry_prompt_template(self):
        """Test geometry agent prompt template"""
        template = PromptTemplate.get_template("geometry", "cfd")
        
        assert "geometry analysis" in template.lower()
        assert "cfd" in template.lower()
        assert "{cad_files}" in template
        assert "{user_requirements}" in template
    
    def test_mesh_prompt_template(self):
        """Test mesh agent prompt template"""
        template = PromptTemplate.get_template("mesh", "structural")
        
        assert "mesh" in template.lower()
        assert "structural" in template.lower()
        assert "{geometry_data}" in template
    
    def test_invalid_template(self):
        """Test invalid template request"""
        with pytest.raises(ValueError):
            PromptTemplate.get_template("invalid_agent", "cfd")

class TestAgentResponse:
    """Test agent response handling"""
    
    def test_successful_response(self):
        """Test successful agent response"""
        response = AgentResponse(
            success=True,
            data={"test": "data"},
            confidence_score=0.85,
            processing_time=1.5
        )
        
        assert response.success
        assert response.data["test"] == "data"
        assert response.confidence_score == 0.85
        assert response.processing_time == 1.5
        assert response.error_message is None
    
    def test_failed_response(self):
        """Test failed agent response"""
        response = AgentResponse(
            success=False,
            data={},
            confidence_score=0.0,
            processing_time=0.5,
            error_message="Test error"
        )
        
        assert not response.success
        assert response.error_message == "Test error"
        assert response.confidence_score == 0.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
