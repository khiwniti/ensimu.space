# WebSocket Protocol Standardization - Critical Issue #2

## Current Issues Identified

### Message Type Mismatches
1. **Backend** uses enum values: `agent_action_request`, `workflow_status_update`, etc.
2. **Frontend** sends mixed types: `hitl_response_submitted`, `user_message`, `ping`, etc.
3. **Inconsistent heartbeat**: Backend expects `heartbeat`, frontend sends `heartbeat` but also `ping`

### URL Construction Inconsistencies
1. **useWorkflow.ts**: `ws://localhost:8000/ws` + params
2. **useWebSocketConnection.ts**: `/ws/${projectId}?user_id=${userId}`
3. **CopilotIntegration.tsx**: `ws://localhost:8000/ws?project_id=${project.id}`

### Message Structure Variations
- Backend expects: `{type, data, timestamp, message_id}`
- Frontend sends various structures with different field names

## Standardized Protocol Design

### 1. Unified Message Types (Backend Enum)
```python
class MessageType(Enum):
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
```

### 2. Standardized URL Pattern
**All components will use:** `/ws?user_id=X&project_id=Y&workflow_id=Z`

### 3. Unified Message Structure
```typescript
interface WebSocketMessage {
  type: string;           // Must match backend enum values
  data: any;             // All payload data goes here
  timestamp: string;     // ISO 8601 format
  message_id: string;    // UUID format
}
```

### 4. Connection Parameters
- `user_id`: Required for user identification
- `project_id`: Required for project-specific updates
- `workflow_id`: Optional, for workflow-specific updates

## Implementation Plan

1. **Backend**: Add missing message types to enum, enhance validation
2. **Frontend**: Standardize all WebSocket hooks to use unified protocol
3. **URL Construction**: Implement single URL builder function
4. **Message Validation**: Add schema validation on both sides
5. **Error Handling**: Standardize error responses and connection handling

## Expected Benefits

1. **Reliability**: Consistent message format reduces parsing errors
2. **Maintainability**: Single source of truth for message types
3. **Debugging**: Standardized logging and error tracking
4. **Scalability**: Easy to add new message types following standard pattern