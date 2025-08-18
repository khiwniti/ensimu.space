import { useCopilotReadable } from "@copilotkit/react-core";
import { useSimulationState } from "./useSimulationState";

export function useSimulationContext(projectId: string) {
  const { simulationState } = useSimulationState(projectId);

  // Make simulation state readable by the agent
  useCopilotReadable({
    description: "Current simulation preprocessing state and progress",
    value: {
      projectId: simulationState.projectId,
      workflowId: simulationState.workflowId,
      userGoal: simulationState.userGoal,
      physicsType: simulationState.physicsType,
      currentStep: simulationState.currentStep,
      progress: simulationState.progress,
      isProcessing: simulationState.isProcessing,
      
      // Status of each preprocessing step
      geometryStatus: simulationState.geometryStatus,
      meshStatus: simulationState.meshStatus,
      materialsStatus: simulationState.materialsStatus,
      physicsStatus: simulationState.physicsStatus,
      
      // Completed and failed steps
      completedSteps: simulationState.completedSteps,
      errors: simulationState.errors,
      warnings: simulationState.warnings,
      
      // Iteration tracking
      iterationCount: simulationState.iterationCount,
      maxIterations: simulationState.maxIterations,
      
      // Active checkpoint information
      activeCheckpoint: simulationState.activeCheckpoint
    }
  });

  // Make project context readable
  useCopilotReadable({
    description: "Current project information and uploaded files",
    value: {
      projectId: simulationState.projectId,
      cadFiles: simulationState.cadFiles.map(file => ({
        id: file.id,
        filename: file.filename,
        fileType: file.fileType,
        uploadStatus: file.uploadStatus,
        hasAnalysisResults: !!file.analysisResults
      })),
      totalFiles: simulationState.cadFiles.length,
      completedUploads: simulationState.cadFiles.filter(f => f.uploadStatus === 'completed').length,
      failedUploads: simulationState.cadFiles.filter(f => f.uploadStatus === 'failed').length
    }
  });

  // Make agent outputs readable
  useCopilotReadable({
    description: "Results from AI agents in the preprocessing workflow",
    value: {
      geometryAnalysis: simulationState.geometryAnalysis ? {
        hasResults: true,
        confidence: simulationState.geometryAnalysis.confidence_score,
        recommendations: simulationState.geometryAnalysis.recommendations,
        issues: simulationState.geometryAnalysis.potential_issues
      } : { hasResults: false },
      
      meshRecommendations: simulationState.meshRecommendations ? {
        hasResults: true,
        confidence: simulationState.meshRecommendations.confidence_score,
        strategy: simulationState.meshRecommendations.mesh_strategy,
        qualityTargets: simulationState.meshRecommendations.quality_targets
      } : { hasResults: false },
      
      materialAssignments: simulationState.materialAssignments ? {
        hasResults: true,
        confidence: simulationState.materialAssignments.confidence_score,
        materials: simulationState.materialAssignments.material_recommendations,
        validation: simulationState.materialAssignments.validation_results
      } : { hasResults: false },
      
      physicsSetup: simulationState.physicsSetup ? {
        hasResults: true,
        confidence: simulationState.physicsSetup.confidence_score,
        boundaryConditions: simulationState.physicsSetup.boundary_conditions,
        solverConfig: simulationState.physicsSetup.solver_configuration
      } : { hasResults: false }
    }
  });

  // Make quality metrics readable
  useCopilotReadable({
    description: "Current mesh quality metrics and validation results",
    value: {
      meshQuality: simulationState.meshQualityMetrics ? {
        aspectRatio: simulationState.meshQualityMetrics.aspectRatio,
        skewness: simulationState.meshQualityMetrics.skewness,
        orthogonalQuality: simulationState.meshQualityMetrics.orthogonalQuality,
        overallScore: simulationState.meshQualityMetrics.overallScore,
        hasQualityIssues: (simulationState.meshQualityMetrics.overallScore || 0) < 7
      } : { hasMetrics: false },
      
      validationResults: simulationState.validationResults ? {
        overallStatus: simulationState.validationResults.overall_status,
        componentValidations: simulationState.validationResults.component_validations,
        hasIssues: simulationState.validationResults.overall_status !== 'passed',
        errorCount: simulationState.validationResults.errors?.length || 0,
        warningCount: simulationState.validationResults.warnings?.length || 0
      } : { hasResults: false }
    }
  });

  // Make workflow status readable for agent decision making
  useCopilotReadable({
    description: "Workflow execution status and next steps",
    value: {
      canStartWorkflow: simulationState.cadFiles.length > 0 && !simulationState.isProcessing,
      canUploadFiles: !simulationState.isProcessing,
      needsHumanInput: !!simulationState.activeCheckpoint,
      hasErrors: simulationState.errors.length > 0,
      hasWarnings: simulationState.warnings.length > 0,
      isStuck: simulationState.iterationCount >= simulationState.maxIterations,
      
      nextRecommendedAction: getNextRecommendedAction(simulationState),
      availableActions: getAvailableActions(simulationState)
    }
  });

  return {
    simulationState,
    isReady: simulationState.cadFiles.length > 0,
    canStartWorkflow: simulationState.cadFiles.length > 0 && !simulationState.isProcessing,
    needsAttention: !!simulationState.activeCheckpoint || simulationState.errors.length > 0
  };
}

function getNextRecommendedAction(state: any): string {
  if (state.activeCheckpoint) {
    return "Review and respond to the current checkpoint";
  }
  
  if (state.errors.length > 0) {
    return "Review and resolve workflow errors";
  }
  
  if (state.cadFiles.length === 0) {
    return "Upload CAD files to begin preprocessing";
  }
  
  if (!state.isProcessing && state.completedSteps.length === 0) {
    return "Start the preprocessing workflow";
  }
  
  if (state.isProcessing) {
    return "Wait for current step to complete";
  }
  
  if (state.completedSteps.length === 4) {
    return "Preprocessing complete - ready for simulation";
  }
  
  return "Continue with preprocessing workflow";
}

function getAvailableActions(state: any): string[] {
  const actions = [];
  
  if (!state.isProcessing) {
    actions.push("upload_cad_file");
  }
  
  if (state.cadFiles.length > 0 && !state.isProcessing && state.completedSteps.length === 0) {
    actions.push("start_preprocessing_workflow");
  }
  
  if (state.workflowId) {
    actions.push("get_workflow_status");
  }
  
  if (state.activeCheckpoint) {
    actions.push("respond_to_checkpoint");
  }
  
  if (state.cadFiles.length > 0) {
    actions.push("analyze_geometry");
  }
  
  return actions;
}
