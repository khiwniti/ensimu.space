import { createClient } from '@supabase/supabase-js';

interface ArchonConfig {
  serverUrl: string;
  mcpUrl: string;
  apiKey?: string;
}

interface KnowledgeEntry {
  id: string;
  title: string;
  content: string;
  type: 'documentation' | 'cad_standard' | 'physics_model' | 'example';
  tags: string[];
  metadata?: Record<string, any>;
}

interface TaskEntry {
  id: string;
  title: string;
  description: string;
  type: 'preprocessing' | 'simulation' | 'analysis' | 'optimization';
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  projectId: string;
  agentId?: string;
  dependencies?: string[];
  metadata?: Record<string, any>;
}

interface SimulationContext {
  projectId: string;
  cadFiles: Array<{
    id: string;
    filename: string;
    type: string;
    metadata?: Record<string, any>;
  }>;
  physicsType: string;
  requirements: string;
  constraints?: Record<string, any>;
}

export class ArchonIntegrationService {
  private config: ArchonConfig;
  private supabase: any;

  constructor(config: ArchonConfig) {
    this.config = config;
    
    // Initialize Supabase client for Archon's knowledge base
    if (process.env.SUPABASE_URL && process.env.SUPABASE_SERVICE_KEY) {
      this.supabase = createClient(
        process.env.SUPABASE_URL,
        process.env.SUPABASE_SERVICE_KEY
      );
    }
  }

  // Knowledge Management
  async searchKnowledge(query: string, type?: string): Promise<KnowledgeEntry[]> {
    try {
      const response = await fetch(`${this.config.serverUrl}/api/knowledge/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`
        },
        body: JSON.stringify({
          query,
          filters: type ? { type } : {},
          limit: 10
        })
      });

