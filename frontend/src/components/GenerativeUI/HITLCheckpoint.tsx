import React, { useState } from 'react';
import { useSimulationState } from '../../hooks/useSimulationState';
import { useWebSocketConnection } from '../../hooks/useWebSocketConnection';

interface HITLCheckpointProps {
  projectId: string;
  userId?: string;
}

export function HITLCheckpoint({ projectId, userId = 'anonymous' }: HITLCheckpointProps) {
  const { simulationState, updateSimulationState } = useSimulationState(projectId);
  const { sendHITLResponse } = useWebSocketConnection(projectId, userId);
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const checkpoint = simulationState.activeCheckpoint;

  if (!checkpoint) {
    return null;
  }

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      // Send via WebSocket for real-time response
      sendHITLResponse(checkpoint.checkpointId, true, feedback);
      
      // Also send via REST API for reliability
      const response = await fetch(
        `/api/workflows/${simulationState.workflowId}/checkpoints/${checkpoint.checkpointId}/respond`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            approved: true,
            feedback: feedback || undefined,
            reviewer_id: userId
          })
        }
      );

      if (response.ok) {
        updateSimulationState({
          activeCheckpoint: undefined,
          isProcessing: true
        });
        setFeedback('');
      } else {
        throw new Error('Failed to approve checkpoint');
      }
    } catch (error) {
      console.error('Error approving checkpoint:', error);
      alert('Failed to approve checkpoint. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!feedback.trim()) {
      alert('Please provide feedback when rejecting a checkpoint.');
      return;
    }

    setIsSubmitting(true);
    try {
      // Send via WebSocket for real-time response
      sendHITLResponse(checkpoint.checkpointId, false, feedback);
      
      // Also send via REST API for reliability
      const response = await fetch(
        `/api/workflows/${simulationState.workflowId}/checkpoints/${checkpoint.checkpointId}/respond`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            approved: false,
            feedback,
            reviewer_id: userId
          })
        }
      );

      if (response.ok) {
        updateSimulationState({
          activeCheckpoint: undefined,
          isProcessing: true
        });
        setFeedback('');
      } else {
        throw new Error('Failed to reject checkpoint');
      }
    } catch (error) {
      console.error('Error rejecting checkpoint:', error);
      alert('Failed to reject checkpoint. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatTimeRemaining = (timeoutAt?: string) => {
    if (!timeoutAt) return null;
    
    const timeout = new Date(timeoutAt);
    const now = new Date();
    const remaining = timeout.getTime() - now.getTime();
    
    if (remaining <= 0) return 'Expired';
    
    const minutes = Math.floor(remaining / (1000 * 60));
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m remaining`;
    } else {
      return `${minutes}m remaining`;
    }
  };

  const getCheckpointIcon = (type: string) => {
    switch (type) {
      case 'preprocessing_review':
        return '🔍';
      case 'geometry_validation':
        return '📐';
      case 'mesh_approval':
        return '🕸️';
      case 'material_review':
        return '🧱';
      case 'physics_validation':
        return '⚡';
      default:
        return '❓';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <span className="text-2xl">{getCheckpointIcon(checkpoint.checkpointType)}</span>
              <div>
                <h2 className="text-xl font-semibold text-gray-900">Human Review Required</h2>
                <p className="text-sm text-gray-600">{checkpoint.description}</p>
              </div>
            </div>
            {checkpoint.timeoutAt && (
              <div className="text-sm text-orange-600 font-medium">
                {formatTimeRemaining(checkpoint.timeoutAt)}
              </div>
            )}
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Agent Recommendations */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">AI Agent Recommendations</h3>
            <div className="bg-blue-50 rounded-lg p-4">
              <ul className="space-y-2">
                {checkpoint.agentRecommendations.map((recommendation, index) => (
                  <li key={index} className="flex items-start space-x-2">
                    <span className="text-blue-500 mt-1">•</span>
                    <span className="text-sm text-blue-800">{recommendation}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Checkpoint Data Summary */}
          {checkpoint.checkpointData && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">Preprocessing Summary</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {checkpoint.checkpointData.geometry_analysis && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">Geometry Analysis</h4>
                    <div className="text-sm text-gray-600">
                      <div>Confidence: {(checkpoint.checkpointData.geometry_analysis.confidence_score * 100).toFixed(1)}%</div>
                      <div>Issues Found: {checkpoint.checkpointData.geometry_analysis.potential_issues?.length || 0}</div>
                    </div>
                  </div>
                )}

                {checkpoint.checkpointData.mesh_recommendations && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">Mesh Strategy</h4>
                    <div className="text-sm text-gray-600">
                      <div>Quality Score: {checkpoint.checkpointData.quality_metrics?.mesh_quality?.predicted_quality_score?.toFixed(1) || 'N/A'}</div>
                      <div>Element Type: {checkpoint.checkpointData.mesh_recommendations.element_types?.primary || 'N/A'}</div>
                    </div>
                  </div>
                )}

                {checkpoint.checkpointData.material_assignments && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">Material Assignment</h4>
                    <div className="text-sm text-gray-600">
                      <div>Confidence: {(checkpoint.checkpointData.material_assignments.confidence_score * 100).toFixed(1)}%</div>
                      <div>Materials: {checkpoint.checkpointData.material_assignments.material_recommendations?.length || 0}</div>
                    </div>
                  </div>
                )}

                {checkpoint.checkpointData.physics_setup && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">Physics Setup</h4>
                    <div className="text-sm text-gray-600">
                      <div>Confidence: {(checkpoint.checkpointData.physics_setup.confidence_score * 100).toFixed(1)}%</div>
                      <div>Boundary Conditions: {Object.keys(checkpoint.checkpointData.physics_setup.boundary_conditions || {}).length}</div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Validation Results */}
          {checkpoint.checkpointData?.validation_results && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">Validation Results</h3>
              <div className={`rounded-lg p-4 ${
                checkpoint.checkpointData.validation_results.overall_status === 'passed' 
                  ? 'bg-green-50 border border-green-200' 
                  : 'bg-red-50 border border-red-200'
              }`}>
                <div className="flex items-center space-x-2 mb-2">
                  <span className={`text-lg ${
                    checkpoint.checkpointData.validation_results.overall_status === 'passed' 
                      ? 'text-green-500' 
                      : 'text-red-500'
                  }`}>
                    {checkpoint.checkpointData.validation_results.overall_status === 'passed' ? '✅' : '❌'}
                  </span>
                  <span className={`font-medium ${
                    checkpoint.checkpointData.validation_results.overall_status === 'passed' 
                      ? 'text-green-800' 
                      : 'text-red-800'
                  }`}>
                    Overall Status: {checkpoint.checkpointData.validation_results.overall_status}
                  </span>
                </div>
                
                {checkpoint.checkpointData.validation_results.errors?.length > 0 && (
                  <div className="mt-2">
                    <div className="text-sm font-medium text-red-800 mb-1">Errors:</div>
                    <ul className="text-sm text-red-700 space-y-1">
                      {checkpoint.checkpointData.validation_results.errors.map((error: string, index: number) => (
                        <li key={index}>• {error}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {checkpoint.checkpointData.validation_results.warnings?.length > 0 && (
                  <div className="mt-2">
                    <div className="text-sm font-medium text-yellow-800 mb-1">Warnings:</div>
                    <ul className="text-sm text-yellow-700 space-y-1">
                      {checkpoint.checkpointData.validation_results.warnings.map((warning: string, index: number) => (
                        <li key={index}>• {warning}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Feedback Section */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">Your Feedback</h3>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Provide feedback or specific instructions for the AI agents..."
              className="w-full h-24 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            />
            <div className="text-sm text-gray-500 mt-1">
              Optional: Provide specific feedback to guide the AI agents if changes are needed.
            </div>
          </div>
        </div>

        <div className="p-6 border-t border-gray-200 flex justify-end space-x-3">
          <button
            onClick={handleReject}
            disabled={isSubmitting}
            className="px-6 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Processing...' : 'Request Changes'}
          </button>
          <button
            onClick={handleApprove}
            disabled={isSubmitting}
            className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Processing...' : 'Approve & Continue'}
          </button>
        </div>
      </div>
    </div>
  );
}
