import axios from 'axios';

interface PhysicsNemoConfig {
  apiUrl: string;
  apiKey?: string;
  timeout?: number;
}

interface SimulationRequest {
  simulationType: 'cfd' | 'structural' | 'thermal' | 'electromagnetic' | 'multi_physics';
  geometry: {
    cadFiles: Array<{
      id: string;
      filename: string;
      data: string; // Base64 encoded CAD data
    }>;
    boundingBox?: {
      min: [number, number, number];
      max: [number, number, number];
    };
  };
  meshConfig: {
    elementSize: number;
    qualityTarget: number;
    adaptiveRefinement: boolean;
  };
  physics: {
    materials: Array<{
      id: string;
      name: string;
      properties: Record<string, number>;
    }>;
    boundaryConditions: Array<{
      type: string;
      location: string;
      values: Record<string, number>;
    }>;
    solverSettings: Record<string, any>;
  };
  mlEnhanced: boolean;
  accelerate: boolean;
}

interface SimulationResult {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress: number;
  results?: {
    meshQuality: {
      aspectRatio: number;
      skewness: number;
      orthogonalQuality: number;
      overallScore: number;
    };
    convergence: {
      iterations: number;
      residuals: number[];
      converged: boolean;
    };
    fieldData?: {
      velocity?: number[][][];
      pressure?: number[][][];
      temperature?: number[][][];
      stress?: number[][][];
    };
    summary: {
      maxVelocity?: number;
      maxPressure?: number;
      maxTemperature?: number;
      maxStress?: number;
      safetyFactor?: number;
    };
  };
  error?: string;
  computeTime: number;
  metadata: Record<string, any>;
}

interface MLOptimizationRequest {
  baseSimulation: SimulationRequest;
  objectives: Array<{
    parameter: string;
    target: 'minimize' | 'maximize';
    weight: number;
  }>;
  constraints: Array<{
    parameter: string;
    min?: number;
    max?: number;
  }>;
  designVariables: Array<{
    parameter: string;
    min: number;
    max: number;
    current: number;
  }>;
  maxIterations: number;
  convergenceTolerance: number;
}

export class PhysicsNemoService {
  private config: PhysicsNemoConfig;
  private axiosInstance: any;

  constructor(config: PhysicsNemoConfig) {
    this.config = config;
    this.axiosInstance = axios.create({
      baseURL: config.apiUrl,
      timeout: config.timeout || 30000,
      headers: {
        'Content-Type': 'application/json',
        ...(config.apiKey && { 'Authorization': `Bearer ${config.apiKey}` })
      }
    });
  }

  // Submit simulation job
  async submitSimulation(request: SimulationRequest): Promise<string | null> {
    try {
      const response = await this.axiosInstance.post('/api/v1/simulations', request);
      return response.data.id;
    } catch (error) {
      console.error('Error submitting simulation:', error);
      return null;
    }
  }

