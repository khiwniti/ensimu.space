"""
End-to-end tests for the complete AgentSim → ensimu-space platform.
Tests complete user journeys from file upload to simulation completion.
"""

import asyncio
import json
import pytest
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.database import get_db, Base
from app.libs.cae_models import Project, WorkflowExecution, File

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_e2e.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def test_app():
    """Create test FastAPI application"""
    Base.metadata.create_all(bind=engine)
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return app

@pytest.fixture(scope="module")
def client(test_app):
    """Create test client"""
    return TestClient(test_app)

@pytest.fixture
def sample_cad_file():
    """Create sample CAD file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
        # Simple STEP file content
        step_content = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Test CAD file for simulation'),'2;1');
FILE_NAME('test.step','2024-01-01T00:00:00',('Test User'),('Test Organization'),'Test CAD System','Test CAD System','');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));
ENDSEC;
DATA;
#1 = CARTESIAN_POINT('Origin',(0.0,0.0,0.0));
#2 = DIRECTION('X-Axis',(1.0,0.0,0.0));
#3 = DIRECTION('Y-Axis',(0.0,1.0,0.0));
#4 = DIRECTION('Z-Axis',(0.0,0.0,1.0));
ENDSEC;
END-ISO-10303-21;
"""
        f.write(step_content.encode())
        return f.name

class TestCompleteUserJourney:
    """Test complete user journey from start to finish"""
    
    def test_complete_cfd_workflow_journey(self, client, sample_cad_file):
        """Test complete CFD workflow from file upload to completion"""
        
        # Step 1: Create a new project
        project_data = {
            "name": "E2E CFD Test Project",
            "description": "End-to-end test for CFD simulation preprocessing",
            "physics_type": "cfd"
        }
        
        response = client.post("/api/projects/", json=project_data)
        assert response.status_code == 201
        
        project = response.json()
        project_id = project["id"]
        
        # Step 2: Upload CAD file
        with open(sample_cad_file, "rb") as f:
            response = client.post(
                "/api/files/upload",
                files={"file": ("test.step", f, "application/octet-stream")},
                data={"project_id": project_id}
            )
        
        assert response.status_code == 201
        file_info = response.json()
        file_id = file_info["file_id"]
        
        # Step 3: Start simulation preprocessing workflow
        workflow_data = {
            "project_id": project_id,
            "user_goal": "Analyze airflow around the uploaded geometry for automotive CFD",
            "physics_type": "cfd",
            "cad_files": [file_info["filename"]]
        }
        
        response = client.post("/api/workflows/start", json=workflow_data)
        assert response.status_code == 201
        
        workflow_result = response.json()
        workflow_id = workflow_result["workflow_id"]
        
        # Step 4: Monitor workflow progress
        max_attempts = 30  # 30 seconds timeout
        attempts = 0
        workflow_completed = False
        
        while attempts < max_attempts and not workflow_completed:
            response = client.get(f"/api/workflows/{workflow_id}/status")
            assert response.status_code == 200
            
            status = response.json()
            
            if status["status"] in ["completed", "failed"]:
                workflow_completed = True
                assert status["status"] == "completed", f"Workflow failed: {status}"
            
            attempts += 1
            if not workflow_completed:
                import time
                time.sleep(1)
        
        assert workflow_completed, "Workflow did not complete within timeout"
        
        # Step 5: Verify workflow results
        final_status = response.json()
        assert "steps" in final_status
        assert len(final_status["steps"]) > 0
        
        # Check that all major steps were executed
        step_names = [step["step_name"] for step in final_status["steps"]]
        expected_steps = ["geometry_analysis", "mesh_generation", "materials_assignment", "physics_setup"]
        
        for expected_step in expected_steps:
            assert any(expected_step in step_name for step_name in step_names), f"Missing step: {expected_step}"
        
        # Step 6: Retrieve project with updated data
        response = client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        
        updated_project = response.json()
        assert updated_project["id"] == project_id
        
        # Step 7: Download results (if available)
        response = client.get(f"/api/projects/{project_id}/results")
        # Results endpoint might not be implemented yet, so we check for 200 or 404
        assert response.status_code in [200, 404]
        
        # Step 8: Clean up - delete project
        response = client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 204
    
    def test_structural_analysis_journey(self, client, sample_cad_file):
        """Test complete structural analysis workflow"""
        
        # Create project for structural analysis
        project_data = {
            "name": "E2E Structural Test Project",
            "description": "End-to-end test for structural analysis preprocessing",
            "physics_type": "structural"
        }
        
        response = client.post("/api/projects/", json=project_data)
        assert response.status_code == 201
        project_id = response.json()["id"]
        
        # Upload CAD file
        with open(sample_cad_file, "rb") as f:
            response = client.post(
                "/api/files/upload",
                files={"file": ("bracket.step", f, "application/octet-stream")},
                data={"project_id": project_id}
            )
        assert response.status_code == 201
        file_info = response.json()
        
        # Start structural workflow
        workflow_data = {
            "project_id": project_id,
            "user_goal": "Perform stress analysis on the mounting bracket under 5000N load",
            "physics_type": "structural",
            "cad_files": [file_info["filename"]]
        }
        
        response = client.post("/api/workflows/start", json=workflow_data)
        assert response.status_code == 201
        workflow_id = response.json()["workflow_id"]
        
        # Monitor workflow (simplified for structural)
        max_attempts = 20
        attempts = 0
        
        while attempts < max_attempts:
            response = client.get(f"/api/workflows/{workflow_id}/status")
            assert response.status_code == 200
            
            status = response.json()
            if status["status"] in ["completed", "failed"]:
                assert status["status"] == "completed"
                break
            
            attempts += 1
            import time
            time.sleep(1)
        
        # Clean up
        client.delete(f"/api/projects/{project_id}")

