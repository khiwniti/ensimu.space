import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SimulationProgress } from '../../components/GenerativeUI/SimulationProgress';

// Mock the useSimulationState hook
vi.mock('../../hooks/useSimulationState', () => ({
  useSimulationState: vi.fn(),
}));

import { useSimulationState } from '../../hooks/useSimulationState';

describe('SimulationProgress', () => {
  const mockUseSimulationState = useSimulationState as any;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders progress component with initial state', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        progress: 0,
        geometryStatus: 'pending',
        meshStatus: 'pending',
        materialsStatus: 'pending',
        physicsStatus: 'pending',
        currentStep: 'initialization',
        isProcessing: false,
        workflowId: null,
        errors: [],
        warnings: [],
        iterationCount: 0,
        maxIterations: 3,
      },
    });

    render(<SimulationProgress projectId="test-project" />);

    expect(screen.getByText('Preprocessing Progress')).toBeInTheDocument();
    expect(screen.getByText('0% Complete')).toBeInTheDocument();
    expect(screen.getByText('Geometry Analysis')).toBeInTheDocument();
    expect(screen.getByText('Mesh Generation')).toBeInTheDocument();
    expect(screen.getByText('Material Assignment')).toBeInTheDocument();
    expect(screen.getByText('Physics Setup')).toBeInTheDocument();
  });

  it('shows processing state correctly', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        progress: 25,
        geometryStatus: 'completed',
        meshStatus: 'processing',
        materialsStatus: 'pending',
        physicsStatus: 'pending',
        currentStep: 'mesh_generation',
        isProcessing: true,
        workflowId: 'workflow-123',
        errors: [],
        warnings: [],
        iterationCount: 0,
        maxIterations: 3,
      },
    });

    render(<SimulationProgress projectId="test-project" />);

    expect(screen.getByText('25% Complete')).toBeInTheDocument();
    expect(screen.getByText('Processing...')).toBeInTheDocument();
    
    // Check for completed geometry step
    const geometryStep = screen.getByText('Geometry Analysis').closest('div');
    expect(geometryStep).toBeInTheDocument();
    
    // Check for processing mesh step
    const meshStep = screen.getByText('Mesh Generation').closest('div');
    expect(meshStep).toBeInTheDocument();
  });

  it('displays errors when present', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        progress: 15,
        geometryStatus: 'failed',
        meshStatus: 'pending',
        materialsStatus: 'pending',
        physicsStatus: 'pending',
        currentStep: 'geometry_processing',
        isProcessing: false,
        workflowId: 'workflow-123',
        errors: [
          {
            step: 'geometry_processing',
            error: 'File format not supported',
            timestamp: '2024-01-01T00:00:00Z',
          },
        ],
        warnings: [],
        iterationCount: 0,
        maxIterations: 3,
      },
    });

    render(<SimulationProgress projectId="test-project" />);

    expect(screen.getByText('1 Error(s) Detected')).toBeInTheDocument();
    expect(screen.getByText('geometry_processing: File format not supported')).toBeInTheDocument();
  });

  it('displays warnings when present', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        progress: 50,
        geometryStatus: 'completed',
        meshStatus: 'completed',
        materialsStatus: 'processing',
        physicsStatus: 'pending',
        currentStep: 'material_assignment',
        isProcessing: true,
        workflowId: 'workflow-123',
        errors: [],
        warnings: [
          {
            step: 'mesh_generation',
            warning: 'Low mesh quality detected',
            timestamp: '2024-01-01T00:00:00Z',
          },
        ],
        iterationCount: 1,
        maxIterations: 3,
      },
    });

    render(<SimulationProgress projectId="test-project" />);

    expect(screen.getByText('1 Warning(s)')).toBeInTheDocument();
    expect(screen.getByText('mesh_generation: Low mesh quality detected')).toBeInTheDocument();
    expect(screen.getByText('Iteration 1 of 3')).toBeInTheDocument();
  });

  it('shows workflow ID when available', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        progress: 75,
        geometryStatus: 'completed',
        meshStatus: 'completed',
        materialsStatus: 'completed',
        physicsStatus: 'processing',
        currentStep: 'physics_setup',
        isProcessing: true,
        workflowId: 'workflow-abc-123',
        errors: [],
        warnings: [],
        iterationCount: 0,
        maxIterations: 3,
      },
    });

    render(<SimulationProgress projectId="test-project" />);

    expect(screen.getByText('Workflow ID: workflow-abc-123')).toBeInTheDocument();
  });

  it('displays current step indicator', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        progress: 60,
        geometryStatus: 'completed',
        meshStatus: 'completed',
        materialsStatus: 'processing',
        physicsStatus: 'pending',
        currentStep: 'material_assignment',
        isProcessing: true,
        workflowId: 'workflow-123',
        errors: [],
        warnings: [],
        iterationCount: 0,
        maxIterations: 3,
      },
    });

    render(<SimulationProgress projectId="test-project" />);

    expect(screen.getByText('Current Step: MATERIAL ASSIGNMENT')).toBeInTheDocument();
    expect(screen.getByText('The AI agents are working on this step...')).toBeInTheDocument();
  });

  it('handles completed workflow state', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        progress: 100,
        geometryStatus: 'completed',
        meshStatus: 'completed',
        materialsStatus: 'completed',
        physicsStatus: 'completed',
        currentStep: 'completed',
        isProcessing: false,
        workflowId: 'workflow-123',
        errors: [],
        warnings: [],
        iterationCount: 0,
        maxIterations: 3,
      },
    });

    render(<SimulationProgress projectId="test-project" />);

    expect(screen.getByText('100% Complete')).toBeInTheDocument();
    
    // All steps should show as completed
    const completedSteps = screen.getAllByText('✓');
    expect(completedSteps).toHaveLength(4); // 4 main steps
  });
});
