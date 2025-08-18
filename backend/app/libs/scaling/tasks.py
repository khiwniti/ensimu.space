"""
Celery tasks for distributed workflow execution.
Implements scalable task execution for AI agents and workflow components.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from celery import Task
    from .task_queue import celery_app
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Mock decorator for when Celery is not available
    def task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    celery_app = type('MockCelery', (), {'task': task})()

logger = logging.getLogger(__name__)

class BaseWorkflowTask(Task):
    """Base class for workflow tasks with common functionality"""
    
    def __init__(self):
        self.start_time = None
        self.task_data = None
    
    def on_start(self, task_id, args, kwargs):
        """Called when task starts"""
        self.start_time = time.time()
        logger.info(f"Starting task {task_id}: {self.name}")
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        duration = time.time() - self.start_time if self.start_time else 0
        logger.info(f"Task {task_id} completed in {duration:.2f}s")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        duration = time.time() - self.start_time if self.start_time else 0
        logger.error(f"Task {task_id} failed after {duration:.2f}s: {exc}")
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """Update task progress"""
        progress = (current / total) * 100 if total > 0 else 0
        self.update_state(
            state='PROGRESS',
            meta={
                'current': current,
                'total': total,
                'progress': progress,
                'message': message
            }
        )

@celery_app.task(bind=True, base=BaseWorkflowTask, name="app.libs.scaling.tasks.process_geometry")
def process_geometry(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process geometry analysis task"""
    try:
        self.update_progress(0, 100, "Starting geometry analysis")
        
        # Import here to avoid circular imports
        from app.libs.cae_agents import AgentFactory, WorkflowContext
        from app.libs.database import get_db
        
        # Extract task information
        workflow_id = task_data["workflow_id"]
        project_id = task_data["project_id"]
        task_payload = task_data["task_data"]
        
        self.update_progress(20, 100, "Initializing geometry agent")
        
        # Create database session
        with get_db() as db_session:
            # Create agent factory and geometry agent
            agent_factory = AgentFactory(db_session)
            geometry_agent = agent_factory.create_agent("geometry")
            
            # Create workflow context
            context = WorkflowContext(
                project_id=project_id,
                workflow_id=workflow_id,
                user_goal=task_payload.get("user_goal", ""),
                physics_type=task_payload.get("physics_type", "cfd"),
                current_step="geometry_processing",
                global_state={},
                agent_outputs={}
            )
            
            self.update_progress(40, 100, "Processing geometry data")
            
            # Process geometry request
            result = asyncio.run(geometry_agent.process_request(task_payload, context))
            
            self.update_progress(80, 100, "Finalizing geometry analysis")
            
            # Prepare response
            response = {
                "task_id": self.request.id,
                "workflow_id": workflow_id,
                "project_id": project_id,
                "task_type": "geometry",
                "success": result.success,
                "data": result.data,
                "confidence_score": result.confidence_score,
                "processing_time": result.processing_time,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            if not result.success:
                response["error"] = result.error_message
            
            self.update_progress(100, 100, "Geometry analysis completed")
            return response
            
    except Exception as e:
        logger.error(f"Geometry processing failed: {e}")
        return {
            "task_id": self.request.id,
            "workflow_id": task_data.get("workflow_id"),
            "project_id": task_data.get("project_id"),
            "task_type": "geometry",
            "success": False,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        }

@celery_app.task(bind=True, base=BaseWorkflowTask, name="app.libs.scaling.tasks.process_mesh")
def process_mesh(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process mesh generation task"""
    try:
        self.update_progress(0, 100, "Starting mesh generation")
        
        from app.libs.cae_agents import AgentFactory, WorkflowContext
        from app.libs.database import get_db
        
        workflow_id = task_data["workflow_id"]
        project_id = task_data["project_id"]
        task_payload = task_data["task_data"]
        
        self.update_progress(20, 100, "Initializing mesh agent")
        
        with get_db() as db_session:
            agent_factory = AgentFactory(db_session)
            mesh_agent = agent_factory.create_agent("mesh")
            
            context = WorkflowContext(
                project_id=project_id,
                workflow_id=workflow_id,
                user_goal=task_payload.get("user_goal", ""),
                physics_type=task_payload.get("physics_type", "cfd"),
                current_step="mesh_generation",
                global_state=task_payload.get("global_state", {}),
                agent_outputs=task_payload.get("agent_outputs", {})
            )
            
            self.update_progress(40, 100, "Generating mesh strategy")
            
            result = asyncio.run(mesh_agent.process_request(task_payload, context))
            
            self.update_progress(80, 100, "Finalizing mesh generation")
            
            response = {
                "task_id": self.request.id,
                "workflow_id": workflow_id,
                "project_id": project_id,
                "task_type": "mesh",
                "success": result.success,
                "data": result.data,
                "confidence_score": result.confidence_score,
                "processing_time": result.processing_time,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            if not result.success:
                response["error"] = result.error_message
            
            self.update_progress(100, 100, "Mesh generation completed")
            return response
            
    except Exception as e:
        logger.error(f"Mesh processing failed: {e}")
        return {
            "task_id": self.request.id,
            "workflow_id": task_data.get("workflow_id"),
            "project_id": task_data.get("project_id"),
            "task_type": "mesh",
            "success": False,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        }

@celery_app.task(bind=True, base=BaseWorkflowTask, name="app.libs.scaling.tasks.process_materials")
def process_materials(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process material assignment task"""
    try:
        self.update_progress(0, 100, "Starting material assignment")
        
        from app.libs.cae_agents import AgentFactory, WorkflowContext
        from app.libs.database import get_db
        
        workflow_id = task_data["workflow_id"]
        project_id = task_data["project_id"]
        task_payload = task_data["task_data"]
        
        self.update_progress(20, 100, "Initializing materials agent")
        
        with get_db() as db_session:
            agent_factory = AgentFactory(db_session)
            materials_agent = agent_factory.create_agent("materials")
            
            context = WorkflowContext(
                project_id=project_id,
                workflow_id=workflow_id,
                user_goal=task_payload.get("user_goal", ""),
                physics_type=task_payload.get("physics_type", "cfd"),
                current_step="material_assignment",
                global_state=task_payload.get("global_state", {}),
                agent_outputs=task_payload.get("agent_outputs", {})
            )
            
            self.update_progress(40, 100, "Assigning materials")
            
            result = asyncio.run(materials_agent.process_request(task_payload, context))
            
            self.update_progress(80, 100, "Finalizing material assignment")
            
            response = {
                "task_id": self.request.id,
                "workflow_id": workflow_id,
                "project_id": project_id,
                "task_type": "materials",
                "success": result.success,
                "data": result.data,
                "confidence_score": result.confidence_score,
                "processing_time": result.processing_time,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            if not result.success:
                response["error"] = result.error_message
            
            self.update_progress(100, 100, "Material assignment completed")
            return response
            
    except Exception as e:
        logger.error(f"Materials processing failed: {e}")
        return {
            "task_id": self.request.id,
            "workflow_id": task_data.get("workflow_id"),
            "project_id": task_data.get("project_id"),
            "task_type": "materials",
            "success": False,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        }

@celery_app.task(bind=True, base=BaseWorkflowTask, name="app.libs.scaling.tasks.process_physics")
def process_physics(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process physics setup task"""
    try:
        self.update_progress(0, 100, "Starting physics setup")
        
        from app.libs.cae_agents import AgentFactory, WorkflowContext
        from app.libs.database import get_db
        
        workflow_id = task_data["workflow_id"]
        project_id = task_data["project_id"]
        task_payload = task_data["task_data"]
        
        self.update_progress(20, 100, "Initializing physics agent")
        
        with get_db() as db_session:
            agent_factory = AgentFactory(db_session)
            physics_agent = agent_factory.create_agent("physics")
            
            context = WorkflowContext(
                project_id=project_id,
                workflow_id=workflow_id,
                user_goal=task_payload.get("user_goal", ""),
                physics_type=task_payload.get("physics_type", "cfd"),
                current_step="physics_setup",
                global_state=task_payload.get("global_state", {}),
                agent_outputs=task_payload.get("agent_outputs", {})
            )
            
            self.update_progress(40, 100, "Configuring physics")
            
            result = asyncio.run(physics_agent.process_request(task_payload, context))
            
            self.update_progress(80, 100, "Finalizing physics setup")
            
            response = {
                "task_id": self.request.id,
                "workflow_id": workflow_id,
                "project_id": project_id,
                "task_type": "physics",
                "success": result.success,
                "data": result.data,
                "confidence_score": result.confidence_score,
                "processing_time": result.processing_time,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            if not result.success:
                response["error"] = result.error_message
            
            self.update_progress(100, 100, "Physics setup completed")
            return response
            
    except Exception as e:
        logger.error(f"Physics processing failed: {e}")
        return {
            "task_id": self.request.id,
            "workflow_id": task_data.get("workflow_id"),
            "project_id": task_data.get("project_id"),
            "task_type": "physics",
            "success": False,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        }

@celery_app.task(bind=True, base=BaseWorkflowTask, name="app.libs.scaling.tasks.execute_workflow")
def execute_workflow(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute complete workflow orchestration"""
    try:
        self.update_progress(0, 100, "Starting workflow execution")
        
        from app.libs.langgraph_workflow import SimulationPreprocessingWorkflow
        from app.libs.database import get_db
        
        workflow_id = task_data["workflow_id"]
        project_id = task_data["project_id"]
        task_payload = task_data["task_data"]
        
        self.update_progress(10, 100, "Initializing workflow")
        
        with get_db() as db_session:
            workflow = SimulationPreprocessingWorkflow(db_session)
            
            self.update_progress(20, 100, "Starting workflow execution")
            
            # Execute workflow
            result_workflow_id = asyncio.run(workflow.start_workflow(
                project_id=project_id,
                user_goal=task_payload.get("user_goal", ""),
                physics_type=task_payload.get("physics_type", "cfd"),
                cad_files=task_payload.get("cad_files", [])
            ))
            
            self.update_progress(90, 100, "Workflow execution completed")
            
            response = {
                "task_id": self.request.id,
                "workflow_id": workflow_id,
                "project_id": project_id,
                "task_type": "workflow",
                "success": True,
                "data": {
                    "executed_workflow_id": result_workflow_id,
                    "status": "completed"
                },
                "completed_at": datetime.utcnow().isoformat()
            }
            
            self.update_progress(100, 100, "Workflow completed successfully")
            return response
            
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        return {
            "task_id": self.request.id,
            "workflow_id": task_data.get("workflow_id"),
            "project_id": task_data.get("project_id"),
            "task_type": "workflow",
            "success": False,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        }

@celery_app.task(bind=True, base=BaseWorkflowTask, name="app.libs.scaling.tasks.cleanup_workflow")
def cleanup_workflow(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Cleanup workflow resources"""
    try:
        self.update_progress(0, 100, "Starting workflow cleanup")
        
        workflow_id = task_data["workflow_id"]
        project_id = task_data["project_id"]
        
        self.update_progress(30, 100, "Cleaning up temporary files")
        
        # Import cleanup utilities
        from app.libs.performance.caching import CacheInvalidator
        from app.libs.performance.memory import memory_monitor
        
        # Invalidate workflow cache
        await CacheInvalidator.invalidate_workflow_cache(workflow_id)
        
        self.update_progress(60, 100, "Invalidating cache")
        
        # Force garbage collection
        memory_monitor.force_garbage_collection()
        
        self.update_progress(90, 100, "Finalizing cleanup")
        
        response = {
            "task_id": self.request.id,
            "workflow_id": workflow_id,
            "project_id": project_id,
            "task_type": "cleanup",
            "success": True,
            "data": {"status": "cleaned"},
            "completed_at": datetime.utcnow().isoformat()
        }
        
        self.update_progress(100, 100, "Cleanup completed")
        return response
        
    except Exception as e:
        logger.error(f"Workflow cleanup failed: {e}")
        return {
            "task_id": self.request.id,
            "workflow_id": task_data.get("workflow_id"),
            "project_id": task_data.get("project_id"),
            "task_type": "cleanup",
            "success": False,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        }
