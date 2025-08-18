import { useEffect, useRef, useState, useCallback } from 'react';
import { useSimulationState } from './useSimulationState';
import { useWebSocket } from './useWebSocket';
import {
  StandardWebSocketMessage,
  MessageType,
  WebSocketConnectionParams,
  createUserMessage,
  createHITLResponseMessage,
  createPredictionRequestMessage,
  createStateChangeMessage,
} from '../utils/websocketUtils';

export function useWebSocketConnection(projectId: string, userId: string = 'anonymous') {
  const [lastMessage, setLastMessage] = useState<StandardWebSocketMessage | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const { updateSimulationState } = useSimulationState(projectId);

  // Use standardized WebSocket connection
  const connectionParams: WebSocketConnectionParams = {
    user_id: userId,
    project_id: projectId,
  };

  const { isConnected, sendRawMessage, connectionState } = useWebSocket({
    connectionParams,
    onMessage: handleStandardMessage,
    onError: (error) => {
      console.error('WebSocket error:', error);
      setConnectionError('WebSocket connection error');
    },
    onValidationError: (error, details) => {
      console.error('WebSocket validation error:', error, details);
      setConnectionError(`Validation error: ${error}`);
    },
  });

  const handleStandardMessage = useCallback((message: StandardWebSocketMessage) => {
    setLastMessage(message);
    handleAGUIEvent(message);
  }, []);

  const handleAGUIEvent = useCallback((message: StandardWebSocketMessage) => {
    const data = message.data;
    
    switch (message.type) {
      case MessageType.AGENT_STATE_UPDATE:
        // Update simulation state with patch from backend
        updateSimulationState(data.state_patch);
        break;
        
      case MessageType.WORKFLOW_STEP_COMPLETE:
        // Update progress and step status
        updateSimulationState({
          currentStep: data.current_step,
          progress: data.progress_percentage,
          completedSteps: data.completed_steps || []
        });
        break;
        
      case MessageType.WORKFLOW_STATUS_UPDATE:
        if (data.status === 'running') {
          updateSimulationState({
            workflowId: data.workflow_id,
            isProcessing: true,
            currentStep: data.current_step || 'geometry_processing',
            progress: data.progress || 5
          });
        } else if (data.status === 'completed') {
          updateSimulationState({
            isProcessing: false,
            progress: 100,
            currentStep: 'completed'
          });
        }
        break;
        
      case MessageType.WORKFLOW_ERROR:
        updateSimulationState({
          isProcessing: false,
          errors: [...(data.errors || []), {
            step: data.failed_step || 'unknown',
            error: data.error_message || 'Workflow failed',
            timestamp: message.timestamp
          }]
        });
        break;
        
      case MessageType.HITL_CHECKPOINT_CREATED:
        // Show HITL checkpoint UI
        updateSimulationState({
          activeCheckpoint: {
            checkpointId: data.checkpoint_id,
            checkpointType: data.checkpoint_data?.checkpoint_type,
            description: data.checkpoint_data?.description,
            checkpointData: data.checkpoint_data,
            agentRecommendations: data.checkpoint_data?.agent_recommendations || [],
            timeoutAt: data.checkpoint_data?.timeout_at
          },
          isProcessing: false
        });
        break;
        
      case MessageType.HITL_RESPONSE_SUBMITTED:
        updateSimulationState({
          activeCheckpoint: undefined,
          isProcessing: data.response_data?.approved || false
        });
        break;
        
      case MessageType.USER_MESSAGE:
        // Handle user messages acknowledgment
        console.log('User message processed:', data);
        break;
        
      case MessageType.PREDICTION_RESPONSE:
        // Handle real-time prediction updates for interactive design
        console.log('Real-time prediction update:', data);
        break;
        
      case MessageType.ERROR:
        console.error('WebSocket error message:', data);
        setConnectionError(data.error || 'Unknown error');
        break;
        
      default:
        console.log('Unhandled WebSocket message:', message.type, data);
    }
  }, [updateSimulationState]);

  const sendMessage = useCallback((message: StandardWebSocketMessage) => {
    if (isConnected) {
      try {
        sendRawMessage(message);
      } catch (error) {
        console.error('Failed to send WebSocket message:', error);
      }
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }, [isConnected, sendRawMessage]);

  const sendUserMessage = useCallback((content: string) => {
    const message = createUserMessage(content);
    sendMessage(message);
  }, [sendMessage]);

  const sendHITLResponse = useCallback((checkpointId: string, approved: boolean, feedback?: string) => {
    const message = createHITLResponseMessage(checkpointId, approved, feedback);
    sendMessage(message);
  }, [sendMessage]);

  const requestPrediction = useCallback((modelKey: string, point: [number, number, number]) => {
    const message = createPredictionRequestMessage(modelKey, point);
    sendMessage(message);
  }, [sendMessage]);

  const sendStateChange = useCallback((workflowId: string, statePatch: any) => {
    const message = createStateChangeMessage(workflowId, statePatch);
    sendMessage(message);
  }, [sendMessage]);

  return {
    isConnected,
    connectionError,
    lastMessage,
    sendMessage,
    sendUserMessage,
    sendHITLResponse,
    requestPrediction,
    sendStateChange,
    connectionState,
  };
}