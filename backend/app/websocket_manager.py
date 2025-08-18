"""
WebSocket manager for real-time communication with frontend.
Implements AG-UI protocol for CopilotKit integration and workflow updates.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from fastapi import WebSocket, WebSocketDisconnect
    from fastapi.websockets import WebSocketState
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Mock classes
    class WebSocket:
        def __init__(self): pass
        async def accept(self): pass
        async def send_text(self, data): pass
        async def receive_text(self): return ""
        async def close(self): pass
    class WebSocketDisconnect(Exception): pass

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for message validation errors"""
    pass

def validate_message_structure(message_data: dict) -> bool:
    """Validate WebSocket message structure"""
    required_fields = ["type", "data"]
    optional_fields = ["timestamp", "message_id"]
    
    # Check required fields
    for field in required_fields:
        if field not in message_data:
            raise ValidationError(f"Missing required field: {field}")
    
    # Validate message type
    try:
        MessageType(message_data["type"])
    except ValueError:
        raise ValidationError(f"Invalid message type: {message_data['type']}")
    
    # Validate data field is a dict
    if not isinstance(message_data["data"], dict):
        raise ValidationError("Message data must be a dictionary")
    
    return True

def validate_connection_params(params: dict) -> dict:
    """Validate and normalize connection parameters"""
    validated_params = {}
    
    # user_id is required
    if "user_id" not in params:
        raise ValidationError("user_id parameter is required")
    validated_params["user_id"] = params["user_id"]
    
    # project_id is required
    if "project_id" not in params:
        raise ValidationError("project_id parameter is required")
    validated_params["project_id"] = params["project_id"]
    
    # workflow_id is optional
    if "workflow_id" in params:
        validated_params["workflow_id"] = params["workflow_id"]
    
    return validated_params

class MessageType(Enum):
    """WebSocket message types"""
    # System messages
    CONNECTION_ESTABLISHED = "connection_established"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    
    # AG-UI Protocol messages
    AGENT_STATE_UPDATE = "agent_state_update"
    AGENT_ACTION_REQUEST = "agent_action_request"
    AGENT_ACTION_RESPONSE = "agent_action_response"
    
    # Workflow messages
    WORKFLOW_STATUS_UPDATE = "workflow_status_update"
    WORKFLOW_STEP_COMPLETE = "workflow_step_complete"
    WORKFLOW_ERROR = "workflow_error"
    
    # HITL messages
    HITL_CHECKPOINT_CREATED = "hitl_checkpoint_created"
    HITL_RESPONSE_REQUIRED = "hitl_response_required"
    HITL_RESPONSE_SUBMITTED = "hitl_response_submitted"
    
    # User interaction messages
    USER_MESSAGE = "user_message"
    PREDICTION_REQUEST = "prediction_request"
    PREDICTION_RESPONSE = "prediction_response"
    STATE_CHANGE = "state_change"

