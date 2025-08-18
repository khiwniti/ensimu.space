"""
Integration tests for CAE preprocessing functionality.
Tests the complete workflow from project creation to results export.
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Mock the main app creation to avoid dependency issues
@pytest.fixture
def mock_app():
    """Create a mock FastAPI app for testing."""
    from fastapi import FastAPI
    from app.apis.cae_preprocessing import router
    
    app = FastAPI()
    app.include_router(router, prefix="/cae-preprocessing")
    return app

@pytest.fixture
def client(mock_app):
    """Create a test client."""
    return TestClient(mock_app)

@pytest.fixture
def sample_project_data():
    """Sample project data for testing."""
    return {
        "name": "Test CAE Project",
        "description": "Integration test project for CAE preprocessing"
    }

@pytest.fixture
def sample_workflow_request():
    """Sample workflow request data."""
    return {
        "project_id": 1,
        "workflow_type": "full_preprocessing",
        "user_requirements": "Complete CFD preprocessing for external flow analysis",
        "solver_target": "ansys_fluent"
    }

class TestProjectManagement:
    """Test project management functionality."""
    
    def test_create_project(self, client, sample_project_data):
        """Test project creation."""
        response = client.post("/cae-preprocessing/projects", json=sample_project_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == sample_project_data["name"]
        assert data["description"] == sample_project_data["description"]
        assert data["status"] == "created"
        assert "id" in data
    
    def test_get_project(self, client, sample_project_data):
        """Test project retrieval."""
        # Create project first
        create_response = client.post("/cae-preprocessing/projects", json=sample_project_data)
        project_id = create_response.json()["id"]
        
        # Get project
        response = client.get(f"/cae-preprocessing/projects/{project_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == sample_project_data["name"]
    
    def test_list_projects(self, client, sample_project_data):
        """Test project listing."""
        # Create a project first
        client.post("/cae-preprocessing/projects", json=sample_project_data)
        
        # List projects
        response = client.get("/cae-preprocessing/projects")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

class TestFileUpload:
    """Test file upload functionality."""
    
    def test_upload_supported_file(self, client, sample_project_data):
        """Test uploading a supported CAD file."""
        # Create project first
        create_response = client.post("/cae-preprocessing/projects", json=sample_project_data)
        project_id = create_response.json()["id"]
        
        # Create a mock STEP file
        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp_file:
            tmp_file.write(b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;")
            tmp_file.flush()
            
            with open(tmp_file.name, "rb") as f:
                response = client.post(
                    f"/cae-preprocessing/projects/{project_id}/upload",
                    files={"file": ("test.step", f, "application/step")}
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.step"
        assert data["file_type"] == "step"
        assert "file_id" in data
    
    def test_upload_unsupported_file(self, client, sample_project_data):
        """Test uploading an unsupported file type."""
        # Create project first
        create_response = client.post("/cae-preprocessing/projects", json=sample_project_data)
        project_id = create_response.json()["id"]
        
        # Try to upload unsupported file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(b"This is not a CAD file")
            tmp_file.flush()
            
            with open(tmp_file.name, "rb") as f:
                response = client.post(
                    f"/cae-preprocessing/projects/{project_id}/upload",
                    files={"file": ("test.txt", f, "text/plain")}
                )
        
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

class TestAIAgents:
    """Test AI agent functionality."""
    
    @patch('app.libs.cae_agents.AsyncOpenAI')
    def test_geometry_agent_analysis(self, mock_openai, client, sample_project_data):
        """Test geometry agent analysis."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "recommendations": ["Remove small holes", "Simplify fillets"],
            "defeaturing_steps": ["Identify small features", "Remove features"],
            "potential_issues": [],
            "mesh_considerations": ["Use tetrahedral mesh"],
            "tool_preparations": [],
            "validation_results": {},
            "downstream_coordination": {},
            "confidence_score": 0.9
        })
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        # Create project
        create_response = client.post("/cae-preprocessing/projects", json=sample_project_data)
        project_id = create_response.json()["id"]
        
        # Test geometry analysis
        analysis_request = {
            "project_id": project_id,
            "agent_type": "geometry",
            "user_input": "Analyze geometry for CFD simulation"
        }
        
        response = client.post(f"/cae-preprocessing/projects/{project_id}/analyze", json=analysis_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["agent_type"] == "geometry"
        assert "recommendations" in data
        assert "next_steps" in data
    
    def test_material_recommendations(self, client):
        """Test material recommendation endpoint."""
        response = client.post(
            "/cae-preprocessing/materials/recommend",
            params={
                "component_info": "Pressure vessel for chemical processing",
                "operating_conditions": "High temperature and corrosive environment",
                "safety_requirements": "ASME pressure vessel code"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert "available_materials" in data

class TestWorkflowManagement:
    """Test workflow management functionality."""
    
    def test_start_workflow(self, client, sample_project_data, sample_workflow_request):
        """Test workflow initiation."""
        # Create project first
        create_response = client.post("/cae-preprocessing/projects", json=sample_project_data)
        project_id = create_response.json()["id"]
        
        # Update workflow request with actual project ID
        sample_workflow_request["project_id"] = project_id
        
        # Start workflow
        response = client.post("/cae-preprocessing/workflows/start", json=sample_workflow_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "workflow_id" in data
        assert data["status"] == "started"
    
    def test_workflow_status(self, client, sample_project_data, sample_workflow_request):
        """Test workflow status retrieval."""
        # Create project and start workflow
        create_response = client.post("/cae-preprocessing/projects", json=sample_project_data)
        project_id = create_response.json()["id"]
        
        sample_workflow_request["project_id"] = project_id
        workflow_response = client.post("/cae-preprocessing/workflows/start", json=sample_workflow_request)
        workflow_id = workflow_response.json()["workflow_id"]
        
        # Get workflow status
        response = client.get(f"/cae-preprocessing/workflows/{workflow_id}/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["workflow_id"] == workflow_id
        assert "status" in data
        assert "progress" in data

class TestUtilityEndpoints:
    """Test utility endpoints."""
    
    def test_supported_formats(self, client):
        """Test supported formats endpoint."""
        response = client.get("/cae-preprocessing/supported-formats")
        assert response.status_code == 200
        
        data = response.json()
        assert "cad_formats" in data
        assert "STEP" in data["cad_formats"]
        assert "STL" in data["cad_formats"]
    
    def test_materials_endpoint(self, client):
        """Test materials database endpoint."""
        response = client.get("/cae-preprocessing/materials")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5  # Should have at least 5 materials
        
        # Check material structure
        material = data[0]
        required_fields = ["name", "category", "density", "elastic_modulus"]
        for field in required_fields:
            assert field in material
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/cae-preprocessing/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "cae_preprocessing"

class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_nonexistent_project(self, client):
        """Test accessing non-existent project."""
        response = client.get("/cae-preprocessing/projects/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_invalid_agent_type(self, client, sample_project_data):
        """Test invalid agent type."""
        # Create project
        create_response = client.post("/cae-preprocessing/projects", json=sample_project_data)
        project_id = create_response.json()["id"]
        
        # Test invalid agent
        analysis_request = {
            "project_id": project_id,
            "agent_type": "invalid_agent",
            "user_input": "Test analysis"
        }
        
        response = client.post(f"/cae-preprocessing/projects/{project_id}/analyze", json=analysis_request)
        assert response.status_code == 400
        assert "Unknown agent type" in response.json()["detail"]
    
    def test_workflow_not_found(self, client):
        """Test accessing non-existent workflow."""
        response = client.get("/cae-preprocessing/workflows/invalid-id/status")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

# Integration test for complete workflow
class TestCompleteWorkflow:
    """Test complete end-to-end workflow."""
    
    @patch('app.libs.cae_agents.AsyncOpenAI')
    def test_complete_cae_workflow(self, mock_openai, client):
        """Test complete CAE preprocessing workflow."""
        # Mock OpenAI responses
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "workflow_type": "cae_preprocessing",
            "steps": [
                {"name": "geometry_analysis", "agent": "geometry"},
                {"name": "mesh_strategy", "agent": "mesh"},
                {"name": "material_assignment", "agent": "materials"},
                {"name": "physics_setup", "agent": "physics"}
            ]
        })
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        # 1. Create project
        project_data = {"name": "Complete Workflow Test", "description": "End-to-end test"}
        create_response = client.post("/cae-preprocessing/projects", json=project_data)
        assert create_response.status_code == 200
        project_id = create_response.json()["id"]
        
        # 2. Upload file
        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp_file:
            tmp_file.write(b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;")
            tmp_file.flush()
            
            with open(tmp_file.name, "rb") as f:
                upload_response = client.post(
                    f"/cae-preprocessing/projects/{project_id}/upload",
                    files={"file": ("test.step", f, "application/step")}
                )
        assert upload_response.status_code == 200
        
        # 3. Start workflow
        workflow_request = {
            "project_id": project_id,
            "workflow_type": "full_preprocessing",
            "user_requirements": "Complete CFD preprocessing",
            "solver_target": "ansys_fluent"
        }
        workflow_response = client.post("/cae-preprocessing/workflows/start", json=workflow_request)
        assert workflow_response.status_code == 200
        workflow_id = workflow_response.json()["workflow_id"]
        
        # 4. Check workflow status
        status_response = client.get(f"/cae-preprocessing/workflows/{workflow_id}/status")
        assert status_response.status_code == 200
        
        # 5. Test individual agent analysis
        analysis_request = {
            "project_id": project_id,
            "agent_type": "geometry",
            "user_input": "Analyze uploaded geometry"
        }
        analysis_response = client.post(f"/cae-preprocessing/projects/{project_id}/analyze", json=analysis_request)
        assert analysis_response.status_code == 200
        
        print("✅ Complete CAE workflow test passed!")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
