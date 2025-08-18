import React, { useState, useEffect } from 'react';
import { useSimulationState } from '../hooks/useSimulationState';
import { SimPrepCADViewer } from './SimPrepCADViewer';
import { ThreeDViewer } from './ThreeDViewer';

interface EnhancedSimulationDashboardProps {
  projectId: string;
}

export function EnhancedSimulationDashboard({ projectId }: EnhancedSimulationDashboardProps) {
  const { simulationState, updateSimulationState } = useSimulationState(projectId);
  const [activeView, setActiveView] = useState<'geometry' | 'mesh' | 'materials' | 'physics'>('geometry');

  const handleFileUpload = async (files: FileList) => {
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const newFile = {
        id: `file-${Date.now()}-${i}`,
        filename: file.name,
        fileType: file.type || 'application/octet-stream',
        uploadStatus: 'uploading' as const
      };

      // Add file to state
      updateSimulationState({
        cadFiles: [...simulationState.cadFiles, newFile]
      });

      // Simulate upload process
      setTimeout(() => {
        updateSimulationState({
          cadFiles: simulationState.cadFiles.map(f => 
            f.id === newFile.id ? { ...f, uploadStatus: 'completed' } : f
          )
        });
      }, 2000);
    }
  };

  const preprocessingSteps = [
    { 
      key: 'geometry', 
      label: 'Geometry Analysis', 
      status: simulationState.geometryStatus,
      description: 'CAD geometry validation and repair'
    },
    { 
      key: 'mesh', 
      label: 'Mesh Generation', 
      status: simulationState.meshStatus,
      description: 'Computational mesh creation and quality check'
    },
    { 
      key: 'materials', 
      label: 'Material Assignment', 
      status: simulationState.materialsStatus,
      description: 'Material properties and boundary conditions'
    },
    { 
      key: 'physics', 
      label: 'Physics Setup', 
      status: simulationState.physicsStatus,
      description: 'Solver configuration and physics models'
    }
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500';
      case 'processing': return 'bg-blue-500 animate-pulse';
      case 'failed': return 'bg-red-500';
      case 'requires_review': return 'bg-yellow-500';
      default: return 'bg-gray-300';
    }
  };

  return (
    <div className="space-y-6">
      {/* File Upload Section */}
      <div className="bg-white p-6 rounded-lg shadow border">
        <h3 className="text-lg font-semibold mb-4">CAD File Management</h3>
        
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
          <input
            type="file"
            multiple
            accept=".step,.stp,.iges,.igs,.stl,.obj,.3mf"
            onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
            className="hidden"
            id="file-upload"
          />
          <label htmlFor="file-upload" className="cursor-pointer">
            <div className="text-4xl mb-2">📁</div>
            <p className="text-lg font-medium text-gray-700">Drop CAD files here or click to browse</p>
            <p className="text-sm text-gray-500 mt-1">
              Supports: STEP, IGES, STL, OBJ, 3MF files
            </p>
          </label>
        </div>

        {/* File List */}
        {simulationState.cadFiles.length > 0 && (
          <div className="mt-6">
            <h4 className="font-medium mb-3">Uploaded Files</h4>
            <div className="space-y-2">
              {simulationState.cadFiles.map((file) => (
                <div key={file.id} className="flex items-center space-x-3 p-3 bg-gray-50 rounded border">
                  <div className={`w-3 h-3 rounded-full ${getStatusColor(file.uploadStatus)}`} />
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{file.filename}</p>
                    <p className="text-sm text-gray-600">{file.fileType}</p>
                  </div>
                  <div className="text-sm text-gray-500 capitalize">
                    {file.uploadStatus.replace('_', ' ')}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Preprocessing Steps */}
      <div className="bg-white p-6 rounded-lg shadow border">
        <h3 className="text-lg font-semibold mb-4">Preprocessing Pipeline</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          {preprocessingSteps.map((step, index) => (
            <button
              key={step.key}
              onClick={() => setActiveView(step.key as any)}
              className={`p-4 rounded-lg border text-left transition-colors ${
                activeView === step.key 
                  ? 'border-blue-500 bg-blue-50' 
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center space-x-3 mb-2">
                <div className={`w-4 h-4 rounded-full ${getStatusColor(step.status)}`} />
                <span className="font-medium">{step.label}</span>
              </div>
              <p className="text-sm text-gray-600">{step.description}</p>
              <div className="mt-2 text-xs text-gray-500 capitalize">
                Status: {step.status.replace('_', ' ')}
              </div>
            </button>
          ))}
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Overall Progress</span>
            <span>{simulationState.progress.toFixed(0)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
              style={{ width: `${simulationState.progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Detailed View Based on Active Tab */}
      <div className="bg-white p-6 rounded-lg shadow border">
        <h3 className="text-lg font-semibold mb-4 capitalize">{activeView} Details</h3>
        
        {activeView === 'geometry' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-3">Geometry Analysis Results</h4>
              {simulationState.geometryAnalysis ? (
                <div className="space-y-3">
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-sm font-medium">Volume: {simulationState.geometryAnalysis.volume || 'N/A'}</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-sm font-medium">Surface Area: {simulationState.geometryAnalysis.surfaceArea || 'N/A'}</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-sm font-medium">Quality Score: {simulationState.geometryAnalysis.qualityScore || 'N/A'}</p>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500">No analysis data available. Upload CAD files to begin.</p>
              )}
            </div>
            <div>
              <SimPrepCADViewer cadFiles={simulationState.cadFiles} />
            </div>
          </div>
        )}

        {activeView === 'mesh' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-3">Mesh Quality Metrics</h4>
              {simulationState.meshQualityMetrics ? (
                <div className="space-y-3">
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-sm font-medium">Aspect Ratio: {simulationState.meshQualityMetrics.aspectRatio?.toFixed(2) || 'N/A'}</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-sm font-medium">Skewness: {simulationState.meshQualityMetrics.skewness?.toFixed(2) || 'N/A'}</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-sm font-medium">Orthogonal Quality: {simulationState.meshQualityMetrics.orthogonalQuality?.toFixed(2) || 'N/A'}</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded">
                    <p className="text-sm font-medium">Overall Score: {simulationState.meshQualityMetrics.overallScore?.toFixed(1) || 'N/A'}/10</p>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500">Mesh generation not started.</p>
              )}
            </div>
            <div>
              <ThreeDViewer type="mesh" data={simulationState.meshRecommendations} />
            </div>
          </div>
        )}

        {activeView === 'materials' && (
          <div>
            <h4 className="font-medium mb-3">Material Properties</h4>
            {simulationState.materialAssignments ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Material assignments would be displayed here */}
                <div className="p-4 border rounded">
                  <h5 className="font-medium">Default Material</h5>
                  <p className="text-sm text-gray-600">Steel (Generic)</p>
                </div>
              </div>
            ) : (
              <p className="text-gray-500">Material assignment not configured.</p>
            )}
          </div>
        )}

        {activeView === 'physics' && (
          <div>
            <h4 className="font-medium mb-3">Physics Configuration</h4>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Physics Type
                </label>
                <select 
                  value={simulationState.physicsType}
                  onChange={(e) => updateSimulationState({ 
                    physicsType: e.target.value as any 
                  })}
                  className="w-full p-2 border border-gray-300 rounded-lg"
                >
                  <option value="cfd">Computational Fluid Dynamics (CFD)</option>
                  <option value="structural">Structural Analysis</option>
                  <option value="thermal">Thermal Analysis</option>
                  <option value="electromagnetic">Electromagnetic</option>
                  <option value="multi_physics">Multi-Physics</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Simulation Goal
                </label>
                <textarea
                  value={simulationState.userGoal}
                  onChange={(e) => updateSimulationState({ userGoal: e.target.value })}
                  placeholder="Describe what you want to achieve with this simulation..."
                  className="w-full p-3 border border-gray-300 rounded-lg h-24 resize-none"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Error and Warning Display */}
      {(simulationState.errors.length > 0 || simulationState.warnings.length > 0) && (
        <div className="bg-white p-6 rounded-lg shadow border">
          <h3 className="text-lg font-semibold mb-4">Issues & Notifications</h3>
          
          {simulationState.errors.length > 0 && (
            <div className="mb-4">
              <h4 className="font-medium text-red-700 mb-2">Errors</h4>
              <div className="space-y-2">
                {simulationState.errors.map((error, index) => (
                  <div key={index} className="p-3 bg-red-50 border border-red-200 rounded">
                    <p className="text-sm text-red-800">{error.error}</p>
                    <p className="text-xs text-red-600 mt-1">Step: {error.step}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {simulationState.warnings.length > 0 && (
            <div>
              <h4 className="font-medium text-yellow-700 mb-2">Warnings</h4>
              <div className="space-y-2">
                {simulationState.warnings.map((warning, index) => (
                  <div key={index} className="p-3 bg-yellow-50 border border-yellow-200 rounded">
                    <p className="text-sm text-yellow-800">{warning.warning}</p>
                    <p className="text-xs text-yellow-600 mt-1">Step: {warning.step}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}