      if (!response.ok) {
        throw new Error(`Knowledge search failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error searching knowledge:', error);
      return [];
    }
  }

  async addKnowledge(entry: Omit<KnowledgeEntry, 'id'>): Promise<string | null> {
    try {
      const response = await fetch(`${this.config.serverUrl}/api/knowledge`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`
        },
        body: JSON.stringify(entry)
      });

      if (!response.ok) {
        throw new Error(`Failed to add knowledge: ${response.statusText}`);
      }

      const result = await response.json();
      return result.id;
    } catch (error) {
      console.error('Error adding knowledge:', error);
      return null;
    }
  }

  // Task Management
  async createTask(task: Omit<TaskEntry, 'id'>): Promise<string | null> {
    try {
      const response = await fetch(`${this.config.serverUrl}/api/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`
        },
        body: JSON.stringify(task)
      });

      if (!response.ok) {
        throw new Error(`Failed to create task: ${response.statusText}`);
      }

      const result = await response.json();
      return result.id;
    } catch (error) {
      console.error('Error creating task:', error);
      return null;
    }
  }

  async updateTask(taskId: string, updates: Partial<TaskEntry>): Promise<boolean> {
    try {
      const response = await fetch(`${this.config.serverUrl}/api/tasks/${taskId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`
        },
        body: JSON.stringify(updates)
      });

      return response.ok;
    } catch (error) {
      console.error('Error updating task:', error);
      return false;
    }
  }

  async getTasks(projectId: string): Promise<TaskEntry[]> {
    try {
      const response = await fetch(
        `${this.config.serverUrl}/api/tasks?projectId=${projectId}`,
        {
          headers: {
            'Authorization': `Bearer ${this.config.apiKey}`
          }
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to get tasks: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting tasks:', error);
      return [];
    }
  }

  // MCP Integration for AI Assistants
  async queryMCP(tool: string, parameters: Record<string, any>): Promise<any> {
    try {
      const response = await fetch(`${this.config.mcpUrl}/mcp/call`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          tool,
          parameters
        })
      });

      if (!response.ok) {
        throw new Error(`MCP query failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error querying MCP:', error);
      return null;
    }
  }

  // Context Management for Simulation Projects
  async setSimulationContext(context: SimulationContext): Promise<boolean> {
    try {
      const contextEntry: Omit<KnowledgeEntry, 'id'> = {
        title: `Simulation Context - ${context.projectId}`,
        content: JSON.stringify(context),
        type: 'example',
        tags: ['simulation', 'context', context.physicsType],
        metadata: {
          projectId: context.projectId,
          contextType: 'simulation',
          timestamp: new Date().toISOString()
        }
      };

      const entryId = await this.addKnowledge(contextEntry);
      return entryId !== null;
    } catch (error) {
      console.error('Error setting simulation context:', error);
      return false;
    }
  }

  async getSimulationContext(projectId: string): Promise<SimulationContext | null> {
    try {
      const entries = await this.searchKnowledge(`projectId:${projectId}`, 'example');
      const contextEntry = entries.find(entry => 
        entry.metadata?.contextType === 'simulation' &&
        entry.metadata?.projectId === projectId
      );

      if (contextEntry) {
        return JSON.parse(contextEntry.content);
      }

      return null;
    } catch (error) {
      console.error('Error getting simulation context:', error);
      return null;
    }
  }

  // AI Agent Communication
  async requestAgentAction(
    agentType: 'preprocessing' | 'simulation' | 'analysis' | 'optimization',
    action: string,
    parameters: Record<string, any>
  ): Promise<any> {
    try {
      // Use MCP to communicate with specific agents
      return await this.queryMCP('agent_action', {
        agentType,
        action,
        parameters
      });
    } catch (error) {
      console.error('Error requesting agent action:', error);
      return null;
    }
  }

  // Engineering Knowledge Integration
  async initializeEngineeringKnowledge(): Promise<void> {
    const standardEntries = [
      {
        title: 'CFD Best Practices',
        content: 'Computational Fluid Dynamics simulation guidelines...',
        type: 'documentation' as const,
        tags: ['cfd', 'best-practices', 'simulation']
      },
      {
        title: 'Mesh Quality Standards',
        content: 'Guidelines for mesh generation and quality assessment...',
        type: 'cad_standard' as const,
        tags: ['mesh', 'quality', 'preprocessing']
      },
      {
        title: 'Structural Analysis Setup',
        content: 'Standard procedures for structural analysis configuration...',
        type: 'documentation' as const,
        tags: ['structural', 'analysis', 'setup']
      },
      {
        title: 'NVIDIA PhysicsNemo Integration',
        content: 'How to integrate with NVIDIA PhysicsNemo for advanced simulations...',
        type: 'documentation' as const,
        tags: ['nvidia', 'physics-nemo', 'integration']
      }
    ];

    for (const entry of standardEntries) {
      await this.addKnowledge(entry);
    }
  }

  // Real-time Updates via WebSocket
  subscribeToUpdates(projectId: string, callback: (update: any) => void): void {
    if (typeof window !== 'undefined' && 'WebSocket' in window) {
      const ws = new WebSocket(`${this.config.serverUrl.replace('http', 'ws')}/ws/project/${projectId}`);
      
      ws.onmessage = (event) => {
        try {
          const update = JSON.parse(event.data);
          callback(update);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      return () => ws.close();
    }
  }

  // Health Check
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.config.serverUrl}/health`);
      return response.ok;
    } catch (error) {
      console.error('Archon health check failed:', error);
      return false;
    }
  }
}

// Singleton instance
let archonService: ArchonIntegrationService | null = null;

export function getArchonService(): ArchonIntegrationService {
  if (!archonService) {
    archonService = new ArchonIntegrationService({
      serverUrl: process.env.REACT_APP_ARCHON_SERVER_URL || 'http://localhost:8181',
      mcpUrl: process.env.REACT_APP_ARCHON_MCP_URL || 'http://localhost:8051',
      apiKey: process.env.REACT_APP_ARCHON_API_KEY
    });
  }
  return archonService;
}

export default ArchonIntegrationService;