/**
 * React hooks for workflow management and real-time updates.
 * Integrates with WebSocket for live workflow status and HITL checkpoints.
 * Uses standardized WebSocket protocol for reliable communication.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import {
  StandardWebSocketMessage,
  MessageType,
  createHITLResponseMessage,
  WebSocketConnectionParams,
} from '../utils/websocketUtils';

export interface WorkflowStep {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  duration?: number;
  result?: any;
  error?: string;
}

export interface WorkflowStatus {
  workflowId: string;
  projectId: string;
  status: 'running' | 'completed' | 'failed' | 'paused';
  currentStep: string;
  progress: number;
  steps: WorkflowStep[];
  createdAt: string;
  updatedAt?: string;
  globalContext?: any;
}

export interface HITLCheckpoint {
  checkpointId: string;
  workflowId: string;
  checkpointType: string;
  status: 'pending' | 'completed' | 'timeout';
  checkpointData: any;
  createdAt: string;
  timeoutAt?: string;
}

export interface WorkflowActions {
  startWorkflow: (projectId: string, userGoal: string, physicsType: string, cadFiles?: string[]) => Promise<string>;
  pauseWorkflow: (workflowId: string) => Promise<boolean>;
  resumeWorkflow: (workflowId: string) => Promise<boolean>;
  stopWorkflow: (workflowId: string) => Promise<boolean>;
  respondToHITL: (checkpointId: string, response: any) => Promise<boolean>;
  getWorkflowStatus: (workflowId: string) => Promise<WorkflowStatus | null>;
}

export interface UseWorkflowReturn {
  currentWorkflow: WorkflowStatus | null;
  workflows: Record<string, WorkflowStatus>;
  hitlCheckpoints: HITLCheckpoint[];
  isLoading: boolean;
  error: string | null;
  actions: WorkflowActions;
}

export const useWorkflow = (projectId?: string, userId: string = 'anonymous'): UseWorkflowReturn => {
  const [workflows, setWorkflows] = useState<Record<string, WorkflowStatus>>({});
  const [currentWorkflow, setCurrentWorkflow] = useState<WorkflowStatus | null>(null);
  const [hitlCheckpoints, setHitlCheckpoints] = useState<HITLCheckpoint[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  
  // WebSocket connection for real-time updates using standardized protocol
  const connectionParams: WebSocketConnectionParams = {
    user_id: userId,
    project_id: projectId || 'default',
  };

  const { isConnected, sendRawMessage } = useWebSocket({
    connectionParams,
    onMessage: handleWebSocketMessage,
    onValidationError: (error, details) => {
      console.error('WebSocket validation error:', error, details);
      setError(`WebSocket validation error: ${error}`);
    },
  });

  function handleWebSocketMessage(message: StandardWebSocketMessage) {
    switch (message.type) {
      case MessageType.WORKFLOW_STATUS_UPDATE:
        handleWorkflowStatusUpdate(message.data);
        break;
      case MessageType.WORKFLOW_STEP_COMPLETE:
        handleWorkflowStepComplete(message.data);
        break;
      case MessageType.HITL_CHECKPOINT_CREATED:
        handleHITLCheckpointCreated(message.data);
        break;
      case MessageType.WORKFLOW_ERROR:
        handleWorkflowError(message.data);
        break;
    }
  }

  const handleWorkflowStatusUpdate = useCallback((data: any) => {
    const { workflow_id, status, current_step, progress } = data;
    
    setWorkflows(prev => ({
      ...prev,
      [workflow_id]: {
        ...prev[workflow_id],
        workflowId: workflow_id,
        status,
        currentStep: current_step,
        progress,
        updatedAt: new Date().toISOString(),
      },
    }));

    // Update current workflow if it matches
    if (currentWorkflow?.workflowId === workflow_id) {
      setCurrentWorkflow(prev => prev ? {
        ...prev,
        status,
        currentStep: current_step,
        progress,
        updatedAt: new Date().toISOString(),
      } : null);
    }
  }, [currentWorkflow?.workflowId]);

  const handleWorkflowStepComplete = useCallback((data: any) => {
    const { workflow_id, step_name, result } = data;
    
    setWorkflows(prev => {
      const workflow = prev[workflow_id];
      if (!workflow) return prev;

      const updatedSteps = workflow.steps.map(step =>
        step.name === step_name
          ? { ...step, status: 'completed' as const, result }
          : step
      );

      return {
        ...prev,
        [workflow_id]: {
          ...workflow,
          steps: updatedSteps,
          updatedAt: new Date().toISOString(),
        },
      };
    });

    // Update current workflow if it matches
    if (currentWorkflow?.workflowId === workflow_id) {
      setCurrentWorkflow(prev => {
        if (!prev) return null;
        
        const updatedSteps = prev.steps.map(step =>
          step.name === step_name
            ? { ...step, status: 'completed' as const, result }
            : step
        );

        return {
          ...prev,
          steps: updatedSteps,
          updatedAt: new Date().toISOString(),
        };
      });
    }
  }, [currentWorkflow?.workflowId]);

  const handleHITLCheckpointCreated = useCallback((data: any) => {
    const { workflow_id, checkpoint_id, checkpoint_data } = data;
    
    const newCheckpoint: HITLCheckpoint = {
      checkpointId: checkpoint_id,
      workflowId: workflow_id,
      checkpointType: checkpoint_data.checkpoint_type || 'quality_review',
      status: 'pending',
      checkpointData: checkpoint_data,
      createdAt: new Date().toISOString(),
    };

    setHitlCheckpoints(prev => [...prev, newCheckpoint]);
  }, []);

  const handleWorkflowError = useCallback((data: any) => {
    const { workflow_id, error: errorMessage } = data;
    
    setError(errorMessage);
    
    setWorkflows(prev => ({
      ...prev,
      [workflow_id]: {
        ...prev[workflow_id],
        status: 'failed',
        updatedAt: new Date().toISOString(),
      },
    }));

    if (currentWorkflow?.workflowId === workflow_id) {
      setCurrentWorkflow(prev => prev ? {
        ...prev,
        status: 'failed',
        updatedAt: new Date().toISOString(),
      } : null);
    }
  }, [currentWorkflow?.workflowId]);

  // API actions
  const startWorkflow = useCallback(async (
    projectId: string,
    userGoal: string,
    physicsType: string,
    cadFiles?: string[]
  ): Promise<string> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/api/workflows/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: projectId,
          user_goal: userGoal,
          physics_type: physicsType,
          cad_files: cadFiles || [],
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to start workflow: ${response.statusText}`);
      }

      const data = await response.json();
      const workflowId = data.workflow_id;

      // Initialize workflow state
      const newWorkflow: WorkflowStatus = {
        workflowId,
        projectId,
        status: 'running',
        currentStep: 'start_workflow',
        progress: 0,
        steps: [],
        createdAt: new Date().toISOString(),
      };

      setWorkflows(prev => ({
        ...prev,
        [workflowId]: newWorkflow,
      }));

      setCurrentWorkflow(newWorkflow);

      return workflowId;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl]);

  const pauseWorkflow = useCallback(async (workflowId: string): Promise<boolean> => {
    try {
      const response = await fetch(`${apiUrl}/api/workflows/${workflowId}/pause`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Failed to pause workflow: ${response.statusText}`);
      }

      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      return false;
    }
  }, [apiUrl]);

  const resumeWorkflow = useCallback(async (workflowId: string): Promise<boolean> => {
    try {
      const response = await fetch(`${apiUrl}/api/workflows/${workflowId}/resume`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Failed to resume workflow: ${response.statusText}`);
      }

      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      return false;
    }
  }, [apiUrl]);

  const stopWorkflow = useCallback(async (workflowId: string): Promise<boolean> => {
    try {
      const response = await fetch(`${apiUrl}/api/workflows/${workflowId}/stop`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Failed to stop workflow: ${response.statusText}`);
      }

      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      return false;
    }
  }, [apiUrl]);

  const respondToHITL = useCallback(async (
    checkpointId: string,
    response: any
  ): Promise<boolean> => {
    try {
      const apiResponse = await fetch(`${apiUrl}/api/workflows/hitl/${checkpointId}/respond`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(response),
      });

      if (!apiResponse.ok) {
        throw new Error(`Failed to respond to HITL checkpoint: ${apiResponse.statusText}`);
      }

      // Update checkpoint status
      setHitlCheckpoints(prev =>
        prev.map(checkpoint =>
          checkpoint.checkpointId === checkpointId
            ? { ...checkpoint, status: 'completed' }
            : checkpoint
        )
      );

      // Send WebSocket message for real-time update
      if (isConnected) {
        const hitlResponseMessage = createHITLResponseMessage(
          checkpointId,
          response.approved || false,
          response.feedback
        );
        sendRawMessage(hitlResponseMessage);
      }

      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      return false;
    }
  }, [apiUrl, isConnected, sendMessage]);

  const getWorkflowStatus = useCallback(async (
    workflowId: string
  ): Promise<WorkflowStatus | null> => {
    try {
      const response = await fetch(`${apiUrl}/api/workflows/${workflowId}/status`);

      if (!response.ok) {
        throw new Error(`Failed to get workflow status: ${response.statusText}`);
      }

      const data = await response.json();
      
      const workflowStatus: WorkflowStatus = {
        workflowId: data.workflow_id,
        projectId: data.project_id,
        status: data.status,
        currentStep: data.current_step,
        progress: data.progress || 0,
        steps: data.steps || [],
        createdAt: data.created_at,
        updatedAt: data.updated_at,
        globalContext: data.global_context,
      };

      // Update local state
      setWorkflows(prev => ({
        ...prev,
        [workflowId]: workflowStatus,
      }));

      return workflowStatus;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      return null;
    }
  }, [apiUrl]);

  // Load workflow status on mount if projectId is provided
  useEffect(() => {
    if (projectId) {
      // Load workflows for this project
      // This would typically be an API call to get all workflows for the project
    }
  }, [projectId]);

  const actions: WorkflowActions = {
    startWorkflow,
    pauseWorkflow,
    resumeWorkflow,
    stopWorkflow,
    respondToHITL,
    getWorkflowStatus,
  };

  return {
    currentWorkflow,
    workflows,
    hitlCheckpoints,
    isLoading,
    error,
    actions,
  };
};
