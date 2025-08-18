"""
Comprehensive tests for Enhanced Simulation API endpoints
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import the API components
from app.apis.enhanced_simulation import router as enhanced_simulation_router
from app.apis.enhanced_simulation.post_processing import post_processing_router

# Create test app
app = FastAPI()
app.include_router(enhanced_simulation_router, prefix="/enhanced-simulation")

client = TestClient(app)

class TestHealthAndStatus:
    """Test health and status endpoints"""
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/enhanced-simulation/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Enhanced Simulation API"
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "active_workflows" in data
        assert "websocket_connections" in data
    
    def test_status_endpoint(self):
        """Test status endpoint"""
        response = client.get("/enhanced-simulation/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Enhanced Simulation API"
        assert data["version"] == "2.0.0"
        assert "features" in data
        assert "supported_agents" in data
        assert "simulation_types" in data
        assert data["status"] == "operational"

class TestWorkflowManagement:
    """Test workflow management endpoints"""
    
    def test_create_workflow_success(self):
        """Test successful workflow creation"""
        workflow_request = {
            "simulation_type": "external_aerodynamics",
            "description": "Test external aerodynamics simulation",
            "parameters": {
                "velocity": 10.0,
                "reference_area": 1.0
            },
            "advanced_settings": {
                "parallel_execution": True
            },
            "workflow_config": {
                "hitl_enabled": False
            }
        }
        
        response = client.post("/enhanced-simulation/workflows", json=workflow_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data
        assert data["status"] == "initializing"
        assert data["simulation_type"] == "external_aerodynamics"
        assert data["progress"] == 0.0
        assert data["current_stage"] == "initialization"
    
    def test_create_workflow_validation_error(self):
        """Test workflow creation with validation errors"""
        invalid_request = {
            "simulation_type": "",  # Empty simulation type
            "description": "Test simulation"
        }
        
        response = client.post("/enhanced-simulation/workflows", json=invalid_request)
        
        # Should handle validation error gracefully
        assert response.status_code in [400, 422]
    
    def test_get_workflow_state(self):
        """Test getting workflow state"""
        # First create a workflow
        workflow_request = {
            "simulation_type": "internal_flow",
            "description": "Test internal flow simulation"
        }
        
        create_response = client.post("/enhanced-simulation/workflows", json=workflow_request)
        workflow_id = create_response.json()["workflow_id"]
        
        # Get workflow state
        response = client.get(f"/enhanced-simulation/workflows/{workflow_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == workflow_id
        assert "status" in data
        assert "progress" in data
        assert "current_stage" in data
        assert "agents_status" in data
        assert "created_at" in data
    
    def test_get_nonexistent_workflow(self):
        """Test getting state of non-existent workflow"""
        response = client.get("/enhanced-simulation/workflows/nonexistent_id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_list_workflows(self):
        """Test listing all workflows"""
        response = client.get("/enhanced-simulation/workflows")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should include any workflows created in previous tests
    
    def test_cancel_workflow(self):
        """Test workflow cancellation"""
        # Create a workflow first
        workflow_request = {
            "simulation_type": "heat_transfer",
            "description": "Test heat transfer simulation"
        }
        
        create_response = client.post("/enhanced-simulation/workflows", json=workflow_request)
        workflow_id = create_response.json()["workflow_id"]
        
        # Cancel the workflow
        response = client.delete(f"/enhanced-simulation/workflows/{workflow_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "cancelled successfully" in data["message"]

class TestHITLCheckpoints:
    """Test HITL checkpoint endpoints"""
    
    def test_get_workflow_checkpoints(self):
        """Test getting workflow checkpoints"""
        # Create a workflow first
        workflow_request = {
            "simulation_type": "external_aerodynamics",
            "description": "Test simulation with checkpoints",
            "workflow_config": {"hitl_enabled": True}
        }
        
        create_response = client.post("/enhanced-simulation/workflows", json=workflow_request)
        workflow_id = create_response.json()["workflow_id"]
        
        # Get checkpoints
        response = client.get(f"/enhanced-simulation/workflows/{workflow_id}/checkpoints")
        
        assert response.status_code == 200
        data = response.json()
        assert "checkpoints" in data
        assert isinstance(data["checkpoints"], list)
    
    def test_respond_to_checkpoint(self):
        """Test responding to a checkpoint"""
        # Create a workflow first
        workflow_request = {
            "simulation_type": "external_aerodynamics",
            "description": "Test simulation with checkpoints",
            "workflow_config": {"hitl_enabled": True}
        }
        
        create_response = client.post("/enhanced-simulation/workflows", json=workflow_request)
        workflow_id = create_response.json()["workflow_id"]
        
        # Mock checkpoint response
        checkpoint_response = {
            "action": "approve",
            "comments": "Geometry looks good",
            "user_id": "test_user"
        }
        
        response = client.post(
            f"/enhanced-simulation/workflows/{workflow_id}/checkpoints/mock_checkpoint/respond",
            json=checkpoint_response
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "approved" in data["message"].lower()

class TestAgentQuery:
    """Test agent query endpoints"""
    
    @patch('app.libs.enhanced_agents.EnhancedKnowledgeAgent.process_query')
    def test_query_knowledge_agent(self, mock_process_query):
        """Test querying the Knowledge Agent"""
        mock_process_query.return_value = {
            "answer": "For external aerodynamics, use kOmegaSST turbulence model",
            "confidence": 0.9,
            "references": ["OpenFOAM_User_Guide.pdf"]
        }
        
        query_request = {
            "query": "What turbulence model should I use for external aerodynamics?",
            "context": "physics_setup",
            "parameters": {"flow_type": "external"}
        }
        
        response = client.post("/enhanced-simulation/agents/knowledge/query", json=query_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["agent_name"] == "Knowledge Agent"
        assert "turbulence" in data["response"].lower()
        assert data["confidence"] > 0.5
        assert "processing_time" in data
        assert mock_process_query.called
    
    def test_query_knowledge_agent_error(self):
        """Test Knowledge Agent query with error"""
        with patch('app.libs.enhanced_agents.EnhancedKnowledgeAgent.process_query') as mock_query:
            mock_query.side_effect = Exception("Knowledge base unavailable")
            
            query_request = {
                "query": "Test query",
                "context": "test"
            }
            
            response = client.post("/enhanced-simulation/agents/knowledge/query", json=query_request)
            
            assert response.status_code == 500
            assert "failed" in response.json()["detail"].lower()

class TestGeometryAnalysis:
    """Test geometry analysis endpoints"""
    
    @patch('app.libs.enhanced_agents.EnhancedGeometryAgent.analyze_geometry')
    def test_analyze_geometry_success(self, mock_analyze):
        """Test successful geometry analysis"""
        mock_analyze.return_value = {
            "status": "completed",
            "geometry_metrics": {
                "volume": 1.0,
                "surface_area": 6.0,
                "characteristic_length": 0.5
            },
            "validation_result": {
                "is_valid": True,
                "quality_score": 0.85
            }
        }
        
        # Create test file content
        test_stl_content = b"solid test\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nendloop\nendfacet\nendsolid"
        
        response = client.post(
            "/enhanced-simulation/agents/geometry/analyze",
            files={"file": ("test.stl", test_stl_content, "application/octet-stream")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "geometry_metrics" in data
        assert mock_analyze.called
    
    @patch('app.libs.enhanced_agents.EnhancedGeometryAgent.analyze_geometry')
    def test_analyze_geometry_with_workflow(self, mock_analyze):
        """Test geometry analysis with workflow notification"""
        mock_analyze.return_value = {
            "status": "completed",
            "geometry_metrics": {"volume": 1.0}
        }
        
        # Create a workflow first
        workflow_request = {"simulation_type": "external_aerodynamics", "description": "Test"}
        create_response = client.post("/enhanced-simulation/workflows", json=workflow_request)
        workflow_id = create_response.json()["workflow_id"]
        
        test_stl_content = b"solid test\nendsolid"
        
        response = client.post(
            f"/enhanced-simulation/agents/geometry/analyze?workflow_id={workflow_id}",
            files={"file": ("test.stl", test_stl_content, "application/octet-stream")}
        )
        
        assert response.status_code == 200
        assert mock_analyze.called

class TestVisualizationAndExport:
    """Test visualization and export endpoints"""
    
    def test_get_visualization_asset(self):
        """Test getting visualization assets"""
        # Create workflow first
        workflow_request = {"simulation_type": "external_aerodynamics", "description": "Test"}
        create_response = client.post("/enhanced-simulation/workflows", json=workflow_request)
        workflow_id = create_response.json()["workflow_id"]
        
        response = client.get(f"/enhanced-simulation/workflows/{workflow_id}/visualizations/mesh")
        
        assert response.status_code == 200
        data = response.json()
        assert "visualization asset" in data["message"].lower()
    
    def test_export_workflow_results_not_completed(self):
        """Test exporting results from incomplete workflow"""
        # Create workflow
        workflow_request = {"simulation_type": "external_aerodynamics", "description": "Test"}
        create_response = client.post("/enhanced-simulation/workflows", json=workflow_request)
        workflow_id = create_response.json()["workflow_id"]
        
        response = client.get(f"/enhanced-simulation/workflows/{workflow_id}/export?format=openfoam")
        
        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()

class TestPostProcessingAPI:
    """Test post-processing API endpoints"""
    
    def test_create_post_processing_job(self):
        """Test creating post-processing job"""
        job_request = {
            "case_directory": "/tmp/test_case",
            "analysis_types": ["convergence", "forces"],
            "visualization_formats": ["png", "html"],
            "case_data": {
                "reference_area": 1.0,
                "velocity": 10.0,
                "density": 1.225
            },
            "parallel_processing": True,
            "generate_report": True
        }
        
        with patch('pathlib.Path.exists', return_value=True):
            response = client.post("/enhanced-simulation/post-processing/jobs", json=job_request)
            
            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "queued"
            assert "created_at" in data
    
    def test_create_post_processing_job_invalid_directory(self):
        """Test creating job with invalid directory"""
        job_request = {
            "case_directory": "/nonexistent/directory",
            "analysis_types": ["convergence"]
        }
        
        response = client.post("/enhanced-simulation/post-processing/jobs", json=job_request)
        
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_post_processing_templates(self):
        """Test getting analysis templates"""
        response = client.get("/enhanced-simulation/post-processing/templates")
        
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "external_aerodynamics" in data["templates"]
        assert "supported_formats" in data
        assert "analysis_types" in data
    
    def test_analyze_convergence_only(self):
        """Test convergence-only analysis"""
        with patch('app.libs.post_processing_pipeline.create_post_processing_pipeline') as mock_create:
            mock_pipeline = Mock()
            mock_pipeline.execute_pipeline.return_value = {
                "status": "completed",
                "results": {"convergence": {"converged": True}}
            }
            mock_create.return_value = mock_pipeline
            
            response = client.post(
                "/enhanced-simulation/post-processing/analyze-convergence",
                params={"case_directory": "/tmp/test_case"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
    
    def test_analyze_forces_only(self):
        """Test forces-only analysis"""
        with patch('app.libs.post_processing_pipeline.create_post_processing_pipeline') as mock_create:
            mock_pipeline = Mock()
            mock_pipeline.execute_pipeline.return_value = {
                "status": "completed",
                "results": {"forces": {"drag_coefficient": 0.5}}
            }
            mock_create.return_value = mock_pipeline
            
            response = client.post(
                "/enhanced-simulation/post-processing/analyze-forces",
                params={
                    "case_directory": "/tmp/test_case",
                    "reference_area": 1.0,
                    "velocity": 10.0,
                    "density": 1.225
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

class TestWebSocketIntegration:
    """Test WebSocket integration (mock tests)"""
    
    @patch('app.apis.enhanced_simulation.websocket.notify_workflow_progress')
    def test_workflow_progress_notification(self, mock_notify):
        """Test workflow progress notifications"""
        # Create workflow
        workflow_request = {"simulation_type": "external_aerodynamics", "description": "Test"}
        response = client.post("/enhanced-simulation/workflows", json=workflow_request)
        
        assert response.status_code == 200
        # In real implementation, this would trigger WebSocket notifications
        # Here we just verify the workflow was created successfully
    
    @patch('app.apis.enhanced_simulation.websocket.notify_checkpoint_created')
    def test_checkpoint_notification(self, mock_notify):
        """Test checkpoint creation notifications"""
        # Create workflow with HITL enabled
        workflow_request = {
            "simulation_type": "external_aerodynamics",
            "description": "Test with checkpoints",
            "workflow_config": {"hitl_enabled": True}
        }
        
        response = client.post("/enhanced-simulation/workflows", json=workflow_request)
        
        assert response.status_code == 200
        # Checkpoint notifications would be triggered during workflow execution

class TestErrorHandling:
    """Test error handling across all endpoints"""
    
    def test_invalid_json_request(self):
        """Test handling of invalid JSON requests"""
        response = client.post(
            "/enhanced-simulation/workflows",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields"""
        incomplete_request = {
            "description": "Missing simulation_type field"
        }
        
        response = client.post("/enhanced-simulation/workflows", json=incomplete_request)
        
        assert response.status_code == 422
    
    def test_internal_server_error_handling(self):
        """Test internal server error handling"""
        with patch('app.apis.enhanced_simulation.EnhancedSimPrepOrchestrator') as mock_orchestrator:
            mock_orchestrator.side_effect = Exception("Internal error")
            
            workflow_request = {
                "simulation_type": "external_aerodynamics",
                "description": "Test error handling"
            }
            
            response = client.post("/enhanced-simulation/workflows", json=workflow_request)
            
            assert response.status_code == 500
            assert "failed" in response.json()["detail"].lower()

