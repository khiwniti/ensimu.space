/**
 * Tests for CopilotKit integration components.
 * Tests AI assistant functionality, WebSocket communication, and user interactions.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import '@testing-library/jest-dom';
import { useCopilotAction, useCopilotReadable, useCopilotChatSuggestions } from '@copilotkit/react-core';

// Mock CopilotKit components
jest.mock('@copilotkit/react-core', () => ({
  CopilotKit: ({ children }: { children: React.ReactNode }) => <div data-testid="copilot-kit">{children}</div>,
  CopilotSidebar: ({ children }: { children: React.ReactNode }) => <div data-testid="copilot-sidebar">{children}</div>,
  CopilotChat: () => <div data-testid="copilot-chat">Chat Component</div>,
  useCopilotAction: jest.fn(),
  useCopilotReadable: jest.fn(),
  useCopilotChatSuggestions: jest.fn(),
}));

jest.mock('@copilotkit/react-ui', () => ({
  CopilotKitCSSProperties: {},
}));

import {
  CopilotIntegration,
  CopilotProvider,
  SimulationCopilotSidebar,
} from '../CopilotIntegration';

// Mock WebSocket
class MockWebSocket {
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  
  constructor(public url: string) {
    setTimeout(() => {
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }
  
  send(data: string) {
    // Mock sending data
  }
  
  close() {
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }
}

    // @ts-expect-error - Global WebSocket mock for testing
global.WebSocket = MockWebSocket;

// Mock environment variables
process.env.REACT_APP_API_URL = 'http://localhost:8000';
process.env.REACT_APP_WS_URL = 'ws://localhost:8000';

describe('CopilotIntegration', () => {
  const mockProject = {
    id: 'test-project-id',
    name: 'Test CFD Project',
    description: 'Test project for CFD simulation',
    physicsType: 'cfd' as const,
    status: 'draft' as const,
    cadFiles: ['test.step'],
  };

  const mockWorkflowStatus = {
    workflowId: 'test-workflow-id',
    status: 'running' as const,
    currentStep: 'geometry_analysis',
    progress: 25,
    steps: [
      { name: 'geometry_analysis', status: 'running' as const },
      { name: 'mesh_generation', status: 'pending' as const },
    ],
  };

  const mockOnProjectUpdate = jest.fn();
  const mockOnWorkflowAction = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', () => {
    render(
      <CopilotIntegration
        project={mockProject}
        onProjectUpdate={mockOnProjectUpdate}
        workflowStatus={mockWorkflowStatus}
        onWorkflowAction={mockOnWorkflowAction}
      />
    );

    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
  });

  it('shows connection status', async () => {
    render(
      <CopilotIntegration
        project={mockProject}
        onProjectUpdate={mockOnProjectUpdate}
        workflowStatus={mockWorkflowStatus}
        onWorkflowAction={mockOnWorkflowAction}
      />
    );

    // Initially disconnected
    expect(screen.getByText('AI Assistant Disconnected')).toBeInTheDocument();

    // Wait for WebSocket connection
    await waitFor(() => {
      expect(screen.getByText('AI Assistant Connected')).toBeInTheDocument();
    });
  });

  it('handles WebSocket messages', async () => {
    const { container } = render(
      <CopilotIntegration
        project={mockProject}
        onProjectUpdate={mockOnProjectUpdate}
        workflowStatus={mockWorkflowStatus}
        onWorkflowAction={mockOnWorkflowAction}
      />
    );

    // Wait for WebSocket connection
    await waitFor(() => {
      expect(screen.getByText('AI Assistant Connected')).toBeInTheDocument();
    });

    // Simulate receiving a message
    const mockMessage = {
      type: 'agent_state_update',
      data: {
        state: {
          currentAgent: 'geometry',
          progress: 50,
          recommendations: ['Test recommendation'],
        },
      },
    };

    // Find the WebSocket instance and trigger message
    const wsInstance = (global.WebSocket as any).mock.instances[0];
    if (wsInstance && wsInstance.onmessage) {
      act(() => {
        wsInstance.onmessage({
          data: JSON.stringify(mockMessage),
        } as MessageEvent);
      });
    }

    // Component should handle the message (no errors thrown)
    expect(container).toBeInTheDocument();
  });
});

describe('CopilotProvider', () => {
  it('renders children with CopilotKit provider', () => {
    render(
      <CopilotProvider>
        <div data-testid="test-child">Test Child</div>
      </CopilotProvider>
    );

    expect(screen.getByTestId('copilot-kit')).toBeInTheDocument();
    expect(screen.getByTestId('test-child')).toBeInTheDocument();
  });

  it('uses correct runtime URL', () => {
    const customUrl = 'http://custom-api.com';
    
    render(
      <CopilotProvider runtimeUrl={customUrl}>
        <div>Test</div>
      </CopilotProvider>
    );

    expect(screen.getByTestId('copilot-kit')).toBeInTheDocument();
  });
});

describe('SimulationCopilotSidebar', () => {
  it('renders copilot sidebar and chat', () => {
    render(<SimulationCopilotSidebar />);

    expect(screen.getByTestId('copilot-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('copilot-chat')).toBeInTheDocument();
  });
});

// Test CopilotKit hooks integration
describe('CopilotKit Hooks Integration', () => {

  beforeEach(() => {
    useCopilotAction.mockClear();
    useCopilotReadable.mockClear();
    useCopilotChatSuggestions.mockClear();
  });

  it('registers copilot actions', () => {
    render(
      <CopilotIntegration
        project={mockProject}
        onProjectUpdate={mockOnProjectUpdate}
        workflowStatus={mockWorkflowStatus}
        onWorkflowAction={mockOnWorkflowAction}
      />
    );

    // Check that actions were registered
    expect(useCopilotAction).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'startSimulationWorkflow',
        description: expect.stringContaining('Start the AI-powered simulation'),
      })
    );

    expect(useCopilotAction).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'updateMeshSettings',
        description: expect.stringContaining('Update mesh generation settings'),
      })
    );

    expect(useCopilotAction).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'addMaterial',
        description: expect.stringContaining('Add material properties'),
      })
    );
  });

  it('makes project data readable by copilot', () => {
    render(
      <CopilotIntegration
        project={mockProject}
        onProjectUpdate={mockOnProjectUpdate}
        workflowStatus={mockWorkflowStatus}
        onWorkflowAction={mockOnWorkflowAction}
      />
    );

    expect(useCopilotReadable).toHaveBeenCalledWith({
      description: 'Current simulation project details',
      value: mockProject,
    });

    expect(useCopilotReadable).toHaveBeenCalledWith({
      description: 'Current workflow execution status',
      value: mockWorkflowStatus,
    });
  });

  it('provides chat suggestions based on project state', () => {
    render(
      <CopilotIntegration
        project={mockProject}
        onProjectUpdate={mockOnProjectUpdate}
        workflowStatus={mockWorkflowStatus}
        onWorkflowAction={mockOnWorkflowAction}
      />
    );

    expect(useCopilotChatSuggestions).toHaveBeenCalledWith({
      instructions: expect.stringContaining('You are an AI assistant for simulation preprocessing'),
    });
  });
});

describe('Copilot Action Handlers', () => {

  it('handles start workflow action', async () => {
    let startWorkflowHandler: any;

    useCopilotAction.mockImplementation((config: any) => {
      if (config.name === 'startSimulationWorkflow') {
        startWorkflowHandler = config.handler;
      }
    });

    render(
      <CopilotIntegration
        project={mockProject}
        onProjectUpdate={mockOnProjectUpdate}
        workflowStatus={mockWorkflowStatus}
        onWorkflowAction={mockOnWorkflowAction}
      />
    );

    // Execute the handler
    const result = await startWorkflowHandler({
      physicsType: 'cfd',
      userGoal: 'Test CFD analysis',
    });

    expect(mockOnProjectUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        physicsType: 'cfd',
        description: 'Test CFD analysis',
        status: 'processing',
      })
    );

    expect(mockOnWorkflowAction).toHaveBeenCalledWith('start', {
      physicsType: 'cfd',
      userGoal: 'Test CFD analysis',
    });

    expect(result).toContain('Started cfd simulation preprocessing workflow');
  });

  it('handles update mesh settings action', async () => {
    let updateMeshHandler: any;

    useCopilotAction.mockImplementation((config: any) => {
      if (config.name === 'updateMeshSettings') {
        updateMeshHandler = config.handler;
      }
    });

    render(
      <CopilotIntegration
        project={mockProject}
        onProjectUpdate={mockOnProjectUpdate}
        workflowStatus={mockWorkflowStatus}
        onWorkflowAction={mockOnWorkflowAction}
      />
    );

    // Execute the handler
    const result = await updateMeshHandler({
      elementSize: 0.1,
      refinementLevel: 3,
      adaptiveMeshing: true,
    });

    expect(mockOnProjectUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        meshSettings: {
          elementSize: 0.1,
          refinementLevel: 3,
          qualityThreshold: 0.3,
          adaptiveMeshing: true,
        },
      })
    );

    expect(result).toContain('Updated mesh settings');
  });

  it('handles add material action', async () => {
    let addMaterialHandler: any;

    useCopilotAction.mockImplementation((config: any) => {
      if (config.name === 'addMaterial') {
        addMaterialHandler = config.handler;
      }
    });

    render(
      <CopilotIntegration
        project={mockProject}
        onProjectUpdate={mockOnProjectUpdate}
        workflowStatus={mockWorkflowStatus}
        onWorkflowAction={mockOnWorkflowAction}
      />
    );

    // Execute the handler
    const result = await addMaterialHandler({
      materialName: 'Water',
      density: 1000,
      viscosity: 0.001,
    });

    expect(mockOnProjectUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        materialProperties: {
          materials: expect.arrayContaining([
            expect.objectContaining({
              name: 'Water',
              density: 1000,
              viscosity: 0.001,
            }),
          ]),
        },
      })
    );

    expect(result).toContain('Added material "Water"');
  });

  it('handles workflow control actions', async () => {
    let controlWorkflowHandler: any;

    useCopilotAction.mockImplementation((config: any) => {
      if (config.name === 'controlWorkflow') {
        controlWorkflowHandler = config.handler;
      }
    });

    render(
      <CopilotIntegration
        project={mockProject}
        onProjectUpdate={mockOnProjectUpdate}
        workflowStatus={mockWorkflowStatus}
        onWorkflowAction={mockOnWorkflowAction}
      />
    );

    // Test pause action
    const pauseResult = await controlWorkflowHandler({ action: 'pause' });
    expect(mockOnWorkflowAction).toHaveBeenCalledWith('pause');
    expect(pauseResult).toContain('Workflow paused successfully');

    // Test resume action
    const resumeResult = await controlWorkflowHandler({ action: 'resume' });
    expect(mockOnWorkflowAction).toHaveBeenCalledWith('resume');
    expect(resumeResult).toContain('Workflow resumed successfully');

    // Test stop action
    const stopResult = await controlWorkflowHandler({ action: 'stop' });
    expect(mockOnWorkflowAction).toHaveBeenCalledWith('stop');
    expect(stopResult).toContain('Workflow stopped successfully');
  });
});

// Test error handling
describe('Error Handling', () => {
  it('handles WebSocket connection errors', async () => {
    // Mock WebSocket that fails to connect
    class FailingWebSocket extends MockWebSocket {
      constructor(url: string) {
        super(url);
        setTimeout(() => {
          if (this.onerror) {
            this.onerror(new Event('error'));
          }
        }, 100);
      }
    }

// @ts-expect-error - Global WebSocket mock for testing
    global.WebSocket = FailingWebSocket;

    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

    render(
      <CopilotIntegration
        project={mockProject}
        onProjectUpdate={mockOnProjectUpdate}
        workflowStatus={mockWorkflowStatus}
        onWorkflowAction={mockOnWorkflowAction}
      />
    );

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('WebSocket error:', expect.any(Event));
    });

    consoleSpy.mockRestore();
  });

  it('handles invalid WebSocket messages', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

    render(
      <CopilotIntegration
        project={mockProject}
        onProjectUpdate={mockOnProjectUpdate}
        workflowStatus={mockWorkflowStatus}
        onWorkflowAction={mockOnWorkflowAction}
      />
    );

    // Wait for connection
    await waitFor(() => {
      expect(screen.getByText('AI Assistant Connected')).toBeInTheDocument();
    });

    // Send invalid JSON
    const wsInstance = (global.WebSocket as any).mock.instances[0];
    if (wsInstance && wsInstance.onmessage) {
      act(() => {
        wsInstance.onmessage({
          data: 'invalid json',
        } as MessageEvent);
      });
    }

    expect(consoleSpy).toHaveBeenCalledWith(
      'Error parsing WebSocket message:',
      expect.any(Error)
    );

    consoleSpy.mockRestore();
  });
});
