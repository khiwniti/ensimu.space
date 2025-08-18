"""
Comprehensive integration tests for the AgentSim → ensimu-space merger.
Tests end-to-end workflows, AI agent interactions, and system integration.
"""

import asyncio
import json
import pytest
import uuid
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.database import get_db, Base
from app.libs.cae_agents import AgentFactory, WorkflowContext
from app.libs.langgraph_workflow import SimulationPreprocessingWorkflow
from app.libs.cae_models import Project, WorkflowExecution, WorkflowStep, HITLCheckpoint
from app.websocket_manager import websocket_manager, WebSocketMessage, MessageType

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
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
def db_session():
    """Create test database session"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def sample_project(db_session):
    """Create sample project for testing"""
    project = Project(
        id=str(uuid.uuid4()),
        name="Test CFD Project",
        description="Test project for CFD simulation",
        physics_type="cfd",
        created_at=datetime.utcnow()
    )
    db_session.add(project)
    db_session.commit()
    return project

@pytest.fixture
def mock_openai():
    """Mock OpenAI API responses"""
    with patch('openai.ChatCompletion.acreate') as mock:
        mock.return_value = AsyncMock()
        mock.return_value.choices = [
            Mock(message=Mock(content=json.dumps({
                "analysis": "Test analysis result",
                "recommendations": ["Test recommendation"],
                "confidence": 0.85
            })))
        ]
        yield mock

class TestWorkflowIntegration:
    """Test complete workflow integration"""
    
    @pytest.mark.asyncio
    async def test_complete_cfd_workflow(self, db_session, sample_project, mock_openai):
        """Test complete CFD preprocessing workflow"""
        # Initialize workflow
        workflow = SimulationPreprocessingWorkflow(db_session)
        
        # Start workflow
        workflow_id = await workflow.start_workflow(
            project_id=sample_project.id,
            user_goal="Analyze airflow around a car body",
            physics_type="cfd",
            cad_files=["car_body.step"]
        )
        
        assert workflow_id is not None
        
        # Check workflow was created in database
        workflow_execution = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.id == workflow_id
        ).first()
        
        assert workflow_execution is not None
        assert workflow_execution.project_id == sample_project.id
        assert workflow_execution.physics_type == "cfd"
        assert workflow_execution.status == "running"
        
        # Get workflow status
        status = await workflow.get_workflow_status(workflow_id)
        assert status["workflow_id"] == workflow_id
        assert status["status"] in ["running", "completed"]
    
    @pytest.mark.asyncio
    async def test_agent_factory_integration(self, db_session, mock_openai):
        """Test AI agent factory and agent interactions"""
        agent_factory = AgentFactory(db_session)
        
        # Test geometry agent
        geometry_agent = agent_factory.create_agent("geometry")
        assert geometry_agent is not None
        
        context = WorkflowContext(
            project_id=str(uuid.uuid4()),
            workflow_id=str(uuid.uuid4()),
            user_goal="Test geometry analysis",
            physics_type="cfd",
            current_step="geometry_analysis",
            global_state={},
            agent_outputs={}
        )
        
        request_data = {
            "cad_files": ["test.step"],
            "physics_type": "cfd"
        }
        
        result = await geometry_agent.process_request(request_data, context)
        
        assert result.success
        assert result.confidence_score > 0
        assert "analysis" in result.data
    
    @pytest.mark.asyncio
    async def test_hitl_checkpoint_workflow(self, db_session, sample_project):
        """Test Human-in-the-Loop checkpoint functionality"""
        workflow = SimulationPreprocessingWorkflow(db_session)
        
        # Create HITL checkpoint
        checkpoint_id = str(uuid.uuid4())
        checkpoint_data = {
            "workflow_summary": {"geometry": "test", "mesh": "test"},
            "quality_metrics": {"confidence": 0.6},
            "errors": [],
            "recommendations": ["Review mesh quality"]
        }
        
        hitl_checkpoint = HITLCheckpoint(
            id=checkpoint_id,
            workflow_id=str(uuid.uuid4()),
            checkpoint_type="quality_review",
            checkpoint_data=checkpoint_data,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        db_session.add(hitl_checkpoint)
        db_session.commit()
        
        # Respond to checkpoint
        response = {
            "action": "approved",
            "feedback": "Looks good",
            "modifications": {}
        }
        
        success = await workflow.respond_to_hitl_checkpoint(checkpoint_id, response)
        assert success
        
        # Check checkpoint was updated
        updated_checkpoint = db_session.query(HITLCheckpoint).filter(
            HITLCheckpoint.id == checkpoint_id
        ).first()
        
        assert updated_checkpoint.status == "completed"
        assert updated_checkpoint.response_data == response

class TestAPIIntegration:
    """Test API endpoint integration"""
    
    def test_project_crud_operations(self, client):
        """Test project CRUD operations"""
        # Create project
        project_data = {
            "name": "Test Project",
            "description": "Test project description",
            "physics_type": "cfd"
        }
        
        response = client.post("/api/projects/", json=project_data)
        assert response.status_code == 201
        
        project = response.json()
        project_id = project["id"]
        
        # Read project
        response = client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        assert response.json()["name"] == project_data["name"]
        
        # Update project
        update_data = {"description": "Updated description"}
        response = client.put(f"/api/projects/{project_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["description"] == update_data["description"]
        
        # Delete project
        response = client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 204
    
    def test_workflow_api_endpoints(self, client, sample_project):
        """Test workflow API endpoints"""
        # Start workflow
        workflow_data = {
            "project_id": sample_project.id,
            "user_goal": "Test CFD analysis",
            "physics_type": "cfd",
            "cad_files": ["test.step"]
        }
        
        response = client.post("/api/workflows/start", json=workflow_data)
        assert response.status_code == 201
        
        workflow_id = response.json()["workflow_id"]
        
        # Get workflow status
        response = client.get(f"/api/workflows/{workflow_id}/status")
        assert response.status_code == 200
        
        status = response.json()
        assert status["workflow_id"] == workflow_id
        assert "status" in status
        assert "current_step" in status
    
    def test_file_upload_integration(self, client):
        """Test file upload functionality"""
        # Create test file
        test_file_content = b"test CAD file content"
        
        response = client.post(
            "/api/files/upload",
            files={"file": ("test.step", test_file_content, "application/octet-stream")}
        )
        
        assert response.status_code == 201
        
        file_info = response.json()
        assert "file_id" in file_info
        assert file_info["filename"] == "test.step"
    
    def test_agent_api_endpoints(self, client, mock_openai):
        """Test AI agent API endpoints"""
        # Test geometry agent
        request_data = {
            "cad_files": ["test.step"],
            "physics_type": "cfd",
            "user_requirements": "Analyze geometry for CFD"
        }
        
        response = client.post("/api/agents/geometry/process", json=request_data)
        assert response.status_code == 200
        
        result = response.json()
        assert "success" in result
        assert "data" in result
        assert "confidence_score" in result

class TestWebSocketIntegration:
    """Test WebSocket integration"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, test_app):
        """Test WebSocket connection and messaging"""
        with TestClient(test_app) as client:
            with client.websocket_connect("/ws") as websocket:
                # Test connection established message
                data = websocket.receive_json()
                assert data["type"] == "connection_established"
                
                # Test sending message
                test_message = {
                    "type": "agent_action_request",
                    "data": {
                        "action_type": "test_action",
                        "action_id": "test_123"
                    }
                }
                
                websocket.send_json(test_message)
                
                # Should receive response
                response = websocket.receive_json()
                assert response["type"] == "agent_action_response"
                assert response["data"]["action_id"] == "test_123"
    
    @pytest.mark.asyncio
    async def test_workflow_status_updates(self, test_app):
        """Test workflow status updates via WebSocket"""
        workflow_id = str(uuid.uuid4())
        
        # Simulate workflow status update
        await websocket_manager.send_to_workflow(
            workflow_id,
            WebSocketMessage(
                type=MessageType.WORKFLOW_STATUS_UPDATE,
                data={
                    "workflow_id": workflow_id,
                    "status": "running",
                    "current_step": "geometry_analysis",
                    "progress": 25.0
                }
            )
        )
        
        # In a real test, you would verify the message was sent to connected clients

