"""
Distributed task queue system for scalable workflow execution.
Implements Celery-based task distribution with Redis backend for high-concurrency scenarios.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from celery import Celery, Task
    from celery.result import AsyncResult
    from celery.signals import task_prerun, task_postrun, task_failure
    from kombu import Queue
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Mock classes for when Celery is not available
    class Celery:
        def __init__(self, *args, **kwargs): pass
        def task(self, *args, **kwargs): 
            def decorator(func): return func
            return decorator
    class Task: pass
    class AsyncResult: pass

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"

@dataclass
class WorkflowTask:
    """Workflow task definition"""
    task_id: str
    workflow_id: str
    project_id: str
    task_type: str
    task_data: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    retry_delay: int = 60
    timeout: int = 3600
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

class CeleryConfig:
    """Celery configuration for production scaling"""
    
    # Broker settings
    broker_url = "redis://localhost:6379/1"
    result_backend = "redis://localhost:6379/2"
    
    # Task settings
    task_serializer = "json"
    result_serializer = "json"
    accept_content = ["json"]
    timezone = "UTC"
    enable_utc = True
    
    # Worker settings
    worker_prefetch_multiplier = 1
    task_acks_late = True
    worker_max_tasks_per_child = 1000
    worker_disable_rate_limits = False
    
    # Queue settings
    task_default_queue = "default"
    task_routes = {
        "app.libs.scaling.tasks.process_geometry": {"queue": "geometry"},
        "app.libs.scaling.tasks.process_mesh": {"queue": "mesh"},
        "app.libs.scaling.tasks.process_materials": {"queue": "materials"},
        "app.libs.scaling.tasks.process_physics": {"queue": "physics"},
        "app.libs.scaling.tasks.execute_workflow": {"queue": "workflows"},
        "app.libs.scaling.tasks.cleanup_workflow": {"queue": "cleanup"},
    }
    
    # Priority queues
    task_queue_max_priority = 10
    task_default_priority = 5
    
    # Retry settings
    task_retry_delay = 60
    task_max_retries = 3
    
    # Result settings
    result_expires = 3600
    result_persistent = True
    
    # Monitoring
    worker_send_task_events = True
    task_send_sent_event = True
    
    # Security
    worker_hijack_root_logger = False
    worker_log_color = False

# Initialize Celery app
def create_celery_app(config_class=CeleryConfig) -> Celery:
    """Create and configure Celery application"""
    if not CELERY_AVAILABLE:
        logger.warning("Celery not available, using mock implementation")
        return Celery()
    
    app = Celery("ensimu_space")
    app.config_from_object(config_class)
    
    # Define queues with priorities
    app.conf.task_queues = (
        Queue("default", routing_key="default"),
        Queue("geometry", routing_key="geometry", queue_arguments={"x-max-priority": 10}),
        Queue("mesh", routing_key="mesh", queue_arguments={"x-max-priority": 10}),
        Queue("materials", routing_key="materials", queue_arguments={"x-max-priority": 10}),
        Queue("physics", routing_key="physics", queue_arguments={"x-max-priority": 10}),
        Queue("workflows", routing_key="workflows", queue_arguments={"x-max-priority": 10}),
        Queue("cleanup", routing_key="cleanup", queue_arguments={"x-max-priority": 5}),
    )
    
    return app

# Global Celery app instance
celery_app = create_celery_app()

class TaskManager:
    """Distributed task management system"""
    
    def __init__(self, celery_app: Celery):
        self.celery_app = celery_app
        self.active_tasks: Dict[str, WorkflowTask] = {}
        self.task_metrics = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
            "retried": 0
        }
    
    def submit_workflow_task(self, task: WorkflowTask) -> str:
        """Submit a workflow task to the distributed queue"""
        try:
            # Determine queue based on task type
            queue_name = self._get_queue_for_task_type(task.task_type)
            
            # Convert priority to Celery priority (0-10 scale)
            celery_priority = self._convert_priority(task.priority)
            
            # Submit task to Celery
            result = self.celery_app.send_task(
                f"app.libs.scaling.tasks.{task.task_type}",
                args=[asdict(task)],
                task_id=task.task_id,
                queue=queue_name,
                priority=celery_priority,
                retry=True,
                retry_policy={
                    "max_retries": task.max_retries,
                    "interval_start": task.retry_delay,
                    "interval_step": task.retry_delay,
                    "interval_max": task.retry_delay * 4,
                }
            )
            
            # Track task
            self.active_tasks[task.task_id] = task
            self.task_metrics["submitted"] += 1
            
            logger.info(f"Submitted task {task.task_id} to queue {queue_name}")
            return result.id
            
        except Exception as e:
            logger.error(f"Failed to submit task {task.task_id}: {e}")
            raise
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a distributed task"""
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            
            return {
                "task_id": task_id,
                "status": result.status,
                "result": result.result if result.successful() else None,
                "error": str(result.result) if result.failed() else None,
                "traceback": result.traceback if result.failed() else None,
                "progress": getattr(result, "info", {}).get("progress", 0) if result.status == "PROGRESS" else None
            }
        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "UNKNOWN",
                "error": str(e)
            }
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a distributed task"""
        try:
            self.celery_app.control.revoke(task_id, terminate=True)
            
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            
            logger.info(f"Cancelled task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            inspect = self.celery_app.control.inspect()
            
            # Get active tasks
            active = inspect.active()
            scheduled = inspect.scheduled()
            reserved = inspect.reserved()
            
            # Get queue lengths
            queue_lengths = {}
            try:
                # This requires additional Redis connection
                import redis
                r = redis.Redis.from_url(self.celery_app.conf.broker_url)
                
                for queue_name in ["default", "geometry", "mesh", "materials", "physics", "workflows", "cleanup"]:
                    queue_lengths[queue_name] = r.llen(queue_name)
            except Exception as e:
                logger.warning(f"Could not get queue lengths: {e}")
                queue_lengths = {}
            
            return {
                "active_tasks": active,
                "scheduled_tasks": scheduled,
                "reserved_tasks": reserved,
                "queue_lengths": queue_lengths,
                "task_metrics": self.task_metrics,
                "worker_count": len(active) if active else 0
            }
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"error": str(e)}
    
    def _get_queue_for_task_type(self, task_type: str) -> str:
        """Determine queue name based on task type"""
        queue_mapping = {
            "process_geometry": "geometry",
            "process_mesh": "mesh",
            "process_materials": "materials",
            "process_physics": "physics",
            "execute_workflow": "workflows",
            "cleanup_workflow": "cleanup"
        }
        return queue_mapping.get(task_type, "default")
    
    def _convert_priority(self, priority: TaskPriority) -> int:
        """Convert TaskPriority to Celery priority (0-10)"""
        priority_mapping = {
            TaskPriority.LOW: 2,
            TaskPriority.NORMAL: 5,
            TaskPriority.HIGH: 8,
            TaskPriority.CRITICAL: 10
        }
        return priority_mapping.get(priority, 5)

class WorkflowOrchestrator:
    """Orchestrates distributed workflow execution"""
    
    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
    
    async def execute_distributed_workflow(self, workflow_id: str, project_id: str, 
                                         workflow_steps: List[Dict[str, Any]]) -> str:
        """Execute a workflow across distributed workers"""
        try:
            # Create workflow execution record
            workflow_execution = {
                "workflow_id": workflow_id,
                "project_id": project_id,
                "status": "running",
                "steps": workflow_steps,
                "current_step": 0,
                "started_at": datetime.utcnow(),
                "task_ids": []
            }
            
            self.active_workflows[workflow_id] = workflow_execution
            
            # Submit initial task
            first_step = workflow_steps[0]
            task = WorkflowTask(
                task_id=str(uuid.uuid4()),
                workflow_id=workflow_id,
                project_id=project_id,
                task_type=first_step["type"],
                task_data=first_step["data"],
                priority=TaskPriority.NORMAL
            )
            
            task_id = self.task_manager.submit_workflow_task(task)
            workflow_execution["task_ids"].append(task_id)
            
            logger.info(f"Started distributed workflow {workflow_id}")
            return workflow_id
            
        except Exception as e:
            logger.error(f"Failed to start distributed workflow {workflow_id}: {e}")
            raise
    
    async def check_workflow_progress(self, workflow_id: str) -> Dict[str, Any]:
        """Check progress of distributed workflow"""
        if workflow_id not in self.active_workflows:
            return {"error": "Workflow not found"}
        
        workflow = self.active_workflows[workflow_id]
        
        # Check status of all tasks
        task_statuses = []
        for task_id in workflow["task_ids"]:
            status = self.task_manager.get_task_status(task_id)
            task_statuses.append(status)
        
        # Determine overall workflow status
        completed_tasks = sum(1 for status in task_statuses if status["status"] == "SUCCESS")
        failed_tasks = sum(1 for status in task_statuses if status["status"] == "FAILURE")
        
        if failed_tasks > 0:
            workflow["status"] = "failed"
        elif completed_tasks == len(workflow["steps"]):
            workflow["status"] = "completed"
        else:
            workflow["status"] = "running"
        
        return {
            "workflow_id": workflow_id,
            "status": workflow["status"],
            "progress": completed_tasks / len(workflow["steps"]) * 100,
            "completed_tasks": completed_tasks,
            "total_tasks": len(workflow["steps"]),
            "task_statuses": task_statuses
        }
    
    def get_workflow_metrics(self) -> Dict[str, Any]:
        """Get workflow execution metrics"""
        total_workflows = len(self.active_workflows)
        running_workflows = sum(1 for w in self.active_workflows.values() if w["status"] == "running")
        completed_workflows = sum(1 for w in self.active_workflows.values() if w["status"] == "completed")
        failed_workflows = sum(1 for w in self.active_workflows.values() if w["status"] == "failed")
        
        return {
            "total_workflows": total_workflows,
            "running_workflows": running_workflows,
            "completed_workflows": completed_workflows,
            "failed_workflows": failed_workflows,
            "success_rate": (completed_workflows / max(total_workflows, 1)) * 100,
            "queue_stats": self.task_manager.get_queue_stats()
        }

# Global instances
task_manager = TaskManager(celery_app)
workflow_orchestrator = WorkflowOrchestrator(task_manager)

# Celery signal handlers for monitoring
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task start"""
    logger.info(f"Task {task_id} started: {task.name}")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, 
                        retval=None, state=None, **kwds):
    """Handle task completion"""
    if task_id in task_manager.active_tasks:
        del task_manager.active_tasks[task_id]
    
    if state == "SUCCESS":
        task_manager.task_metrics["completed"] += 1
        logger.info(f"Task {task_id} completed successfully")
    elif state == "FAILURE":
        task_manager.task_metrics["failed"] += 1
        logger.error(f"Task {task_id} failed")

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Handle task failure"""
    task_manager.task_metrics["failed"] += 1
    logger.error(f"Task {task_id} failed with exception: {exception}")

# Convenience functions
def submit_workflow_task(workflow_id: str, project_id: str, task_type: str, 
                        task_data: Dict[str, Any], priority: TaskPriority = TaskPriority.NORMAL) -> str:
    """Submit a workflow task to the distributed queue"""
    task = WorkflowTask(
        task_id=str(uuid.uuid4()),
        workflow_id=workflow_id,
        project_id=project_id,
        task_type=task_type,
        task_data=task_data,
        priority=priority
    )
    return task_manager.submit_workflow_task(task)

async def execute_distributed_workflow(workflow_id: str, project_id: str, 
                                      workflow_steps: List[Dict[str, Any]]) -> str:
    """Execute a workflow across distributed workers"""
    return await workflow_orchestrator.execute_distributed_workflow(workflow_id, project_id, workflow_steps)

def get_workflow_metrics() -> Dict[str, Any]:
    """Get comprehensive workflow metrics"""
    return workflow_orchestrator.get_workflow_metrics()
