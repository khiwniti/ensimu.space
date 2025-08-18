"""
Comprehensive tests for enhanced agents
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import numpy as np

from app.libs.enhanced_agents import (
    EnhancedGeometryAgent,
    EnhancedMeshAgent,
    EnhancedMaterialAgent,
    EnhancedKnowledgeAgent,
    AgentState,
    AnalysisResult
)

class TestEnhancedGeometryAgent:
    """Test suite for Enhanced Geometry Agent"""
    
    @pytest.fixture
    def geometry_agent(self):
        return EnhancedGeometryAgent()
    
    @pytest.fixture
    def temp_geometry_file(self):
        """Create a temporary STL file for testing"""
        temp_dir = tempfile.mkdtemp()
        stl_file = Path(temp_dir) / "test_geometry.stl"
        
        # Create a simple STL content (mock)
        stl_content = """solid test
facet normal 0.0 0.0 1.0
  outer loop
    vertex 0.0 0.0 0.0
    vertex 1.0 0.0 0.0
    vertex 0.0 1.0 0.0
  endloop
endfacet
endsolid test
"""
        stl_file.write_text(stl_content)
        
        yield str(stl_file)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, geometry_agent):
        """Test agent initialization"""
        assert geometry_agent.name == "Enhanced Geometry Agent"
        assert geometry_agent.state == AgentState.IDLE
        assert geometry_agent.capabilities is not None
        assert "geometry_analysis" in geometry_agent.capabilities
    
    @pytest.mark.asyncio
    async def test_analyze_geometry_success(self, geometry_agent, temp_geometry_file):
        """Test successful geometry analysis"""
        with open(temp_geometry_file, 'rb') as f:
            file_content = f.read()
        
        with patch('pyvista.read') as mock_read:
            # Mock PyVista mesh
            mock_mesh = Mock()
            mock_mesh.n_points = 100
            mock_mesh.n_cells = 50
            mock_mesh.bounds = [-1, 1, -1, 1, -1, 1]
            mock_mesh.volume = 8.0
            mock_mesh.area = 24.0
            mock_read.return_value = mock_mesh
            
            result = await geometry_agent.analyze_geometry(file_content, "test.stl")
            
            assert isinstance(result, dict)
            assert "analysis_summary" in result
            assert "geometry_metrics" in result
            assert result["status"] == "completed"
            assert geometry_agent.state == AgentState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_analyze_geometry_invalid_file(self, geometry_agent):
        """Test geometry analysis with invalid file"""
        invalid_content = b"invalid content"
        
        result = await geometry_agent.analyze_geometry(invalid_content, "invalid.stl")
        
        assert result["status"] == "error"
        assert "error" in result
        assert geometry_agent.state == AgentState.ERROR
    
    @pytest.mark.asyncio
    async def test_validate_geometry_good(self, geometry_agent):
        """Test geometry validation with good geometry"""
        with patch('pyvista.read') as mock_read:
            mock_mesh = Mock()
            mock_mesh.n_points = 1000
            mock_mesh.n_cells = 500
            mock_mesh.is_all_triangles = True
            mock_mesh.volume = 1.0
            mock_read.return_value = mock_mesh
            
            result = await geometry_agent.validate_geometry("/fake/path/geometry.stl")
            
            assert result["is_valid"] is True
            assert result["quality_score"] > 0.5
            assert "recommendations" in result
    
    @pytest.mark.asyncio
    async def test_validate_geometry_poor(self, geometry_agent):
        """Test geometry validation with poor geometry"""
        with patch('pyvista.read') as mock_read:
            mock_mesh = Mock()
            mock_mesh.n_points = 10  # Very low point count
            mock_mesh.n_cells = 5
            mock_mesh.is_all_triangles = False
            mock_mesh.volume = 0.0  # Invalid volume
            mock_read.return_value = mock_mesh
            
            result = await geometry_agent.validate_geometry("/fake/path/poor_geometry.stl")
            
            assert result["is_valid"] is False
            assert result["quality_score"] < 0.5
            assert len(result["issues"]) > 0

class TestEnhancedMeshAgent:
    """Test suite for Enhanced Mesh Agent"""
    
    @pytest.fixture
    def mesh_agent(self):
        return EnhancedMeshAgent()
    
    @pytest.fixture
    def temp_case_dir(self):
        """Create temporary OpenFOAM case directory"""
        temp_dir = tempfile.mkdtemp()
        case_dir = Path(temp_dir) / "test_case"
        case_dir.mkdir()
        
        # Create basic OpenFOAM structure
        (case_dir / "system").mkdir()
        (case_dir / "constant").mkdir()
        (case_dir / "0").mkdir()
        
        # Create basic meshQuality dict
        mesh_quality_content = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      meshQualityDict;
}

maxNonOrtho     65;
maxBoundarySkewness 20;
maxInternalSkewness 4;
maxConcave      80;
minVol          1e-13;
minTetQuality   1e-9;
minArea         -1;
minTwist        0.02;
minDeterminant  0.001;
minFaceWeight   0.02;
minVolRatio     0.01;
minTriangleTwist -1;
"""
        (case_dir / "system" / "meshQualityDict").write_text(mesh_quality_content)
        
        yield str(case_dir)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_mesh_agent_initialization(self, mesh_agent):
        """Test mesh agent initialization"""
        assert mesh_agent.name == "Enhanced Mesh Agent"
        assert mesh_agent.state == AgentState.IDLE
        assert "mesh_generation" in mesh_agent.capabilities
        assert "mesh_quality_analysis" in mesh_agent.capabilities
    
    @pytest.mark.asyncio
    async def test_generate_mesh_success(self, mesh_agent, temp_case_dir):
        """Test successful mesh generation"""
        mesh_params = {
            "refinement_level": 2,
            "boundary_layers": True,
            "max_cell_size": 0.1
        }
        
        with patch('subprocess.run') as mock_run:
            # Mock successful blockMesh execution
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "blockMesh completed successfully"
            
            result = await mesh_agent.generate_mesh(temp_case_dir, mesh_params)
            
            assert result["status"] == "completed"
            assert "mesh_statistics" in result
            assert mesh_agent.state == AgentState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_analyze_mesh_quality(self, mesh_agent, temp_case_dir):
        """Test mesh quality analysis"""
        with patch('subprocess.run') as mock_run:
            # Mock checkMesh output
            mock_output = """Checking geometry...
Overall domain bounding box (-1 -1 -1) (1 1 1)
Mesh stats
    points:           1000
    internal points:  800
    faces:            2000
    internal faces:   1800
    cells:            500
    boundary patches: 6
    point zones:      0
    face zones:       0
    cell zones:       0

Overall number of cells of each type:
    hexahedra:     450
    prisms:        50
    wedges:        0
    pyramids:      0
    tet wedges:    0
    tetrahedra:    0
    polyhedra:     0

Checking topology...
    Boundary definition OK.
    Cell to face addressing OK.
    Point usage OK.
    Upper triangular ordering OK.
    Face vertices OK.
    Number of regions: 1 (OK).

Checking patch topology for multiply connected surfaces...
    Patch               Faces    Points   Surface topology
    inlet               10       20       ok (non-closed singly connected)
    outlet              10       20       ok (non-closed singly connected)
    walls               30       60       ok (non-closed singly connected)

Checking geometry...
    Overall domain bounding box (-1 -1 -1) (1 1 1)
    Mesh has 3 geometric (non-empty/wedge) directions (x y z)
    Mesh has 3 solution (non-empty) directions (x y z)
    Boundary openness (-1.23456e-16 -2.34567e-16 -3.45678e-16) OK.
    Max cell openness = 2.34567e-05 OK.
    Max aspect ratio = 1.5 OK.
    Minimum face area = 0.001. Maximum face area = 0.01.  Face area magnitudes OK.
    Min volume = 0.0001. Max volume = 0.001.  Total volume = 8.  Cell volumes OK.
    Mesh non-orthogonality Max: 45 average: 15
    Non-orthogonality check OK.
    Face pyramids OK.
    Max skewness = 0.8 OK.
    Coupled point location match (average 0) OK.

Mesh OK.
"""
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = mock_output
            
            result = await mesh_agent.analyze_mesh_quality(temp_case_dir)
            
            assert result["status"] == "completed"
            assert "quality_metrics" in result
            assert "recommendations" in result
            assert result["quality_metrics"]["max_non_orthogonality"] == 45
            assert result["quality_metrics"]["max_skewness"] == 0.8

