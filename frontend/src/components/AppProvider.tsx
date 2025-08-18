"use client";

import React, { useEffect, useState } from 'react';
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";
import { getArchonService } from '../services/archonIntegration';

interface AppProviderProps {
  children: React.ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
  const [archonConnected, setArchonConnected] = useState(false);
  const archonService = getArchonService();

  useEffect(() => {
    // Initialize Archon connection and engineering knowledge
    const initializeArchon = async () => {
      try {
        const isHealthy = await archonService.healthCheck();
        if (isHealthy) {
          await archonService.initializeEngineeringKnowledge();
          setArchonConnected(true);
          console.log('Archon OS integrated successfully');
        }
      } catch (error) {
        console.error('Failed to initialize Archon integration:', error);
      }
    };

    initializeArchon();
  }, []);

  const enhancedInstructions = `I'm your AI-powered simulation assistant with access to advanced engineering knowledge and workflow automation through Archon OS.

  **My Capabilities:**
  • 🔍 **Smart Knowledge Search**: Access to engineering documentation, CAD standards, and physics models
  • 🤖 **Agentic Workflows**: Automated preprocessing, simulation setup, and optimization
  • 📊 **NVIDIA PhysicsNemo Integration**: Advanced physics simulations and ML-enhanced analysis  
  • 🛠️ **Task Management**: Intelligent project planning and execution tracking
  • 💬 **Multi-Agent Coordination**: Collaborate with specialized engineering agents
  
  **Available Commands:**
  • "Search for CFD best practices"
  • "Set up structural analysis workflow"
  • "Optimize mesh quality"
  • "Generate physics setup for [physics type]"
  • "Create preprocessing task list"
  
  ${archonConnected ? '✅ **Archon OS Connected** - Enhanced AI capabilities active' : '⚠️ **Archon OS Connecting** - Basic capabilities available'}`;

  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      agent="enhanced-simulation-agent"
      showDevConsole={process.env.NODE_ENV === 'development'}
    >
      <div className="flex h-screen">
        <div className="flex-1">
          {children}
        </div>
        <CopilotSidebar
          title="Enhanced AI Assistant"
          instructions={enhancedInstructions}
          defaultOpen={false}
          clickOutsideToClose={true}
          className="w-96"
        />
      </div>

      {/* Archon Connection Status */}
      <div className="fixed bottom-4 left-4 z-50">
        <div className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
          archonConnected 
            ? 'bg-green-100 text-green-800 border border-green-200' 
            : 'bg-yellow-100 text-yellow-800 border border-yellow-200'
        }`}>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${
              archonConnected ? 'bg-green-500' : 'bg-yellow-500 animate-pulse'
            }`} />
            <span>
              {archonConnected ? 'Archon OS Connected' : 'Connecting to Archon OS...'}
            </span>
          </div>
        </div>
      </div>
    </CopilotKit>
  );
}