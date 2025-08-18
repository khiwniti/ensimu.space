"""
Pytest configuration and shared fixtures for enhanced simulation testing
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np

# Import test utilities
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Test configuration
pytest_plugins = ["pytest_asyncio"]

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_openfoam_case(temp_dir):
    """Create a complete mock OpenFOAM case directory"""
    case_dir = Path(temp_dir) / "test_case"
    case_dir.mkdir()
    
    # Create directory structure
    (case_dir / "0").mkdir()
    (case_dir / "constant").mkdir()
    (case_dir / "system").mkdir()
    (case_dir / "postProcessing").mkdir()
    
    # Create basic files
    create_mock_control_dict(case_dir / "system" / "controlDict")
    create_mock_transport_properties(case_dir / "constant" / "transportProperties")
    create_mock_boundary_conditions(case_dir / "0")
    create_mock_mesh_files(case_dir / "constant")
    create_mock_solution_data(case_dir / "postProcessing")
    
    yield str(case_dir)

def create_mock_control_dict(file_path):
    """Create mock controlDict file"""
    content = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}

application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1000;
deltaT          1;
writeControl    timeStep;
writeInterval   100;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

functions
{
    forceCoeffs
    {
        type            forceCoeffs;
        libs            ("libforces.so");
        writeControl    timeStep;
        writeInterval   1;
        patches         (walls);
        rho             rhoInf;
        rhoInf          1.225;
        liftDir         (0 1 0);
        dragDir         (1 0 0);
        CofR            (0 0 0);
        pitchAxis       (0 0 1);
        magUInf         10;
        lRef            1;
        Aref            1;
    }
}
"""
    file_path.write_text(content)

def create_mock_transport_properties(file_path):
    """Create mock transportProperties file"""
    content = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      transportProperties;
}

transportModel  Newtonian;
nu              [0 2 -1 0 0 0 0] 1.48e-05;
"""
    file_path.write_text(content)

def create_mock_boundary_conditions(zero_dir):
    """Create mock boundary condition files"""
    # Velocity field
    u_content = """FoamFile
{
    version     2.0;
    format      ascii;
    class       volVectorField;
    object      U;
}

dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (10 0 0);

boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform (10 0 0);
    }
    outlet
    {
        type            zeroGradient;
    }
    walls
    {
        type            noSlip;
    }
    frontAndBack
    {
        type            empty;
    }
}
"""
    (zero_dir / "U").write_text(u_content)
    
    # Pressure field
    p_content = """FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      p;
}

dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;

boundaryField
{
    inlet
    {
        type            zeroGradient;
    }
    outlet
    {
        type            fixedValue;
        value           uniform 0;
    }
    walls
    {
        type            zeroGradient;
    }
    frontAndBack
    {
        type            empty;
    }
}
"""
    (zero_dir / "p").write_text(p_content)

def create_mock_mesh_files(constant_dir):
    """Create mock mesh files"""
    # polyMesh directory
    poly_mesh_dir = constant_dir / "polyMesh"
    poly_mesh_dir.mkdir()
    
    # Mock points file
    points_content = """FoamFile
{
    version     2.0;
    format      ascii;
    class       vectorField;
    object      points;
}

8
(
(0 0 0)
(1 0 0)
(1 1 0)
(0 1 0)
(0 0 1)
(1 0 1)
(1 1 1)
(0 1 1)
)
"""
    (poly_mesh_dir / "points").write_text(points_content)
    
    # Mock faces file
    faces_content = """FoamFile
{
    version     2.0;
    format      ascii;
    class       faceList;
    object      faces;
}

12
(
4(0 4 7 3)
4(2 6 5 1)
4(0 1 5 4)
4(3 7 6 2)
4(0 3 2 1)
4(4 5 6 7)
4(0 4 7 3)
4(2 6 5 1)
4(0 1 5 4)
4(3 7 6 2)
4(0 3 2 1)
4(4 5 6 7)
)
"""
    (poly_mesh_dir / "faces").write_text(faces_content)

def create_mock_solution_data(postprocessing_dir):
    """Create mock solution data files"""
    # Create forces directory
    forces_dir = postprocessing_dir / "forceCoeffs" / "0"
    forces_dir.mkdir(parents=True)
    
    # Mock force coefficients data
    force_data = """# Time    Cd    Cs    Cl    CmRoll    CmPitch    CmYaw    Cd(f)    Cd(r)    Cs(f)    Cs(r)    Cl(f)    Cl(r)