class TestEnhancedMaterialAgent:
    """Test suite for Enhanced Material Agent"""
    
    @pytest.fixture
    def material_agent(self):
        return EnhancedMaterialAgent()
    
    @pytest.fixture
    def temp_case_dir(self):
        """Create temporary case directory"""
        temp_dir = tempfile.mkdtemp()
        case_dir = Path(temp_dir) / "test_case"
        case_dir.mkdir()
        
        # Create basic structure
        (case_dir / "constant").mkdir()
        (case_dir / "system").mkdir()
        
        yield str(case_dir)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_material_agent_initialization(self, material_agent):
        """Test material agent initialization"""
        assert material_agent.name == "Enhanced Material Agent"
        assert material_agent.state == AgentState.IDLE
        assert "material_definition" in material_agent.capabilities
        assert "physics_setup" in material_agent.capabilities
    
    @pytest.mark.asyncio
    async def test_setup_physics_incompressible(self, material_agent, temp_case_dir):
        """Test incompressible flow physics setup"""
        physics_config = {
            "solver_type": "incompressible",
            "turbulence_model": "kOmegaSST",
            "fluid_properties": {
                "density": 1.225,
                "viscosity": 1.8e-05
            },
            "boundary_conditions": {
                "inlet": {"type": "velocity", "value": [10, 0, 0]},
                "outlet": {"type": "pressure", "value": 0},
                "walls": {"type": "wall"}
            }
        }
        
        result = await material_agent.setup_physics(temp_case_dir, physics_config)
        
        assert result["status"] == "completed"
        assert "files_created" in result
        assert material_agent.state == AgentState.COMPLETED
        
        # Check if files were created
        transport_props = Path(temp_case_dir) / "constant" / "transportProperties"
        turbulence_props = Path(temp_case_dir) / "constant" / "turbulenceProperties"
        
        assert transport_props.exists()
        assert turbulence_props.exists()
    
    @pytest.mark.asyncio
    async def test_validate_physics_setup(self, material_agent, temp_case_dir):
        """Test physics setup validation"""
        # Create some basic physics files
        transport_content = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      transportProperties;
}