  // Get simulation status and results
  async getSimulationStatus(simulationId: string): Promise<SimulationResult | null> {
    try {
      const response = await this.axiosInstance.get(`/api/v1/simulations/${simulationId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting simulation status:', error);
      return null;
    }
  }

  // Cancel simulation
  async cancelSimulation(simulationId: string): Promise<boolean> {
    try {
      await this.axiosInstance.delete(`/api/v1/simulations/${simulationId}`);
      return true;
    } catch (error) {
      console.error('Error canceling simulation:', error);
      return false;
    }
  }

  // ML-Enhanced Preprocessing
  async optimizeMesh(geometry: any, targetQuality: number = 0.8): Promise<any> {
    try {
      const response = await this.axiosInstance.post('/api/v1/ml/mesh-optimization', {
        geometry,
        targetQuality,
        useML: true
      });
      return response.data;
    } catch (error) {
      console.error('Error optimizing mesh:', error);
      return null;
    }
  }

  // Physics-Informed Neural Network (PINN) simulation
  async runPINNSimulation(request: SimulationRequest): Promise<string | null> {
    try {
      const pinnRequest = {
        ...request,
        solverType: 'pinn',
        mlEnhanced: true,
        neuralNetworkConfig: {
          layers: [100, 100, 100, 100],
          activation: 'tanh',
          learningRate: 0.001,
          epochs: 10000
        }
      };

      const response = await this.axiosInstance.post('/api/v1/pinn/simulate', pinnRequest);
      return response.data.id;
    } catch (error) {
      console.error('Error running PINN simulation:', error);
      return null;
    }
  }

  // Multi-objective optimization
  async optimizeDesign(request: MLOptimizationRequest): Promise<string | null> {
    try {
      const response = await this.axiosInstance.post('/api/v1/optimization', request);
      return response.data.optimizationId;
    } catch (error) {
      console.error('Error starting optimization:', error);
      return null;
    }
  }

  // Real-time simulation monitoring
  subscribeToSimulation(
    simulationId: string, 
    onUpdate: (result: SimulationResult) => void,
    onError: (error: string) => void
  ): () => void {
    if (typeof window !== 'undefined' && 'EventSource' in window) {
      const eventSource = new EventSource(
        `${this.config.apiUrl}/api/v1/simulations/${simulationId}/stream`
      );

      eventSource.onmessage = (event) => {
        try {
          const result = JSON.parse(event.data);
          onUpdate(result);
        } catch (error) {
          onError(`Failed to parse simulation update: ${error}`);
        }
      };

      eventSource.onerror = (error) => {
        onError(`Simulation stream error: ${error}`);
      };

      return () => eventSource.close();
    }

    // Fallback to polling for environments without EventSource
    const pollInterval = setInterval(async () => {
      const result = await this.getSimulationStatus(simulationId);
      if (result) {
        onUpdate(result);
        if (result.status === 'completed' || result.status === 'failed') {
          clearInterval(pollInterval);
        }
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }

  // Get available GPU resources
  async getGPUResources(): Promise<any> {
    try {
      const response = await this.axiosInstance.get('/api/v1/resources/gpu');
      return response.data;
    } catch (error) {
      console.error('Error getting GPU resources:', error);
      return null;
    }
  }

  // Estimate simulation time and cost
  async estimateSimulation(request: SimulationRequest): Promise<any> {
    try {
      const response = await this.axiosInstance.post('/api/v1/estimate', request);
      return response.data;
    } catch (error) {
      console.error('Error estimating simulation:', error);
      return null;
    }
  }

  // Batch simulation management
  async submitBatchSimulations(requests: SimulationRequest[]): Promise<string[]> {
    try {
      const response = await this.axiosInstance.post('/api/v1/batch', {
        simulations: requests
      });
      return response.data.simulationIds;
    } catch (error) {
      console.error('Error submitting batch simulations:', error);
      return [];
    }
  }

  // Advanced post-processing
  async generateVisualization(
    simulationId: string, 
    visualizationType: 'contour' | 'streamline' | 'vector' | 'isosurface'
  ): Promise<any> {
    try {
      const response = await this.axiosInstance.post(`/api/v1/simulations/${simulationId}/visualize`, {
        type: visualizationType,
        format: 'webgl',
        resolution: 'high'
      });
      return response.data;
    } catch (error) {
      console.error('Error generating visualization:', error);
      return null;
    }
  }

  // Export results
  async exportResults(
    simulationId: string, 
    format: 'vtk' | 'csv' | 'json' | 'hdf5'
  ): Promise<any> {
    try {
      const response = await this.axiosInstance.get(
        `/api/v1/simulations/${simulationId}/export?format=${format}`,
        { responseType: 'blob' }
      );
      return response.data;
    } catch (error) {
      console.error('Error exporting results:', error);
      return null;
    }
  }

  // Health check
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.axiosInstance.get('/health');
      return response.status === 200;
    } catch (error) {
      console.error('PhysicsNemo health check failed:', error);
      return false;
    }
  }

  // Get supported simulation types
  async getSupportedTypes(): Promise<string[]> {
    try {
      const response = await this.axiosInstance.get('/api/v1/capabilities');
      return response.data.simulationTypes;
    } catch (error) {
      console.error('Error getting supported types:', error);
      return [];
    }
  }
}

// Singleton instance
let physicsNemoService: PhysicsNemoService | null = null;

export function getPhysicsNemoService(): PhysicsNemoService {
  if (!physicsNemoService) {
    physicsNemoService = new PhysicsNemoService({
      apiUrl: process.env.REACT_APP_PHYSICS_NEMO_URL || 'http://localhost:8053',
      apiKey: process.env.REACT_APP_NVIDIA_API_KEY,
      timeout: 60000 // 1 minute timeout for simulation operations
    });
  }
  return physicsNemoService;
}

export default PhysicsNemoService;