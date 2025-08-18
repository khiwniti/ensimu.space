import React from 'react';
import { useSimulationState } from '../../hooks/useSimulationState';

interface SimulationProgressProps {
  projectId: string;
}

export function SimulationProgress({ projectId }: SimulationProgressProps) {
  const { simulationState } = useSimulationState(projectId);

  const steps = [
    { 
      key: 'geometry_processing', 
      label: 'Geometry Analysis', 
      status: simulationState.geometryStatus,
      description: 'Analyzing CAD geometry and preparing for meshing'
    },
    { 
      key: 'mesh_generation', 
      label: 'Mesh Generation', 
      status: simulationState.meshStatus,
      description: 'Creating computational mesh with quality control'
    },
    { 
      key: 'material_assignment', 
      label: 'Material Assignment', 
      status: simulationState.materialsStatus,
      description: 'Assigning material properties and validation'
    },
    { 
      key: 'physics_setup', 
      label: 'Physics Setup', 
      status: simulationState.physicsStatus,
      description: 'Configuring boundary conditions and solver settings'
    }
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return '✓';
      case 'processing':
        return '⟳';
      case 'failed':
        return '✗';
      case 'requires_review':
        return '!';
      default:
        return '';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500 text-white';
      case 'processing':
        return 'bg-blue-500 text-white animate-pulse';
      case 'failed':
        return 'bg-red-500 text-white';
      case 'requires_review':
        return 'bg-yellow-500 text-white';
      default:
        return 'bg-gray-200 text-gray-600';
    }
  };

  const getStepNumber = (index: number, status: string) => {
    if (status === 'completed' || status === 'processing' || status === 'failed' || status === 'requires_review') {
      return getStatusIcon(status);
    }
    return index + 1;
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg border">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Preprocessing Progress</h3>
        <div className="flex items-center space-x-2">
          <div className="text-sm text-gray-500">
            {simulationState.progress}% Complete
          </div>
          <div className="w-24 bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${simulationState.progress}%` }}
            />
          </div>
        </div>
      </div>
      
      <div className="space-y-4">
        {steps.map((step, index) => (
          <div key={step.key} className="flex items-start space-x-4">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${getStatusColor(step.status)}`}>
              {getStepNumber(index, step.status)}
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <div className="font-medium text-gray-900">{step.label}</div>
                <div className="text-sm text-gray-500 capitalize">
                  {step.status.replace('_', ' ')}
                </div>
              </div>
              <div className="text-sm text-gray-600 mt-1">
                {step.description}
              </div>
              
              {/* Show additional info for current step */}
              {simulationState.currentStep === step.key && simulationState.isProcessing && (
                <div className="mt-2 flex items-center space-x-2">
                  <div className="w-4 h-4">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                  </div>
                  <span className="text-sm text-blue-600">Processing...</span>
                </div>
              )}
              
              {/* Show iteration info if applicable */}
              {simulationState.iterationCount > 0 && simulationState.currentStep === step.key && (
                <div className="mt-2 text-xs text-orange-600">
                  Iteration {simulationState.iterationCount} of {simulationState.maxIterations}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Current step indicator */}
      {simulationState.currentStep && simulationState.currentStep !== 'initialization' && (
        <div className="mt-6 p-3 bg-blue-50 rounded border-l-4 border-blue-500">
          <div className="text-sm font-medium text-blue-800">
            Current Step: {simulationState.currentStep.replace('_', ' ').toUpperCase()}
          </div>
          {simulationState.isProcessing && (
            <div className="text-xs text-blue-600 mt-1">
              The AI agents are working on this step...
            </div>
          )}
        </div>
      )}

      {/* Workflow ID display */}
      {simulationState.workflowId && (
        <div className="mt-4 text-xs text-gray-500">
          Workflow ID: {simulationState.workflowId}
        </div>
      )}

      {/* Error display */}
      {simulationState.errors.length > 0 && (
        <div className="mt-4 p-3 bg-red-50 rounded border-l-4 border-red-500">
          <div className="text-sm font-medium text-red-800">
            {simulationState.errors.length} Error(s) Detected
          </div>
          <div className="mt-2 space-y-1">
            {simulationState.errors.slice(-3).map((error, index) => (
              <div key={index} className="text-xs text-red-600">
                {error.step}: {error.error}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Warning display */}
      {simulationState.warnings.length > 0 && (
        <div className="mt-4 p-3 bg-yellow-50 rounded border-l-4 border-yellow-500">
          <div className="text-sm font-medium text-yellow-800">
            {simulationState.warnings.length} Warning(s)
          </div>
          <div className="mt-2 space-y-1">
            {simulationState.warnings.slice(-3).map((warning, index) => (
              <div key={index} className="text-xs text-yellow-600">
                {warning.step}: {warning.warning}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
