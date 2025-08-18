# WebSocket Protocol Specification

## Overview

This document defines the standardized WebSocket protocol for real-time communication between the Ensumu Space frontend and backend. This protocol ensures reliable message exchange, proper error handling, and AG-UI compatibility.

## Connection Establishment

### URL Pattern
All WebSocket connections must use the standardized URL pattern:
```
/ws?user_id=<USER_ID>&project_id=<PROJECT_ID>&workflow_id=<WORKFLOW_ID>
```

#### Parameters
- `user_id` (required): Unique identifier for the user
- `project_id` (required): Unique identifier for the project
- `workflow_id` (optional): Unique identifier for the workflow

#### Example URLs
```
ws://localhost:8000/ws?user_id=user123&project_id=proj456
ws://localhost:8000/ws?user_id=user123&project_id=proj456&workflow_id=wf789
```

## Message Format

### Standard Message Structure
All messages must follow this JSON structure:

```typescript
interface WebSocketMessage {
  type: string;           // Message type (see MessageType enum)
  data: object;          // Message payload
  timestamp: string;     // ISO 8601 timestamp
  message_id: string;    // Unique message identifier (UUID format)
}
```

### Example Message
```json
{
  "type": "workflow_status_update",
  "data": {
    "workflow_id": "wf789",
    "status": "running",
    "current_step": "mesh_generation",
    "progress": 0.45
  },
  "timestamp": "2025-08-18T02:06:24.806Z",
  "message_id": "msg_1692324384806_abc123"
}
```

## Message Types

### System Messages
- `connection_established`: Server confirms connection
- `heartbeat`: Keep-alive ping/pong
- `error`: Error notifications

### AG-UI Protocol Messages
- `agent_state_update`: Agent state changes
- `agent_action_request`: Request for agent action
- `agent_action_response`: Response to agent action

### Workflow Messages
- `workflow_status_update`: Workflow status changes
- `workflow_step_complete`: Workflow step completion
- `workflow_error`: Workflow error notifications

### HITL Messages
- `hitl_checkpoint_created`: New HITL checkpoint
- `hitl_response_required`: HITL response needed
- `hitl_response_submitted`: HITL response submitted

### User Interaction Messages
- `user_message`: User chat/communication
- `prediction_request`: Real-time prediction request
- `prediction_response`: Real-time prediction result
- `state_change`: Application state change

## Validation Rules

### Message Validation
1. **Required Fields**: `type` and `data` are mandatory
2. **Type Validation**: `type` must match enum values
3. **Data Structure**: `data` must be a valid object
4. **Timestamp Format**: Must be ISO 8601 format if provided
5. **Message ID**: Must be unique string if provided

### Connection Validation
1. **Required Parameters**: `user_id` and `project_id` must be provided
2. **Parameter Format**: Must be non-empty strings
3. **Optional Parameters**: `workflow_id` is optional but must be valid if provided

## Error Handling

### Validation Errors
When message validation fails, the server responds with:
```json
{
  "type": "error",
  "data": {
    "error": "Message validation failed",
    "details": "Missing required field: type",
    "received_data": "truncated original message"
  },
  "timestamp": "2025-08-18T02:06:24.806Z",
  "message_id": "error_msg_123"
}
```

### Handler Errors
When message processing fails, the server responds with:
```json
{
  "type": "error",
  "data": {
    "error": "Handler execution failed",
    "message_type": "workflow_status_update",
    "details": "Database connection failed"
  },
  "timestamp": "2025-08-18T02:06:24.806Z",
  "message_id": "error_msg_456"
}
```

### Connection Errors
Invalid connection parameters result in immediate connection closure:
- Code 1008: Invalid parameters
- Reason: "Invalid parameters: user_id parameter is required"

## Heartbeat Mechanism

### Server Heartbeat
- Interval: 30 seconds
- Timeout: 60 seconds
- Automatic disconnection if no heartbeat received

### Client Heartbeat
Clients should send heartbeat messages:
```json
{
  "type": "heartbeat",
  "data": {
    "client_time": "2025-08-18T02:06:24.806Z"
  },
  "timestamp": "2025-08-18T02:06:24.806Z",
  "message_id": "heartbeat_123"
}
```

### Server Heartbeat Response
```json
{
  "type": "heartbeat",
  "data": {
    "server_time": "2025-08-18T02:06:24.806Z"
  },
  "timestamp": "2025-08-18T02:06:24.806Z",
  "message_id": "heartbeat_response_123"
}
```

## AG-UI Protocol Compatibility

### Message Mapping
The protocol maintains compatibility with AG-UI by mapping:
- `agent_state_update` → AG-UI state updates
- `agent_action_request` → AG-UI action requests
- `hitl_checkpoint_created` → AG-UI checkpoint notifications

### CopilotKit Integration
- Messages are processed through CopilotKit actions
- State updates are made available to Copilot context
- Error handling integrates with CopilotKit error system

## Security Considerations

### Message Validation
- All incoming messages are validated before processing
- Malformed messages are rejected with error responses
- Message size limits prevent DoS attacks

### Connection Security
- Parameter validation prevents injection attacks
- Connection rate limiting prevents abuse
- Proper error messages without sensitive information leakage

## Performance Characteristics

### Message Throughput
- Target: 1000+ messages/second per connection
- Latency: <10ms for message processing
- Memory: O(1) per message (no accumulation)

### Connection Limits
- Max connections per user: 10
- Max connections per project: 100
- Connection timeout: 5 minutes idle

## Monitoring and Logging

### Metrics Tracked
- Total connections established
- Active connections count
- Messages sent/received per second
- Validation errors per minute
- Handler errors per minute

### Log Levels
- DEBUG: Message details and flow
- INFO: Connection events and status
- WARN: Validation failures and timeouts
- ERROR: Handler failures and system errors

## Migration Guide

### From Legacy Protocol
1. Update URL construction to use standard pattern
2. Replace message types with enum values
3. Add message validation to client code
4. Update error handling for new error format
5. Test bidirectional communication

### Breaking Changes
- URL parameters now required for all connections
- Message structure now strictly validated
- Old message types no longer supported
- Error response format changed

## Testing Protocol

### Unit Tests
- Message validation functions
- URL construction utilities
- Error handling scenarios
- Heartbeat mechanism

### Integration Tests
- End-to-end message flow
- Connection parameter validation
- Error propagation
- Performance under load

### Compatibility Tests
- AG-UI protocol compliance
- CopilotKit integration
- Legacy client migration
- Multi-browser support