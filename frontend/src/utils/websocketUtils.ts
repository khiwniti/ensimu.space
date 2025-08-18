/**
 * WebSocket utilities for standardized protocol implementation
 * Provides consistent URL construction and message formatting
 */

// Standardized message types matching backend enum
export enum MessageType {
  // System messages
  CONNECTION_ESTABLISHED = "connection_established",
  HEARTBEAT = "heartbeat",
  ERROR = "error",
  
  // AG-UI Protocol messages
  AGENT_STATE_UPDATE = "agent_state_update",
  AGENT_ACTION_REQUEST = "agent_action_request",
  AGENT_ACTION_RESPONSE = "agent_action_response",
  
  // Workflow messages
  WORKFLOW_STATUS_UPDATE = "workflow_status_update",
  WORKFLOW_STEP_COMPLETE = "workflow_step_complete",
  WORKFLOW_ERROR = "workflow_error",
  
  // HITL messages
  HITL_CHECKPOINT_CREATED = "hitl_checkpoint_created",
  HITL_RESPONSE_REQUIRED = "hitl_response_required",
  HITL_RESPONSE_SUBMITTED = "hitl_response_submitted",
  
  // User interaction messages
  USER_MESSAGE = "user_message",
  PREDICTION_REQUEST = "prediction_request",
  PREDICTION_RESPONSE = "prediction_response",
  STATE_CHANGE = "state_change",
}

// Standardized message interface
export interface StandardWebSocketMessage {
  type: MessageType | string;
  data: Record<string, any>;
  timestamp?: string;
  message_id?: string;
}

// Connection parameters interface
export interface WebSocketConnectionParams {
  user_id: string;
  project_id: string;
  workflow_id?: string;
}

/**
 * Build standardized WebSocket URL
 * Pattern: /ws?user_id=X&project_id=Y&workflow_id=Z
 */
export function buildWebSocketUrl(
  baseUrl: string = 'ws://localhost:8000',
  params: WebSocketConnectionParams
): string {
  const wsUrl = new URL('/ws', baseUrl);
  
  // Add required parameters
  wsUrl.searchParams.set('user_id', params.user_id);
  wsUrl.searchParams.set('project_id', params.project_id);
  
  // Add optional parameters
  if (params.workflow_id) {
    wsUrl.searchParams.set('workflow_id', params.workflow_id);
  }
  
  return wsUrl.toString();
}

/**
 * Create standardized WebSocket message
 */
export function createStandardMessage(
  type: MessageType,
  data: Record<string, any>,
  messageId?: string
): StandardWebSocketMessage {
  return {
    type,
    data,
    timestamp: new Date().toISOString(),
    message_id: messageId || `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
  };
}

/**
 * Validate message structure
 */
export function validateMessage(message: any): message is StandardWebSocketMessage {
  if (typeof message !== 'object' || message === null) {
    return false;
  }
  
  // Check required fields
  if (!message.type || typeof message.type !== 'string') {
    return false;
  }
  
  if (!message.data || typeof message.data !== 'object') {
    return false;
  }
  
  return true;
}

/**
 * Parse WebSocket message safely
 */
export function parseWebSocketMessage(data: string): StandardWebSocketMessage | null {
  try {
    const parsed = JSON.parse(data);
    
    if (!validateMessage(parsed)) {
      console.error('Invalid message structure:', parsed);
      return null;
    }
    
    return parsed;
  } catch (error) {
    console.error('Failed to parse WebSocket message:', error);
    return null;
  }
}

/**
 * Create heartbeat message
 */
export function createHeartbeatMessage(): StandardWebSocketMessage {
  return createStandardMessage(MessageType.HEARTBEAT, {
    client_time: new Date().toISOString(),
  });
}

/**
 * Create HITL response message
 */
export function createHITLResponseMessage(
  checkpointId: string,
  approved: boolean,
  feedback?: string
): StandardWebSocketMessage {
  return createStandardMessage(MessageType.HITL_RESPONSE_SUBMITTED, {
    checkpoint_id: checkpointId,
    response_data: { approved, feedback },
  });
}

/**
 * Create user message
 */
export function createUserMessage(content: string): StandardWebSocketMessage {
  return createStandardMessage(MessageType.USER_MESSAGE, {
    content,
  });
}

/**
 * Create prediction request message
 */
export function createPredictionRequestMessage(
  modelKey: string,
  point: [number, number, number]
): StandardWebSocketMessage {
  return createStandardMessage(MessageType.PREDICTION_REQUEST, {
    model_key: modelKey,
    point,
  });
}

/**
 * Create state change message
 */
export function createStateChangeMessage(
  workflowId: string,
  statePatch: Record<string, any>
): StandardWebSocketMessage {
  return createStandardMessage(MessageType.STATE_CHANGE, {
    workflow_id: workflowId,
    state_patch: statePatch,
  });
}

/**
 * Get WebSocket base URL from environment
 */
export function getWebSocketBaseUrl(): string {
  // Try different environment variable names
  const wsUrl = process.env.REACT_APP_WS_URL || 
                process.env.REACT_APP_WEBSOCKET_URL || 
                'ws://localhost:8000';
  
  // Ensure it starts with ws:// or wss://
  if (!wsUrl.startsWith('ws://') && !wsUrl.startsWith('wss://')) {
    // Convert http to ws protocol
    const url = new URL(wsUrl.startsWith('http') ? wsUrl : `http://${wsUrl}`);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return url.toString().slice(0, -1); // Remove trailing slash
  }
  
  return wsUrl;
}

/**
 * Error codes for WebSocket connection issues
 */
export enum WebSocketErrorCode {
  INVALID_PARAMETERS = 1008,
  MESSAGE_VALIDATION_FAILED = 1007,
  HANDLER_ERROR = 1011,
  INTERNAL_ERROR = 1012,
}

/**
 * Check if error is a validation error
 */
export function isValidationError(message: StandardWebSocketMessage): boolean {
  return message.type === MessageType.ERROR && 
         message.data.error === 'Message validation failed';
}

/**
 * Check if error is a handler error
 */
export function isHandlerError(message: StandardWebSocketMessage): boolean {
  return message.type === MessageType.ERROR && 
         message.data.error === 'Handler execution failed';
}

/**
 * Extract error details from error message
 */
export function extractErrorDetails(message: StandardWebSocketMessage): {
  error: string;
  details?: string;
  messageType?: string;
} {
  if (message.type !== MessageType.ERROR) {
    throw new Error('Message is not an error message');
  }
  
  return {
    error: message.data.error || 'Unknown error',
    details: message.data.details,
    messageType: message.data.message_type,
  };
}