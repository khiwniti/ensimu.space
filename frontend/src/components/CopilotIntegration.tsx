/**
 * CopilotKit integration for AI-powered simulation preprocessing.
 * Implements AG-UI protocol for seamless AI agent interaction.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  CopilotKit,
  CopilotSidebar,
  CopilotChat,
  useCopilotAction,
  useCopilotReadable,
  useCopilotChatSuggestions,
} from '@copilotkit/react-core';
import { CopilotKitCSSProperties } from '@copilotkit/react-ui';

// Types for simulation preprocessing
interface SimulationProject {
  id: string;
  name: string;
  description: string;
  physicsType: 'cfd' | 'structural' | 'thermal' | 'electromagnetic';
  status: 'draft' | 'processing' | 'completed' | 'failed';
  cadFiles: string[];
  meshSettings?: MeshSettings;
  materialProperties?: MaterialProperties;
  boundaryConditions?: BoundaryConditions;
}

interface MeshSettings {
  elementSize: number;
  refinementLevel: number;
  qualityThreshold: number;
  adaptiveMeshing: boolean;
}

interface MaterialProperties {
  materials: Array<{
    name: string;
    density: number;
    viscosity?: number;
    thermalConductivity?: number;
    elasticModulus?: number;
  }>;
}

interface BoundaryConditions {
  inlet?: { velocity: number; temperature?: number };
  outlet?: { pressure: number };
  walls?: { temperature?: number; heatFlux?: number };
}

interface WorkflowStatus {
  workflowId: string;
  status: 'running' | 'completed' | 'failed' | 'paused';
  currentStep: string;
  progress: number;
  steps: Array<{
    name: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    duration?: number;
  }>;
}

interface CopilotIntegrationProps {
  project: SimulationProject;
  onProjectUpdate: (project: SimulationProject) => void;
  workflowStatus?: WorkflowStatus;
  onWorkflowAction: (action: string, params?: any) => void;
}

export const CopilotIntegration: React.FC<CopilotIntegrationProps> = ({
  project,
  onProjectUpdate,
  workflowStatus,
  onWorkflowAction,
}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [agentState, setAgentState] = useState<any>({});

  // Make project data readable by Copilot
  useCopilotReadable({
    description: 'Current simulation project details',
    value: project,
  });

  // Make workflow status readable by Copilot
  useCopilotReadable({
    description: 'Current workflow execution status',
    value: workflowStatus,
  });

  // Make agent state readable by Copilot
  useCopilotReadable({
    description: 'Current AI agent state and recommendations',
    value: agentState,
  });

  // Action: Start simulation preprocessing workflow
  useCopilotAction({
    name: 'startSimulationWorkflow',
    description: 'Start the AI-powered simulation preprocessing workflow',
    parameters: [
      {
        name: 'physicsType',
        type: 'string',
        description: 'Type of physics simulation (cfd, structural, thermal, electromagnetic)',
        enum: ['cfd', 'structural', 'thermal', 'electromagnetic'],
      },
      {
        name: 'userGoal',
        type: 'string',
        description: 'User description of simulation goals and requirements',
      },
    ],
    handler: async ({ physicsType, userGoal }) => {
      const updatedProject = {
        ...project,
        physicsType: physicsType as any,
        description: userGoal,
        status: 'processing' as const,
      };
      
      onProjectUpdate(updatedProject);
      onWorkflowAction('start', { physicsType, userGoal });
      
      return `Started ${physicsType} simulation preprocessing workflow with goal: ${userGoal}`;
    },
  });

  // Action: Update mesh settings
  useCopilotAction({
    name: 'updateMeshSettings',
    description: 'Update mesh generation settings for the simulation',
    parameters: [
      {
        name: 'elementSize',
        type: 'number',
        description: 'Mesh element size (smaller = finer mesh)',
      },
      {
        name: 'refinementLevel',
        type: 'number',
        description: 'Mesh refinement level (1-5)',
      },
      {
        name: 'adaptiveMeshing',
        type: 'boolean',
        description: 'Enable adaptive mesh refinement',
      },
    ],
    handler: async ({ elementSize, refinementLevel, adaptiveMeshing }) => {
      const meshSettings: MeshSettings = {
        elementSize,
        refinementLevel,
        qualityThreshold: 0.3, // Default
        adaptiveMeshing,
      };

      const updatedProject = {
        ...project,
        meshSettings,
      };

      onProjectUpdate(updatedProject);
      
      return `Updated mesh settings: element size ${elementSize}, refinement level ${refinementLevel}, adaptive meshing ${adaptiveMeshing ? 'enabled' : 'disabled'}`;
    },
  });

  // Action: Add material properties
  useCopilotAction({
    name: 'addMaterial',
    description: 'Add material properties for the simulation',
    parameters: [
      {
        name: 'materialName',
        type: 'string',
        description: 'Name of the material (e.g., "Water", "Steel", "Air")',
      },
      {
        name: 'density',
        type: 'number',
        description: 'Material density in kg/m³',
      },
      {
        name: 'viscosity',
        type: 'number',
        description: 'Dynamic viscosity in Pa·s (for fluid simulations)',
        required: false,
      },
      {
        name: 'thermalConductivity',
        type: 'number',
        description: 'Thermal conductivity in W/(m·K) (for thermal simulations)',
        required: false,
      },
    ],
    handler: async ({ materialName, density, viscosity, thermalConductivity }) => {
      const newMaterial = {
        name: materialName,
        density,
        ...(viscosity && { viscosity }),
        ...(thermalConductivity && { thermalConductivity }),
      };

      const materialProperties: MaterialProperties = {
        materials: [
          ...(project.materialProperties?.materials || []),
          newMaterial,
        ],
      };

      const updatedProject = {
        ...project,
        materialProperties,
      };

      onProjectUpdate(updatedProject);
      
      return `Added material "${materialName}" with density ${density} kg/m³`;
    },
  });

  // Action: Set boundary conditions
  useCopilotAction({
    name: 'setBoundaryConditions',
    description: 'Set boundary conditions for the simulation',
    parameters: [
      {
        name: 'inletVelocity',
        type: 'number',
        description: 'Inlet velocity in m/s',
        required: false,
      },
      {
        name: 'outletPressure',
        type: 'number',
        description: 'Outlet pressure in Pa',
        required: false,
      },
      {
        name: 'wallTemperature',
        type: 'number',
        description: 'Wall temperature in K',
        required: false,
      },
    ],
    handler: async ({ inletVelocity, outletPressure, wallTemperature }) => {
      const boundaryConditions: BoundaryConditions = {
        ...(inletVelocity && { inlet: { velocity: inletVelocity } }),
        ...(outletPressure && { outlet: { pressure: outletPressure } }),
        ...(wallTemperature && { walls: { temperature: wallTemperature } }),
      };

      const updatedProject = {
        ...project,
        boundaryConditions,
      };

      onProjectUpdate(updatedProject);
      
      return `Set boundary conditions: ${Object.keys(boundaryConditions).join(', ')}`;
    },
  });

  // Action: Get workflow recommendations
  useCopilotAction({
    name: 'getWorkflowRecommendations',
    description: 'Get AI recommendations for improving the simulation setup',
    parameters: [],
    handler: async () => {
      // This would typically call your backend API
      const recommendations = [
        'Consider refining the mesh near the inlet for better accuracy',
        'The current Reynolds number suggests turbulent flow - consider using a turbulence model',
        'Material properties look good for this type of analysis',
      ];
      
      return `AI Recommendations:\n${recommendations.map((r, i) => `${i + 1}. ${r}`).join('\n')}`;
    },
  });

  // Action: Pause/Resume workflow
  useCopilotAction({
    name: 'controlWorkflow',
    description: 'Pause, resume, or stop the current workflow',
    parameters: [
      {
        name: 'action',
        type: 'string',
        description: 'Action to perform',
        enum: ['pause', 'resume', 'stop'],
      },
    ],
    handler: async ({ action }) => {
      onWorkflowAction(action);
      return `Workflow ${action}d successfully`;
    },
  });

  // Chat suggestions based on current state
  useCopilotChatSuggestions({
    instructions: `
      You are an AI assistant for simulation preprocessing. Based on the current project state:
      - Physics Type: ${project.physicsType}
      - Status: ${project.status}
      - Current Step: ${workflowStatus?.currentStep || 'Not started'}
      
      Provide helpful suggestions for:
      1. Optimizing mesh settings
      2. Selecting appropriate materials
      3. Setting boundary conditions
      4. Improving simulation accuracy
      5. Troubleshooting common issues
      
      Be specific and technical, but also explain concepts clearly.
    `,
  });

  // WebSocket connection for real-time updates using standardized protocol
  useEffect(() => {
    // This would typically use the useWebSocket hook, but for this component
    // we'll create a simple connection to demonstrate the standardized URL pattern
    import('../utils/websocketUtils').then(({ buildWebSocketUrl, getWebSocketBaseUrl, MessageType, parseWebSocketMessage }) => {
      const connectionParams = {
        user_id: 'copilot_user', // This should come from auth context
        project_id: project.id,
      };
      
      const wsUrl = buildWebSocketUrl(getWebSocketBaseUrl(), connectionParams);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
        console.log('Connected to simulation preprocessing WebSocket');
      };

      ws.onmessage = (event) => {
        try {
          const message = parseWebSocketMessage(event.data);
          
          if (!message) {
            console.error('Failed to parse WebSocket message');
            return;
          }
          
          switch (message.type) {
            case MessageType.AGENT_STATE_UPDATE:
              setAgentState(message.data.state);
              break;
            case MessageType.WORKFLOW_STATUS_UPDATE:
              // Handle workflow status updates
              break;
            case MessageType.HITL_CHECKPOINT_CREATED:
              // Handle HITL checkpoint notifications
              break;
            case MessageType.ERROR:
              console.error('WebSocket error:', message.data);
              break;
          }
        } catch (error) {
          console.error('Error handling WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('Disconnected from simulation preprocessing WebSocket');
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      return () => {
        ws.close();
      };
    });
  }, [project.id]);

  return (
    <div className="copilot-integration">
      <div className="connection-status">
        <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '🟢' : '🔴'}
        </span>
        <span>AI Assistant {isConnected ? 'Connected' : 'Disconnected'}</span>
      </div>
    </div>
  );
};

// CopilotKit provider component
interface CopilotProviderProps {
  children: React.ReactNode;
  runtimeUrl?: string;
}

export const CopilotProvider: React.FC<CopilotProviderProps> = ({
  children,
  runtimeUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000',
}) => {
  return (
    <CopilotKit runtimeUrl={`${runtimeUrl}/copilot`}>
      {children}
    </CopilotKit>
  );
};

// Sidebar component with custom styling
export const SimulationCopilotSidebar: React.FC = () => {
  const copilotKitProps: CopilotKitCSSProperties = {
    '--copilot-kit-primary-color': '#2563eb',
    '--copilot-kit-secondary-color': '#64748b',
    '--copilot-kit-muted-color': '#f1f5f9',
    '--copilot-kit-overlay-color': 'rgba(0, 0, 0, 0.1)',
    '--copilot-kit-separator-color': '#e2e8f0',
  };

  return (
    <CopilotSidebar
      style={copilotKitProps}
      defaultOpen={false}
      clickOutsideToClose={true}
      labels={{
        title: 'Simulation AI Assistant',
        initial: 'Hi! I can help you set up and optimize your simulation preprocessing. What would you like to work on?',
      }}
    >
      <CopilotChat
        instructions="You are an expert simulation engineer AI assistant. Help users with CAD preprocessing, mesh generation, material selection, and boundary condition setup. Provide specific, actionable advice."
        makeSystemMessage={(instructions) => ({
          content: instructions,
          role: 'system',
        })}
      />
    </CopilotSidebar>
  );
};

export default CopilotIntegration;