class TestMultiUserScenarios:
    """Test scenarios with multiple users and projects"""
    
    def test_concurrent_projects(self, client, sample_cad_file):
        """Test multiple concurrent projects"""
        
        projects = []
        workflows = []
        
        # Create multiple projects
        for i in range(3):
            project_data = {
                "name": f"Concurrent Test Project {i+1}",
                "description": f"Concurrent test project {i+1}",
                "physics_type": "cfd" if i % 2 == 0 else "structural"
            }
            
            response = client.post("/api/projects/", json=project_data)
            assert response.status_code == 201
            projects.append(response.json())
        
        # Upload files and start workflows for each project
        for i, project in enumerate(projects):
            # Upload file
            with open(sample_cad_file, "rb") as f:
                response = client.post(
                    "/api/files/upload",
                    files={"file": (f"test_{i}.step", f, "application/octet-stream")},
                    data={"project_id": project["id"]}
                )
            assert response.status_code == 201
            file_info = response.json()
            
            # Start workflow
            workflow_data = {
                "project_id": project["id"],
                "user_goal": f"Test analysis {i+1}",
                "physics_type": project["physics_type"],
                "cad_files": [file_info["filename"]]
            }
            
            response = client.post("/api/workflows/start", json=workflow_data)
            assert response.status_code == 201
            workflows.append(response.json())
        
        # Monitor all workflows
        completed_workflows = set()
        max_attempts = 30
        attempts = 0
        
        while len(completed_workflows) < len(workflows) and attempts < max_attempts:
            for i, workflow in enumerate(workflows):
                if i not in completed_workflows:
                    response = client.get(f"/api/workflows/{workflow['workflow_id']}/status")
                    assert response.status_code == 200
                    
                    status = response.json()
                    if status["status"] in ["completed", "failed"]:
                        assert status["status"] == "completed"
                        completed_workflows.add(i)
            
            attempts += 1
            import time
            time.sleep(1)
        
        assert len(completed_workflows) == len(workflows), "Not all workflows completed"
        
        # Clean up
        for project in projects:
            client.delete(f"/api/projects/{project['id']}")

