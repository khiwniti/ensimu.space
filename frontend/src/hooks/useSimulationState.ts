import { useCoAgent } from "@copilotkit/react-core";

export interface SimulationState {
  // Project context
  projectId: string;
  workflowId?: string;
  userGoal: string;
  physicsType: 'cfd' | 'structural' | 'thermal' | 'electromagnetic' | 'multi_physics';
  
  // File management
  cadFiles: Array<{
    id: string;
    filename: string;
    fileType: string;
    uploadStatus: 'pending' | 'uploading' | 'completed' | 'failed';
    analysisResults?: any;
  }>;
  
  // Preprocessing status
  geometryStatus: 'pending' | 'processing' | 'completed' | 'failed' | 'requires_review';
  meshStatus: 'pending' | 'processing' | 'completed' | 'failed' | 'requires_review';
  materialsStatus: 'pending' | 'processing' | 'completed' | 'failed' | 'requires_review';
  physicsStatus: 'pending' | 'processing' | 'completed' | 'failed' | 'requires_review';
  
  // Agent outputs
  geometryAnalysis?: any;
  meshRecommendations?: any;
  materialAssignments?: any;
  physicsSetup?: any;
  
  // Workflow control
  currentStep: string;
  completedSteps: string[];
  progress: number; // 0-100
  
  // HITL checkpoints
  activeCheckpoint?: {
    checkpointId: string;
    checkpointType: string;
    description: string;
    checkpointData: any;
    agentRecommendations: string[];
    timeoutAt?: string;
  };
  
  // Quality metrics
  meshQualityMetrics?: {
    aspectRatio?: number;
    skewness?: number;
    orthogonalQuality?: number;
    overallScore?: number;
  };
  validationResults?: any;
  
  // UI state
  isProcessing: boolean;
  errors: Array<{ step: string; error: string; timestamp: string }>;
  warnings: Array<{ step: string; warning: string; timestamp: string }>;
  
  // Iteration tracking
  iterationCount: number;
  maxIterations: number;
}

export function useSimulationState(projectId: string) {
  const { state, setState } = useCoAgent<SimulationState>({
    name: "simulation-preprocessing",
    initialState: {
      projectId,
      userGoal: "",
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
      maxIterations: 3
    }
  });

  const updateSimulationState = (updates: Partial<SimulationState>) => {
    setState(prevState => ({
      ...prevState,
      ...updates,
      // Always update timestamp when state changes
      lastUpdated: new Date().toISOString()
    }));
  };

  const resetSimulationState = () => {
    setState({
      projectId,
      userGoal: "",
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
      maxIterations: 3
    });
  };

  const addError = (step: string, error: string) => {
    updateSimulationState({
      errors: [...state.errors, {
        step,
        error,
        timestamp: new Date().toISOString()
      }]
    });
  };

  const addWarning = (step: string, warning: string) => {
    updateSimulationState({
      warnings: [...state.warnings, {
        step,
        warning,
        timestamp: new Date().toISOString()
      }]
    });
  };

  const clearErrors = () => {
    updateSimulationState({ errors: [] });
  };

  const clearWarnings = () => {
    updateSimulationState({ warnings: [] });
  };

  return {
    simulationState: state,
    updateSimulationState,
    resetSimulationState,
    addError,
    addWarning,
    clearErrors,
    clearWarnings
  };
}
