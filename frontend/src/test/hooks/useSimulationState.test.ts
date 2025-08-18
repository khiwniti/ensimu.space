import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSimulationState } from '../../hooks/useSimulationState';

// Mock CopilotKit
vi.mock('@copilotkit/react-core', () => ({
  useCoAgent: vi.fn(),
}));

import { useCoAgent } from '@copilotkit/react-core';

describe('useSimulationState', () => {
  const mockUseCoAgent = useCoAgent as any;
  let mockState: any;
  let mockSetState: any;

  beforeEach(() => {
    vi.clearAllMocks();
    
    mockState = {
      projectId: 'test-project',
      userGoal: '',
      physicsType: 'cfd',
      cadFiles: [],
      geometryStatus: 'pending',
      meshStatus: 'pending',
      materialsStatus: 'pending',
      physicsStatus: 'pending',
      currentStep: 'initialization',
      completedSteps: [],
      progress: 0,
      isProcessing: false,
      errors: [],
      warnings: [],
      iterationCount: 0,
      maxIterations: 3,
    };

    mockSetState = vi.fn((updater) => {
      if (typeof updater === 'function') {
        mockState = updater(mockState);
      } else {
        mockState = { ...mockState, ...updater };
      }
    });

    mockUseCoAgent.mockReturnValue({
      state: mockState,
      setState: mockSetState,
    });
  });

  it('initializes with correct default state', () => {
    const { result } = renderHook(() => useSimulationState('test-project'));

    expect(result.current.simulationState.projectId).toBe('test-project');
    expect(result.current.simulationState.physicsType).toBe('cfd');
    expect(result.current.simulationState.cadFiles).toEqual([]);
    expect(result.current.simulationState.geometryStatus).toBe('pending');
    expect(result.current.simulationState.progress).toBe(0);
    expect(result.current.simulationState.isProcessing).toBe(false);
  });

  it('updates simulation state correctly', () => {
    const { result } = renderHook(() => useSimulationState('test-project'));

    act(() => {
      result.current.updateSimulationState({
        userGoal: 'Test CFD simulation',
        physicsType: 'structural',
        progress: 25,
      });
    });

    expect(mockSetState).toHaveBeenCalledWith(expect.any(Function));
  });

  it('resets simulation state to initial values', () => {
    const { result } = renderHook(() => useSimulationState('test-project'));

    // First update the state
    act(() => {
      result.current.updateSimulationState({
        userGoal: 'Test simulation',
        progress: 50,
        isProcessing: true,
      });
    });

    // Then reset it
    act(() => {
      result.current.resetSimulationState();
    });

    expect(mockSetState).toHaveBeenCalledWith({
      projectId: 'test-project',
      userGoal: '',
      physicsType: 'cfd',
      cadFiles: [],
      geometryStatus: 'pending',
      meshStatus: 'pending',
      materialsStatus: 'pending',
      physicsStatus: 'pending',
      currentStep: 'initialization',
      completedSteps: [],
      progress: 0,
      isProcessing: false,
      errors: [],
      warnings: [],
      iterationCount: 0,
      maxIterations: 3,
    });
  });

  it('adds errors correctly', () => {
    const { result } = renderHook(() => useSimulationState('test-project'));

    act(() => {
      result.current.addError('geometry_processing', 'File format not supported');
    });

    expect(mockSetState).toHaveBeenCalledWith({
      errors: [
        {
          step: 'geometry_processing',
          error: 'File format not supported',
          timestamp: expect.any(String),
        },
      ],
    });
  });

  it('adds warnings correctly', () => {
    const { result } = renderHook(() => useSimulationState('test-project'));

    act(() => {
      result.current.addWarning('mesh_generation', 'Low mesh quality detected');
    });

    expect(mockSetState).toHaveBeenCalledWith({
      warnings: [
        {
          step: 'mesh_generation',
          warning: 'Low mesh quality detected',
          timestamp: expect.any(String),
        },
      ],
    });
  });

  it('clears errors correctly', () => {
    // Set up initial state with errors
    mockState.errors = [
      { step: 'test', error: 'test error', timestamp: '2024-01-01' },
    ];

    const { result } = renderHook(() => useSimulationState('test-project'));

    act(() => {
      result.current.clearErrors();
    });

    expect(mockSetState).toHaveBeenCalledWith({ errors: [] });
  });

  it('clears warnings correctly', () => {
    // Set up initial state with warnings
    mockState.warnings = [
      { step: 'test', warning: 'test warning', timestamp: '2024-01-01' },
    ];

    const { result } = renderHook(() => useSimulationState('test-project'));

    act(() => {
      result.current.clearWarnings();
    });

    expect(mockSetState).toHaveBeenCalledWith({ warnings: [] });
  });

  it('handles multiple errors and warnings', () => {
    const { result } = renderHook(() => useSimulationState('test-project'));

    // Add first error
    act(() => {
      result.current.addError('geometry', 'Error 1');
    });

    // Add second error
    act(() => {
      result.current.addError('mesh', 'Error 2');
    });

    // Add warning
    act(() => {
      result.current.addWarning('materials', 'Warning 1');
    });

    // Verify multiple calls to setState
    expect(mockSetState).toHaveBeenCalledTimes(3);
  });

  it('preserves existing errors when adding new ones', () => {
    // Set up initial state with existing error
    mockState.errors = [
      { step: 'existing', error: 'existing error', timestamp: '2024-01-01' },
    ];

    const { result } = renderHook(() => useSimulationState('test-project'));

    act(() => {
      result.current.addError('new_step', 'new error');
    });

    expect(mockSetState).toHaveBeenCalledWith({
      errors: [
        { step: 'existing', error: 'existing error', timestamp: '2024-01-01' },
        {
          step: 'new_step',
          error: 'new error',
          timestamp: expect.any(String),
        },
      ],
    });
  });

  it('preserves existing warnings when adding new ones', () => {
    // Set up initial state with existing warning
    mockState.warnings = [
      { step: 'existing', warning: 'existing warning', timestamp: '2024-01-01' },
    ];

    const { result } = renderHook(() => useSimulationState('test-project'));

    act(() => {
      result.current.addWarning('new_step', 'new warning');
    });

    expect(mockSetState).toHaveBeenCalledWith({
      warnings: [
        { step: 'existing', warning: 'existing warning', timestamp: '2024-01-01' },
        {
          step: 'new_step',
          warning: 'new warning',
          timestamp: expect.any(String),
        },
      ],
    });
  });

  it('updates lastUpdated timestamp when state changes', () => {
    const { result } = renderHook(() => useSimulationState('test-project'));

    act(() => {
      result.current.updateSimulationState({
        progress: 50,
      });
    });

    expect(mockSetState).toHaveBeenCalledWith(expect.any(Function));
    
    // Verify the function adds lastUpdated
    const updateFunction = mockSetState.mock.calls[0][0];
    const updatedState = updateFunction(mockState);
    expect(updatedState.lastUpdated).toBeDefined();
    expect(typeof updatedState.lastUpdated).toBe('string');
  });
});
