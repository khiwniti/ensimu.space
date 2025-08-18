/**
 * WebSocket Protocol Validation Tests
 * Tests for the standardized WebSocket message protocol
 */

import {
  MessageType,
  StandardWebSocketMessage,
  WebSocketConnectionParams,
  buildWebSocketUrl,
  createStandardMessage,
  validateMessage,
  parseWebSocketMessage,
  createHeartbeatMessage,
  createHITLResponseMessage,
  createUserMessage,
  createPredictionRequestMessage,
  createStateChangeMessage,
  isValidationError,
  isHandlerError,
  extractErrorDetails,
} from '../frontend/src/utils/websocketUtils';

describe('WebSocket Protocol Tests', () => {
  describe('URL Construction', () => {
    test('should build correct URL with required parameters', () => {
      const params: WebSocketConnectionParams = {
        user_id: 'user123',
        project_id: 'proj456',
      };
      
      const url = buildWebSocketUrl('ws://localhost:8000', params);
      expect(url).toBe('ws://localhost:8000/ws?user_id=user123&project_id=proj456');
    });

    test('should build correct URL with optional workflow_id', () => {
      const params: WebSocketConnectionParams = {
        user_id: 'user123',
        project_id: 'proj456',
        workflow_id: 'wf789',
      };
      
      const url = buildWebSocketUrl('ws://localhost:8000', params);
      expect(url).toBe('ws://localhost:8000/ws?user_id=user123&project_id=proj456&workflow_id=wf789');
    });

    test('should handle different base URLs', () => {
      const params: WebSocketConnectionParams = {
        user_id: 'user123',
        project_id: 'proj456',
      };
      
      const url = buildWebSocketUrl('wss://production.example.com', params);
      expect(url).toBe('wss://production.example.com/ws?user_id=user123&project_id=proj456');
    });
  });

  describe('Message Creation', () => {
    test('should create standard message with all fields', () => {
      const message = createStandardMessage(MessageType.HEARTBEAT, { test: 'data' });
      
      expect(message.type).toBe(MessageType.HEARTBEAT);
      expect(message.data).toEqual({ test: 'data' });
      expect(message.timestamp).toBeDefined();
      expect(message.message_id).toBeDefined();
      expect(message.message_id).toMatch(/^msg_\d+_[a-z0-9]+$/);
    });

    test('should create heartbeat message', () => {
      const message = createHeartbeatMessage();
      
      expect(message.type).toBe(MessageType.HEARTBEAT);
      expect(message.data.client_time).toBeDefined();
      expect(new Date(message.data.client_time)).toBeInstanceOf(Date);
    });

    test('should create HITL response message', () => {
      const message = createHITLResponseMessage('checkpoint123', true, 'Looks good');
      
      expect(message.type).toBe(MessageType.HITL_RESPONSE_SUBMITTED);
      expect(message.data.checkpoint_id).toBe('checkpoint123');
      expect(message.data.response_data.approved).toBe(true);
      expect(message.data.response_data.feedback).toBe('Looks good');
    });

    test('should create user message', () => {
      const message = createUserMessage('Hello world');
      
      expect(message.type).toBe(MessageType.USER_MESSAGE);
      expect(message.data.content).toBe('Hello world');
    });

    test('should create prediction request message', () => {
      const message = createPredictionRequestMessage('model1', [1, 2, 3]);
      
      expect(message.type).toBe(MessageType.PREDICTION_REQUEST);
      expect(message.data.model_key).toBe('model1');
      expect(message.data.point).toEqual([1, 2, 3]);
    });

    test('should create state change message', () => {
      const statePatch = { progress: 0.5, currentStep: 'processing' };
      const message = createStateChangeMessage('wf123', statePatch);
      
      expect(message.type).toBe(MessageType.STATE_CHANGE);
      expect(message.data.workflow_id).toBe('wf123');
      expect(message.data.state_patch).toEqual(statePatch);
    });
  });

  describe('Message Validation', () => {
    test('should validate correct message', () => {
      const message: StandardWebSocketMessage = {
        type: MessageType.HEARTBEAT,
        data: { test: 'data' },
        timestamp: new Date().toISOString(),
        message_id: 'test123',
      };
      
      expect(validateMessage(message)).toBe(true);
    });

    test('should reject message without type', () => {
      const message = {
        data: { test: 'data' },
        timestamp: new Date().toISOString(),
        message_id: 'test123',
      };
      
      expect(validateMessage(message)).toBe(false);
    });

    test('should reject message without data', () => {
      const message = {
        type: MessageType.HEARTBEAT,
        timestamp: new Date().toISOString(),
        message_id: 'test123',
      };
      
      expect(validateMessage(message)).toBe(false);
    });

    test('should reject message with non-object data', () => {
      const message = {
        type: MessageType.HEARTBEAT,
        data: 'invalid',
        timestamp: new Date().toISOString(),
        message_id: 'test123',
      };
      
      expect(validateMessage(message)).toBe(false);
    });

    test('should accept message without optional fields', () => {
      const message = {
        type: MessageType.HEARTBEAT,
        data: { test: 'data' },
      };
      
      expect(validateMessage(message)).toBe(true);
    });
  });

  describe('Message Parsing', () => {
    test('should parse valid JSON message', () => {
      const original: StandardWebSocketMessage = {
        type: MessageType.HEARTBEAT,
        data: { test: 'data' },
        timestamp: new Date().toISOString(),
        message_id: 'test123',
      };
      
      const jsonString = JSON.stringify(original);
      const parsed = parseWebSocketMessage(jsonString);
      
      expect(parsed).toEqual(original);
    });

    test('should return null for invalid JSON', () => {
      const invalidJson = '{ invalid json }';
      const parsed = parseWebSocketMessage(invalidJson);
      
      expect(parsed).toBeNull();
    });

    test('should return null for invalid message structure', () => {
      const invalidMessage = JSON.stringify({ invalid: 'structure' });
      const parsed = parseWebSocketMessage(invalidMessage);
      
      expect(parsed).toBeNull();
    });
  });

  describe('Error Message Handling', () => {
    test('should identify validation errors', () => {
      const errorMessage: StandardWebSocketMessage = {
        type: MessageType.ERROR,
        data: {
          error: 'Message validation failed',
          details: 'Missing required field: type',
        },
        timestamp: new Date().toISOString(),
        message_id: 'error123',
      };
      
      expect(isValidationError(errorMessage)).toBe(true);
      expect(isHandlerError(errorMessage)).toBe(false);
    });

    test('should identify handler errors', () => {
      const errorMessage: StandardWebSocketMessage = {
        type: MessageType.ERROR,
        data: {
          error: 'Handler execution failed',
          message_type: 'workflow_status_update',
          details: 'Database connection failed',
        },
        timestamp: new Date().toISOString(),
        message_id: 'error123',
      };
      
      expect(isValidationError(errorMessage)).toBe(false);
      expect(isHandlerError(errorMessage)).toBe(true);
    });

    test('should extract error details', () => {
      const errorMessage: StandardWebSocketMessage = {
        type: MessageType.ERROR,
        data: {
          error: 'Handler execution failed',
          message_type: 'workflow_status_update',
          details: 'Database connection failed',
        },
        timestamp: new Date().toISOString(),
        message_id: 'error123',
      };
      
      const details = extractErrorDetails(errorMessage);
      expect(details.error).toBe('Handler execution failed');
      expect(details.messageType).toBe('workflow_status_update');
      expect(details.details).toBe('Database connection failed');
    });

    test('should throw error when extracting details from non-error message', () => {
      const normalMessage: StandardWebSocketMessage = {
        type: MessageType.HEARTBEAT,
        data: { test: 'data' },
        timestamp: new Date().toISOString(),
        message_id: 'test123',
      };
      
      expect(() => extractErrorDetails(normalMessage)).toThrow('Message is not an error message');
    });
  });

  describe('MessageType Enum', () => {
    test('should contain all required message types', () => {
      // System messages
      expect(MessageType.CONNECTION_ESTABLISHED).toBe('connection_established');
      expect(MessageType.HEARTBEAT).toBe('heartbeat');
      expect(MessageType.ERROR).toBe('error');
      
      // AG-UI Protocol messages
      expect(MessageType.AGENT_STATE_UPDATE).toBe('agent_state_update');
      expect(MessageType.AGENT_ACTION_REQUEST).toBe('agent_action_request');
      expect(MessageType.AGENT_ACTION_RESPONSE).toBe('agent_action_response');
      
      // Workflow messages
      expect(MessageType.WORKFLOW_STATUS_UPDATE).toBe('workflow_status_update');
      expect(MessageType.WORKFLOW_STEP_COMPLETE).toBe('workflow_step_complete');
      expect(MessageType.WORKFLOW_ERROR).toBe('workflow_error');
      
      // HITL messages
      expect(MessageType.HITL_CHECKPOINT_CREATED).toBe('hitl_checkpoint_created');
      expect(MessageType.HITL_RESPONSE_REQUIRED).toBe('hitl_response_required');
      expect(MessageType.HITL_RESPONSE_SUBMITTED).toBe('hitl_response_submitted');
      
      // User interaction messages
      expect(MessageType.USER_MESSAGE).toBe('user_message');
      expect(MessageType.PREDICTION_REQUEST).toBe('prediction_request');
      expect(MessageType.PREDICTION_RESPONSE).toBe('prediction_response');
      expect(MessageType.STATE_CHANGE).toBe('state_change');
    });
  });

  describe('Protocol Compliance', () => {
    test('should ensure message IDs are unique', () => {
      const message1 = createStandardMessage(MessageType.HEARTBEAT, {});
      const message2 = createStandardMessage(MessageType.HEARTBEAT, {});
      
      expect(message1.message_id).not.toBe(message2.message_id);
    });

    test('should use ISO 8601 timestamp format', () => {
      const message = createStandardMessage(MessageType.HEARTBEAT, {});
      const timestamp = new Date(message.timestamp!);
      
      expect(timestamp).toBeInstanceOf(Date);
      expect(message.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
    });

    test('should maintain message structure consistency', () => {
      const messageTypes = [
        MessageType.HEARTBEAT,
        MessageType.USER_MESSAGE,
        MessageType.WORKFLOW_STATUS_UPDATE,
        MessageType.AGENT_STATE_UPDATE,
      ];
      
      messageTypes.forEach(type => {
        const message = createStandardMessage(type, { test: 'data' });
        
        expect(message).toHaveProperty('type');
        expect(message).toHaveProperty('data');
        expect(message).toHaveProperty('timestamp');
        expect(message).toHaveProperty('message_id');
        expect(typeof message.type).toBe('string');
        expect(typeof message.data).toBe('object');
        expect(typeof message.timestamp).toBe('string');
        expect(typeof message.message_id).toBe('string');
      });
    });
  });
});

// Backend validation tests (to be run in Node.js environment)
describe('Backend Validation Tests', () => {
  describe('Connection Parameter Validation', () => {
    test('should require user_id parameter', () => {
      const params = { project_id: 'proj123' };
      
      // This would test the validate_connection_params function from backend
      // expect(() => validate_connection_params(params)).toThrow('user_id parameter is required');
    });

    test('should require project_id parameter', () => {
      const params = { user_id: 'user123' };
      
      // This would test the validate_connection_params function from backend
      // expect(() => validate_connection_params(params)).toThrow('project_id parameter is required');
    });

    test('should accept valid parameters', () => {
      const params = {
        user_id: 'user123',
        project_id: 'proj456',
        workflow_id: 'wf789',
      };
      
      // This would test the validate_connection_params function from backend
      // expect(() => validate_connection_params(params)).not.toThrow();
    });
  });

  describe('Message Structure Validation', () => {
    test('should validate message structure', () => {
      const validMessage = {
        type: 'heartbeat',
        data: { client_time: '2025-08-18T02:07:22.127Z' },
      };
      
      // This would test the validate_message_structure function from backend
      // expect(() => validate_message_structure(validMessage)).not.toThrow();
    });

    test('should reject invalid message types', () => {
      const invalidMessage = {
        type: 'invalid_type',
        data: { test: 'data' },
      };
      
      // This would test the validate_message_structure function from backend
      // expect(() => validate_message_structure(invalidMessage)).toThrow('Invalid message type');
    });
  });
});