@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    type: MessageType
    data: Dict[str, Any]
    timestamp: datetime = None
    message_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps({
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'WebSocketMessage':
        """Create message from JSON string"""
        data = json.loads(json_str)
        return cls(
            type=MessageType(data["type"]),
            data=data["data"],
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
            message_id=data.get("message_id", str(uuid.uuid4()))
        )

@dataclass
class ConnectionInfo:
    """WebSocket connection information"""
    connection_id: str
    websocket: WebSocket
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    workflow_id: Optional[str] = None
    connected_at: datetime = None
    last_heartbeat: datetime = None
    subscriptions: Set[str] = None
    
    def __post_init__(self):
        if self.connected_at is None:
            self.connected_at = datetime.utcnow()
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.utcnow()
        if self.subscriptions is None:
            self.subscriptions = set()

class WebSocketManager:
    """Manages WebSocket connections and message routing"""
    
    def __init__(self):
        self.connections: Dict[str, ConnectionInfo] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        self.project_connections: Dict[str, Set[str]] = {}  # project_id -> connection_ids
        self.workflow_connections: Dict[str, Set[str]] = {}  # workflow_id -> connection_ids
        
        # Message handlers
        self.message_handlers: Dict[MessageType, List[callable]] = {}
        
        # Heartbeat settings
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 60   # seconds
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0
        }
    
    async def connect(self, websocket: WebSocket, connection_params: dict = None) -> str:
        """Accept new WebSocket connection with parameter validation"""
        await websocket.accept()
        
        # Validate connection parameters
        if connection_params:
            try:
                validated_params = validate_connection_params(connection_params)
                user_id = validated_params.get("user_id")
                project_id = validated_params.get("project_id")
                workflow_id = validated_params.get("workflow_id")
            except ValidationError as e:
                logger.error(f"Connection parameter validation failed: {e}")
                await websocket.close(code=1008, reason=f"Invalid parameters: {e}")
                raise
        else:
            user_id = project_id = workflow_id = None
        
        connection_id = str(uuid.uuid4())
        connection_info = ConnectionInfo(
            connection_id=connection_id,
            websocket=websocket,
            user_id=user_id,
            project_id=project_id,
            workflow_id=workflow_id
        )
        
        # Store connection
        self.connections[connection_id] = connection_info
        
        # Index by user, project, workflow
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        if project_id:
            if project_id not in self.project_connections:
                self.project_connections[project_id] = set()
            self.project_connections[project_id].add(connection_id)
        
        if workflow_id:
            if workflow_id not in self.workflow_connections:
                self.workflow_connections[workflow_id] = set()
            self.workflow_connections[workflow_id].add(connection_id)
        
        # Update statistics
        self.stats["total_connections"] += 1
        self.stats["active_connections"] += 1
        
        # Send connection established message
        await self.send_to_connection(connection_id, WebSocketMessage(
            type=MessageType.CONNECTION_ESTABLISHED,
            data={
                "connection_id": connection_id,
                "server_time": datetime.utcnow().isoformat(),
                "heartbeat_interval": self.heartbeat_interval
            }
        ))
        
        # Start heartbeat if not already running
        if not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        logger.info(f"WebSocket connection established: {connection_id}")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Disconnect WebSocket connection"""
        if connection_id not in self.connections:
            return
        
        connection_info = self.connections[connection_id]
        
        # Remove from indexes
        if connection_info.user_id and connection_info.user_id in self.user_connections:
            self.user_connections[connection_info.user_id].discard(connection_id)
            if not self.user_connections[connection_info.user_id]:
                del self.user_connections[connection_info.user_id]
        
        if connection_info.project_id and connection_info.project_id in self.project_connections:
            self.project_connections[connection_info.project_id].discard(connection_id)
            if not self.project_connections[connection_info.project_id]:
                del self.project_connections[connection_info.project_id]
        
        if connection_info.workflow_id and connection_info.workflow_id in self.workflow_connections:
            self.workflow_connections[connection_info.workflow_id].discard(connection_id)
            if not self.workflow_connections[connection_info.workflow_id]:
                del self.workflow_connections[connection_info.workflow_id]
        
        # Close WebSocket
        try:
            if connection_info.websocket.client_state == WebSocketState.CONNECTED:
                await connection_info.websocket.close()
        except Exception as e:
            logger.warning(f"Error closing WebSocket {connection_id}: {e}")
        
        # Remove connection
        del self.connections[connection_id]
        self.stats["active_connections"] -= 1
        
        logger.info(f"WebSocket connection disconnected: {connection_id}")
    
    async def send_to_connection(self, connection_id: str, message: WebSocketMessage) -> bool:
        """Send message to specific connection"""
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        
        try:
            if connection_info.websocket.client_state == WebSocketState.CONNECTED:
                await connection_info.websocket.send_text(message.to_json())
                self.stats["messages_sent"] += 1
                return True
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            self.stats["errors"] += 1
            # Disconnect on error
            await self.disconnect(connection_id)
        
        return False
    
    async def send_to_user(self, user_id: str, message: WebSocketMessage) -> int:
        """Send message to all connections for a user"""
        if user_id not in self.user_connections:
            return 0
        
        sent_count = 0
        connection_ids = list(self.user_connections[user_id])  # Copy to avoid modification during iteration
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def send_to_project(self, project_id: str, message: WebSocketMessage) -> int:
        """Send message to all connections for a project"""
        if project_id not in self.project_connections:
            return 0
        
        sent_count = 0
        connection_ids = list(self.project_connections[project_id])
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def send_to_workflow(self, workflow_id: str, message: WebSocketMessage) -> int:
        """Send message to all connections for a workflow"""
        if workflow_id not in self.workflow_connections:
            return 0
        
        sent_count = 0
        connection_ids = list(self.workflow_connections[workflow_id])
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def broadcast(self, message: WebSocketMessage) -> int:
        """Broadcast message to all connections"""
        sent_count = 0
        connection_ids = list(self.connections.keys())
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def handle_message(self, connection_id: str, message_data: str):
        """Handle incoming WebSocket message with validation"""
        try:
            # Parse JSON
            try:
                raw_data = json.loads(message_data)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON format: {e}")
            
            # Validate message structure
            validate_message_structure(raw_data)
            
            # Create validated message object
            message = WebSocketMessage.from_json(message_data)
            self.stats["messages_received"] += 1
            
            # Update last heartbeat if it's a heartbeat message
            if message.type == MessageType.HEARTBEAT:
                if connection_id in self.connections:
                    self.connections[connection_id].last_heartbeat = datetime.utcnow()
                # Send heartbeat response
                heartbeat_response = WebSocketMessage(
                    type=MessageType.HEARTBEAT,
                    data={"server_time": datetime.utcnow().isoformat()}
                )
                await self.send_to_connection(connection_id, heartbeat_response)
                return
            
            # Call registered handlers
            if message.type in self.message_handlers:
                for handler in self.message_handlers[message.type]:
                    try:
                        await handler(connection_id, message)
                    except Exception as e:
                        logger.error(f"Message handler error for {message.type.value}: {e}")
                        # Send error response to client
                        error_message = WebSocketMessage(
                            type=MessageType.ERROR,
                            data={
                                "error": "Handler execution failed",
                                "message_type": message.type.value,
                                "details": str(e)
                            }
                        )
                        await self.send_to_connection(connection_id, error_message)
            else:
                logger.warning(f"No handler registered for message type: {message.type.value}")
            
            logger.debug(f"Handled message {message.type.value} from {connection_id}")
            
        except ValidationError as e:
            logger.error(f"Message validation error from {connection_id}: {e}")
            self.stats["errors"] += 1
            
            # Send validation error response
            error_message = WebSocketMessage(
                type=MessageType.ERROR,
                data={
                    "error": "Message validation failed",
                    "details": str(e),
                    "received_data": message_data[:500]  # Truncate for safety
                }
            )
            await self.send_to_connection(connection_id, error_message)
            
        except Exception as e:
            logger.error(f"Unexpected error handling message from {connection_id}: {e}")
            self.stats["errors"] += 1
            
            # Send generic error response
            error_message = WebSocketMessage(
                type=MessageType.ERROR,
                data={"error": "Internal server error", "details": "Message processing failed"}
            )
            await self.send_to_connection(connection_id, error_message)
    
    def register_handler(self, message_type: MessageType, handler: callable):
        """Register message handler"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)
    
    async def _heartbeat_loop(self):
        """Heartbeat loop to check connection health"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                current_time = datetime.utcnow()
                disconnected_connections = []
                
                # Check for stale connections
                for connection_id, connection_info in self.connections.items():
                    time_since_heartbeat = (current_time - connection_info.last_heartbeat).total_seconds()
                    
                    if time_since_heartbeat > self.heartbeat_timeout:
                        disconnected_connections.append(connection_id)
                    else:
                        # Send heartbeat
                        heartbeat_message = WebSocketMessage(
                            type=MessageType.HEARTBEAT,
                            data={"server_time": current_time.isoformat()}
                        )
                        await self.send_to_connection(connection_id, heartbeat_message)
                
                # Disconnect stale connections
                for connection_id in disconnected_connections:
                    logger.warning(f"Disconnecting stale connection: {connection_id}")
                    await self.disconnect(connection_id)
                
                # Stop heartbeat if no connections
                if not self.connections:
                    break
                    
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
        
        self.heartbeat_task = None
    
    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection information"""
        return self.connections.get(connection_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics"""
        return {
            **self.stats,
            "connections_by_user": {user_id: len(conn_ids) for user_id, conn_ids in self.user_connections.items()},
            "connections_by_project": {project_id: len(conn_ids) for project_id, conn_ids in self.project_connections.items()},
            "connections_by_workflow": {workflow_id: len(conn_ids) for workflow_id, conn_ids in self.workflow_connections.items()}
        }

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

# AG-UI Protocol handlers
async def handle_agent_action_request(connection_id: str, message: WebSocketMessage):
    """Handle agent action request from frontend"""
    action_data = message.data
    
    # Process the action (this would integrate with your agent system)
    logger.info(f"Agent action requested: {action_data.get('action_type')} from {connection_id}")
    
    # Send response back
    response_message = WebSocketMessage(
        type=MessageType.AGENT_ACTION_RESPONSE,
        data={
            "action_id": action_data.get("action_id"),
            "status": "completed",
            "result": {"success": True}
        }
    )
    await websocket_manager.send_to_connection(connection_id, response_message)

async def handle_hitl_response(connection_id: str, message: WebSocketMessage):
    """Handle HITL checkpoint response"""
    response_data = message.data
    
    # Process HITL response (this would integrate with your workflow system)
    logger.info(f"HITL response received: {response_data.get('action')} from {connection_id}")
    
    # Notify workflow system
    confirmation_message = WebSocketMessage(
        type=MessageType.HITL_RESPONSE_SUBMITTED,
        data={
            "checkpoint_id": response_data.get("checkpoint_id"),
            "status": "submitted"
        }
    )
    await websocket_manager.send_to_connection(connection_id, confirmation_message)

# New message handlers for standardized protocol
async def handle_user_message(connection_id: str, message: WebSocketMessage):
    """Handle user message from frontend"""
    user_data = message.data
    logger.info(f"User message from {connection_id}: {user_data.get('content', '')}")
    
    # Process user message (could integrate with chat system)
    response_message = WebSocketMessage(
        type=MessageType.USER_MESSAGE,
        data={
            "status": "received",
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    await websocket_manager.send_to_connection(connection_id, response_message)

async def handle_prediction_request(connection_id: str, message: WebSocketMessage):
    """Handle prediction request from frontend"""
    request_data = message.data
    logger.info(f"Prediction request from {connection_id}: {request_data}")
    
    # Process prediction request (would integrate with PhysicsNeMo)
    response_message = WebSocketMessage(
        type=MessageType.PREDICTION_RESPONSE,
        data={
            "model_key": request_data.get("model_key"),
            "point": request_data.get("point"),
            "prediction_result": {"value": 0.0, "confidence": 0.95},  # Mock response
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    await websocket_manager.send_to_connection(connection_id, response_message)

async def handle_state_change(connection_id: str, message: WebSocketMessage):
    """Handle state change from frontend"""
    state_data = message.data
    logger.info(f"State change from {connection_id}: {state_data}")
    
    # Process state change (would update workflow state)
    confirmation_message = WebSocketMessage(
        type=MessageType.STATE_CHANGE,
        data={
            "workflow_id": state_data.get("workflow_id"),
            "status": "applied",
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    await websocket_manager.send_to_connection(connection_id, confirmation_message)

# Register all handlers
websocket_manager.register_handler(MessageType.AGENT_ACTION_REQUEST, handle_agent_action_request)
websocket_manager.register_handler(MessageType.HITL_RESPONSE_SUBMITTED, handle_hitl_response)
websocket_manager.register_handler(MessageType.USER_MESSAGE, handle_user_message)
websocket_manager.register_handler(MessageType.PREDICTION_REQUEST, handle_prediction_request)
websocket_manager.register_handler(MessageType.STATE_CHANGE, handle_state_change)

# Utility functions for workflow integration
async def notify_workflow_status_update(workflow_id: str, status: str, step: str, progress: float = None):
    """Notify clients of workflow status update"""
    message = WebSocketMessage(
        type=MessageType.WORKFLOW_STATUS_UPDATE,
        data={
            "workflow_id": workflow_id,
            "status": status,
            "current_step": step,
            "progress": progress,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    await websocket_manager.send_to_workflow(workflow_id, message)

async def notify_workflow_step_complete(workflow_id: str, step_name: str, result: Dict[str, Any]):
    """Notify clients of workflow step completion"""
    message = WebSocketMessage(
        type=MessageType.WORKFLOW_STEP_COMPLETE,
        data={
            "workflow_id": workflow_id,
            "step_name": step_name,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    await websocket_manager.send_to_workflow(workflow_id, message)

async def notify_hitl_checkpoint_created(workflow_id: str, checkpoint_id: str, checkpoint_data: Dict[str, Any]):
    """Notify clients of new HITL checkpoint"""
    message = WebSocketMessage(
        type=MessageType.HITL_CHECKPOINT_CREATED,
        data={
            "workflow_id": workflow_id,
            "checkpoint_id": checkpoint_id,
            "checkpoint_data": checkpoint_data,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    await websocket_manager.send_to_workflow(workflow_id, message)

async def notify_agent_state_update(project_id: str, agent_type: str, state: Dict[str, Any]):
    """Notify clients of agent state update"""
    message = WebSocketMessage(
        type=MessageType.AGENT_STATE_UPDATE,
        data={
            "project_id": project_id,
            "agent_type": agent_type,
            "state": state,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    await websocket_manager.send_to_project(project_id, message)
