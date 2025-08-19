"""
NVIDIA API endpoints for Llama-3.3-Nemotron and PhysicsNemo integration
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import logging

from ...libs.nvidia_client import get_nvidia_client
from ...libs.physics_nemo_agent import get_physics_nemo_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nvidia", tags=["nvidia"])

# Request/Response Models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024
    stream: bool = False

class ChatCompletionResponse(BaseModel):
    choices: List[Dict[str, Any]]
    model: str
    usage: Optional[Dict[str, Any]] = None

class PhysicsAnalysisRequest(BaseModel):
    simulation_type: str  # CFD, FEA, thermal
    geometry_description: str
    boundary_conditions: Dict[str, Any]
    material_properties: Dict[str, Any]
    analysis_objectives: List[str] = []

class PhysicsAnalysisResponse(BaseModel):
    mesh_recommendations: Dict[str, Any]
    solver_settings: Dict[str, Any]
    boundary_condition_setup: Dict[str, Any]
    material_assignments: Dict[str, Any]
    convergence_criteria: Dict[str, Any]
    expected_challenges: List[str]
    optimization_suggestions: List[str]
    confidence_score: float
    analysis_timestamp: str

@router.get("/health")
async def health_check():
    """Health check for NVIDIA integration"""
    try:
        client = await get_nvidia_client()
        validation = await client.validate_setup()
        return {
            "status": "healthy",
            "nvidia_api": validation["status"],
            "model": validation.get("config", {}).get("model", "unknown"),
            "timestamp": validation.get("timestamp")
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"NVIDIA API unavailable: {str(e)}")

@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completion(request: ChatCompletionRequest):
    """
    Generate chat completion using NVIDIA Llama-3.3-Nemotron
    """
    try:
        client = await get_nvidia_client()
        
        # Convert Pydantic models to dict
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        response = await client.chat_completion(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream
        )
        
        return ChatCompletionResponse(**response)
        
    except Exception as e:
        logger.error(f"Chat completion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")

@router.post("/physics/cfd", response_model=PhysicsAnalysisResponse)
async def analyze_cfd(request: PhysicsAnalysisRequest):
    """
    Analyze CFD simulation setup using PhysicsNemo
    """
    try:
        agent = await get_physics_nemo_agent()
        
        result = await agent.analyze_cfd_setup(
            geometry_description=request.geometry_description,
            flow_conditions=request.boundary_conditions,
            fluid_properties=request.material_properties
        )
        
        return PhysicsAnalysisResponse(
            mesh_recommendations=result.mesh_recommendations,
            solver_settings=result.solver_settings,
            boundary_condition_setup=result.boundary_condition_setup,
            material_assignments=result.material_assignments,
            convergence_criteria=result.convergence_criteria,
            expected_challenges=result.expected_challenges,
            optimization_suggestions=result.optimization_suggestions,
            confidence_score=result.confidence_score,
            analysis_timestamp=result.analysis_timestamp
        )
        
    except Exception as e:
        logger.error(f"CFD analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"CFD analysis failed: {str(e)}")

@router.post("/physics/fea", response_model=PhysicsAnalysisResponse)
async def analyze_fea(request: PhysicsAnalysisRequest):
    """
    Analyze FEA simulation setup using PhysicsNemo
    """
    try:
        agent = await get_physics_nemo_agent()
        
        result = await agent.analyze_fea_setup(
            geometry_description=request.geometry_description,
            loading_conditions=request.boundary_conditions,
            material_properties=request.material_properties
        )
        
        return PhysicsAnalysisResponse(
            mesh_recommendations=result.mesh_recommendations,
            solver_settings=result.solver_settings,
            boundary_condition_setup=result.boundary_condition_setup,
            material_assignments=result.material_assignments,
            convergence_criteria=result.convergence_criteria,
            expected_challenges=result.expected_challenges,
            optimization_suggestions=result.optimization_suggestions,
            confidence_score=result.confidence_score,
            analysis_timestamp=result.analysis_timestamp
        )
        
    except Exception as e:
        logger.error(f"FEA analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"FEA analysis failed: {str(e)}")

@router.post("/physics/thermal", response_model=PhysicsAnalysisResponse)
async def analyze_thermal(request: PhysicsAnalysisRequest):
    """
    Analyze thermal simulation setup using PhysicsNemo
    """
    try:
        agent = await get_physics_nemo_agent()
        
        result = await agent.analyze_thermal_setup(
            geometry_description=request.geometry_description,
            thermal_conditions=request.boundary_conditions,
            material_properties=request.material_properties
        )
        
        return PhysicsAnalysisResponse(
            mesh_recommendations=result.mesh_recommendations,
            solver_settings=result.solver_settings,
            boundary_condition_setup=result.boundary_condition_setup,
            material_assignments=result.material_assignments,
            convergence_criteria=result.convergence_criteria,
            expected_challenges=result.expected_challenges,
            optimization_suggestions=result.optimization_suggestions,
            confidence_score=result.confidence_score,
            analysis_timestamp=result.analysis_timestamp
        )
        
    except Exception as e:
        logger.error(f"Thermal analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Thermal analysis failed: {str(e)}")

@router.get("/models")
async def list_models():
    """
    List available NVIDIA models
    """
    return {
        "models": [
            {
                "id": "nvidia/llama-3.3-nemotron-super-49b-v1",
                "name": "Llama 3.3 Nemotron Super 49B",
                "description": "Advanced language model for technical and scientific applications",
                "capabilities": ["chat", "physics_analysis", "cae_assistance"]
            }
        ],
        "physics_domains": ["CFD", "FEA", "thermal", "multiphysics"],
        "analysis_types": ["preprocessing", "setup_optimization", "troubleshooting"]
    }

@router.get("/usage")
async def get_usage_stats():
    """
    Get usage statistics for NVIDIA integration
    """
    try:
        agent = await get_physics_nemo_agent()
        history = await agent.get_analysis_history()
        
        return {
            "total_analyses": len(history),
            "analysis_types": {
                "CFD": len([h for h in history if h["request"]["simulation_type"] == "CFD"]),
                "FEA": len([h for h in history if h["request"]["simulation_type"] == "FEA"]),
                "thermal": len([h for h in history if h["request"]["simulation_type"] == "thermal"])
            },
            "average_confidence": sum(h["result"]["confidence_score"] for h in history) / len(history) if history else 0,
            "recent_analyses": history[-5:] if len(history) > 5 else history
        }
        
    except Exception as e:
        logger.error(f"Usage stats failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Usage stats failed: {str(e)}")

# Include router in main app
def get_router():
    return router