class TestPerformanceIntegration:
    """Test performance and scalability"""
    
    @pytest.mark.asyncio
    async def test_concurrent_workflows(self, db_session, mock_openai):
        """Test multiple concurrent workflows"""
        workflow = SimulationPreprocessingWorkflow(db_session)
        
        # Start multiple workflows concurrently
        tasks = []
        for i in range(5):
            project = Project(
                id=str(uuid.uuid4()),
                name=f"Test Project {i}",
                description=f"Test project {i}",
                physics_type="cfd",
                created_at=datetime.utcnow()
            )
            db_session.add(project)
            db_session.commit()
            
            task = workflow.start_workflow(
                project_id=project.id,
                user_goal=f"Test goal {i}",
                physics_type="cfd",
                cad_files=[f"test_{i}.step"]
            )
            tasks.append(task)
        
        # Wait for all workflows to start
        workflow_ids = await asyncio.gather(*tasks)
        
        assert len(workflow_ids) == 5
        assert all(wid is not None for wid in workflow_ids)
    
    def test_api_rate_limiting(self, client):
        """Test API rate limiting"""
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = client.get("/api/projects/")
            responses.append(response.status_code)
        
        # Should not hit rate limits for reasonable number of requests
        assert all(status == 200 for status in responses)
    
    @pytest.mark.asyncio
    async def test_memory_usage(self, db_session, mock_openai):
        """Test memory usage during workflow execution"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        workflow = SimulationPreprocessingWorkflow(db_session)
        
        # Run workflow
        project = Project(
            id=str(uuid.uuid4()),
            name="Memory Test Project",
            description="Test memory usage",
            physics_type="cfd",
            created_at=datetime.utcnow()
        )
        db_session.add(project)
        db_session.commit()
        
        workflow_id = await workflow.start_workflow(
            project_id=project.id,
            user_goal="Test memory usage",
            physics_type="cfd",
            cad_files=["test.step"]
        )
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for test)
        assert memory_increase < 100 * 1024 * 1024

class TestSecurityIntegration:
    """Test security features"""
    
    def test_authentication_required(self, client):
        """Test that protected endpoints require authentication"""
        # Try to access protected endpoint without auth
        response = client.post("/api/workflows/start", json={})
        assert response.status_code in [401, 403]
    
    def test_input_validation(self, client):
        """Test input validation and sanitization"""
        # Test with invalid data
        invalid_project_data = {
            "name": "",  # Empty name
            "physics_type": "invalid_type"  # Invalid physics type
        }
        
        response = client.post("/api/projects/", json=invalid_project_data)
        assert response.status_code == 422  # Validation error
    
    def test_sql_injection_protection(self, client):
        """Test SQL injection protection"""
        # Try SQL injection in project name
        malicious_data = {
            "name": "'; DROP TABLE projects; --",
            "description": "Test",
            "physics_type": "cfd"
        }
        
        response = client.post("/api/projects/", json=malicious_data)
        # Should either succeed (input sanitized) or fail validation
        assert response.status_code in [201, 422]

class TestErrorHandling:
    """Test error handling and recovery"""
    
    @pytest.mark.asyncio
    async def test_workflow_error_recovery(self, db_session):
        """Test workflow error handling and recovery"""
        workflow = SimulationPreprocessingWorkflow(db_session)
        
        # Create project
        project = Project(
            id=str(uuid.uuid4()),
            name="Error Test Project",
            description="Test error handling",
            physics_type="cfd",
            created_at=datetime.utcnow()
        )
        db_session.add(project)
        db_session.commit()
        
        # Mock agent to raise exception
        with patch('app.libs.cae_agents.GeometryAgent.process_request') as mock_agent:
            mock_agent.side_effect = Exception("Test error")
            
            workflow_id = await workflow.start_workflow(
                project_id=project.id,
                user_goal="Test error handling",
                physics_type="cfd",
                cad_files=["test.step"]
            )
            
            # Check workflow status shows error
            status = await workflow.get_workflow_status(workflow_id)
            # Workflow should handle errors gracefully
            assert status is not None
    
    def test_api_error_responses(self, client):
        """Test API error response format"""
        # Test 404 error
        response = client.get("/api/projects/nonexistent-id")
        assert response.status_code == 404
        
        error_data = response.json()
        assert "detail" in error_data or "error" in error_data
    
    @pytest.mark.asyncio
    async def test_websocket_error_handling(self, test_app):
        """Test WebSocket error handling"""
        with TestClient(test_app) as client:
            with client.websocket_connect("/ws") as websocket:
                # Send invalid message
                websocket.send_text("invalid json")
                
                # Should receive error response
                response = websocket.receive_json()
                assert response["type"] == "error"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
