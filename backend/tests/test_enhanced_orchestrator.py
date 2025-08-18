"""
Comprehensive tests for Enhanced SimPrep Orchestrator
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from app.libs.enhanced_orchestrator import (
    EnhancedSimPrepOrchestrator,
    EnhancedWorkflowState,
    HITLCheckpointType,
    WorkflowStage,
    AgentRole,
    CheckpointStatus
)
from app.libs.enhanced_agents import AgentState, AnalysisResult

class TestEnhancedWorkflowState:
    """Test Enhanced Workflow State management"""
    
    def test_workflow_state_initialization(self):
        """Test workflow state initialization"""
        state = EnhancedWorkflowState()
        
        assert state.stage == WorkflowStage.INITIALIZATION
        assert state.progress == 0.0
        assert state.current_agent is None
        assert len(state.agents_status) == 0
        assert state.checkpoint_data is None
        assert state.error_details is None
    
    def test_workflow_state_update_progress(self):
        """Test progress update"""
        state = EnhancedWorkflowState()
        
        state.update_progress(25.0, WorkflowStage.GEOMETRY_ANALYSIS, "geometry")
        
        assert state.progress == 25.0
        assert state.stage == WorkflowStage.GEOMETRY_ANALYSIS
        assert state.current_agent == "geometry"
        assert state.updated_at > state.created_at
    
    def test_workflow_state_agent_status_tracking(self):
        """Test agent status tracking"""
        state = EnhancedWorkflowState()
        
        # Add agent status
        state.update_agent_status("geometry", {
            "state": AgentState.PROCESSING,
            "progress": 50.0,
            "message": "Analyzing geometry..."
        })
        
        assert "geometry" in state.agents_status
        assert state.agents_status["geometry"]["state"] == AgentState.PROCESSING
        assert state.agents_status["geometry"]["progress"] == 50.0
    
    def test_workflow_state_checkpoint_management(self):
        """Test checkpoint management"""
        state = EnhancedWorkflowState()
        
        checkpoint_data = {
            "id": "checkpoint_123",
            "type": HITLCheckpointType.GEOMETRY_VALIDATION,
            "data": {"geometry_valid": True},
            "created_at": datetime.utcnow().isoformat()
        }
        
        state.set_checkpoint(checkpoint_data)
        
        assert state.checkpoint_data == checkpoint_data
        assert state.has_pending_checkpoint()
        
        # Clear checkpoint
        state.clear_checkpoint()
        assert state.checkpoint_data is None
        assert not state.has_pending_checkpoint()
    
    def test_workflow_state_error_handling(self):
        """Test error handling in workflow state"""
        state = EnhancedWorkflowState()
        
        error_details = {
            "error": "Geometry validation failed",
            "agent": "geometry",
            "timestamp": datetime.utcnow().isoformat(),
            "recoverable": True
        }
        
        state.set_error(error_details)
        
        assert state.error_details == error_details
        assert state.has_error()
        
        # Clear error
        state.clear_error()
        assert state.error_details is None
        assert not state.has_error()

class TestEnhancedSimPrepOrchestrator:
    """Test Enhanced SimPrep Orchestrator"""
    
    @pytest.fixture
    def orchestrator(self):
        return EnhancedSimPrepOrchestrator()
    
    @pytest.fixture
    def temp_case_dir(self):
        """Create temporary case directory"""
        temp_dir = tempfile.mkdtemp()
        case_dir = Path(temp_dir) / "test_case"
        case_dir.mkdir()
        
        # Create basic OpenFOAM structure
        (case_dir / "0").mkdir()
        (case_dir / "constant").mkdir()
        (case_dir / "system").mkdir()
        
        yield str(case_dir)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization"""
        assert orchestrator.state.stage == WorkflowStage.INITIALIZATION
        assert len(orchestrator.agents) == 4  # geometry, mesh, material, knowledge
        assert orchestrator.checkpoint_manager is not None
        assert orchestrator.performance_monitor is not None
    
    @pytest.mark.asyncio
    async def test_execute_workflow_success(self, orchestrator, temp_case_dir):
        """Test successful workflow execution"""
        workflow_config = {
            "simulation_type": "external_aerodynamics",
            "case_directory": temp_case_dir,
            "geometry_file": "test.stl",
            "parallel_execution": True
        }
        
        # Mock agent responses
        with patch.object(orchestrator.agents["geometry"], 'analyze_geometry') as mock_geo, \
             patch.object(orchestrator.agents["mesh"], 'generate_mesh') as mock_mesh, \
             patch.object(orchestrator.agents["material"], 'setup_physics') as mock_material:
            
            mock_geo.return_value = {
                "status": "completed",
                "geometry_metrics": {"volume": 1.0, "surface_area": 6.0}
            }
            mock_mesh.return_value = {
                "status": "completed",
                "mesh_statistics": {"cells": 10000, "points": 5000}
            }
            mock_material.return_value = {
                "status": "completed",
                "files_created": ["transportProperties", "turbulenceProperties"]
            }
            
            result = await orchestrator.execute_workflow(workflow_config)
            
            assert result["status"] == "completed"
            assert orchestrator.state.stage == WorkflowStage.FINALIZATION
            assert orchestrator.state.progress == 100.0
    
    @pytest.mark.asyncio
    async def test_execute_workflow_with_hitl_checkpoint(self, orchestrator, temp_case_dir):
        """Test workflow execution with HITL checkpoints"""
        workflow_config = {
            "simulation_type": "external_aerodynamics",
            "case_directory": temp_case_dir,
            "geometry_file": "test.stl",
            "hitl_enabled": True,
            "checkpoint_types": [HITLCheckpointType.GEOMETRY_VALIDATION]
        }
        
        # Mock checkpoint creation
        with patch.object(orchestrator.checkpoint_manager, 'create_checkpoint') as mock_checkpoint:
            mock_checkpoint.return_value = {
                "id": "checkpoint_123",
                "type": HITLCheckpointType.GEOMETRY_VALIDATION,
                "status": CheckpointStatus.PENDING,
                "data": {"requires_approval": True}
            }
            
            # Mock agent response
            with patch.object(orchestrator.agents["geometry"], 'analyze_geometry') as mock_geo:
                mock_geo.return_value = {
                    "status": "completed",
                    "requires_validation": True,
                    "geometry_metrics": {"volume": 1.0}
                }
                
                result = await orchestrator.execute_workflow(workflow_config)
                
                assert result["status"] == "checkpoint_pending"
                assert orchestrator.state.has_pending_checkpoint()
                assert mock_checkpoint.called
    
    @pytest.mark.asyncio
    async def test_handle_checkpoint_response_approve(self, orchestrator):
        """Test handling checkpoint approval"""
        # Set up pending checkpoint
        checkpoint_data = {
            "id": "checkpoint_123",
            "type": HITLCheckpointType.GEOMETRY_VALIDATION,
            "status": CheckpointStatus.PENDING,
            "data": {"geometry_valid": True}
        }
        orchestrator.state.set_checkpoint(checkpoint_data)
        
        # Mock checkpoint manager
        with patch.object(orchestrator.checkpoint_manager, 'respond_to_checkpoint') as mock_respond:
            mock_respond.return_value = {"status": "approved"}
            
            result = await orchestrator.handle_checkpoint_response(
                "checkpoint_123", 
                "approve", 
                "Geometry looks good",
                "user123"
            )
            
            assert result["action"] == "approve"
            assert not orchestrator.state.has_pending_checkpoint()
            assert mock_respond.called
    
    @pytest.mark.asyncio
    async def test_handle_checkpoint_response_reject(self, orchestrator):
        """Test handling checkpoint rejection"""
        # Set up pending checkpoint
        checkpoint_data = {
            "id": "checkpoint_123",
            "type": HITLCheckpointType.MESH_QUALITY,
            "status": CheckpointStatus.PENDING,
            "data": {"mesh_quality": "poor"}
        }
        orchestrator.state.set_checkpoint(checkpoint_data)
        
        with patch.object(orchestrator.checkpoint_manager, 'respond_to_checkpoint') as mock_respond:
            mock_respond.return_value = {"status": "rejected"}
            
            result = await orchestrator.handle_checkpoint_response(
                "checkpoint_123",
                "reject",
                "Mesh quality needs improvement",
                "user123"
            )
            
            assert result["action"] == "reject"
            assert orchestrator.state.stage == WorkflowStage.MESH_GENERATION  # Should go back
    
    @pytest.mark.asyncio
    async def test_parallel_agent_execution(self, orchestrator, temp_case_dir):
        """Test parallel agent execution"""
        workflow_config = {
            "simulation_type": "external_aerodynamics",
            "case_directory": temp_case_dir,
            "parallel_execution": True,
            "max_parallel_agents": 2
        }
        
        # Mock agents with different execution times
        async def mock_quick_agent():
            await asyncio.sleep(0.1)
            return {"status": "completed", "execution_time": 0.1}
        
        async def mock_slow_agent():
            await asyncio.sleep(0.2)
            return {"status": "completed", "execution_time": 0.2}
        
        with patch.object(orchestrator.agents["geometry"], 'analyze_geometry', side_effect=mock_quick_agent), \
             patch.object(orchestrator.agents["knowledge"], 'process_query', side_effect=mock_slow_agent):
            
            start_time = asyncio.get_event_loop().time()
            
            # Execute independent agents in parallel
            results = await orchestrator._execute_parallel_agents([
                ("geometry", "analyze_geometry", {}),
                ("knowledge", "process_query", {"query": "test"})
            ])
            
            end_time = asyncio.get_event_loop().time()
            
            assert len(results) == 2
            # Should complete in roughly the time of the slower agent (parallel execution)
            assert (end_time - start_time) < 0.3
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, orchestrator, temp_case_dir):
        """Test error recovery mechanisms"""
        workflow_config = {
            "simulation_type": "external_aerodynamics",
            "case_directory": temp_case_dir,
            "error_recovery": True,
            "max_retries": 2
        }
        
        # Mock agent that fails first time, succeeds second time
        call_count = 0
        async def mock_failing_agent(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary failure")
            return {"status": "completed", "retry_count": call_count}
        
        with patch.object(orchestrator.agents["geometry"], 'analyze_geometry', side_effect=mock_failing_agent):
            result = await orchestrator.execute_workflow(workflow_config)
            
            assert result["status"] == "completed"
            assert call_count == 2  # Failed once, succeeded on retry
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self, orchestrator, temp_case_dir):
        """Test performance monitoring"""
        workflow_config = {
            "simulation_type": "external_aerodynamics",
            "case_directory": temp_case_dir,
            "performance_monitoring": True
        }
        
        # Mock agent with measurable performance
        async def mock_timed_agent(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate work
            return {"status": "completed", "data": "test"}
        
        with patch.object(orchestrator.agents["geometry"], 'analyze_geometry', side_effect=mock_timed_agent):
            result = await orchestrator.execute_workflow(workflow_config)
            
            assert "performance_metrics" in result
            assert "total_execution_time" in result["performance_metrics"]
            assert "agent_timings" in result["performance_metrics"]
            assert result["performance_metrics"]["total_execution_time"] > 0
    
    @pytest.mark.asyncio
    async def test_workflow_stage_transitions(self, orchestrator):
        """Test proper workflow stage transitions"""
        # Test stage progression
        stages = [
            WorkflowStage.INITIALIZATION,
            WorkflowStage.GEOMETRY_ANALYSIS,
            WorkflowStage.MESH_GENERATION,
            WorkflowStage.PHYSICS_SETUP,
            WorkflowStage.FINALIZATION
        ]
        
        for i, stage in enumerate(stages[1:], 1):
            await orchestrator._transition_to_stage(stage)
            assert orchestrator.state.stage == stage
            assert orchestrator.state.progress >= i * 20  # Rough progress calculation
    
    @pytest.mark.asyncio
    async def test_agent_communication(self, orchestrator):
        """Test inter-agent communication"""
        # Mock geometry analysis result
        geometry_result = {
            "status": "completed",
            "geometry_metrics": {
                "characteristic_length": 0.1,
                "volume": 1.0,
                "complexity": "medium"
            }
        }
        
        # Test that mesh agent receives and uses geometry data
        with patch.object(orchestrator.agents["mesh"], 'generate_mesh') as mock_mesh:
            mock_mesh.return_value = {"status": "completed"}
            
            await orchestrator._execute_mesh_generation(geometry_result)
            
            # Verify mesh agent was called with adapted parameters
            call_args = mock_mesh.call_args
            mesh_params = call_args[1] if len(call_args) > 1 else call_args[0][1]
            
            assert "max_cell_size" in mesh_params
            # Should be based on characteristic length
            assert mesh_params["max_cell_size"] <= geometry_result["geometry_metrics"]["characteristic_length"] / 5
    
    def test_checkpoint_expiry_handling(self, orchestrator):
        """Test checkpoint expiry handling"""
        # Create expired checkpoint
        expired_checkpoint = {
            "id": "checkpoint_expired",
            "type": HITLCheckpointType.GEOMETRY_VALIDATION,
            "status": CheckpointStatus.PENDING,
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "expires_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()
        }
        
        orchestrator.state.set_checkpoint(expired_checkpoint)
        
        # Check if checkpoint is recognized as expired
        is_expired = orchestrator._is_checkpoint_expired(expired_checkpoint)
        assert is_expired
    
    @pytest.mark.asyncio
    async def test_workflow_cancellation(self, orchestrator, temp_case_dir):
        """Test workflow cancellation"""
        workflow_config = {
            "simulation_type": "external_aerodynamics",
            "case_directory": temp_case_dir
        }
        
        # Start workflow
        async def mock_long_running_agent(*args, **kwargs):
            await asyncio.sleep(1.0)  # Long running task
            return {"status": "completed"}
        
        with patch.object(orchestrator.agents["geometry"], 'analyze_geometry', side_effect=mock_long_running_agent):
            # Start workflow in background
            workflow_task = asyncio.create_task(orchestrator.execute_workflow(workflow_config))
            
            # Cancel after short delay
            await asyncio.sleep(0.1)
            await orchestrator.cancel_workflow("User requested cancellation")
            
            # Wait for workflow to complete
            result = await workflow_task
            
            assert result["status"] == "cancelled"
            assert orchestrator.state.stage == WorkflowStage.CANCELLED

class TestWorkflowIntegration:
    """Integration tests for complete workflow scenarios"""
    
    @pytest.fixture
    def complete_case_setup(self):
        """Setup complete test case with all required files"""
        temp_dir = tempfile.mkdtemp()
        case_dir = Path(temp_dir) / "complete_case"
        case_dir.mkdir()
        
        # Create complete OpenFOAM structure
        (case_dir / "0").mkdir()
        (case_dir / "constant").mkdir()
        (case_dir / "system").mkdir()
        (case_dir / "geometry").mkdir()
        
        # Create geometry file
        geometry_file = case_dir / "geometry" / "test.stl"
        geometry_file.write_text("solid test\nendsolid test")
        
        # Create basic system files
        (case_dir / "system" / "controlDict").write_text("// controlDict")
        (case_dir / "system" / "blockMeshDict").write_text("// blockMeshDict")
        
        yield str(case_dir)
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_complete_external_aerodynamics_workflow(self, complete_case_setup):
        """Test complete external aerodynamics workflow"""
        orchestrator = EnhancedSimPrepOrchestrator()
        
        workflow_config = {
            "simulation_type": "external_aerodynamics",
            "case_directory": complete_case_setup,
            "geometry_file": "geometry/test.stl",
            "reference_values": {
                "velocity": 10.0,
                "length": 1.0,
                "area": 1.0
            },
            "mesh_refinement": {
                "global_level": 2,
                "surface_level": 3
            },
            "physics_config": {
                "solver_type": "incompressible",
                "turbulence_model": "kOmegaSST"
            }
        }
        
        # Mock all agent operations
        with patch.object(orchestrator.agents["geometry"], 'analyze_geometry') as mock_geo, \
             patch.object(orchestrator.agents["mesh"], 'generate_mesh') as mock_mesh, \
             patch.object(orchestrator.agents["material"], 'setup_physics') as mock_material, \
             patch.object(orchestrator.agents["knowledge"], 'process_query') as mock_knowledge:
            
            mock_geo.return_value = {
                "status": "completed",
                "geometry_metrics": {
                    "volume": 1.0,
                    "surface_area": 6.0,
                    "characteristic_length": 0.5,
                    "complexity": "medium"
                },
                "validation_result": {"is_valid": True, "quality_score": 0.85}
            }
            
            mock_mesh.return_value = {
                "status": "completed",
                "mesh_statistics": {
                    "cells": 50000,
                    "points": 25000,
                    "max_aspect_ratio": 10.5,
                    "max_skewness": 0.8
                },
                "quality_assessment": {"overall_quality": "good"}
            }
            
            mock_material.return_value = {
                "status": "completed",
                "files_created": [
                    "transportProperties",
                    "turbulenceProperties",
                    "fvSchemes",
                    "fvSolution"
                ],
                "boundary_conditions": {
                    "inlet": "velocity_inlet",
                    "outlet": "pressure_outlet",
                    "walls": "no_slip_wall"
                }
            }
            
            mock_knowledge.return_value = {
                "answer": "External aerodynamics best practices applied",
                "confidence": 0.9,
                "references": ["OpenFOAM_User_Guide.pdf"]
            }
            
            result = await orchestrator.execute_workflow(workflow_config)
            
            # Verify successful completion
            assert result["status"] == "completed"
            assert orchestrator.state.stage == WorkflowStage.FINALIZATION
            assert orchestrator.state.progress == 100.0
            
            # Verify all agents were called
            assert mock_geo.called
            assert mock_mesh.called
            assert mock_material.called
            
            # Verify performance metrics
            assert "performance_metrics" in result
            assert "agent_timings" in result["performance_metrics"]
    
    @pytest.mark.asyncio
    async def test_workflow_with_multiple_hitl_checkpoints(self, complete_case_setup):
        """Test workflow with multiple HITL checkpoints"""
        orchestrator = EnhancedSimPrepOrchestrator()
        
        workflow_config = {
            "simulation_type": "external_aerodynamics",
            "case_directory": complete_case_setup,
            "hitl_enabled": True,
            "checkpoint_types": [
                HITLCheckpointType.GEOMETRY_VALIDATION,
                HITLCheckpointType.MESH_QUALITY,
                HITLCheckpointType.PHYSICS_VALIDATION
            ]
        }
        
        checkpoint_responses = []
        
        # Mock checkpoint manager to track checkpoints
        async def mock_create_checkpoint(checkpoint_type, data):
            checkpoint_id = f"checkpoint_{len(checkpoint_responses) + 1}"
            checkpoint_responses.append({
                "id": checkpoint_id,
                "type": checkpoint_type,
                "data": data,
                "status": CheckpointStatus.PENDING
            })
            return checkpoint_responses[-1]
        
        with patch.object(orchestrator.checkpoint_manager, 'create_checkpoint', side_effect=mock_create_checkpoint), \
             patch.object(orchestrator.agents["geometry"], 'analyze_geometry') as mock_geo, \
             patch.object(orchestrator.agents["mesh"], 'generate_mesh') as mock_mesh, \
             patch.object(orchestrator.agents["material"], 'setup_physics') as mock_material:
            
            # Configure agents to require validation
            mock_geo.return_value = {
                "status": "completed",
                "requires_validation": True,
                "geometry_metrics": {"volume": 1.0}
            }
            mock_mesh.return_value = {
                "status": "completed", 
                "requires_validation": True,
                "mesh_statistics": {"cells": 10000}
            }
            mock_material.return_value = {
                "status": "completed",
                "requires_validation": True,
                "files_created": ["transportProperties"]
            }
            
            result = await orchestrator.execute_workflow(workflow_config)
            
            # Should stop at first checkpoint
            assert result["status"] == "checkpoint_pending"
            assert len(checkpoint_responses) >= 1
            assert checkpoint_responses[0]["type"] == HITLCheckpointType.GEOMETRY_VALIDATION

# Performance benchmarks
class TestPerformanceBenchmarks:
    """Performance benchmarks for orchestrator"""
    
    @pytest.mark.asyncio
    async def test_workflow_execution_performance(self):
        """Benchmark workflow execution performance"""
        orchestrator = EnhancedSimPrepOrchestrator()
        
        # Mock fast agents
        async def fast_agent(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms simulation
            return {"status": "completed", "data": "benchmark"}
        
        with patch.object(orchestrator.agents["geometry"], 'analyze_geometry', side_effect=fast_agent), \
             patch.object(orchestrator.agents["mesh"], 'generate_mesh', side_effect=fast_agent), \
             patch.object(orchestrator.agents["material"], 'setup_physics', side_effect=fast_agent):
            
            start_time = asyncio.get_event_loop().time()
            
            result = await orchestrator.execute_workflow({
                "simulation_type": "external_aerodynamics",
                "case_directory": "/tmp/benchmark",
                "parallel_execution": True
            })
            
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            assert result["status"] == "completed"
            # Should complete within reasonable time (< 1 second for mocked agents)
            assert execution_time < 1.0
            print(f"Workflow execution time: {execution_time:.3f}s")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])