1         0.5    0.0    0.1    0.0      0.05      0.0     0.3      0.2      0.0      0.0      0.05     0.05
2         0.48   0.0    0.12   0.0      0.06      0.0     0.28     0.2      0.0      0.0      0.06     0.06
3         0.46   0.0    0.14   0.0      0.07      0.0     0.26     0.2      0.0      0.0      0.07     0.07
4         0.45   0.0    0.15   0.0      0.075     0.0     0.25     0.2      0.0      0.0      0.075    0.075
5         0.44   0.0    0.16   0.0      0.08      0.0     0.24     0.2      0.0      0.0      0.08     0.08
"""
    (forces_dir / "forceCoeffs.dat").write_text(force_data)
    
    # Create residuals directory
    residuals_dir = postprocessing_dir / "residuals" / "0"
    residuals_dir.mkdir(parents=True)
    
    # Mock residuals data
    residuals_data = """# Time    UxFinalRes    UyFinalRes    UzFinalRes    pFinalRes
1         1e-3          1e-3          1e-3          1e-4
2         1e-4          1e-4          1e-4          1e-5
3         1e-5          1e-5          1e-5          1e-6
4         1e-6          1e-6          1e-6          1e-7
5         1e-7          1e-7          1e-7          1e-8
"""
    (residuals_dir / "residuals.dat").write_text(residuals_data)

@pytest.fixture
def mock_geometry_file(temp_dir):
    """Create a mock STL geometry file"""
    stl_file = Path(temp_dir) / "test_geometry.stl"
    
    stl_content = """solid test_geometry
facet normal 0.0 0.0 1.0
  outer loop
    vertex 0.0 0.0 0.0
    vertex 1.0 0.0 0.0
    vertex 0.0 1.0 0.0
  endloop
endfacet
facet normal 0.0 0.0 1.0
  outer loop
    vertex 1.0 0.0 0.0
    vertex 1.0 1.0 0.0
    vertex 0.0 1.0 0.0
  endloop
endfacet
facet normal 0.0 0.0 -1.0
  outer loop
    vertex 0.0 0.0 1.0
    vertex 0.0 1.0 1.0
    vertex 1.0 0.0 1.0
  endloop
endfacet
facet normal 0.0 0.0 -1.0
  outer loop
    vertex 1.0 0.0 1.0
    vertex 0.0 1.0 1.0
    vertex 1.0 1.0 1.0
  endloop
