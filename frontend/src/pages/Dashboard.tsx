import React, { useState, useEffect } from 'react';
import { CopilotChat } from "@copilotkit/react-ui";
import { useSimulationState } from '../hooks/useSimulationState';
import { EnhancedSimulationDashboard } from '../components/EnhancedSimulationDashboard';
import { PostProcessingDashboard } from '../components/PostProcessingDashboard';
import { WorkflowStateVisualization } from '../components/WorkflowStateVisualization';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<'overview' | 'preprocessing' | 'processing' | 'postprocessing'>('overview');
  const [projectId] = useState('dashboard-project'); // In real app, get from URL params
  
  const { simulationState, updateSimulationState } = useSimulationState(projectId);

  const stats = {
    totalProjects: 12,
    activeSimulations: 3,
    completedToday: 7,
    successRate: 94
  };

  const quickActions = [
    { id: 'new-project', label: 'New Simulation Project', icon: '🚀', color: 'bg-blue-500' },
    { id: 'upload-cad', label: 'Upload CAD Files', icon: '📁', color: 'bg-green-500' },
    { id: 'view-results', label: 'View Results', icon: '📊', color: 'bg-purple-500' },
    { id: 'help', label: 'AI Assistant Help', icon: '🤖', color: 'bg-orange-500' }
  ];

  const recentProjects = [
    { id: '1', name: 'Heat Exchanger CFD', type: 'CFD', status: 'Processing', progress: 67 },
    { id: '2', name: 'Bridge Structural Analysis', type: 'Structural', status: 'Completed', progress: 100 },
    { id: '3', name: 'Thermal Management', type: 'Thermal', status: 'Setup', progress: 25 },
    { id: '4', name: 'Electromagnetic Field', type: 'EM', status: 'Processing', progress: 45 }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Simulation Dashboard</h1>
                <p className="text-gray-600 mt-2">
                  AI-powered engineering simulation platform
                </p>
              </div>
              <div className="flex space-x-3">
                <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                  + New Project
                </button>
                <button className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors">
                  Settings
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow border">
            <div className="flex items-center">
              <div className="p-3 bg-blue-100 rounded-lg">
                <span className="text-2xl">📊</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">Total Projects</p>
                <p className="text-2xl font-bold text-gray-900">{stats.totalProjects}</p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow border">
            <div className="flex items-center">
              <div className="p-3 bg-green-100 rounded-lg">
                <span className="text-2xl">⚡</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">Active Simulations</p>
                <p className="text-2xl font-bold text-gray-900">{stats.activeSimulations}</p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow border">
            <div className="flex items-center">
              <div className="p-3 bg-purple-100 rounded-lg">
                <span className="text-2xl">✅</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">Completed Today</p>
                <p className="text-2xl font-bold text-gray-900">{stats.completedToday}</p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow border">
            <div className="flex items-center">
              <div className="p-3 bg-orange-100 rounded-lg">
                <span className="text-2xl">🎯</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">Success Rate</p>
                <p className="text-2xl font-bold text-gray-900">{stats.successRate}%</p>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {quickActions.map((action) => (
              <button
                key={action.id}
                className="bg-white p-4 rounded-lg shadow border hover:shadow-md transition-shadow text-left"
              >
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded ${action.color} text-white`}>
                    <span className="text-xl">{action.icon}</span>
                  </div>
                  <span className="font-medium text-gray-900">{action.label}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Main Content Tabs */}
        <div className="bg-white rounded-lg shadow border">
          <div className="border-b">
            <nav className="flex space-x-8 px-6">
              {['overview', 'preprocessing', 'processing', 'postprocessing'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab as any)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm capitalize ${
                    activeTab === tab
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'overview' && (
              <div>
                <h3 className="text-lg font-semibold mb-4">Recent Projects</h3>
                <div className="space-y-4">
                  {recentProjects.map((project) => (
                    <div key={project.id} className="border rounded-lg p-4 hover:bg-gray-50">
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="font-medium text-gray-900">{project.name}</h4>
                          <p className="text-sm text-gray-600">{project.type} Simulation</p>
                        </div>
                        <div className="text-right">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            project.status === 'Completed' ? 'bg-green-100 text-green-800' :
                            project.status === 'Processing' ? 'bg-blue-100 text-blue-800' :
                            'bg-yellow-100 text-yellow-800'
                          }`}>
                            {project.status}
                          </span>
                          <div className="mt-2 w-24 bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-blue-600 h-2 rounded-full" 
                              style={{ width: `${project.progress}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'preprocessing' && (
              <EnhancedSimulationDashboard projectId={projectId} />
            )}

            {activeTab === 'processing' && (
              <WorkflowStateVisualization projectId={projectId} />
            )}

            {activeTab === 'postprocessing' && (
              <PostProcessingDashboard projectId={projectId} />
            )}
          </div>
        </div>
      </div>

      {/* AI Assistant Integration */}
      <div className="fixed bottom-4 right-4">
        <div className="bg-white rounded-lg shadow-lg border p-4 max-w-sm">
          <CopilotChat
            instructions="I'm your simulation assistant. I can help you set up projects, analyze results, troubleshoot issues, and optimize your workflows."
            className="h-64"
          />
        </div>
      </div>
    </div>
  );
}