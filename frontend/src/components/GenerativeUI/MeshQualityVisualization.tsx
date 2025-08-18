import React from 'react';
import { useSimulationState } from '../../hooks/useSimulationState';

interface MeshQualityVisualizationProps {
  projectId: string;
}

export function MeshQualityVisualization({ projectId }: MeshQualityVisualizationProps) {
  const { simulationState } = useSimulationState(projectId);
  const meshMetrics = simulationState.meshQualityMetrics;

  if (!meshMetrics) {
    return (
      <div className="bg-white p-6 rounded-lg shadow border">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">Mesh Quality Metrics</h3>
        <div className="text-center py-8 text-gray-500">
          <div className="text-4xl mb-2">📊</div>
          <div>Mesh quality metrics will appear here after mesh generation</div>
        </div>
      </div>
    );
  }

  const getQualityColor = (value: number, metric: string) => {
    switch (metric) {
      case 'aspectRatio':
      case 'orthogonalQuality':
        return value > 0.8 ? 'bg-green-500' : value > 0.6 ? 'bg-yellow-500' : 'bg-red-500';
      case 'skewness':
        return value < 0.2 ? 'bg-green-500' : value < 0.5 ? 'bg-yellow-500' : 'bg-red-500';
      case 'overallScore':
        return value > 8 ? 'bg-green-500' : value > 6 ? 'bg-yellow-500' : 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getQualityText = (value: number, metric: string) => {
    switch (metric) {
      case 'aspectRatio':
      case 'orthogonalQuality':
        return value > 0.8 ? 'Excellent' : value > 0.6 ? 'Good' : 'Needs Improvement';
      case 'skewness':
        return value < 0.2 ? 'Excellent' : value < 0.5 ? 'Good' : 'Needs Improvement';
      case 'overallScore':
        return value > 8 ? 'Excellent' : value > 6 ? 'Good' : 'Needs Improvement';
      default:
        return 'Unknown';
    }
  };

  const formatValue = (value: number | undefined, metric: string) => {
    if (value === undefined) return 'N/A';
    
    switch (metric) {
      case 'overallScore':
        return `${value.toFixed(1)}/10`;
      case 'aspectRatio':
      case 'orthogonalQuality':
        return value.toFixed(2);
      case 'skewness':
        return value.toFixed(3);
      default:
        return value.toFixed(2);
    }
  };

  const getProgressWidth = (value: number | undefined, metric: string) => {
    if (value === undefined) return 0;
    
    switch (metric) {
      case 'aspectRatio':
      case 'orthogonalQuality':
        return Math.min(value * 100, 100);
      case 'skewness':
        return Math.min((1 - value) * 100, 100);
      case 'overallScore':
        return Math.min(value * 10, 100);
      default:
        return 0;
    }
  };

  const metrics = [
    {
      key: 'aspectRatio',
      label: 'Aspect Ratio',
      value: meshMetrics.aspectRatio,
      description: 'Ratio of longest to shortest edge in elements'
    },
    {
      key: 'skewness',
      label: 'Skewness',
      value: meshMetrics.skewness,
      description: 'Measure of element distortion from ideal shape'
    },
    {
      key: 'orthogonalQuality',
      label: 'Orthogonal Quality',
      value: meshMetrics.orthogonalQuality,
      description: 'Measure of how close faces are to being perpendicular'
    },
    {
      key: 'overallScore',
      label: 'Overall Score',
      value: meshMetrics.overallScore,
      description: 'Combined quality score based on all metrics'
    }
  ];

  const overallQuality = meshMetrics.overallScore || 0;
  const qualityLevel = overallQuality > 8 ? 'excellent' : overallQuality > 6 ? 'good' : 'poor';

  return (
    <div className="bg-white p-6 rounded-lg shadow border">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Mesh Quality Metrics</h3>
        <div className={`px-3 py-1 rounded-full text-sm font-medium ${
          qualityLevel === 'excellent' ? 'bg-green-100 text-green-800' :
          qualityLevel === 'good' ? 'bg-yellow-100 text-yellow-800' :
          'bg-red-100 text-red-800'
        }`}>
          {getQualityText(overallQuality, 'overallScore')}
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {metrics.map((metric) => (
          <div key={metric.key} className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700">{metric.label}</span>
              <span className="text-sm font-semibold text-gray-900">
                {formatValue(metric.value, metric.key)}
              </span>
            </div>
            
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div 
                className={`h-3 rounded-full transition-all duration-500 ${getQualityColor(metric.value || 0, metric.key)}`}
                style={{ width: `${getProgressWidth(metric.value, metric.key)}%` }}
              />
            </div>
            
            <div className="text-xs text-gray-500">
              {metric.description}
            </div>
            
            <div className="text-xs font-medium">
              Status: <span className={`${
                getQualityText(metric.value || 0, metric.key) === 'Excellent' ? 'text-green-600' :
                getQualityText(metric.value || 0, metric.key) === 'Good' ? 'text-yellow-600' :
                'text-red-600'
              }`}>
                {getQualityText(metric.value || 0, metric.key)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Recommendations based on quality */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-900 mb-2">Quality Recommendations</h4>
        <div className="space-y-2 text-sm text-gray-600">
          {overallQuality < 6 && (
            <div className="flex items-start space-x-2">
              <span className="text-red-500">•</span>
              <span>Consider mesh refinement to improve quality before simulation</span>
            </div>
          )}
          {(meshMetrics.skewness || 0) > 0.5 && (
            <div className="flex items-start space-x-2">
              <span className="text-yellow-500">•</span>
              <span>High skewness detected - review element shapes in critical regions</span>
            </div>
          )}
          {(meshMetrics.aspectRatio || 0) < 0.6 && (
            <div className="flex items-start space-x-2">
              <span className="text-yellow-500">•</span>
              <span>Poor aspect ratio - consider adjusting element sizing</span>
            </div>
          )}
          {overallQuality >= 8 && (
            <div className="flex items-start space-x-2">
              <span className="text-green-500">•</span>
              <span>Excellent mesh quality - ready for high-accuracy simulation</span>
            </div>
          )}
        </div>
      </div>

      {/* Mesh statistics if available */}
      {simulationState.meshRecommendations && (
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="p-3 bg-blue-50 rounded">
            <div className="text-lg font-semibold text-blue-900">
              {simulationState.meshRecommendations.computational_cost_estimate?.element_count?.toLocaleString() || 'N/A'}
            </div>
            <div className="text-xs text-blue-600">Elements</div>
          </div>
          <div className="p-3 bg-green-50 rounded">
            <div className="text-lg font-semibold text-green-900">
              {simulationState.meshRecommendations.element_types?.primary || 'N/A'}
            </div>
            <div className="text-xs text-green-600">Element Type</div>
          </div>
          <div className="p-3 bg-purple-50 rounded">
            <div className="text-lg font-semibold text-purple-900">
              {simulationState.meshRecommendations.performance_optimization?.memory_estimate?.mesh_memory_gb?.toFixed(1) || 'N/A'}
            </div>
            <div className="text-xs text-purple-600">Memory (GB)</div>
          </div>
          <div className="p-3 bg-orange-50 rounded">
            <div className="text-lg font-semibold text-orange-900">
              {simulationState.meshRecommendations.performance_optimization?.runtime_estimate?.mesh_generation_minutes || 'N/A'}
            </div>
            <div className="text-xs text-orange-600">Est. Time (min)</div>
          </div>
        </div>
      )}
    </div>
  );
}
