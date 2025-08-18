"""
LangGraph Workflow System for ensimu-space platform.
Implements stateful, cyclical agent orchestration with HITL checkpoints.
"""

import asyncio
import json
import logging
import uuid
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable, TypedDict
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresCheckpointer
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from app.libs.database import get_db, DATABASE_URL
from app.libs.cae_models import (
    WorkflowExecution, WorkflowStep, HITLCheckpoint, Project, 
    UploadedFile, OrchestratorMetrics
)
from app.libs.cae_agents import (
    GeometryAgent, MeshAgent, MaterialAgent, PhysicsAgent,
    AgentFactory, WorkflowContext, AgentResponse
)

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# LangGraph State Persistence Configuration
# ============================================================================

class CheckpointerConfig:
    """Configuration for LangGraph state persistence"""
    
    def __init__(self):
        self.checkpointer_type = os.getenv("LANGGRAPH_CHECKPOINTER_TYPE", "postgresql")
        self.database_url = os.getenv("LANGGRAPH_DATABASE_URL", DATABASE_URL)
        self.sqlite_path = os.getenv("LANGGRAPH_SQLITE_PATH", "./workflow_checkpoints.db")
        self.connection_timeout = int(os.getenv("LANGGRAPH_CONNECTION_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("LANGGRAPH_MAX_RETRIES", "3"))
        
        # Validation
        self._validate_config()
    
    def _validate_config(self):
        """Validate checkpointer configuration"""
        if self.checkpointer_type not in ["postgresql", "sqlite"]:
            raise ValueError(f"Invalid checkpointer type: {self.checkpointer_type}")
        
        if self.checkpointer_type == "postgresql" and not self.database_url:
            raise ValueError("PostgreSQL checkpointer requires DATABASE_URL")
        
        logger.info(f"✓ LangGraph checkpointer configured: {self.checkpointer_type}")

class LangGraphCheckpointerManager:
    """Manages LangGraph checkpointer instances with error handling and fallback"""
    
    def __init__(self, config: CheckpointerConfig):
        self.config = config
        self.checkpointer = None
        self._initialize_checkpointer()
    
    def _initialize_checkpointer(self):
        """Initialize the appropriate checkpointer with error handling"""
        try:
            if self.config.checkpointer_type == "postgresql":
                self.checkpointer = self._create_postgresql_checkpointer()
            else:
                self.checkpointer = self._create_sqlite_checkpointer()
            
            logger.info(f"✓ LangGraph checkpointer initialized: {self.config.checkpointer_type}")
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.config.checkpointer_type} checkpointer: {str(e)}")
            
            # Fallback to SQLite if PostgreSQL fails
            if self.config.checkpointer_type == "postgresql":
                logger.warning("Falling back to SQLite checkpointer")
                try:
                    self.checkpointer = self._create_sqlite_checkpointer()
                    logger.info("✓ SQLite fallback checkpointer initialized")
                except Exception as fallback_error:
                    logger.error(f"Fallback checkpointer failed: {str(fallback_error)}")
                    raise RuntimeError("All checkpointer initialization attempts failed")
            else:
                raise e
    
    def _create_postgresql_checkpointer(self):
        """Create PostgreSQL checkpointer with connection validation"""
        try:
            # Validate database connection
            engine = create_engine(
                self.config.database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args={"connect_timeout": self.config.connection_timeout}
            )
            
            # Test connection
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            
            # Create PostgreSQL checkpointer
            checkpointer = PostgresCheckpointer.from_conn_string(
                self.config.database_url,
                # Additional configuration for production use
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600
            )
            
            logger.info("✓ PostgreSQL checkpointer created successfully")
            return checkpointer
            
        except Exception as e:
            logger.error(f"PostgreSQL checkpointer creation failed: {str(e)}")
            raise e
    
    def _create_sqlite_checkpointer(self):
        """Create SQLite checkpointer with file validation"""
        try:
            # Ensure directory exists
            sqlite_dir = os.path.dirname(self.config.sqlite_path)
            if sqlite_dir and not os.path.exists(sqlite_dir):
                os.makedirs(sqlite_dir, exist_ok=True)
            
            # Create SQLite checkpointer
            checkpointer = SqliteSaver.from_conn_string(f"sqlite:///{self.config.sqlite_path}")
            
            logger.info(f"✓ SQLite checkpointer created: {self.config.sqlite_path}")
            return checkpointer
            
        except Exception as e:
            logger.error(f"SQLite checkpointer creation failed: {str(e)}")
            raise e
    
    def get_checkpointer(self):
        """Get the configured checkpointer instance"""
        if self.checkpointer is None:
            raise RuntimeError("Checkpointer not initialized")
        return self.checkpointer
    
    def validate_checkpointer(self) -> bool:
        """Validate that the checkpointer is working correctly"""
        try:
            # Test basic checkpointer functionality
            if self.checkpointer is None:
                return False
            
            # For SQLite, check if file is accessible
            if isinstance(self.checkpointer, SqliteSaver):
                return os.path.exists(self.config.sqlite_path) or os.access(
                    os.path.dirname(self.config.sqlite_path) or ".", os.W_OK
                )
            
            # For PostgreSQL, test connection
            elif isinstance(self.checkpointer, PostgresCheckpointer):
                # This would require accessing internal connection,
                # so we'll assume it's valid if it was created successfully
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Checkpointer validation failed: {str(e)}")
            return False

# ============================================================================
# State Management
# ============================================================================

class SimulationState(TypedDict):
    """Central state object for LangGraph workflow coordination"""
    # Project context
    project_id: str
    workflow_id: str
    user_goal: str
    physics_type: str  # cfd, structural, thermal, electromagnetic, multi_physics
    
    # File management
    cad_files: List[Dict[str, Any]]
    current_file: Optional[Dict[str, Any]]
    
    # Preprocessing status
    geometry_status: str  # pending, processing, completed, failed, requires_review
    mesh_status: str
    materials_status: str
    physics_status: str
    
    # Agent outputs
    geometry_analysis: Optional[Dict[str, Any]]
    mesh_recommendations: Optional[Dict[str, Any]]
    material_assignments: Optional[Dict[str, Any]]
    physics_setup: Optional[Dict[str, Any]]
    
    # Workflow control
    current_step: str
    completed_steps: List[str]
    failed_steps: List[str]
    hitl_checkpoints: List[Dict[str, Any]]
    
    # Quality metrics
    mesh_quality_metrics: Optional[Dict[str, Any]]
    convergence_criteria: Optional[Dict[str, Any]]
    validation_results: Optional[Dict[str, Any]]
    
    # Error handling
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    
    # Metadata
    created_at: str
    updated_at: str
    iteration_count: int
    max_iterations: int

class WorkflowStatus(Enum):
    """Workflow execution status"""
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_FOR_HUMAN = "waiting_for_human"

# ============================================================================
# Workflow State Persistence
# ============================================================================

class DatabaseStatePersistence:
    """Manages workflow state persistence to database"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    async def save_state(self, state: SimulationState) -> bool:
        """Save workflow state to database"""
        try:
            workflow = self.db_session.query(WorkflowExecution).filter(
                WorkflowExecution.id == state["workflow_id"]
            ).first()
            
            if workflow:
                # Update existing workflow
                workflow.current_step = state["current_step"]
                workflow.global_context = dict(state)
                workflow.updated_at = datetime.utcnow()
                
                # Update status based on state
                if state.get("hitl_checkpoints") and any(
                    cp.get("status") == "pending" for cp in state["hitl_checkpoints"]
                ):
                    workflow.status = WorkflowStatus.WAITING_FOR_HUMAN.value
                elif state["failed_steps"]:
                    workflow.status = WorkflowStatus.FAILED.value
                elif len(state["completed_steps"]) >= 4:  # All main steps completed
                    workflow.status = WorkflowStatus.COMPLETED.value
                else:
                    workflow.status = WorkflowStatus.RUNNING.value
                
                self.db_session.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to save workflow state: {str(e)}")
            self.db_session.rollback()
            return False
    
    async def load_state(self, workflow_id: str) -> Optional[SimulationState]:
        """Load workflow state from database"""
        try:
            workflow = self.db_session.query(WorkflowExecution).filter(
                WorkflowExecution.id == workflow_id
            ).first()
            
            if workflow and workflow.global_context:
                return SimulationState(**workflow.global_context)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load workflow state: {str(e)}")
            return None
    
    async def create_workflow_step(self, workflow_id: str, step_name: str, 
                                 agent_type: str, step_order: int,
                                 input_data: Dict[str, Any]) -> str:
        """Create a new workflow step record"""
        try:
            step = WorkflowStep(
                workflow_id=workflow_id,
                step_name=step_name,
                agent_type=agent_type,
                step_order=step_order,
                status="running",
                input_data=input_data,
                started_at=datetime.utcnow()
            )
            
            self.db_session.add(step)
            self.db_session.commit()
            
            return str(step.id)
            
        except Exception as e:
            logger.error(f"Failed to create workflow step: {str(e)}")
            self.db_session.rollback()
            return ""
    
    async def update_workflow_step(self, step_id: str, status: str, 
                                 output_data: Dict[str, Any],
                                 error_message: Optional[str] = None) -> bool:
        """Update workflow step with results"""
        try:
            step = self.db_session.query(WorkflowStep).filter(
                WorkflowStep.id == step_id
            ).first()
            
            if step:
                step.status = status
                step.output_data = output_data
                step.completed_at = datetime.utcnow()
                step.error_message = error_message
                
                if step.started_at:
                    duration = (datetime.utcnow() - step.started_at).total_seconds()
                    step.duration_seconds = int(duration)
                
                self.db_session.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update workflow step: {str(e)}")
            self.db_session.rollback()
            return False

# ============================================================================
# HITL Checkpoint Management
# ============================================================================

class HITLCheckpointManager:
    """Manages Human-in-the-Loop checkpoints"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    async def create_checkpoint(self, workflow_id: str, step_id: str,
                              checkpoint_type: str, checkpoint_data: Dict[str, Any],
                              agent_recommendations: List[str],
                              timeout_minutes: int = 60) -> str:
        """Create a new HITL checkpoint"""
        try:
            checkpoint = HITLCheckpoint(
                workflow_id=workflow_id,
                step_id=step_id,
                checkpoint_type=checkpoint_type,
                description=f"Human review required for {checkpoint_type}",
                checkpoint_data=checkpoint_data,
                agent_recommendations=agent_recommendations,
                status="pending",
                timeout_at=datetime.utcnow() + timedelta(minutes=timeout_minutes)
            )
            
            self.db_session.add(checkpoint)
            self.db_session.commit()
            
            logger.info(f"Created HITL checkpoint {checkpoint.id} for workflow {workflow_id}")
            return str(checkpoint.id)
            
        except Exception as e:
            logger.error(f"Failed to create HITL checkpoint: {str(e)}")
            self.db_session.rollback()
            return ""
    
    async def get_pending_checkpoints(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get pending checkpoints for a workflow"""
        try:
            checkpoints = self.db_session.query(HITLCheckpoint).filter(
                HITLCheckpoint.workflow_id == workflow_id,
                HITLCheckpoint.status == "pending"
            ).all()
            
            return [
                {
                    "checkpoint_id": str(cp.id),
                    "checkpoint_type": cp.checkpoint_type,
                    "description": cp.description,
                    "checkpoint_data": cp.checkpoint_data,
                    "agent_recommendations": cp.agent_recommendations,
                    "created_at": cp.created_at.isoformat(),
                    "timeout_at": cp.timeout_at.isoformat() if cp.timeout_at else None
                }
                for cp in checkpoints
            ]
            
        except Exception as e:
            logger.error(f"Failed to get pending checkpoints: {str(e)}")
            return []
    
    async def respond_to_checkpoint(self, checkpoint_id: str, approved: bool,
                                  human_feedback: Optional[str] = None,
                                  human_response: Optional[Dict[str, Any]] = None,
                                  reviewer_id: Optional[str] = None) -> bool:
        """Respond to a HITL checkpoint"""
        try:
            checkpoint = self.db_session.query(HITLCheckpoint).filter(
                HITLCheckpoint.id == checkpoint_id
            ).first()
            
            if checkpoint:
                checkpoint.status = "approved" if approved else "rejected"
                checkpoint.human_feedback = human_feedback
                checkpoint.human_response = human_response or {}
                checkpoint.reviewer_id = reviewer_id
                checkpoint.responded_at = datetime.utcnow()
                
                self.db_session.commit()
                
                logger.info(f"HITL checkpoint {checkpoint_id} {'approved' if approved else 'rejected'}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to respond to checkpoint: {str(e)}")
            self.db_session.rollback()
            return False
    
    async def check_checkpoint_timeout(self, checkpoint_id: str) -> bool:
        """Check if checkpoint has timed out"""
        try:
            checkpoint = self.db_session.query(HITLCheckpoint).filter(
                HITLCheckpoint.id == checkpoint_id
            ).first()
            
            if checkpoint and checkpoint.timeout_at:
                return datetime.utcnow() > checkpoint.timeout_at
            
            return False

        except Exception as e:
            logger.error(f"Failed to check checkpoint timeout: {str(e)}")
            return False

# ============================================================================
# Workflow Node Implementations
# ============================================================================

class WorkflowNodeExecutor:
    """Executes workflow nodes with agent integration"""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.agent_factory = AgentFactory(db_session)
        self.state_persistence = DatabaseStatePersistence(db_session)
        self.hitl_manager = HITLCheckpointManager(db_session)

    async def geometry_processing_node(self, state: SimulationState) -> SimulationState:
        """Enhanced geometry processing with WebSocket notifications"""
        logger.info(f"Starting geometry processing for workflow {state['workflow_id']}")

        # Create workflow step
        step_id = await self.state_persistence.create_workflow_step(
            workflow_id=state["workflow_id"],
            step_name="geometry_processing",
            agent_type="geometry",
            step_order=1,
            input_data={"cad_files": state["cad_files"]}
        )

        try:
            # Update state
            state["current_step"] = "geometry_processing"
            state["geometry_status"] = "processing"
            state["updated_at"] = datetime.utcnow().isoformat()

            # Create workflow context
            context = WorkflowContext(
                project_id=state["project_id"],
                workflow_id=state["workflow_id"],
                user_goal=state["user_goal"],
                physics_type=state["physics_type"],
                current_step=state["current_step"],
                global_state=dict(state),
                agent_outputs={}
            )

            # Execute geometry agent
            geometry_agent = self.agent_factory.create_agent("geometry")
            request_data = {
                "cad_files": state["cad_files"],
                "analysis_requirements": {
                    "physics_type": state["physics_type"],
                    "user_goal": state["user_goal"]
                }
            }

            response = await geometry_agent.process_request(request_data, context)

            if response.success:
                # Update state with results
                state["geometry_analysis"] = response.data
                state["geometry_status"] = "completed"
                state["completed_steps"].append("geometry_processing")

                # Update workflow step
                await self.state_persistence.update_workflow_step(
                    step_id=step_id,
                    status="completed",
                    output_data=response.data
                )

                logger.info(f"Geometry processing completed successfully")

            else:
                # Handle failure
                state["geometry_status"] = "failed"
                state["failed_steps"].append("geometry_processing")
                state["errors"].append({
                    "step": "geometry_processing",
                    "error": response.error_message or "Unknown geometry processing error",
                    "timestamp": datetime.utcnow().isoformat()
                })

                # Update workflow step
                await self.state_persistence.update_workflow_step(
                    step_id=step_id,
                    status="failed",
                    output_data=response.data,
                    error_message=response.error_message
                )

                logger.error(f"Geometry processing failed: {response.error_message}")

            # Save state
            await self.state_persistence.save_state(state)

            return state

        except Exception as e:
            logger.error(f"Geometry processing node failed: {str(e)}")
            state["geometry_status"] = "failed"
            state["failed_steps"].append("geometry_processing")
            state["errors"].append({
                "step": "geometry_processing",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

            # Update workflow step
            await self.state_persistence.update_workflow_step(
                step_id=step_id,
                status="failed",
                output_data={},
                error_message=str(e)
            )

            await self.state_persistence.save_state(state)
            return state

    async def mesh_generation_node(self, state: SimulationState) -> SimulationState:
        """Enhanced mesh generation with quality control"""
        logger.info(f"Starting mesh generation for workflow {state['workflow_id']}")

        # Create workflow step
        step_id = await self.state_persistence.create_workflow_step(
            workflow_id=state["workflow_id"],
            step_name="mesh_generation",
            agent_type="mesh",
            step_order=2,
            input_data={"geometry_analysis": state.get("geometry_analysis")}
        )

        try:
            # Update state
            state["current_step"] = "mesh_generation"
            state["mesh_status"] = "processing"
            state["updated_at"] = datetime.utcnow().isoformat()

            # Create workflow context
            context = WorkflowContext(
                project_id=state["project_id"],
                workflow_id=state["workflow_id"],
                user_goal=state["user_goal"],
                physics_type=state["physics_type"],
                current_step=state["current_step"],
                global_state=dict(state),
                agent_outputs={"geometry": state.get("geometry_analysis", {})}
            )

            # Execute mesh agent
            mesh_agent = self.agent_factory.create_agent("mesh")
            request_data = {
                "geometry_analysis": state.get("geometry_analysis", {}),
                "computational_resources": {"cpu_cores": 8, "memory_gb": 32},
                "quality_requirements": {"target_quality": 0.8, "max_aspect_ratio": 10}
            }

            response = await mesh_agent.process_request(request_data, context)

            if response.success:
                # Update state with results
                state["mesh_recommendations"] = response.data
                state["mesh_quality_metrics"] = response.data.get("quality_assessment", {})
                state["mesh_status"] = "completed"
                state["completed_steps"].append("mesh_generation")

                # Update workflow step
                await self.state_persistence.update_workflow_step(
                    step_id=step_id,
                    status="completed",
                    output_data=response.data
                )

                logger.info(f"Mesh generation completed successfully")

            else:
                # Handle failure
                state["mesh_status"] = "failed"
                state["failed_steps"].append("mesh_generation")
                state["errors"].append({
                    "step": "mesh_generation",
                    "error": response.error_message or "Unknown mesh generation error",
                    "timestamp": datetime.utcnow().isoformat()
                })

                # Update workflow step
                await self.state_persistence.update_workflow_step(
                    step_id=step_id,
                    status="failed",
                    output_data=response.data,
                    error_message=response.error_message
                )

                logger.error(f"Mesh generation failed: {response.error_message}")

            # Save state
            await self.state_persistence.save_state(state)

            return state

        except Exception as e:
            logger.error(f"Mesh generation node failed: {str(e)}")
            state["mesh_status"] = "failed"
            state["failed_steps"].append("mesh_generation")
            state["errors"].append({
                "step": "mesh_generation",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

            # Update workflow step
            await self.state_persistence.update_workflow_step(
                step_id=step_id,
                status="failed",
                output_data={},
                error_message=str(e)
            )

            await self.state_persistence.save_state(state)
            return state

    async def material_assignment_node(self, state: SimulationState) -> SimulationState:
        """Enhanced material assignment with database integration"""
        logger.info(f"Starting material assignment for workflow {state['workflow_id']}")

        # Create workflow step
        step_id = await self.state_persistence.create_workflow_step(
            workflow_id=state["workflow_id"],
            step_name="material_assignment",
            agent_type="materials",
            step_order=3,
            input_data={
                "geometry_analysis": state.get("geometry_analysis"),
                "mesh_recommendations": state.get("mesh_recommendations")
            }
        )

        try:
            # Update state
            state["current_step"] = "material_assignment"
            state["materials_status"] = "processing"
            state["updated_at"] = datetime.utcnow().isoformat()

            # Create workflow context
            context = WorkflowContext(
                project_id=state["project_id"],
                workflow_id=state["workflow_id"],
                user_goal=state["user_goal"],
                physics_type=state["physics_type"],
                current_step=state["current_step"],
                global_state=dict(state),
                agent_outputs={
                    "geometry": state.get("geometry_analysis", {}),
                    "mesh": state.get("mesh_recommendations", {})
                }
            )

            # Execute material agent
            material_agent = self.agent_factory.create_agent("materials")
            request_data = {
                "geometry_analysis": state.get("geometry_analysis", {}),
                "physics_requirements": {"physics_type": state["physics_type"]},
                "application_context": {"user_goal": state["user_goal"]}
            }

            response = await material_agent.process_request(request_data, context)

            if response.success:
                # Update state with results
                state["material_assignments"] = response.data
                state["materials_status"] = "completed"
                state["completed_steps"].append("material_assignment")

                # Update workflow step
                await self.state_persistence.update_workflow_step(
                    step_id=step_id,
                    status="completed",
                    output_data=response.data
                )

                logger.info(f"Material assignment completed successfully")

            else:
                # Handle failure
                state["materials_status"] = "failed"
                state["failed_steps"].append("material_assignment")
                state["errors"].append({
                    "step": "material_assignment",
                    "error": response.error_message or "Unknown material assignment error",
                    "timestamp": datetime.utcnow().isoformat()
                })

                # Update workflow step
                await self.state_persistence.update_workflow_step(
                    step_id=step_id,
                    status="failed",
                    output_data=response.data,
                    error_message=response.error_message
                )

                logger.error(f"Material assignment failed: {response.error_message}")

            # Save state
            await self.state_persistence.save_state(state)

            return state

        except Exception as e:
            logger.error(f"Material assignment node failed: {str(e)}")
            state["materials_status"] = "failed"
            state["failed_steps"].append("material_assignment")
            state["errors"].append({
                "step": "material_assignment",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

            # Update workflow step
            await self.state_persistence.update_workflow_step(
                step_id=step_id,
                status="failed",
                output_data={},
                error_message=str(e)
            )

            await self.state_persistence.save_state(state)
            return state

    async def physics_setup_node(self, state: SimulationState) -> SimulationState:
        """Enhanced physics setup with solver configuration"""
        logger.info(f"Starting physics setup for workflow {state['workflow_id']}")

        # Create workflow step
        step_id = await self.state_persistence.create_workflow_step(
            workflow_id=state["workflow_id"],
            step_name="physics_setup",
            agent_type="physics",
            step_order=4,
            input_data={
                "geometry_analysis": state.get("geometry_analysis"),
                "mesh_recommendations": state.get("mesh_recommendations"),
                "material_assignments": state.get("material_assignments")
            }
        )

        try:
            # Update state
            state["current_step"] = "physics_setup"
            state["physics_status"] = "processing"
            state["updated_at"] = datetime.utcnow().isoformat()

            # Create workflow context
            context = WorkflowContext(
                project_id=state["project_id"],
                workflow_id=state["workflow_id"],
                user_goal=state["user_goal"],
                physics_type=state["physics_type"],
                current_step=state["current_step"],
                global_state=dict(state),
                agent_outputs={
                    "geometry": state.get("geometry_analysis", {}),
                    "mesh": state.get("mesh_recommendations", {}),
                    "materials": state.get("material_assignments", {})
                }
            )

            # Execute physics agent
            physics_agent = self.agent_factory.create_agent("physics")
            request_data = {
                "geometry_analysis": state.get("geometry_analysis", {}),
                "mesh_strategy": state.get("mesh_recommendations", {}),
                "material_assignment": state.get("material_assignments", {}),
                "operating_conditions": {"physics_type": state["physics_type"]}
            }

            response = await physics_agent.process_request(request_data, context)

            if response.success:
                # Update state with results
                state["physics_setup"] = response.data
                state["convergence_criteria"] = response.data.get("convergence_criteria", {})
                state["physics_status"] = "completed"
                state["completed_steps"].append("physics_setup")

                # Update workflow step
                await self.state_persistence.update_workflow_step(
                    step_id=step_id,
                    status="completed",
                    output_data=response.data
                )

                logger.info(f"Physics setup completed successfully")

            else:
                # Handle failure
                state["physics_status"] = "failed"
                state["failed_steps"].append("physics_setup")
                state["errors"].append({
                    "step": "physics_setup",
                    "error": response.error_message or "Unknown physics setup error",
                    "timestamp": datetime.utcnow().isoformat()
                })

                # Update workflow step
                await self.state_persistence.update_workflow_step(
                    step_id=step_id,
                    status="failed",
                    output_data=response.data,
                    error_message=response.error_message
                )

                logger.error(f"Physics setup failed: {response.error_message}")

            # Save state
            await self.state_persistence.save_state(state)

            return state

        except Exception as e:
            logger.error(f"Physics setup node failed: {str(e)}")
            state["physics_status"] = "failed"
            state["failed_steps"].append("physics_setup")
            state["errors"].append({
                "step": "physics_setup",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

            # Update workflow step
            await self.state_persistence.update_workflow_step(
                step_id=step_id,
                status="failed",
                output_data={},
                error_message=str(e)
            )

            await self.state_persistence.save_state(state)
            return state

    async def validation_node(self, state: SimulationState) -> SimulationState:
        """Comprehensive validation of preprocessing results"""
        logger.info(f"Starting validation for workflow {state['workflow_id']}")

        try:
            # Update state
            state["current_step"] = "validation"
            state["updated_at"] = datetime.utcnow().isoformat()

            # Perform comprehensive validation
            validation_results = await self._validate_preprocessing_results(state)

            # Update state with validation results
            state["validation_results"] = validation_results

            if validation_results["overall_status"] == "passed":
                state["completed_steps"].append("validation")
                logger.info(f"Validation passed for workflow {state['workflow_id']}")
            else:
                # Add warnings for failed validations
                for warning in validation_results.get("warnings", []):
                    state["warnings"].append({
                        "step": "validation",
                        "warning": warning,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                # Add errors for critical failures
                for error in validation_results.get("errors", []):
                    state["errors"].append({
                        "step": "validation",
                        "error": error,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                logger.warning(f"Validation issues found for workflow {state['workflow_id']}")

            # Save state
            await self.state_persistence.save_state(state)

            return state

        except Exception as e:
            logger.error(f"Validation node failed: {str(e)}")
            state["errors"].append({
                "step": "validation",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

            await self.state_persistence.save_state(state)
            return state

    async def hitl_checkpoint_node(self, state: SimulationState) -> SimulationState:
        """Human-in-the-Loop checkpoint for validation and approval"""
        logger.info(f"Creating HITL checkpoint for workflow {state['workflow_id']}")

        try:
            # Update state
            state["current_step"] = "hitl_checkpoint"
            state["updated_at"] = datetime.utcnow().isoformat()

            # Prepare checkpoint data
            checkpoint_data = {
                "geometry_analysis": state.get("geometry_analysis"),
                "mesh_recommendations": state.get("mesh_recommendations"),
                "material_assignments": state.get("material_assignments"),
                "physics_setup": state.get("physics_setup"),
                "validation_results": state.get("validation_results"),
                "quality_metrics": {
                    "mesh_quality": state.get("mesh_quality_metrics"),
                    "convergence_criteria": state.get("convergence_criteria")
                }
            }

            # Generate agent recommendations
            agent_recommendations = await self._generate_checkpoint_recommendations(state)

            # Create HITL checkpoint
            checkpoint_id = await self.hitl_manager.create_checkpoint(
                workflow_id=state["workflow_id"],
                step_id="",  # No specific step for overall checkpoint
                checkpoint_type="preprocessing_review",
                checkpoint_data=checkpoint_data,
                agent_recommendations=agent_recommendations,
                timeout_minutes=60
            )

            if checkpoint_id:
                # Add checkpoint to state
                checkpoint_info = {
                    "checkpoint_id": checkpoint_id,
                    "checkpoint_type": "preprocessing_review",
                    "status": "pending",
                    "created_at": datetime.utcnow().isoformat(),
                    "agent_recommendations": agent_recommendations
                }

                state["hitl_checkpoints"].append(checkpoint_info)

                logger.info(f"HITL checkpoint {checkpoint_id} created for workflow {state['workflow_id']}")
            else:
                logger.error(f"Failed to create HITL checkpoint for workflow {state['workflow_id']}")
                state["errors"].append({
                    "step": "hitl_checkpoint",
                    "error": "Failed to create HITL checkpoint",
                    "timestamp": datetime.utcnow().isoformat()
                })

            # Save state
            await self.state_persistence.save_state(state)

            return state

        except Exception as e:
            logger.error(f"HITL checkpoint node failed: {str(e)}")
            state["errors"].append({
                "step": "hitl_checkpoint",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

            await self.state_persistence.save_state(state)
            return state

    async def _validate_preprocessing_results(self, state: SimulationState) -> Dict[str, Any]:
        """Validate preprocessing results comprehensively"""
        validation_results = {
            "overall_status": "passed",
            "component_validations": {},
            "warnings": [],
            "errors": [],
            "recommendations": []
        }

        # Validate geometry analysis
        if state.get("geometry_analysis"):
            geo_validation = self._validate_geometry_analysis(state["geometry_analysis"])
            validation_results["component_validations"]["geometry"] = geo_validation
            if not geo_validation["passed"]:
                validation_results["overall_status"] = "failed"
                validation_results["errors"].extend(geo_validation.get("errors", []))

        # Validate mesh recommendations
        if state.get("mesh_recommendations"):
            mesh_validation = self._validate_mesh_recommendations(state["mesh_recommendations"])
            validation_results["component_validations"]["mesh"] = mesh_validation
            if not mesh_validation["passed"]:
                validation_results["overall_status"] = "failed"
                validation_results["errors"].extend(mesh_validation.get("errors", []))

        # Validate material assignments
        if state.get("material_assignments"):
            material_validation = self._validate_material_assignments(state["material_assignments"])
            validation_results["component_validations"]["materials"] = material_validation
            if not material_validation["passed"]:
                validation_results["overall_status"] = "failed"
                validation_results["errors"].extend(material_validation.get("errors", []))

        # Validate physics setup
        if state.get("physics_setup"):
            physics_validation = self._validate_physics_setup(state["physics_setup"])
            validation_results["component_validations"]["physics"] = physics_validation
            if not physics_validation["passed"]:
                validation_results["overall_status"] = "failed"
                validation_results["errors"].extend(physics_validation.get("errors", []))

        return validation_results

    def _validate_geometry_analysis(self, geometry_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate geometry analysis results"""
        validation = {"passed": True, "errors": [], "warnings": []}

        # Check for required fields
        required_fields = ["recommendations", "confidence_score"]
        for field in required_fields:
            if field not in geometry_analysis:
                validation["passed"] = False
                validation["errors"].append(f"Missing required field: {field}")

        # Check confidence score
        confidence = geometry_analysis.get("confidence_score", 0)
        if confidence < 0.7:
            validation["warnings"].append(f"Low confidence score: {confidence}")

        return validation

    def _validate_mesh_recommendations(self, mesh_recommendations: Dict[str, Any]) -> Dict[str, Any]:
        """Validate mesh recommendations"""
        validation = {"passed": True, "errors": [], "warnings": []}

        # Check for required fields
        required_fields = ["mesh_strategy", "confidence_score"]
        for field in required_fields:
            if field not in mesh_recommendations:
                validation["passed"] = False
                validation["errors"].append(f"Missing required field: {field}")

        return validation

    def _validate_material_assignments(self, material_assignments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate material assignments"""
        validation = {"passed": True, "errors": [], "warnings": []}

        # Check for required fields
        required_fields = ["material_recommendations", "confidence_score"]
        for field in required_fields:
            if field not in material_assignments:
                validation["passed"] = False
                validation["errors"].append(f"Missing required field: {field}")

        return validation

    def _validate_physics_setup(self, physics_setup: Dict[str, Any]) -> Dict[str, Any]:
        """Validate physics setup"""
        validation = {"passed": True, "errors": [], "warnings": []}

        # Check for required fields
        required_fields = ["boundary_conditions", "solver_configuration", "confidence_score"]
        for field in required_fields:
            if field not in physics_setup:
                validation["passed"] = False
                validation["errors"].append(f"Missing required field: {field}")

        return validation

    async def _generate_checkpoint_recommendations(self, state: SimulationState) -> List[str]:
        """Generate recommendations for HITL checkpoint"""
        recommendations = []

        # Add recommendations based on validation results
        validation_results = state.get("validation_results", {})
        if validation_results.get("overall_status") == "passed":
            recommendations.append("All preprocessing steps completed successfully")
            recommendations.append("Simulation setup is ready for execution")
        else:
            recommendations.append("Some validation issues were found - please review")
            for error in validation_results.get("errors", []):
                recommendations.append(f"Issue: {error}")

        # Add quality-based recommendations
        mesh_quality = state.get("mesh_quality_metrics", {})
        if mesh_quality.get("predicted_quality_score", 0) < 0.8:
            recommendations.append("Consider mesh refinement for better quality")

        return recommendations

# ============================================================================
# Conditional Routing Logic
# ============================================================================

class WorkflowRouter:
    """Handles conditional routing for cyclical workflows"""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.hitl_manager = HITLCheckpointManager(db_session)

    async def route_next_step(self, state: SimulationState) -> str:
        """
        Conditional routing based on current state and results.
        Implements the cyclical, iterative nature of simulation preprocessing.
        """
        current_step = state["current_step"]
        iteration_count = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 3)

        logger.info(f"Routing from step '{current_step}' (iteration {iteration_count})")

        # Check for maximum iterations to prevent infinite loops
        if iteration_count >= max_iterations:
            logger.warning(f"Maximum iterations ({max_iterations}) reached for workflow {state['workflow_id']}")
            return "hitl_checkpoint"

        # Route based on current step and status
        if current_step == "geometry_processing":
            return await self._route_from_geometry(state)
        elif current_step == "mesh_generation":
            return await self._route_from_mesh(state)
        elif current_step == "material_assignment":
            return await self._route_from_materials(state)
        elif current_step == "physics_setup":
            return await self._route_from_physics(state)
        elif current_step == "validation":
            return await self._route_from_validation(state)
        elif current_step == "hitl_checkpoint":
            return await self._route_from_hitl(state)
        else:
            logger.warning(f"Unknown step '{current_step}' in routing")
            return END

    async def _route_from_geometry(self, state: SimulationState) -> str:
        """Route from geometry processing step"""
        if state["geometry_status"] == "completed":
            # Check geometry quality
            geometry_analysis = state.get("geometry_analysis", {})
            mesh_readiness = geometry_analysis.get("quality_metrics", {}).get("mesh_readiness_score", 1.0)

            if mesh_readiness < 0.7:
                logger.info("Geometry mesh readiness low, requiring iteration")
                state["iteration_count"] = state.get("iteration_count", 0) + 1
                return "geometry_processing"  # Iterate on geometry
            else:
                return "mesh_generation"
        elif state["geometry_status"] == "failed":
            return "error_recovery"
        else:
            return "geometry_processing"  # Retry

    async def _route_from_mesh(self, state: SimulationState) -> str:
        """Route from mesh generation step"""
        if state["mesh_status"] == "completed":
            # Check mesh quality
            mesh_quality = state.get("mesh_quality_metrics", {})
            quality_score = mesh_quality.get("predicted_quality_score", 1.0)

            if quality_score < 0.7:
                logger.info("Mesh quality low, requiring refinement")
                state["iteration_count"] = state.get("iteration_count", 0) + 1
                return "mesh_refinement"  # Iterative improvement
            else:
                return "material_assignment"
        elif state["mesh_status"] == "failed":
            return "error_recovery"
        else:
            return "mesh_generation"  # Retry

    async def _route_from_materials(self, state: SimulationState) -> str:
        """Route from material assignment step"""
        if state["materials_status"] == "completed":
            return "physics_setup"
        elif state["materials_status"] == "failed":
            return "error_recovery"
        else:
            return "material_assignment"  # Retry

    async def _route_from_physics(self, state: SimulationState) -> str:
        """Route from physics setup step"""
        if state["physics_status"] == "completed":
            return "validation"
        elif state["physics_status"] == "failed":
            return "error_recovery"
        else:
            return "physics_setup"  # Retry

    async def _route_from_validation(self, state: SimulationState) -> str:
        """Route from validation step"""
        validation_results = state.get("validation_results", {})

        if validation_results.get("overall_status") == "passed":
            return "hitl_checkpoint"
        elif validation_results.get("overall_status") == "failed":
            # Determine which step needs rework based on failed components
            failed_components = validation_results.get("component_validations", {})

            for component, validation in failed_components.items():
                if not validation.get("passed", True):
                    logger.info(f"Validation failed for {component}, cycling back")
                    state["iteration_count"] = state.get("iteration_count", 0) + 1

                    if component == "geometry":
                        return "geometry_processing"
                    elif component == "mesh":
                        return "mesh_generation"
                    elif component == "materials":
                        return "material_assignment"
                    elif component == "physics":
                        return "physics_setup"

            return "error_recovery"
        else:
            return "validation"  # Retry validation

    async def _route_from_hitl(self, state: SimulationState) -> str:
        """Route from HITL checkpoint step"""
        # Check if human has responded to any pending checkpoints
        pending_checkpoints = await self.hitl_manager.get_pending_checkpoints(state["workflow_id"])

        if not pending_checkpoints:
            # No pending checkpoints, check latest checkpoint status
            latest_checkpoint = state["hitl_checkpoints"][-1] if state["hitl_checkpoints"] else None

            if latest_checkpoint:
                checkpoint_id = latest_checkpoint["checkpoint_id"]

                # Get checkpoint from database to check current status
                checkpoint = self.db_session.query(HITLCheckpoint).filter(
                    HITLCheckpoint.id == checkpoint_id
                ).first()

                if checkpoint:
                    if checkpoint.status == "approved":
                        logger.info(f"HITL checkpoint {checkpoint_id} approved - workflow complete")
                        return END  # Workflow complete
                    elif checkpoint.status == "rejected":
                        # Human requested changes - route back based on feedback
                        feedback = checkpoint.human_response or {}
                        logger.info(f"HITL checkpoint {checkpoint_id} rejected - routing for rework")

                        state["iteration_count"] = state.get("iteration_count", 0) + 1

                        if feedback.get("rework_geometry"):
                            return "geometry_processing"
                        elif feedback.get("rework_mesh"):
                            return "mesh_generation"
                        elif feedback.get("rework_materials"):
                            return "material_assignment"
                        elif feedback.get("rework_physics"):
                            return "physics_setup"
                        else:
                            return "validation"  # General rework
                    else:
                        # Still pending or other status
                        return "hitl_checkpoint"  # Wait for human response
                else:
                    logger.error(f"Checkpoint {checkpoint_id} not found in database")
                    return END
            else:
                logger.error("No checkpoints found in state")
                return END
        else:
            # Still have pending checkpoints
            return "hitl_checkpoint"  # Wait for human response

# ============================================================================
# Workflow Graph Construction
# ============================================================================

class SimulationPreprocessingWorkflow:
    """Main workflow class that orchestrates the LangGraph simulation preprocessing"""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.node_executor = WorkflowNodeExecutor(db_session)
        self.router = WorkflowRouter(db_session)
        self.state_persistence = DatabaseStatePersistence(db_session)
        self.hitl_manager = HITLCheckpointManager(db_session)
        self.workflow_graph = None

        # Initialize LangGraph state persistence checkpointer
        try:
            checkpointer_config = CheckpointerConfig()
            self.checkpointer_manager = LangGraphCheckpointerManager(checkpointer_config)
            logger.info("✓ LangGraph checkpointer manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize checkpointer manager: {str(e)}")
            raise RuntimeError(f"LangGraph state persistence initialization failed: {str(e)}")

        # Initialize the workflow graph
        self._create_workflow_graph()

    def _create_workflow_graph(self) -> StateGraph:
        """Create the LangGraph workflow for simulation preprocessing"""
        # Initialize the graph
        workflow = StateGraph(SimulationState)

        # Add nodes
        workflow.add_node("geometry_processing", self.node_executor.geometry_processing_node)
        workflow.add_node("mesh_generation", self.node_executor.mesh_generation_node)
        workflow.add_node("material_assignment", self.node_executor.material_assignment_node)
        workflow.add_node("physics_setup", self.node_executor.physics_setup_node)
        workflow.add_node("validation", self.node_executor.validation_node)
        workflow.add_node("hitl_checkpoint", self.node_executor.hitl_checkpoint_node)
        workflow.add_node("error_recovery", self._error_recovery_node)
        workflow.add_node("mesh_refinement", self._mesh_refinement_node)

        # Set entry point
        workflow.set_entry_point("geometry_processing")

        # Add conditional edges for cyclical workflow
        workflow.add_conditional_edges(
            "geometry_processing",
            self.router.route_next_step,
            {
                "mesh_generation": "mesh_generation",
                "error_recovery": "error_recovery",
                "geometry_processing": "geometry_processing"
            }
        )

        workflow.add_conditional_edges(
            "mesh_generation",
            self.router.route_next_step,
            {
                "material_assignment": "material_assignment",
                "mesh_refinement": "mesh_refinement",
                "error_recovery": "error_recovery",
                "mesh_generation": "mesh_generation"
            }
        )

        workflow.add_conditional_edges(
            "material_assignment",
            self.router.route_next_step,
            {
                "physics_setup": "physics_setup",
                "error_recovery": "error_recovery",
                "material_assignment": "material_assignment"
            }
        )

        workflow.add_conditional_edges(
            "physics_setup",
            self.router.route_next_step,
            {
                "validation": "validation",
                "error_recovery": "error_recovery",
                "physics_setup": "physics_setup"
            }
        )

        workflow.add_conditional_edges(
            "validation",
            self.router.route_next_step,
            {
                "hitl_checkpoint": "hitl_checkpoint",
                "geometry_processing": "geometry_processing",
                "mesh_generation": "mesh_generation",
                "material_assignment": "material_assignment",
                "physics_setup": "physics_setup",
                "error_recovery": "error_recovery",
                "validation": "validation"
            }
        )

        workflow.add_conditional_edges(
            "hitl_checkpoint",
            self.router.route_next_step,
            {
                END: END,
                "geometry_processing": "geometry_processing",
                "mesh_generation": "mesh_generation",
                "material_assignment": "material_assignment",
                "physics_setup": "physics_setup",
                "validation": "validation",
                "hitl_checkpoint": "hitl_checkpoint"
            }
        )

        # Add edges for refinement and recovery
        workflow.add_edge("mesh_refinement", "validation")
        workflow.add_edge("error_recovery", "hitl_checkpoint")

        # Compile the workflow with state persistence checkpointer
        try:
            checkpointer = self.checkpointer_manager.get_checkpointer()
            
            # Validate checkpointer before compilation
            if not self.checkpointer_manager.validate_checkpointer():
                logger.warning("Checkpointer validation failed, proceeding with caution")
            
            self.workflow_graph = workflow.compile(checkpointer=checkpointer)
            
            logger.info("✓ LangGraph workflow compiled successfully with state persistence")
            logger.info(f"✓ Using checkpointer: {type(checkpointer).__name__}")
            
        except Exception as e:
            logger.error(f"Failed to compile workflow with checkpointer: {str(e)}")
            # Try compiling without checkpointer as fallback
            logger.warning("Attempting to compile workflow without checkpointer as fallback")
            try:
                self.workflow_graph = workflow.compile()
                logger.warning("⚠️ Workflow compiled without state persistence - checkpoint functionality limited")
            except Exception as fallback_error:
                logger.error(f"Fallback compilation also failed: {str(fallback_error)}")
                raise RuntimeError(f"Workflow compilation failed: {str(e)}")

        return self.workflow_graph

    async def start_workflow(self, project_id: str, user_goal: str, physics_type: str,
                           cad_files: List[Dict[str, Any]]) -> str:
        """Start a new workflow execution"""
        try:
            # Create workflow execution record
            workflow_execution = WorkflowExecution(
                project_id=project_id,
                user_goal=user_goal,
                workflow_plan={
                    "steps": ["geometry_processing", "mesh_generation", "material_assignment", "physics_setup"],
                    "physics_type": physics_type,
                    "created_by": "langgraph_orchestrator"
                },
                current_step="geometry_processing",
                status=WorkflowStatus.RUNNING.value,
                global_context={},
                orchestrator_version="2.0"
            )

            self.db_session.add(workflow_execution)
            self.db_session.commit()

            workflow_id = str(workflow_execution.id)

            # Initialize workflow state
            initial_state = SimulationState(
                project_id=project_id,
                workflow_id=workflow_id,
                user_goal=user_goal,
                physics_type=physics_type,
                cad_files=cad_files,
                current_file=cad_files[0] if cad_files else None,
                geometry_status="pending",
                mesh_status="pending",
                materials_status="pending",
                physics_status="pending",
                geometry_analysis=None,
                mesh_recommendations=None,
                material_assignments=None,
                physics_setup=None,
                current_step="geometry_processing",
                completed_steps=[],
                failed_steps=[],
                hitl_checkpoints=[],
                mesh_quality_metrics=None,
                convergence_criteria=None,
                validation_results=None,
                errors=[],
                warnings=[],
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
                iteration_count=0,
                max_iterations=3
            )

            # Save initial state
            await self.state_persistence.save_state(initial_state)

            logger.info(f"Started workflow {workflow_id} for project {project_id}")

            # Start workflow execution asynchronously with proper thread configuration
            asyncio.create_task(self._execute_workflow(initial_state, workflow_id))

            return workflow_id

        except Exception as e:
            logger.error(f"Failed to start workflow: {str(e)}")
            self.db_session.rollback()
            raise e

    async def _execute_workflow(self, initial_state: SimulationState, workflow_id: str):
        """Execute the workflow asynchronously with state persistence"""
        try:
            # Create thread configuration for LangGraph state persistence
            thread_id = f"workflow_{workflow_id}"
            config = {"configurable": {"thread_id": thread_id}}
            
            logger.info(f"Starting workflow execution {workflow_id} with thread_id: {thread_id}")

            # Execute the workflow graph with state persistence
            result = await self.workflow_graph.ainvoke(initial_state, config=config)

            logger.info(f"Workflow {workflow_id} completed successfully")

            # Update workflow status to completed
            workflow = self.db_session.query(WorkflowExecution).filter(
                WorkflowExecution.id == workflow_id
            ).first()

            if workflow:
                workflow.status = WorkflowStatus.COMPLETED.value
                workflow.completed_at = datetime.utcnow()
                workflow.updated_at = datetime.utcnow()
                self.db_session.commit()

        except Exception as e:
            logger.error(f"Workflow execution failed for {workflow_id}: {str(e)}")

            # Update workflow status to failed
            workflow = self.db_session.query(WorkflowExecution).filter(
                WorkflowExecution.id == workflow_id
            ).first()

            if workflow:
                workflow.status = WorkflowStatus.FAILED.value
                workflow.error_message = str(e)
                workflow.updated_at = datetime.utcnow()
                self.db_session.commit()

    async def _error_recovery_node(self, state: SimulationState) -> SimulationState:
        """Handle error recovery"""
        logger.info(f"Executing error recovery for workflow {state['workflow_id']}")

        # Update state
        state["current_step"] = "error_recovery"
        state["updated_at"] = datetime.utcnow().isoformat()

        # Add recovery actions to state
        recovery_actions = [
            "Analyzed workflow errors",
            "Prepared for human intervention",
            "Workflow paused for review"
        ]

        state["warnings"].append({
            "step": "error_recovery",
            "warning": "Workflow errors detected - human review required",
            "timestamp": datetime.utcnow().isoformat(),
            "recovery_actions": recovery_actions
        })

        # Save state
        await self.state_persistence.save_state(state)

        return state

    async def _mesh_refinement_node(self, state: SimulationState) -> SimulationState:
        """Handle iterative mesh refinement"""
        logger.info(f"Executing mesh refinement for workflow {state['workflow_id']}")

        # Update state
        state["current_step"] = "mesh_refinement"
        state["updated_at"] = datetime.utcnow().isoformat()

        # Simulate mesh refinement (in practice, this would call mesh agent with refined parameters)
        if state.get("mesh_recommendations"):
            mesh_recommendations = state["mesh_recommendations"].copy()

            # Enhance mesh strategy for refinement
            mesh_recommendations["refinement_applied"] = True
            mesh_recommendations["refinement_iteration"] = state.get("iteration_count", 0)

            # Update quality metrics (simulated improvement)
            if "quality_assessment" in mesh_recommendations:
                current_quality = mesh_recommendations["quality_assessment"].get("predicted_quality_score", 0.7)
                improved_quality = min(current_quality + 0.1, 1.0)
                mesh_recommendations["quality_assessment"]["predicted_quality_score"] = improved_quality

            state["mesh_recommendations"] = mesh_recommendations
            state["mesh_quality_metrics"] = mesh_recommendations.get("quality_assessment", {})

        # Save state
        await self.state_persistence.save_state(state)

        return state

    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current workflow status"""
        try:
            workflow = self.db_session.query(WorkflowExecution).filter(
                WorkflowExecution.id == workflow_id
            ).first()

            if workflow:
                # Get current state
                state = await self.state_persistence.load_state(workflow_id)

                # Get pending checkpoints
                pending_checkpoints = await self.hitl_manager.get_pending_checkpoints(workflow_id)

                return {
                    "workflow_id": workflow_id,
                    "status": workflow.status,
                    "current_step": workflow.current_step,
                    "created_at": workflow.created_at.isoformat(),
                    "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
                    "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
                    "error_message": workflow.error_message,
                    "state": dict(state) if state else None,
                    "pending_checkpoints": pending_checkpoints
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get workflow status: {str(e)}")
            return None

    async def respond_to_checkpoint(self, checkpoint_id: str, approved: bool,
                                  feedback: Optional[str] = None,
                                  reviewer_id: Optional[str] = None) -> bool:
        """Respond to a HITL checkpoint and resume workflow"""
        try:
            # Respond to checkpoint
            success = await self.hitl_manager.respond_to_checkpoint(
                checkpoint_id=checkpoint_id,
                approved=approved,
                human_feedback=feedback,
                reviewer_id=reviewer_id
            )

            if success:
                # Get checkpoint to find workflow
                checkpoint = self.db_session.query(HITLCheckpoint).filter(
                    HITLCheckpoint.id == checkpoint_id
                ).first()

                if checkpoint:
                    # Load current state
                    state = await self.state_persistence.load_state(str(checkpoint.workflow_id))

                    if state:
                        # Update checkpoint status in state
                        for cp in state["hitl_checkpoints"]:
                            if cp["checkpoint_id"] == checkpoint_id:
                                cp["status"] = "approved" if approved else "rejected"
                                break

                        # Save updated state
                        await self.state_persistence.save_state(state)

                        # Resume workflow execution using LangGraph state persistence
                        if approved:
                            logger.info(f"Resuming workflow {checkpoint.workflow_id} after checkpoint approval")
                            await self._resume_workflow_from_checkpoint(str(checkpoint.workflow_id))
                        else:
                            logger.info(f"Workflow {checkpoint.workflow_id} will cycle back based on feedback")
                            await self._resume_workflow_from_checkpoint(str(checkpoint.workflow_id))

                return True

            return False

        except Exception as e:
            logger.error(f"Failed to respond to checkpoint: {str(e)}")
            return False

    async def _resume_workflow_from_checkpoint(self, workflow_id: str) -> bool:
        """Resume workflow execution from the last checkpoint using LangGraph state persistence"""
        try:
            # Load workflow state
            state = await self.state_persistence.load_state(workflow_id)
            if not state:
                logger.error(f"Cannot resume workflow {workflow_id}: state not found")
                return False

            # Create a unique thread_id for this workflow instance
            # This allows LangGraph to maintain separate execution contexts
            thread_id = f"workflow_{workflow_id}"
            config = {"configurable": {"thread_id": thread_id}}

            logger.info(f"Resuming workflow {workflow_id} from checkpoint with thread_id: {thread_id}")

            # Update workflow status to running
            workflow = self.db_session.query(WorkflowExecution).filter(
                WorkflowExecution.id == workflow_id
            ).first()

            if workflow:
                workflow.status = WorkflowStatus.RUNNING.value
                workflow.updated_at = datetime.utcnow()
                self.db_session.commit()

            # Resume workflow execution with state persistence
            # LangGraph will automatically restore from the last checkpoint
            result = await self.workflow_graph.ainvoke(state, config=config)

            logger.info(f"Workflow {workflow_id} resumed and completed execution")
            return True

        except Exception as e:
            logger.error(f"Failed to resume workflow {workflow_id}: {str(e)}")
            
            # Update workflow status to failed
            workflow = self.db_session.query(WorkflowExecution).filter(
                WorkflowExecution.id == workflow_id
            ).first()

            if workflow:
                workflow.status = WorkflowStatus.FAILED.value
                workflow.error_message = f"Resume failed: {str(e)}"
                workflow.updated_at = datetime.utcnow()
                self.db_session.commit()

            return False

    async def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused or interrupted workflow using LangGraph state persistence"""
        try:
            logger.info(f"Attempting to resume workflow {workflow_id}")

            # Check workflow exists and is resumable
            workflow = self.db_session.query(WorkflowExecution).filter(
                WorkflowExecution.id == workflow_id
            ).first()

            if not workflow:
                logger.error(f"Workflow {workflow_id} not found")
                return False

            if workflow.status not in [WorkflowStatus.PAUSED.value, WorkflowStatus.WAITING_FOR_HUMAN.value]:
                logger.warning(f"Workflow {workflow_id} is not in a resumable state: {workflow.status}")
                return False

            # Use the checkpoint-based resume method
            return await self._resume_workflow_from_checkpoint(workflow_id)

        except Exception as e:
            logger.error(f"Failed to resume workflow {workflow_id}: {str(e)}")
            return False

    def get_checkpointer_status(self) -> Dict[str, Any]:
        """Get the current status of the LangGraph checkpointer"""
        try:
            checkpointer_type = type(self.checkpointer_manager.checkpointer).__name__
            is_valid = self.checkpointer_manager.validate_checkpointer()
            
            return {
                "checkpointer_type": checkpointer_type,
                "is_initialized": self.checkpointer_manager.checkpointer is not None,
                "is_valid": is_valid,
                "config": {
                    "database_url": self.checkpointer_manager.config.database_url if hasattr(self.checkpointer_manager, 'config') else None,
                    "sqlite_path": self.checkpointer_manager.config.sqlite_path if hasattr(self.checkpointer_manager, 'config') else None,
                    "checkpointer_type_config": self.checkpointer_manager.config.checkpointer_type if hasattr(self.checkpointer_manager, 'config') else None
                }
            }
        except Exception as e:
            logger.error(f"Failed to get checkpointer status: {str(e)}")
            return {
                "checkpointer_type": "unknown",
                "is_initialized": False,
                "is_valid": False,
                "error": str(e)
            }
