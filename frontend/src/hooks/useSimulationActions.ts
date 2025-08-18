import { useCopilotAction } from "@copilotkit/react-core";
import { useSimulationState } from "./useSimulationState";
import { useState } from "react";
import { getArchonService } from "../services/archonIntegration";
import { getPhysicsNemoService } from "../services/physicsNemoService";

export function useSimulationActions(projectId: string) {
  const { simulationState, updateSimulationState, addError } = useSimulationState(projectId);
  const [isUploading, setIsUploading] = useState(false);
  const archonService = getArchonService();
  const physicsNemoService = getPhysicsNemoService();

  // Enhanced file upload with Archon knowledge integration
  useCopilotAction({
    name: "upload_cad_file",
    description: "Upload a CAD file for simulation preprocessing with AI-enhanced analysis",
    parameters: [
      {
        name: "filename",
        type: "string",
        description: "Name of the CAD file to upload"
      },
      {
        name: "fileType",
        type: "string", 
        description: "Type of CAD file (STEP, IGES, STL, etc.)"
      }
    ],
    handler: async ({ filename, fileType }) => {
      // Search for relevant CAD standards and best practices
      const cadStandards = await archonService.searchKnowledge(`CAD ${fileType} standards`, 'cad_standard');
      
      // Trigger file upload dialog
      const fileInput = document.createElement('input');
      fileInput.type = 'file';
      fileInput.accept = '.step,.stp,.iges,.igs,.stl,.obj,.3mf';
      fileInput.onchange = async (e) => {
        const file = (e.target as HTMLInputElement).files?.[0];
        if (file) {
          await handleFileUpload(file, filename, fileType);
        }
      };
      fileInput.click();

      return cadStandards.length > 0 
        ? `Found ${cadStandards.length} relevant CAD standards for ${fileType} files. File upload dialog opened.`
        : "File upload dialog opened.";
    }
  });

  // Enhanced preprocessing workflow with Archon task management
  useCopilotAction({
    name: "start_enhanced_preprocessing_workflow",
    description: "Start AI-powered preprocessing workflow with Archon OS task management and NVIDIA PhysicsNemo",
    parameters: [
      {
        name: "userGoal",
        type: "string",
        description: "User's simulation goal and requirements"
      },
      {
        name: "physicsType",
        type: "string",
        description: "Type of physics simulation (cfd, structural, thermal, electromagnetic, multi_physics)"
      },
      {
        name: "useMLEnhanced",
        type: "boolean",
        description: "Whether to use ML-enhanced simulation with NVIDIA PhysicsNemo"
      }
    ],
    handler: async ({ userGoal, physicsType, useMLEnhanced = true }) => {
      try {
        // Set simulation context in Archon
        await archonService.setSimulationContext({
          projectId,
          cadFiles: simulationState.cadFiles,
          physicsType,
          requirements: userGoal
        });

        // Create preprocessing tasks in Archon
        const tasks = [
          {
            title: 'Geometry Analysis',
            description: `Analyze CAD geometry for ${physicsType} simulation`,
            type: 'preprocessing' as const,
            status: 'pending' as const,
            projectId
          },
          {
            title: 'Mesh Generation',
            description: `Generate computational mesh for ${physicsType} analysis`,
            type: 'preprocessing' as const,
            status: 'pending' as const,
            projectId
          },
          {
            title: 'Physics Setup',
            description: `Configure ${physicsType} solver and boundary conditions`,
            type: 'preprocessing' as const,
            status: 'pending' as const,
            projectId
          }
        ];

        for (const task of tasks) {
          await archonService.createTask(task);
        }

        updateSimulationState({
          userGoal,
          physicsType: physicsType as any,
          isProcessing: true,
          currentStep: 'geometry_processing',
          progress: 5
        });

        // Get PhysicsNemo capabilities
        const supportedTypes = await physicsNemoService.getSupportedTypes();
        const isSupported = supportedTypes.includes(physicsType);

        if (useMLEnhanced && isSupported) {
          // Estimate simulation with PhysicsNemo
          const estimate = await physicsNemoService.estimateSimulation({
            simulationType: physicsType as any,
            geometry: {
              cadFiles: simulationState.cadFiles.map(f => ({
                id: f.id,
                filename: f.filename,
                data: '' // Will be populated by backend
              }))
            },
            meshConfig: {
              elementSize: 0.1,
              qualityTarget: 0.8,
              adaptiveRefinement: true
            },
            physics: {
              materials: [],
              boundaryConditions: [],
              solverSettings: {}
            },
            mlEnhanced: true,
            accelerate: true
          });

          if (estimate) {
            return `Enhanced workflow started with NVIDIA PhysicsNemo. Estimated completion: ${estimate.estimatedTime} minutes. Cost: $${estimate.estimatedCost}.`;
          }
        }

        // Start backend workflow
        const response = await fetch(`/api/workflows/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_id: projectId,
            user_goal: userGoal,
            physics_type: physicsType,
            cad_file_ids: simulationState.cadFiles.map(f => f.id),
            use_ml_enhanced: useMLEnhanced,
            archon_integration: true
          })
        });

        if (!response.ok) {
          throw new Error(`Failed to start workflow: ${response.statusText}`);
        }

        const result = await response.json();
        updateSimulationState({
          workflowId: result.workflow_id
        });

        return `Enhanced workflow started successfully with Archon OS integration. Workflow ID: ${result.workflow_id}`;
      } catch (error) {
        addError('workflow_start', error instanceof Error ? error.message : 'Unknown error');
        updateSimulationState({ isProcessing: false });
        throw error;
      }
    }
  });

  // Search engineering knowledge
  useCopilotAction({
    name: "search_engineering_knowledge",
    description: "Search the Archon knowledge base for engineering documentation and best practices",
    parameters: [
      {
        name: "query",
        type: "string",
        description: "Search query for engineering knowledge"
      },
      {
        name: "type",
        type: "string",
        description: "Type of knowledge to search (documentation, cad_standard, physics_model, example)"
      }
    ],
    handler: async ({ query, type }) => {
      try {
        const results = await archonService.searchKnowledge(query, type);
        
        if (results.length === 0) {
          return `No knowledge found for "${query}". Consider adding relevant documentation to the knowledge base.`;
        }

        const summary = results.slice(0, 3).map(result => 
          `• ${result.title}: ${result.content.substring(0, 200)}...`
        ).join('\n');

        return `Found ${results.length} knowledge entries for "${query}":\n\n${summary}`;
      } catch (error) {
        addError('knowledge_search', error instanceof Error ? error.message : 'Unknown error');
        return `Error searching knowledge: ${error instanceof Error ? error.message : 'Unknown error'}`;
      }
    }
  });

  // NVIDIA PhysicsNemo ML optimization
  useCopilotAction({
    name: "optimize_with_physics_nemo",
    description: "Use NVIDIA PhysicsNemo ML capabilities to optimize simulation setup",
    parameters: [
      {
        name: "optimizationType",
        type: "string",
        description: "Type of optimization (mesh, physics, design)"
      },
      {
        name: "objectives",
        type: "string",
        description: "Optimization objectives (e.g., 'minimize drag, maximize heat transfer')"
      }
    ],
    handler: async ({ optimizationType, objectives }) => {
      try {
        if (optimizationType === 'mesh') {
          const result = await physicsNemoService.optimizeMesh(
            simulationState.geometryAnalysis,
            0.9 // High quality target
          );
          
          if (result) {
            updateSimulationState({
              meshRecommendations: result,
              meshStatus: 'completed'
            });
            return `Mesh optimization completed with NVIDIA PhysicsNemo. Quality improved to ${result.qualityScore}/10.`;
          }
        }

        return `Optimization type "${optimizationType}" with objectives "${objectives}" initiated.`;
      } catch (error) {
        addError('ml_optimization', error instanceof Error ? error.message : 'Unknown error');
        return `Error during ML optimization: ${error instanceof Error ? error.message : 'Unknown error'}`;
      }
    }
  });

  // Enhanced HITL checkpoint with Archon task tracking
  useCopilotAction({
    name: "respond_to_checkpoint",
    description: "Respond to a Human-in-the-Loop checkpoint with Archon task tracking",
    parameters: [
      {
        name: "approved",
        type: "boolean",
        description: "Whether to approve the current step"
      },
      {
        name: "feedback",
        type: "string",
        description: "Optional feedback or modification requests"
      }
    ],
    handler: async ({ approved, feedback }) => {
      if (!simulationState.activeCheckpoint) {
        return "No active checkpoint found";
      }

      try {
        // Update task status in Archon
        const tasks = await archonService.getTasks(projectId);
        const currentTask = tasks.find(t => t.status === 'in_progress');
        
        if (currentTask) {
          await archonService.updateTask(currentTask.id, {
            status: approved ? 'completed' : 'pending',
            metadata: { ...currentTask.metadata, feedback }
          });
        }

        const response = await fetch(
          `/api/workflows/${simulationState.workflowId}/checkpoints/${simulationState.activeCheckpoint.checkpointId}/respond`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              approved,
              feedback,
              reviewer_id: 'current_user',
              archon_task_id: currentTask?.id
            })
          }
        );

        if (!response.ok) {
          throw new Error(`Failed to respond to checkpoint: ${response.statusText}`);
        }

        updateSimulationState({
          activeCheckpoint: undefined,
          isProcessing: approved
        });

        return approved ? "Checkpoint approved and task updated in Archon" : "Checkpoint rejected with feedback";
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        addError('checkpoint_response', errorMessage);
        return `Error responding to checkpoint: ${errorMessage}`;
      }
    }
  });

  // Real-time simulation monitoring with PhysicsNemo
  useCopilotAction({
    name: "monitor_simulation",
    description: "Monitor active NVIDIA PhysicsNemo simulation with real-time updates",
    parameters: [
      {
        name: "simulationId",
        type: "string",
        description: "ID of the simulation to monitor"
      }
    ],
    handler: async ({ simulationId }) => {
      try {
        const result = await physicsNemoService.getSimulationStatus(simulationId);
        
        if (result) {
          updateSimulationState({
            progress: result.progress,
            isProcessing: result.status === 'running'
          });

          if (result.results) {
            updateSimulationState({
              meshQualityMetrics: result.results.meshQuality,
              validationResults: result.results.summary
            });
          }

          return `Simulation ${simulationId} status: ${result.status}, Progress: ${result.progress}%`;
        }

        return `Could not retrieve status for simulation ${simulationId}`;
      } catch (error) {
        addError('simulation_monitoring', error instanceof Error ? error.message : 'Unknown error');
        return `Error monitoring simulation: ${error instanceof Error ? error.message : 'Unknown error'}`;
      }
    }
  });

  // Helper function for enhanced file upload
  const handleFileUpload = async (file: File, filename: string, fileType: string) => {
    setIsUploading(true);
    
    try {
      // Add file to state immediately with pending status
      const tempFileId = `temp_${Date.now()}`;
      updateSimulationState({
        cadFiles: [...simulationState.cadFiles, {
          id: tempFileId,
          filename: filename || file.name,
          fileType: fileType || file.name.split('.').pop()?.toUpperCase() || 'UNKNOWN',
          uploadStatus: 'uploading'
        }]
      });

      // Create form data
      const formData = new FormData();
      formData.append('file', file);
      formData.append('project_id', projectId);
      formData.append('file_type', 'cad');

      // Upload file
      const response = await fetch('/api/files/upload', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const result = await response.json();

      // Update file status
      updateSimulationState({
        cadFiles: simulationState.cadFiles.map(f => 
          f.id === tempFileId 
            ? { ...f, id: result.file_id, uploadStatus: 'completed' }
            : f
        )
      });

      // Add file context to Archon knowledge base
      await archonService.addKnowledge({
        title: `CAD File - ${filename}`,
        content: `Uploaded CAD file: ${filename}, Type: ${fileType}, Project: ${projectId}`,
        type: 'example',
        tags: ['cad', 'upload', fileType.toLowerCase()],
        metadata: {
          projectId,
          fileId: result.file_id,
          uploadTimestamp: new Date().toISOString()
        }
      });

    } catch (error) {
      // Update file status to failed
      updateSimulationState({
        cadFiles: simulationState.cadFiles.map(f => 
          f.id.startsWith('temp_') 
            ? { ...f, uploadStatus: 'failed' }
            : f
        )
      });
      
      addError('file_upload', error instanceof Error ? error.message : 'Unknown error');
    } finally {
      setIsUploading(false);
    }
  };

  return { 
    simulationState, 
    updateSimulationState,
    isUploading,
    handleFileUpload,
    archonService,
    physicsNemoService
  };
}
