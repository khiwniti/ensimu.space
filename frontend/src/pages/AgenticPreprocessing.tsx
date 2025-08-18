import React, { useState } from 'react';
import { CopilotTextarea } from "@copilotkit/react-textarea";
import { useSimulationActions } from '../hooks/useSimulationActions';
import { useSimulationContext } from '../hooks/useSimulationContext';
import { SimulationProgress } from '../components/GenerativeUI/SimulationProgress';
import { HITLCheckpoint } from '../components/GenerativeUI/HITLCheckpoint';

export default function AgenticPreprocessing() {
  const [projectId] = useState('preprocessing-demo'); // In real app, get from URL params
  const [userId] = useState('demo-user'); // In real app, get from auth context

  const { simulationState } = useSimulationActions(projectId);
  const { isReady, canStartWorkflow, needsAttention } = useSimulationContext(projectId);

  const [instructions, setInstructions] = useState('');

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <h1 className="text-3xl font-bold text-gray-900">AI Simulation Preprocessing</h1>
            <p className="text-gray-600 mt-2">
              Intelligent preprocessing with conversational AI assistance
            </p>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - Chat Interface */}
          <div className="space-y-6">
            {/* Instructions Panel */}
            <div className="bg-white p-6 rounded-lg shadow border">
              <h3 className="text-lg font-semibold mb-4 text-gray-900">
                Describe Your Simulation
              </h3>

              <CopilotTextarea
                className="w-full h-40 p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                value={instructions}
                onValueChange={setInstructions}
                placeholder="Describe your simulation goals, geometry, physics requirements, and any specific constraints..."
                autosuggestionsConfig={{
                  textareaPurpose: "Simulation preprocessing instructions",
                  chatApiConfigs: {
                    suggestionsApiConfig: {
                      forwardedParams: {
                        max_tokens: 20,
                        stop: [".", "!", "?", ";", ":", "\n"],
                      },
                    },
                  },
                }}
              />

              <div className="mt-4 text-sm text-gray-600">
                <p className="mb-2">💡 <strong>Tips:</strong></p>
                <ul className="space-y-1 text-xs">
                  <li>• Describe the physical phenomenon you want to simulate</li>
                  <li>• Mention material properties if known</li>
                  <li>• Specify boundary conditions and operating conditions</li>
                  <li>• Include accuracy requirements or computational constraints</li>
                </ul>
              </div>
            </div>

            {/* Current Status */}
            <div className="bg-white p-6 rounded-lg shadow border">
              <h3 className="text-lg font-semibold mb-4 text-gray-900">Current Status</h3>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Project Ready</span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    isReady ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {isReady ? 'Yes' : 'No'}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Can Start Workflow</span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    canStartWorkflow ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {canStartWorkflow ? 'Ready' : 'Waiting'}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Needs Attention</span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    needsAttention ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                  }`}>
                    {needsAttention ? 'Yes' : 'No'}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Processing</span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    simulationState.isProcessing ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {simulationState.isProcessing ? 'Active' : 'Idle'}
                  </span>
                </div>
              </div>
            </div>

            {/* File Management */}
            <div className="bg-white p-6 rounded-lg shadow border">
              <h3 className="text-lg font-semibold mb-4 text-gray-900">CAD Files</h3>

              {simulationState.cadFiles.length === 0 ? (
                <div className="text-center py-6 text-gray-500">
                  <div className="text-3xl mb-2">📁</div>
                  <p className="text-sm">No files uploaded</p>
                  <p className="text-xs mt-1">Ask the AI assistant to help you upload files</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {simulationState.cadFiles.map((file) => (
                    <div key={file.id} className="flex items-center space-x-3 p-3 bg-gray-50 rounded">
                      <div className={`w-2 h-2 rounded-full ${
                        file.uploadStatus === 'completed' ? 'bg-green-500' :
                        file.uploadStatus === 'uploading' ? 'bg-blue-500 animate-pulse' :
                        file.uploadStatus === 'failed' ? 'bg-red-500' :
                        'bg-gray-400'
                      }`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{file.filename}</p>
                        <p className="text-xs text-gray-500">{file.fileType}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Column - Progress and Results */}
          <div className="space-y-6">
            {/* Simulation Progress */}
            <SimulationProgress projectId={projectId} />

            {/* Quick Stats */}
            <div className="bg-white p-6 rounded-lg shadow border">
              <h3 className="text-lg font-semibold mb-4 text-gray-900">Quick Stats</h3>

              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-3 bg-blue-50 rounded">
                  <div className="text-2xl font-bold text-blue-900">
                    {simulationState.completedSteps.length}
                  </div>
                  <div className="text-xs text-blue-600">Steps Completed</div>
                </div>

                <div className="text-center p-3 bg-green-50 rounded">
                  <div className="text-2xl font-bold text-green-900">
                    {simulationState.progress.toFixed(0)}%
                  </div>
                  <div className="text-xs text-green-600">Progress</div>
                </div>

                <div className="text-center p-3 bg-purple-50 rounded">
                  <div className="text-2xl font-bold text-purple-900">
                    {simulationState.cadFiles.length}
                  </div>
                  <div className="text-xs text-purple-600">CAD Files</div>
                </div>

                <div className="text-center p-3 bg-orange-50 rounded">
                  <div className="text-2xl font-bold text-orange-900">
                    {simulationState.iterationCount}
                  </div>
                  <div className="text-xs text-orange-600">Iterations</div>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="bg-white p-6 rounded-lg shadow border">
              <h3 className="text-lg font-semibold mb-4 text-gray-900">Recent Activity</h3>

              <div className="space-y-3">
                {simulationState.errors.length === 0 && simulationState.warnings.length === 0 &&
                 simulationState.completedSteps.length === 0 ? (
                  <div className="text-center py-4 text-gray-500">
                    <div className="text-2xl mb-2">🚀</div>
                    <p className="text-sm">Ready to start preprocessing</p>
                  </div>
                ) : (
                  <>
                    {/* Show completed steps */}
                    {simulationState.completedSteps.map((step, index) => (
                      <div key={index} className="flex items-center space-x-3">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="text-sm text-gray-700">
                          Completed: {step.replace('_', ' ')}
                        </span>
                      </div>
                    ))}

                    {/* Show recent errors */}
                    {simulationState.errors.slice(-3).map((error, index) => (
                      <div key={index} className="flex items-center space-x-3">
                        <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                        <span className="text-sm text-red-700">
                          Error in {error.step}: {error.error}
                        </span>
                      </div>
                    ))}

                    {/* Show recent warnings */}
                    {simulationState.warnings.slice(-3).map((warning, index) => (
                      <div key={index} className="flex items-center space-x-3">
                        <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                        <span className="text-sm text-yellow-700">
                          Warning in {warning.step}: {warning.warning}
                        </span>
                      </div>
                    ))}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* HITL Checkpoint Modal */}
      <HITLCheckpoint projectId={projectId} userId={userId} />
    </div>
  );
}