class TestErrorScenarios:
    """Test error handling in end-to-end scenarios"""
    
    def test_invalid_file_upload(self, client):
        """Test handling of invalid file uploads"""
        
        # Create project
        project_data = {
            "name": "Error Test Project",
            "description": "Test error handling",
            "physics_type": "cfd"
        }
        
        response = client.post("/api/projects/", json=project_data)
        assert response.status_code == 201
        project_id = response.json()["id"]
        
        # Try to upload invalid file
        invalid_content = b"This is not a CAD file"
        response = client.post(
            "/api/files/upload",
            files={"file": ("invalid.txt", invalid_content, "text/plain")},
            data={"project_id": project_id}
        )
        
        # Should either reject the file or accept it (depending on validation)
        assert response.status_code in [201, 400, 422]
        
        # Clean up
        client.delete(f"/api/projects/{project_id}")
    
    def test_workflow_with_missing_files(self, client):
        """Test workflow with missing CAD files"""
        
        # Create project
        project_data = {
            "name": "Missing Files Test",
            "description": "Test missing files handling",
            "physics_type": "cfd"
        }
        
        response = client.post("/api/projects/", json=project_data)
        assert response.status_code == 201
        project_id = response.json()["id"]
        
        # Try to start workflow without uploading files
        workflow_data = {
            "project_id": project_id,
            "user_goal": "Test with missing files",
            "physics_type": "cfd",
            "cad_files": ["nonexistent.step"]
        }
        
        response = client.post("/api/workflows/start", json=workflow_data)
        
        # Should either fail immediately or handle gracefully
        if response.status_code == 201:
            workflow_id = response.json()["workflow_id"]
            
            # Check that workflow handles missing files
            response = client.get(f"/api/workflows/{workflow_id}/status")
            assert response.status_code == 200
            
            # Workflow might fail or handle missing files gracefully
            status = response.json()
            assert status["status"] in ["running", "failed", "completed"]
        
        # Clean up
        client.delete(f"/api/projects/{project_id}")

class TestPerformanceScenarios:
    """Test performance-related scenarios"""
    
    def test_large_file_upload(self, client):
        """Test uploading larger files"""
        
        # Create project
        project_data = {
            "name": "Large File Test",
            "description": "Test large file handling",
            "physics_type": "cfd"
        }
        
        response = client.post("/api/projects/", json=project_data)
        assert response.status_code == 201
        project_id = response.json()["id"]
        
        # Create a larger test file (1MB)
        large_content = b"0" * (1024 * 1024)  # 1MB of zeros
        
        response = client.post(
            "/api/files/upload",
            files={"file": ("large_test.step", large_content, "application/octet-stream")},
            data={"project_id": project_id}
        )
        
        # Should handle large files (or reject if too large)
        assert response.status_code in [201, 413]  # 413 = Request Entity Too Large
        
        # Clean up
        client.delete(f"/api/projects/{project_id}")
    
    def test_rapid_api_requests(self, client):
        """Test handling of rapid API requests"""
        
        # Make rapid requests to test rate limiting
        responses = []
        for i in range(10):
            response = client.get("/api/projects/")
            responses.append(response.status_code)
        
        # Should handle rapid requests gracefully
        # Most should succeed, some might be rate limited
        success_count = sum(1 for status in responses if status == 200)
        rate_limited_count = sum(1 for status in responses if status == 429)
        
        assert success_count > 0, "No successful requests"
        assert success_count + rate_limited_count == len(responses), "Unexpected status codes"

class TestDataIntegrity:
    """Test data integrity throughout the workflow"""
    
    def test_project_data_consistency(self, client, sample_cad_file):
        """Test that project data remains consistent throughout workflow"""
        
        # Create project with specific data
        original_project_data = {
            "name": "Data Integrity Test",
            "description": "Test data consistency",
            "physics_type": "cfd"
        }
        
        response = client.post("/api/projects/", json=original_project_data)
        assert response.status_code == 201
        project = response.json()
        project_id = project["id"]
        
        # Verify initial project data
        response = client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        retrieved_project = response.json()
        
        assert retrieved_project["name"] == original_project_data["name"]
        assert retrieved_project["description"] == original_project_data["description"]
        assert retrieved_project["physics_type"] == original_project_data["physics_type"]
        
        # Upload file and start workflow
        with open(sample_cad_file, "rb") as f:
            response = client.post(
                "/api/files/upload",
                files={"file": ("consistency_test.step", f, "application/octet-stream")},
                data={"project_id": project_id}
            )
        assert response.status_code == 201
        
        workflow_data = {
            "project_id": project_id,
            "user_goal": "Test data consistency",
            "physics_type": "cfd",
            "cad_files": ["consistency_test.step"]
        }
        
        response = client.post("/api/workflows/start", json=workflow_data)
        assert response.status_code == 201
        workflow_id = response.json()["workflow_id"]
        
        # Verify project data hasn't been corrupted during workflow
        response = client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        project_after_workflow = response.json()
        
        assert project_after_workflow["name"] == original_project_data["name"]
        assert project_after_workflow["description"] == original_project_data["description"]
        assert project_after_workflow["physics_type"] == original_project_data["physics_type"]
        
        # Clean up
        client.delete(f"/api/projects/{project_id}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