endfacet
endsolid test_geometry
"""
    stl_file.write_text(stl_content)
    yield str(stl_file)

@pytest.fixture
def mock_pyvista_mesh():
    """Create a mock PyVista mesh object"""
    mock_mesh = Mock()
    mock_mesh.n_points = 1000
    mock_mesh.n_cells = 500
    mock_mesh.bounds = [-1, 1, -1, 1, -1, 1]
    mock_mesh.volume = 8.0
    mock_mesh.area = 24.0
    mock_mesh.is_all_triangles = True
    return mock_mesh

@pytest.fixture
def mock_chromadb_collection():
    """Create a mock ChromaDB collection"""
    mock_collection = Mock()
    mock_collection.query.return_value = {
        'documents': [['OpenFOAM turbulence modeling guide', 'CFD best practices']],
        'distances': [[0.2, 0.3]],
        'metadatas': [[{'source': 'openfoam_guide.pdf'}, {'source': 'cfd_handbook.pdf'}]]
    }
    return mock_collection

@pytest.fixture
def sample_workflow_config():
    """Sample workflow configuration for testing"""
    return {
        "simulation_type": "external_aerodynamics",
        "description": "Test external aerodynamics simulation",
        "case_directory": "/tmp/test_case",
        "geometry_file": "test.stl",
        "parameters": {
            "velocity": 10.0,
            "reference_area": 1.0,
            "reference_length": 1.0,
            "density": 1.225,
            "viscosity": 1.8e-05
        },
        "mesh_config": {
            "refinement_level": 2,
            "boundary_layers": True,
            "max_cell_size": 0.1,
            "min_cell_size": 0.001
        },
        "physics_config": {
            "solver_type": "incompressible",
            "turbulence_model": "kOmegaSST",
            "time_scheme": "steady"
        },
        "advanced_settings": {
            "parallel_execution": True,
            "hitl_enabled": False,
            "error_recovery": True,
            "performance_monitoring": True
        }
    }

@pytest.fixture
def sample_post_processing_config():
    """Sample post-processing configuration for testing"""
    return {
        "case_directory": "/tmp/test_case",
        "output_directory": "/tmp/test_case/postProcessing/analysis",
        "analysis_types": ["convergence", "forces", "pressure_drop"],
        "visualization_formats": ["png", "html", "vtk"],
        "case_data": {
            "reference_area": 1.0,
            "velocity": 10.0,
            "density": 1.225,
            "reference_length": 1.0
        },
        "parallel_processing": True,
        "generate_report": True
    }

@pytest.fixture
def mock_agent_responses():
    """Mock responses from various agents"""
    return {
        "geometry": {
            "status": "completed",
            "geometry_metrics": {
                "volume": 1.0,
                "surface_area": 6.0,
                "characteristic_length": 0.5,
                "complexity": "medium"
            },
            "validation_result": {
                "is_valid": True,
                "quality_score": 0.85,
                "issues": [],
                "recommendations": ["Consider surface smoothing"]
            }
        },
        "mesh": {
            "status": "completed",
            "mesh_statistics": {
                "cells": 50000,
                "points": 25000,
                "faces": 100000,
                "max_aspect_ratio": 10.5,
                "max_skewness": 0.8,
                "max_non_orthogonality": 45
            },
            "quality_assessment": {
                "overall_quality": "good",
                "quality_score": 0.78,
                "recommendations": ["Improve boundary layer mesh"]
            }
        },
        "material": {
            "status": "completed",
            "files_created": [
                "transportProperties",
                "turbulenceProperties",
                "fvSchemes",
                "fvSolution",
                "boundary_conditions"
            ],
            "physics_setup": {
                "solver": "simpleFoam",
                "turbulence_model": "kOmegaSST",
                "boundary_conditions": {
                    "inlet": "velocity_inlet",
                    "outlet": "pressure_outlet",
                    "walls": "no_slip_wall"
                }
            }
        },
        "knowledge": {
            "answer": "For external aerodynamics, use kOmegaSST turbulence model with appropriate y+ values",
            "confidence": 0.9,
            "references": [
                "OpenFOAM_User_Guide.pdf",
                "Turbulence_Modeling_Handbook.pdf"
            ],
            "processing_time": 0.15
        }
    }

@pytest.fixture
def test_app():
    """Create a test FastAPI application"""
    from app.apis.enhanced_simulation import router as enhanced_simulation_router
    
    app = FastAPI()
    app.include_router(enhanced_simulation_router, prefix="/enhanced-simulation")
    
    return app

@pytest.fixture
def test_client(test_app):
    """Create a test client"""
    return TestClient(test_app)

# Utility functions for tests
def assert_workflow_state_valid(state_data):
    """Assert that workflow state data is valid"""
    required_fields = [
        "workflow_id", "status", "progress", "current_stage",
        "created_at", "updated_at"
    ]
    for field in required_fields:
        assert field in state_data, f"Missing required field: {field}"
    
    assert 0 <= state_data["progress"] <= 100, "Progress should be between 0 and 100"
    assert state_data["status"] in [
        "initializing", "running", "completed", "error", 
        "cancelled", "checkpoint_pending"
    ], f"Invalid status: {state_data['status']}"

def assert_agent_response_valid(response_data):
    """Assert that agent response data is valid"""
    required_fields = ["status"]
    for field in required_fields:
        assert field in response_data, f"Missing required field: {field}"
    
    assert response_data["status"] in [
        "completed", "error", "processing"
    ], f"Invalid status: {response_data['status']}"

def create_test_numpy_data(size=100):
    """Create test numpy data for performance tests"""
    return {
        "time": np.linspace(0, 100, size),
        "residuals": np.exp(-np.linspace(0, 5, size)) + 0.001 * np.random.random(size),
        "forces": 0.5 + 0.1 * np.sin(np.linspace(0, 10, size)) + 0.02 * np.random.random(size),
        "pressure": np.random.normal(0, 1, size)
    }

# Markers for different test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.performance = pytest.mark.performance
pytest.mark.slow = pytest.mark.slow

# Test data constants
TEST_SIMULATION_TYPES = [
    "external_aerodynamics",
    "internal_flow", 
    "heat_transfer",
    "multiphase"
]

TEST_ANALYSIS_TYPES = [
    "convergence",
    "forces",
    "pressure_drop",
    "heat_flux",
    "temperature",
    "velocity_profiles"
]

TEST_TURBULENCE_MODELS = [
    "kEpsilon",
    "kOmegaSST",
    "LES",
    "laminar"
]