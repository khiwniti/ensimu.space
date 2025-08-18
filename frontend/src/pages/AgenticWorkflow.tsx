import React, { useState, useEffect } from 'react';
import { useSimulationActions } from '../hooks/useSimulationActions';
import { useSimulationContext } from '../hooks/useSimulationContext';
import { useWebSocketConnection } from '../hooks/useWebSocketConnection';
import { SimulationProgress } from '../components/GenerativeUI/SimulationProgress';
import { MeshQualityVisualization } from '../components/GenerativeUI/MeshQualityVisualization';
import { HITLCheckpoint } from '../components/GenerativeUI/HITLCheckpoint';

export default function AgenticWorkflow() {
  const [projectId] = useState('demo-project-001'); // In real app, get from URL params or context
  const [userId] = useState('demo-user'); // In real app, get from auth context

  const { simulationState, isUploading } = useSimulationActions(projectId);
  const { isReady, canStartWorkflow, needsAttention } = useSimulationContext(projectId);
  const { isConnected, connectionError } = useWebSocketConnection(projectId, userId);

  const [userGoal, setUserGoal] = useState('');
  const [physicsType, setPhysicsType] = useState<'cfd' | 'structural' | 'thermal' | 'electromagnetic' | 'multi_physics'>('cfd');

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">AI-Powered Simulation Preprocessing</h1>
              <p className="text-sm text-gray-600 mt-1">
                Intelligent workflow orchestration with LangGraph and CopilotKit
              </p>
            </div>

            {/* Connection Status */}
            <div className="flex items-center space-x-4">
              <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-sm ${
                isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              }`}>
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
              </div>

              {needsAttention && (
                <div className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-medium animate-pulse">
                  Attention Required
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Controls and Setup */}
          <div className="lg:col-span-1 space-y-6">
            {/* Project Setup */}
            <div className="bg-white p-6 rounded-lg shadow border">
              <h3 className="text-lg font-semibold mb-4 text-gray-900">Project Setup</h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Simulation Goal
                  </label>
                  <textarea
                    value={userGoal}
                    onChange={(e) => setUserGoal(e.target.value)}
                    placeholder="Describe your simulation objectives..."
                    className="w-full h-20 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Physics Type
                  </label>
                  <select
                    value={physicsType}
                    onChange={(e) => setPhysicsType(e.target.value as any)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="cfd">Computational Fluid Dynamics</option>
                    <option value="structural">Structural Analysis</option>
                    <option value="thermal">Thermal Analysis</option>
                    <option value="electromagnetic">Electromagnetic</option>
                    <option value="multi_physics">Multi-Physics</option>
                  </select>
                </div>
              </div>
            </div>

            {/* File Upload */}
            <div className="bg-white p-6 rounded-lg shadow border">
              <h3 className="text-lg font-semibold mb-4 text-gray-900">CAD Files</h3>

              <div className="space-y-4">
                {simulationState.cadFiles.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <div className="text-4xl mb-2">📁</div>
                    <div>No CAD files uploaded yet</div>
                    <div className="text-sm">Upload STEP, IGES, or STL files to begin</div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {simulationState.cadFiles.map((file) => (
                      <div key={file.id} className="flex items-center justify-between p-3 bg-gray-50 rounded border">
                        <div className="flex items-center space-x-3">
                          <div className={`w-3 h-3 rounded-full ${
                            file.uploadStatus === 'completed' ? 'bg-green-500' :
                            file.uploadStatus === 'uploading' ? 'bg-blue-500 animate-pulse' :
                            file.uploadStatus === 'failed' ? 'bg-red-500' :
                            'bg-gray-400'
                          }`} />
                          <div>
                            <div className="text-sm font-medium text-gray-900">{file.filename}</div>
                            <div className="text-xs text-gray-500">{file.fileType}</div>
                          </div>
                        </div>
                        <div className="text-xs text-gray-500 capitalize">
                          {file.uploadStatus.replace('_', ' ')}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {isUploading && (
                  <div className="text-center py-4">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
                    <div className="text-sm text-gray-600 mt-2">Uploading file...</div>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-white p-6 rounded-lg shadow border">
              <h3 className="text-lg font-semibold mb-4 text-gray-900">Quick Actions</h3>

              <div className="space-y-3">
                <button
                  disabled={!canStartWorkflow || !userGoal.trim()}
                  className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  {simulationState.isProcessing ? 'Processing...' : 'Start AI Preprocessing'}
                </button>

                <button
                  disabled={simulationState.isProcessing}
                  className="w-full px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Upload CAD File
                </button>

                {simulationState.workflowId && (
                  <button
                    className="w-full px-4 py-2 border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 focus:ring-2 focus:ring-blue-500"
                  >
                    Check Status
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Right Column - Progress and Visualizations */}
          <div className="lg:col-span-2 space-y-6">
            {/* Simulation Progress */}
            <SimulationProgress projectId={projectId} />

            {/* Mesh Quality Visualization */}
            <MeshQualityVisualization projectId={projectId} />

            {/* Agent Outputs Summary */}
            {(simulationState.geometryAnalysis || simulationState.meshRecommendations ||
              simulationState.materialAssignments || simulationState.physicsSetup) && (
              <div className="bg-white p-6 rounded-lg shadow border">
                <h3 className="text-lg font-semibold mb-4 text-gray-900">AI Agent Results</h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {simulationState.geometryAnalysis && (
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <h4 className="font-medium text-blue-900 mb-2">Geometry Analysis</h4>
                      <div className="text-sm text-blue-800">
                        <div>Confidence: {(simulationState.geometryAnalysis.confidence_score * 100).toFixed(1)}%</div>
                        <div>Issues: {simulationState.geometryAnalysis.potential_issues?.length || 0}</div>
                      </div>
                    </div>
                  )}

                  {simulationState.meshRecommendations && (
                    <div className="p-4 bg-green-50 rounded-lg">
                      <h4 className="font-medium text-green-900 mb-2">Mesh Strategy</h4>
                      <div className="text-sm text-green-800">
                        <div>Confidence: {(simulationState.meshRecommendations.confidence_score * 100).toFixed(1)}%</div>
                        <div>Strategy: {simulationState.meshRecommendations.mesh_strategy?.approach || 'N/A'}</div>
                      </div>
                    </div>
                  )}

                  {simulationState.materialAssignments && (
                    <div className="p-4 bg-purple-50 rounded-lg">
                      <h4 className="font-medium text-purple-900 mb-2">Material Assignment</h4>
                      <div className="text-sm text-purple-800">
                        <div>Confidence: {(simulationState.materialAssignments.confidence_score * 100).toFixed(1)}%</div>
                        <div>Materials: {simulationState.materialAssignments.material_recommendations?.length || 0}</div>
                      </div>
                    </div>
                  )}

                  {simulationState.physicsSetup && (
                    <div className="p-4 bg-orange-50 rounded-lg">
                      <h4 className="font-medium text-orange-900 mb-2">Physics Setup</h4>
                      <div className="text-sm text-orange-800">
                        <div>Confidence: {(simulationState.physicsSetup.confidence_score * 100).toFixed(1)}%</div>
                        <div>BC Count: {Object.keys(simulationState.physicsSetup.boundary_conditions || {}).length}</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* HITL Checkpoint Modal */}
      <HITLCheckpoint projectId={projectId} userId={userId} />

      {/* Connection Error Toast */}
      {connectionError && (
        <div className="fixed bottom-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded shadow-lg">
          <div className="flex items-center space-x-2">
            <span className="text-red-500">⚠️</span>
            <span className="text-sm">{connectionError}</span>
          </div>
        </div>
      )}
    </div>
  );
}