class TestConcurrency:
    """Test concurrent request handling"""
    
    def test_multiple_concurrent_workflows(self):
        """Test creating multiple workflows concurrently"""
        import concurrent.futures
        
        def create_workflow(i):
            workflow_request = {
                "simulation_type": "external_aerodynamics",
                "description": f"Concurrent test workflow {i}"
            }
            return client.post("/enhanced-simulation/workflows", json=workflow_request)
        
        # Create multiple workflows concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_workflow, i) for i in range(5)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        assert all(response.status_code == 200 for response in responses)
        
        # All should have unique workflow IDs
        workflow_ids = [response.json()["workflow_id"] for response in responses]
        assert len(set(workflow_ids)) == len(workflow_ids)

class TestPerformance:
    """Performance tests for API endpoints"""
    
    def test_health_endpoint_performance(self):
        """Test health endpoint response time"""
        import time
        
        start_time = time.time()
        response = client.get("/enhanced-simulation/health")
        end_time = time.time()
        
        assert response.status_code == 200
        # Health check should be very fast
        assert (end_time - start_time) < 0.1  # Less than 100ms
    
    def test_workflow_creation_performance(self):
        """Test workflow creation performance"""
        import time
        
        workflow_request = {
            "simulation_type": "external_aerodynamics",
            "description": "Performance test workflow"
        }
        
        start_time = time.time()
        response = client.post("/enhanced-simulation/workflows", json=workflow_request)
        end_time = time.time()
        
        assert response.status_code == 200
        # Workflow creation should be reasonably fast
        assert (end_time - start_time) < 1.0  # Less than 1 second

