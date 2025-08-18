"""
FastAPI endpoints for LangGraph workflow management.
Provides REST API for starting, monitoring, and controlling simulation preprocessing workflows.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.libs.database import get_db
from app.libs.cae_models import Project, UploadedFile, WorkflowExecution
from app.libs.langgraph_workflow import SimulationPreprocessingWorkflow

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/workflows", tags=["workflows"])

# ============================================================================
# Request/Response Models
# ============================================================================

class StartWorkflowRequest(BaseModel):
    """Request model for starting a new workflow"""
    project_id: str = Field(..., description="Project ID for the workflow")
    user_goal: str = Field(..., description="User's simulation goal and requirements")
    physics_type: str = Field(..., description="Type of physics simulation", 
                             regex="^(cfd|structural|thermal|electromagnetic|multi_physics)$")
    cad_file_ids: List[str] = Field(default=[], description="List of uploaded CAD file IDs")

class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status"""
    workflow_id: str
    status: str
    current_step: str
    created_at: str
    updated_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]
    progress_percentage: float
    pending_checkpoints: List[Dict[str, Any]]

class HITLCheckpointResponse(BaseModel):
    """Response model for HITL checkpoint"""
    checkpoint_id: str
    checkpoint_type: str
    description: str
    agent_recommendations: List[str]
    created_at: str
    timeout_at: Optional[str]

class HITLResponseRequest(BaseModel):
    """Request model for responding to HITL checkpoint"""
    approved: bool = Field(..., description="Whether to approve the checkpoint")
    feedback: Optional[str] = Field(None, description="Human feedback or modification requests")
    reviewer_id: Optional[str] = Field(None, description="ID of the reviewer")

class WorkflowListResponse(BaseModel):
    """Response model for workflow list"""
    workflows: List[Dict[str, Any]]
    total_count: int

# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/start", response_model=Dict[str, str])
async def start_workflow(
    request: StartWorkflowRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start a new simulation preprocessing workflow"""
    try:
        # Validate project exists
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get CAD files
        cad_files = []
        if request.cad_file_ids:
            files = db.query(UploadedFile).filter(
                UploadedFile.id.in_(request.cad_file_ids),
                UploadedFile.project_id == request.project_id
            ).all()
            
            cad_files = [
                {
                    "id": str(file.id),
                    "filename": file.filename,
                    "file_path": file.file_path,
                    "file_type": file.file_type,
                    "file_format": file.file_format
                }
                for file in files
            ]
        
        # Create workflow instance
        workflow = SimulationPreprocessingWorkflow(db)
        
        # Start workflow
        workflow_id = await workflow.start_workflow(
            project_id=request.project_id,
            user_goal=request.user_goal,
            physics_type=request.physics_type,
            cad_files=cad_files
        )
        
        logger.info(f"Started workflow {workflow_id} for project {request.project_id}")
        
        return {
            "workflow_id": workflow_id,
            "status": "started",
            "message": "Workflow started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")

@router.get("/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    db: Session = Depends(get_db)
):
    """Get current status of a workflow"""
    try:
        # Create workflow instance
        workflow = SimulationPreprocessingWorkflow(db)
        
        # Get workflow status
        status_data = await workflow.get_workflow_status(workflow_id)
        
        if not status_data:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Calculate progress percentage
        progress = _calculate_progress_percentage(status_data.get("state", {}))
        
        return WorkflowStatusResponse(
            workflow_id=status_data["workflow_id"],
            status=status_data["status"],
            current_step=status_data["current_step"],
            created_at=status_data["created_at"],
            updated_at=status_data.get("updated_at"),
            completed_at=status_data.get("completed_at"),
            error_message=status_data.get("error_message"),
            progress_percentage=progress,
            pending_checkpoints=status_data.get("pending_checkpoints", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {str(e)}")

@router.get("/{workflow_id}/checkpoints", response_model=List[HITLCheckpointResponse])
async def get_workflow_checkpoints(
    workflow_id: str,
    db: Session = Depends(get_db)
):
    """Get pending HITL checkpoints for a workflow"""
    try:
        # Create workflow instance
        workflow = SimulationPreprocessingWorkflow(db)
        
        # Get pending checkpoints
        checkpoints = await workflow.hitl_manager.get_pending_checkpoints(workflow_id)
        
        return [
            HITLCheckpointResponse(
                checkpoint_id=cp["checkpoint_id"],
                checkpoint_type=cp["checkpoint_type"],
                description=cp["description"],
                agent_recommendations=cp["agent_recommendations"],
                created_at=cp["created_at"],
                timeout_at=cp.get("timeout_at")
            )
            for cp in checkpoints
        ]
        
    except Exception as e:
        logger.error(f"Failed to get workflow checkpoints: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow checkpoints: {str(e)}")

@router.post("/{workflow_id}/checkpoints/{checkpoint_id}/respond")
async def respond_to_checkpoint(
    workflow_id: str,
    checkpoint_id: str,
    request: HITLResponseRequest,
    db: Session = Depends(get_db)
):
    """Respond to a HITL checkpoint"""
    try:
        # Create workflow instance
        workflow = SimulationPreprocessingWorkflow(db)
        
        # Respond to checkpoint
        success = await workflow.respond_to_checkpoint(
            checkpoint_id=checkpoint_id,
            approved=request.approved,
            feedback=request.feedback,
            reviewer_id=request.reviewer_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to respond to checkpoint")
        
        logger.info(f"Checkpoint {checkpoint_id} {'approved' if request.approved else 'rejected'}")
        
        return {
            "success": True,
            "message": f"Checkpoint {'approved' if request.approved else 'rejected'} successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to respond to checkpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to respond to checkpoint: {str(e)}")

@router.get("/project/{project_id}", response_model=WorkflowListResponse)
async def get_project_workflows(
    project_id: str,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get workflows for a specific project"""
    try:
        # Validate project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get workflows
        workflows_query = db.query(WorkflowExecution).filter(
            WorkflowExecution.project_id == project_id
        ).order_by(WorkflowExecution.created_at.desc())
        
        total_count = workflows_query.count()
        workflows = workflows_query.offset(offset).limit(limit).all()
        
        workflow_list = [
            {
                "workflow_id": str(workflow.id),
                "status": workflow.status,
                "current_step": workflow.current_step,
                "user_goal": workflow.user_goal,
                "created_at": workflow.created_at.isoformat(),
                "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
                "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
                "error_message": workflow.error_message
            }
            for workflow in workflows
        ]
        
        return WorkflowListResponse(
            workflows=workflow_list,
            total_count=total_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get project workflows: {str(e)}")

@router.delete("/{workflow_id}")
async def cancel_workflow(
    workflow_id: str,
    db: Session = Depends(get_db)
):
    """Cancel a running workflow"""
    try:
        # Get workflow
        workflow = db.query(WorkflowExecution).filter(
            WorkflowExecution.id == workflow_id
        ).first()
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        if workflow.status in ["completed", "failed"]:
            raise HTTPException(status_code=400, detail="Cannot cancel completed or failed workflow")
        
        # Update workflow status
        workflow.status = "cancelled"
        workflow.completed_at = datetime.utcnow()
        workflow.error_message = "Cancelled by user"
        
        db.commit()
        
        logger.info(f"Cancelled workflow {workflow_id}")
        
        return {
            "success": True,
            "message": "Workflow cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cancel workflow: {str(e)}")

# ============================================================================
# Utility Functions
# ============================================================================

def _calculate_progress_percentage(state: Dict[str, Any]) -> float:
    """Calculate workflow progress percentage"""
    if not state:
        return 0.0
    
    completed_steps = state.get("completed_steps", [])
    total_steps = 4  # geometry, mesh, materials, physics
    
    # Base progress from completed steps
    base_progress = (len(completed_steps) / total_steps) * 100
    
    # Add partial progress for current step
    current_step = state.get("current_step", "")
    step_progress_map = {
        "geometry_processing": 0,
        "mesh_generation": 25,
        "material_assignment": 50,
        "physics_setup": 75,
        "validation": 90,
        "hitl_checkpoint": 95
    }
    
    current_step_progress = step_progress_map.get(current_step, 0)
    
    # If current step is not in completed steps, add partial progress
    if current_step and current_step.replace("_processing", "").replace("_generation", "").replace("_assignment", "").replace("_setup", "") not in [step.replace("_processing", "").replace("_generation", "").replace("_assignment", "").replace("_setup", "") for step in completed_steps]:
        return min(current_step_progress + 5, 100.0)  # Add 5% for being in progress
    
    return min(base_progress, 100.0)