nu              [0 2 -1 0 0 0 0] 1.48e-05;
"""
        (Path(temp_case_dir) / "constant" / "transportProperties").write_text(transport_content)
        
        result = await material_agent.validate_physics_setup(temp_case_dir)
        
        assert "validation_results" in result
        assert "issues" in result
        assert "recommendations" in result

class TestEnhancedKnowledgeAgent:
    """Test suite for Enhanced Knowledge Agent"""
    
    @pytest.fixture
    def knowledge_agent(self):
        return EnhancedKnowledgeAgent()
    
    @pytest.mark.asyncio
    async def test_knowledge_agent_initialization(self, knowledge_agent):
        """Test knowledge agent initialization"""
        assert knowledge_agent.name == "Enhanced Knowledge Agent"
        assert knowledge_agent.state == AgentState.IDLE
        assert "technical_guidance" in knowledge_agent.capabilities
        assert "rag_search" in knowledge_agent.capabilities
    
    @pytest.mark.asyncio
    async def test_process_query_basic(self, knowledge_agent):
        """Test basic query processing"""
        with patch.object(knowledge_agent, '_search_knowledge_base') as mock_search:
            mock_search.return_value = [
                {"content": "OpenFOAM mesh generation guide", "score": 0.9},
                {"content": "Best practices for CFD meshing", "score": 0.8}
            ]
            
            result = await knowledge_agent.process_query(
                query="How to generate a good mesh in OpenFOAM?",
                context="mesh_generation"
            )
            
            assert "answer" in result
            assert "confidence" in result
            assert "references" in result
            assert result["confidence"] > 0.5
    
    @pytest.mark.asyncio
    async def test_process_query_with_parameters(self, knowledge_agent):
        """Test query processing with specific parameters"""
        with patch.object(knowledge_agent, '_search_knowledge_base') as mock_search:
            mock_search.return_value = [
                {"content": "Turbulence modeling in CFD", "score": 0.95}
            ]
            
            result = await knowledge_agent.process_query(
                query="What turbulence model should I use?",
                context="physics_setup",
                parameters={"flow_type": "external", "reynolds_number": 1e6}
            )
            
            assert "answer" in result
            assert "turbulence" in result["answer"].lower()
            assert result["confidence"] > 0.7
    
    @pytest.mark.asyncio
    async def test_search_knowledge_base(self, knowledge_agent):
        """Test knowledge base search functionality"""
        with patch('chromadb.Client') as mock_client:
            # Mock ChromaDB client and collection
            mock_collection = Mock()
            mock_collection.query.return_value = {
                'documents': [['Sample CFD documentation']],
                'distances': [[0.2]],
                'metadatas': [[{'source': 'openfoam_guide.pdf'}]]
            }
            mock_client.return_value.get_collection.return_value = mock_collection
            
            results = await knowledge_agent._search_knowledge_base("mesh generation")
            
            assert len(results) > 0
            assert "content" in results[0]
            assert "score" in results[0]

class TestAgentIntegration:
    """Integration tests for agent interactions"""
    
    @pytest.fixture
    def agents(self):
        return {
            "geometry": EnhancedGeometryAgent(),
            "mesh": EnhancedMeshAgent(),
            "material": EnhancedMaterialAgent(),
            "knowledge": EnhancedKnowledgeAgent()
        }
    
    @pytest.mark.asyncio
    async def test_workflow_agent_communication(self, agents):
        """Test communication between agents in a workflow"""
        geometry_agent = agents["geometry"]
        mesh_agent = agents["mesh"]
        
        # Mock geometry analysis result
        geometry_result = {
            "status": "completed",
            "geometry_metrics": {
                "volume": 1.0,
                "surface_area": 6.0,
                "characteristic_length": 0.1
            }
        }
        
        # Test that mesh agent can use geometry results
        with patch.object(mesh_agent, 'generate_mesh') as mock_generate:
            mock_generate.return_value = {"status": "completed", "mesh_statistics": {}}
            
            # Mesh agent should adapt parameters based on geometry
            mesh_params = mesh_agent._adapt_mesh_parameters_from_geometry(geometry_result)
            
            assert "max_cell_size" in mesh_params
            assert mesh_params["max_cell_size"] <= geometry_result["geometry_metrics"]["characteristic_length"] / 10
    
    @pytest.mark.asyncio
    async def test_error_propagation(self, agents):
        """Test error propagation between agents"""
        geometry_agent = agents["geometry"]
        
        # Simulate geometry agent error
        geometry_agent.state = AgentState.ERROR
        geometry_agent.error_message = "Invalid geometry file"
        
        # Check that downstream agents can handle the error
        mesh_agent = agents["mesh"]
        
        with pytest.raises(Exception) as exc_info:
            await mesh_agent.generate_mesh("/fake/path", {})
        
        assert "prerequisite" in str(exc_info.value).lower() or "geometry" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_agent_state_transitions(self, agents):
        """Test proper agent state transitions"""
        agent = agents["geometry"]
        
        # Initial state
        assert agent.state == AgentState.IDLE
        
        # Start processing
        await agent._set_state(AgentState.PROCESSING)
        assert agent.state == AgentState.PROCESSING
        
        # Complete successfully
        await agent._set_state(AgentState.COMPLETED)
        assert agent.state == AgentState.COMPLETED
        
        # Reset for next task
        await agent.reset()
        assert agent.state == AgentState.IDLE

class TestPerformanceAndScaling:
    """Performance and scaling tests"""
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(self):
        """Test concurrent execution of multiple agents"""
        agents = [EnhancedGeometryAgent() for _ in range(5)]
        
        async def mock_analysis(agent):
            await asyncio.sleep(0.1)  # Simulate work
            return {"status": "completed", "agent_id": id(agent)}
        
        # Execute agents concurrently
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*[mock_analysis(agent) for agent in agents])
        end_time = asyncio.get_event_loop().time()
        
        assert len(results) == 5
        assert all(result["status"] == "completed" for result in results)
        # Should complete in roughly the time of one execution (parallel)
        assert (end_time - start_time) < 0.5
    
    @pytest.mark.asyncio
    async def test_memory_cleanup(self):
        """Test that agents properly clean up memory"""
        agent = EnhancedGeometryAgent()
        
        # Simulate large data processing
        large_data = np.random.rand(1000, 1000)
        agent._temp_data = large_data
        
        # Reset agent
        await agent.reset()
        
        # Check cleanup
        assert not hasattr(agent, '_temp_data') or agent._temp_data is None

# Fixtures and utilities
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_openfoam_case():
    """Create a mock OpenFOAM case directory structure"""
    temp_dir = tempfile.mkdtemp()
    case_dir = Path(temp_dir) / "test_case"
    
    # Create directory structure
    case_dir.mkdir()
    (case_dir / "0").mkdir()
    (case_dir / "constant").mkdir()
    (case_dir / "system").mkdir()
    
    # Create basic files
    (case_dir / "system" / "controlDict").touch()
    (case_dir / "system" / "fvSchemes").touch()
    (case_dir / "system" / "fvSolution").touch()
    (case_dir / "constant" / "transportProperties").touch()
    
    yield str(case_dir)
    
    # Cleanup
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])