# Integration test for complete API workflow
class TestCompleteAPIWorkflow:
    """Integration test for complete API workflow"""
    
    def test_complete_simulation_workflow_api(self):
        """Test complete simulation workflow through API"""
        # 1. Create workflow
        workflow_request = {
            "simulation_type": "external_aerodynamics",
            "description": "Complete API workflow test",
            "parameters": {
                "velocity": 10.0,
                "reference_area": 1.0
            },
            "workflow_config": {
                "hitl_enabled": False,
                "parallel_execution": True
            }
        }
        
        create_response = client.post("/enhanced-simulation/workflows", json=workflow_request)
        assert create_response.status_code == 200
        workflow_id = create_response.json()["workflow_id"]
        
        # 2. Check workflow state
        state_response = client.get(f"/enhanced-simulation/workflows/{workflow_id}")
        assert state_response.status_code == 200
        assert state_response.json()["workflow_id"] == workflow_id
        
        # 3. Query Knowledge Agent
        query_request = {
            "query": "Best practices for external aerodynamics simulation",
            "context": "simulation_setup"
        }
        
        with patch('app.libs.enhanced_agents.EnhancedKnowledgeAgent.process_query') as mock_query:
            mock_query.return_value = {
                "answer": "Use appropriate mesh refinement and turbulence models",
                "confidence": 0.9,
                "references": []
            }
            
            query_response = client.post("/enhanced-simulation/agents/knowledge/query", json=query_request)
            assert query_response.status_code == 200
        
        # 4. Analyze geometry (if needed)
        test_stl = b"solid test\nendsolid"
        
        with patch('app.libs.enhanced_agents.EnhancedGeometryAgent.analyze_geometry') as mock_analyze:
            mock_analyze.return_value = {"status": "completed", "geometry_metrics": {}}
            
            geo_response = client.post(
                f"/enhanced-simulation/agents/geometry/analyze?workflow_id={workflow_id}",
                files={"file": ("test.stl", test_stl, "application/octet-stream")}
            )
            assert geo_response.status_code == 200
        
        # 5. Create post-processing job
        pp_request = {
            "case_directory": "/tmp/test_case",
            "analysis_types": ["convergence"]
        }
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('app.libs.post_processing_pipeline.create_post_processing_pipeline') as mock_pp:
            
            mock_pipeline = Mock()
            mock_pipeline.execute_pipeline.return_value = {"status": "completed"}
            mock_pp.return_value = mock_pipeline
            
            pp_response = client.post("/enhanced-simulation/post-processing/jobs", json=pp_request)
            assert pp_response.status_code == 200
        
        # 6. List all workflows
        list_response = client.get("/enhanced-simulation/workflows")
        assert list_response.status_code == 200
        workflows = list_response.json()
        assert any(w["workflow_id"] == workflow_id for w in workflows)
        
        print(f"Complete API workflow test passed for workflow {workflow_id}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])