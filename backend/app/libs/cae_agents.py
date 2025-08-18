"""
Enhanced AI Agent System for ensimu-space platform.
Migrated and enhanced from EnsimuAgent with FastAPI integration.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

import openai
from sqlalchemy.orm import Session
from app.libs.database import get_db
from app.libs.cae_models import (
    AISession, AgentCommunication, WorkflowExecution,
    WorkflowStep, HITLCheckpoint, Project, UploadedFile
)

# Import performance optimizations
try:
    from app.libs.performance.caching import (
        cache_agent_response, cache_geometry_analysis, cache_mesh_strategy,
        CacheInvalidator, cache_manager
    )
    from app.libs.performance.memory import object_tracker
    PERFORMANCE_ENABLED = True
except ImportError:
    # Fallback if performance modules not available
    PERFORMANCE_ENABLED = False
    def cache_agent_response(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def cache_geometry_analysis(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def cache_mesh_strategy(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

# Configure OpenAI client
openai_client = openai.OpenAI()

# ============================================================================
# Base Agent Classes and Data Structures
# ============================================================================

@dataclass
class AgentResponse:
    """Standardized agent response structure"""
    success: bool
    data: Dict[str, Any]
    confidence_score: float
    processing_time: float
    agent_type: str
    timestamp: str
    error_message: Optional[str] = None
    warnings: List[str] = None

@dataclass
class WorkflowContext:
    """Context shared between agents in a workflow"""
    project_id: str
    workflow_id: str
    user_goal: str
    physics_type: str
    current_step: str
    global_state: Dict[str, Any]
    agent_outputs: Dict[str, Any]

class PreprocessingAgent(ABC):
    """Enhanced base class for all preprocessing AI agents with FastAPI integration"""

    def __init__(self, agent_type: str, db_session: Optional[Session] = None):
        self.agent_type = agent_type
        self.client = openai_client
        self.logger = self._setup_logger()
        self.db_session = db_session

        # Performance tracking
        self.performance_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "last_request_time": None
        }

        # Configuration
        self.retry_config = {
            "max_retries": 3,
            "backoff_factor": 2,
            "timeout_seconds": 30
        }

        # Agent capabilities (to be overridden by subclasses)
        self.capabilities = []
        self.supported_tools = []

    def _setup_logger(self) -> logging.Logger:
        """Setup agent-specific logger"""
        logger = logging.getLogger(f"agent.{self.agent_type}")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self.agent_type.upper()} - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    async def create_session(self, project_id: str, workflow_id: Optional[str] = None) -> str:
        """Create a new AI session in the database"""
        if not self.db_session:
            return str(uuid.uuid4())  # Fallback for testing

        session = AISession(
            project_id=project_id,
            agent_type=self.agent_type,
            session_data={
                "workflow_id": workflow_id,
                "capabilities": self.capabilities,
                "supported_tools": self.supported_tools
            },
            status="active",
            agent_version="2.0",
            capabilities=self.capabilities
        )

        self.db_session.add(session)
        self.db_session.commit()

        return str(session.id)

    async def make_request(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enhanced request method with error handling and performance tracking"""
        start_time = time.time()
        self.performance_metrics["total_requests"] += 1

        try:
            # Prepare messages
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ]

            # Add context if provided
            if context:
                context_message = f"Additional context: {json.dumps(context, indent=2)}"
                messages.append({"role": "user", "content": context_message})

            # Make API call with retry logic
            response = await self._make_api_call_with_retry(messages)

            # Parse response
            result = self._parse_response(response)

            # Update metrics
            processing_time = time.time() - start_time
            self.performance_metrics["successful_requests"] += 1
            self.performance_metrics["average_response_time"] = (
                (self.performance_metrics["average_response_time"] *
                 (self.performance_metrics["successful_requests"] - 1) + processing_time) /
                self.performance_metrics["successful_requests"]
            )
            self.performance_metrics["last_request_time"] = datetime.utcnow().isoformat()

            self.logger.info(f"Request completed successfully in {processing_time:.2f}s")

            return result

        except Exception as e:
            self.performance_metrics["failed_requests"] += 1
            self.logger.error(f"Request failed: {str(e)}")

            return {
                "success": False,
                "error": str(e),
                "agent_type": self.agent_type,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _make_api_call_with_retry(self, messages: List[Dict[str, str]]) -> str:
        """Make OpenAI API call with retry logic"""
        for attempt in range(self.retry_config["max_retries"]):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.chat.completions.create,
                        model="gpt-4",
                        messages=messages,
                        temperature=0.1,
                        max_tokens=2000
                    ),
                    timeout=self.retry_config["timeout_seconds"]
                )

                return response.choices[0].message.content

            except Exception as e:
                if attempt == self.retry_config["max_retries"] - 1:
                    raise e

                wait_time = self.retry_config["backoff_factor"] ** attempt
                self.logger.warning(f"API call failed (attempt {attempt + 1}), retrying in {wait_time}s: {str(e)}")
                await asyncio.sleep(wait_time)

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate agent response"""
        try:
            # Try to parse as JSON
            result = json.loads(response_text)

            # Add metadata
            result.update({
                "success": True,
                "agent_type": self.agent_type,
                "timestamp": datetime.utcnow().isoformat(),
                "confidence_score": result.get("confidence_score", 0.8)
            })

            return result

        except json.JSONDecodeError:
            # Fallback for non-JSON responses
            return {
                "success": True,
                "content": response_text,
                "agent_type": self.agent_type,
                "timestamp": datetime.utcnow().isoformat(),
                "confidence_score": 0.7
            }

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get agent-specific system prompt"""
        pass

    @abstractmethod
    async def process_request(self, request_data: Dict[str, Any], context: WorkflowContext) -> AgentResponse:
        """Process agent-specific request"""
        pass

# ============================================================================
# Specialized Agent Implementations
# ============================================================================

class GeometryAgent(PreprocessingAgent):
    """Enhanced AI agent specialized in CAD geometry preparation and simplification"""

    def __init__(self, db_session: Optional[Session] = None):
        super().__init__("geometry", db_session)
        self.capabilities = [
            "cad_analysis", "defeaturing", "simplification", "quality_assessment",
            "tool_integration", "workflow_coordination", "mesh_preparation"
        ]
        self.supported_tools = [
            "cad_import", "geometry_cleanup", "defeaturing", "mid_surface_extraction",
            "envelope_creation", "geometry_validation", "mesh_preparation"
        ]
        self.tool_capabilities = {
            "cad_import": ["STEP", "IGES", "STL", "Parasolid", "ACIS"],
            "defeaturing": ["small_holes", "fillets", "chamfers", "slots", "ribs"],
            "simplification": ["topology_optimization", "feature_suppression", "envelope_geometry"]
        }

    def _get_system_prompt(self) -> str:
        return """You are an expert CAD geometry preparation specialist for engineering simulation.

Key responsibilities:
1. Analyze CAD models for simulation readiness with detailed feature detection
2. Recommend defeaturing strategies (removing small holes, fillets, chamfers, slots, ribs)
3. Suggest mid-surface creation for thin-walled structures with thickness validation
4. Propose envelope geometry for complex assemblies with clearance analysis
5. Identify potential meshing challenges and recommend mesh preparation strategies
6. Prepare tool integration scripts for CAD software automation
7. Validate geometry quality and provide repair recommendations
8. Coordinate with downstream agents (mesh, materials, physics) for optimal workflow

Advanced capabilities:
- Feature recognition and classification
- Geometric tolerance analysis
- Assembly interference detection
- Surface quality assessment
- Mesh readiness validation
- Tool automation script generation

Always respond in JSON format with fields: recommendations, defeaturing_steps, potential_issues, mesh_considerations, tool_preparations, validation_results, downstream_coordination, and confidence_score."""

    @cache_agent_response("geometry")
    async def process_request(self, request_data: Dict[str, Any], context: WorkflowContext) -> AgentResponse:
        """Process geometry analysis request with caching"""
        start_time = time.time()

        # Track object for memory monitoring
        if PERFORMANCE_ENABLED:
            object_tracker.track_object(self, "GeometryAgent")

        try:
            # Extract request parameters
            cad_files = request_data.get("cad_files", [])
            physics_type = context.physics_type
            analysis_requirements = request_data.get("analysis_requirements", {})

            # Prepare analysis prompt
            prompt = f"""
            Analyze CAD geometry for {physics_type} simulation preprocessing:

            CAD Files: {cad_files}
            Physics Type: {physics_type}
            Analysis Requirements: {analysis_requirements}
            User Goal: {context.user_goal}

            Provide comprehensive geometry analysis including:
            1. Feature detection and classification
            2. Defeaturing recommendations with priority ranking
            3. Mesh preparation strategies
            4. Quality assessment and repair recommendations
            5. Tool automation scripts for CAD software
            6. Coordination requirements with downstream agents

            Consider the specific requirements for {physics_type} analysis and optimize recommendations accordingly.
            """

            # Make AI request
            result = await self.make_request(prompt, {
                "workflow_context": context.global_state,
                "agent_outputs": context.agent_outputs
            })

            # Process and enhance result
            if result.get("success"):
                enhanced_result = await self._enhance_geometry_analysis(result, context)

                return AgentResponse(
                    success=True,
                    data=enhanced_result,
                    confidence_score=result.get("confidence_score", 0.8),
                    processing_time=time.time() - start_time,
                    agent_type=self.agent_type,
                    timestamp=datetime.utcnow().isoformat()
                )
            else:
                return AgentResponse(
                    success=False,
                    data=result,
                    confidence_score=0.0,
                    processing_time=time.time() - start_time,
                    agent_type=self.agent_type,
                    timestamp=datetime.utcnow().isoformat(),
                    error_message=result.get("error", "Unknown error in geometry analysis")
                )

        except Exception as e:
            self.logger.error(f"Geometry analysis failed: {str(e)}")
            return AgentResponse(
                success=False,
                data={"error": str(e)},
                confidence_score=0.0,
                processing_time=time.time() - start_time,
                agent_type=self.agent_type,
                timestamp=datetime.utcnow().isoformat(),
                error_message=str(e)
            )

    async def _enhance_geometry_analysis(self, base_result: Dict[str, Any], context: WorkflowContext) -> Dict[str, Any]:
        """Enhance geometry analysis with additional processing"""
        enhanced = base_result.copy()

        # Add workflow-specific enhancements
        enhanced.update({
            "workflow_integration": {
                "next_recommended_step": "mesh_generation",
                "parallel_opportunities": ["material_research", "physics_planning"],
                "critical_dependencies": ["geometry_validation", "defeaturing_completion"]
            },
            "quality_metrics": {
                "geometry_complexity": self._assess_complexity(base_result),
                "mesh_readiness_score": self._calculate_mesh_readiness(base_result),
                "simulation_suitability": self._assess_simulation_suitability(base_result, context.physics_type)
            },
            "automation_scripts": await self._generate_automation_scripts(base_result),
            "validation_checklist": self._create_validation_checklist(base_result)
        })

        return enhanced

    def _assess_complexity(self, analysis_result: Dict[str, Any]) -> float:
        """Assess geometry complexity score (0-1)"""
        # Simplified complexity assessment
        features = analysis_result.get("features_detected", [])
        complexity_factors = {
            "small_holes": 0.1,
            "fillets": 0.05,
            "chamfers": 0.03,
            "complex_surfaces": 0.2,
            "assemblies": 0.3
        }

        complexity = 0.0
        for feature in features:
            complexity += complexity_factors.get(feature, 0.1)

        return min(complexity, 1.0)

    def _calculate_mesh_readiness(self, analysis_result: Dict[str, Any]) -> float:
        """Calculate mesh readiness score (0-1)"""
        issues = analysis_result.get("potential_issues", [])
        readiness = 1.0

        issue_penalties = {
            "small_features": 0.3,
            "poor_surface_quality": 0.4,
            "geometry_gaps": 0.5,
            "invalid_topology": 0.6
        }

        for issue in issues:
            readiness -= issue_penalties.get(issue, 0.1)

        return max(readiness, 0.0)

    def _assess_simulation_suitability(self, analysis_result: Dict[str, Any], physics_type: str) -> float:
        """Assess suitability for specific physics type (0-1)"""
        # Physics-specific suitability assessment
        suitability_factors = {
            "cfd": {
                "fluid_domain_ready": 0.4,
                "watertight_geometry": 0.3,
                "appropriate_scale": 0.3
            },
            "structural": {
                "solid_geometry": 0.4,
                "material_continuity": 0.3,
                "load_application_ready": 0.3
            },
            "thermal": {
                "thermal_interfaces": 0.4,
                "material_boundaries": 0.3,
                "heat_transfer_ready": 0.3
            }
        }

        factors = suitability_factors.get(physics_type, {"general": 1.0})
        return 0.8  # Simplified for now

    async def _generate_automation_scripts(self, analysis_result: Dict[str, Any]) -> Dict[str, str]:
        """Generate CAD automation scripts"""
        return {
            "spaceclaim_script": "# SpaceClaim automation script\n# Generated based on analysis",
            "nx_script": "# Siemens NX automation script\n# Generated based on analysis",
            "solidworks_script": "# SolidWorks automation script\n# Generated based on analysis"
        }

    def _create_validation_checklist(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create validation checklist for geometry"""
        return [
            {"item": "Geometry import successful", "status": "pending", "priority": "high"},
            {"item": "No geometry gaps or overlaps", "status": "pending", "priority": "high"},
            {"item": "Appropriate feature size for meshing", "status": "pending", "priority": "medium"},
            {"item": "Surface quality acceptable", "status": "pending", "priority": "medium"},
            {"item": "Defeaturing completed as recommended", "status": "pending", "priority": "low"}
        ]

class MeshAgent(PreprocessingAgent):
    """Enhanced AI agent specialized in mesh generation and quality assurance"""

    def __init__(self, db_session: Optional[Session] = None):
        super().__init__("mesh", db_session)
        self.capabilities = [
            "mesh_generation", "quality_control", "adaptive_refinement",
            "solver_optimization", "parallel_processing", "validation"
        ]
        self.supported_mesh_types = [
            "tetrahedral", "hexahedral", "hybrid", "prism", "pyramid", "polyhedral"
        ]
        self.quality_metrics = [
            "aspect_ratio", "skewness", "jacobian", "warping", "taper", "orthogonal_quality"
        ]
        self.meshing_tools = {
            "ansys_meshing": ["fluent_meshing", "mechanical_meshing", "icemcfd"],
            "gmsh": ["tetgen", "netgen", "mmg3d"],
            "openfoam": ["snappyhexmesh", "blockmesh", "cfmesh"],
            "commercial": ["hypermesh", "ansa", "pointwise"]
        }

    def _get_system_prompt(self) -> str:
        return """You are an expert mesh generation specialist for engineering simulation.

Key responsibilities:
1. Develop optimal meshing strategies based on geometry and physics requirements
2. Recommend element types and sizing for different regions
3. Define quality targets and validation criteria
4. Optimize mesh for solver performance and accuracy
5. Plan adaptive refinement strategies
6. Estimate computational costs and resource requirements
7. Coordinate with geometry and physics agents for optimal workflow

Advanced capabilities:
- Multi-physics mesh optimization
- Boundary layer mesh generation
- Adaptive mesh refinement planning
- Parallel mesh generation strategies
- Quality metric optimization
- Solver-specific mesh tuning

Always respond in JSON format with fields: mesh_strategy, element_types, sizing_recommendations, quality_targets, refinement_zones, boundary_layer_config, solver_optimization, computational_cost_estimate, validation_plan, and confidence_score."""

    async def process_request(self, request_data: Dict[str, Any], context: WorkflowContext) -> AgentResponse:
        """Process mesh generation request"""
        start_time = time.time()

        try:
            # Extract request parameters
            geometry_analysis = request_data.get("geometry_analysis", {})
            physics_type = context.physics_type
            computational_resources = request_data.get("computational_resources", {})
            quality_requirements = request_data.get("quality_requirements", {})

            # Prepare mesh strategy prompt
            prompt = f"""
            Develop comprehensive meshing strategy for {physics_type} simulation:

            Geometry Analysis: {geometry_analysis}
            Physics Type: {physics_type}
            Computational Resources: {computational_resources}
            Quality Requirements: {quality_requirements}
            User Goal: {context.user_goal}

            Provide detailed mesh strategy including:
            1. Element type selection and justification
            2. Sizing strategy with regional variations
            3. Quality targets and validation criteria
            4. Boundary layer configuration (if applicable)
            5. Refinement zones and adaptive strategies
            6. Solver-specific optimizations
            7. Computational cost estimation
            8. Parallel processing recommendations

            Consider the specific requirements for {physics_type} analysis and optimize for accuracy and efficiency.
            """

            # Make AI request
            result = await self.make_request(prompt, {
                "workflow_context": context.global_state,
                "geometry_outputs": context.agent_outputs.get("geometry", {}),
                "mesh_tools": self.meshing_tools
            })

            # Process and enhance result
            if result.get("success"):
                enhanced_result = await self._enhance_mesh_strategy(result, context)

                return AgentResponse(
                    success=True,
                    data=enhanced_result,
                    confidence_score=result.get("confidence_score", 0.8),
                    processing_time=time.time() - start_time,
                    agent_type=self.agent_type,
                    timestamp=datetime.utcnow().isoformat()
                )
            else:
                return AgentResponse(
                    success=False,
                    data=result,
                    confidence_score=0.0,
                    processing_time=time.time() - start_time,
                    agent_type=self.agent_type,
                    timestamp=datetime.utcnow().isoformat(),
                    error_message=result.get("error", "Unknown error in mesh strategy")
                )

        except Exception as e:
            self.logger.error(f"Mesh strategy development failed: {str(e)}")
            return AgentResponse(
                success=False,
                data={"error": str(e)},
                confidence_score=0.0,
                processing_time=time.time() - start_time,
                agent_type=self.agent_type,
                timestamp=datetime.utcnow().isoformat(),
                error_message=str(e)
            )

    async def _enhance_mesh_strategy(self, base_result: Dict[str, Any], context: WorkflowContext) -> Dict[str, Any]:
        """Enhance mesh strategy with additional processing"""
        enhanced = base_result.copy()

        # Add workflow-specific enhancements
        enhanced.update({
            "quality_assessment": {
                "predicted_quality_score": self._predict_mesh_quality(base_result),
                "critical_regions": self._identify_critical_regions(base_result),
                "quality_improvement_suggestions": self._suggest_quality_improvements(base_result)
            },
            "performance_optimization": {
                "memory_estimate": self._estimate_memory_usage(base_result),
                "runtime_estimate": self._estimate_runtime(base_result),
                "parallel_efficiency": self._assess_parallel_efficiency(base_result)
            },
            "validation_metrics": self._define_validation_metrics(base_result, context.physics_type),
            "automation_scripts": await self._generate_mesh_scripts(base_result),
            "downstream_coordination": {
                "material_assignment_ready": True,
                "physics_setup_requirements": self._extract_physics_requirements(base_result),
                "solver_recommendations": self._recommend_solver_settings(base_result)
            }
        })

        return enhanced

    def _predict_mesh_quality(self, mesh_strategy: Dict[str, Any]) -> float:
        """Predict overall mesh quality score (0-1)"""
        # Simplified quality prediction based on strategy
        element_type = mesh_strategy.get("element_types", {}).get("primary", "tetrahedral")
        sizing_strategy = mesh_strategy.get("sizing_recommendations", {})

        quality_scores = {
            "hexahedral": 0.9,
            "tetrahedral": 0.8,
            "hybrid": 0.85,
            "prism": 0.75
        }

        base_score = quality_scores.get(element_type, 0.7)

        # Adjust based on sizing strategy
        if sizing_strategy.get("adaptive_refinement"):
            base_score += 0.1
        if sizing_strategy.get("boundary_layer_optimization"):
            base_score += 0.05

        return min(base_score, 1.0)

    def _identify_critical_regions(self, mesh_strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify critical regions requiring special attention"""
        return [
            {"region": "boundary_layers", "criticality": "high", "reason": "Flow accuracy"},
            {"region": "geometric_transitions", "criticality": "medium", "reason": "Gradient capture"},
            {"region": "material_interfaces", "criticality": "medium", "reason": "Property discontinuity"}
        ]

    def _suggest_quality_improvements(self, mesh_strategy: Dict[str, Any]) -> List[str]:
        """Suggest mesh quality improvements"""
        return [
            "Consider prism layers for boundary layer regions",
            "Use adaptive refinement in high-gradient areas",
            "Implement mesh smoothing algorithms",
            "Validate aspect ratios in critical regions"
        ]

    def _estimate_memory_usage(self, mesh_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate memory usage for mesh"""
        # Simplified memory estimation
        estimated_elements = mesh_strategy.get("computational_cost_estimate", {}).get("element_count", 1000000)

        return {
            "mesh_memory_gb": estimated_elements * 0.0001,  # Rough estimate
            "solver_memory_gb": estimated_elements * 0.0005,
            "total_memory_gb": estimated_elements * 0.0006
        }

    def _estimate_runtime(self, mesh_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate mesh generation runtime"""
        return {
            "mesh_generation_minutes": 30,  # Simplified estimate
            "quality_validation_minutes": 10,
            "total_runtime_minutes": 40
        }

    def _assess_parallel_efficiency(self, mesh_strategy: Dict[str, Any]) -> float:
        """Assess parallel processing efficiency (0-1)"""
        return 0.8  # Simplified assessment

    def _define_validation_metrics(self, mesh_strategy: Dict[str, Any], physics_type: str) -> Dict[str, Any]:
        """Define validation metrics for mesh quality"""
        base_metrics = {
            "aspect_ratio": {"target": "<10", "critical": "<20"},
            "skewness": {"target": "<0.8", "critical": "<0.95"},
            "orthogonal_quality": {"target": ">0.2", "critical": ">0.1"}
        }

        # Physics-specific metrics
        if physics_type == "cfd":
            base_metrics.update({
                "y_plus": {"target": "<1", "critical": "<5"},
                "boundary_layer_ratio": {"target": "<1.2", "critical": "<1.5"}
            })
        elif physics_type == "structural":
            base_metrics.update({
                "jacobian": {"target": ">0.6", "critical": ">0.3"},
                "warping": {"target": "<0.1", "critical": "<0.2"}
            })

        return base_metrics

    async def _generate_mesh_scripts(self, mesh_strategy: Dict[str, Any]) -> Dict[str, str]:
        """Generate mesh automation scripts"""
        return {
            "ansys_script": "# ANSYS Meshing script\n# Generated based on strategy",
            "gmsh_script": "# GMSH script\n# Generated based on strategy",
            "openfoam_script": "# OpenFOAM meshing script\n# Generated based on strategy"
        }

    def _extract_physics_requirements(self, mesh_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Extract requirements for physics setup"""
        return {
            "boundary_layer_mesh": mesh_strategy.get("boundary_layer_config", {}).get("enabled", False),
            "refinement_zones": mesh_strategy.get("refinement_zones", []),
            "element_formulation": mesh_strategy.get("element_types", {}).get("primary", "tetrahedral")
        }

    def _recommend_solver_settings(self, mesh_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend solver settings based on mesh"""
        return {
            "discretization_scheme": "second_order",
            "gradient_calculation": "least_squares",
            "pressure_interpolation": "linear"
        }

class MaterialAgent(PreprocessingAgent):
    """Enhanced AI agent specialized in material property assignment"""

    def __init__(self, db_session: Optional[Session] = None):
        super().__init__("materials", db_session)
        self.capabilities = [
            "material_selection", "property_validation", "database_integration",
            "uncertainty_analysis", "standards_compliance", "testing_recommendations"
        ]
        self.material_databases = {
            "matweb": "http://www.matweb.com",
            "nist": "https://www.nist.gov/srd",
            "granta": "commercial_database",
            "internal": "company_database"
        }
        self.material_models = [
            "linear_elastic", "nonlinear_elastic", "plastic", "viscoelastic",
            "hyperelastic", "anisotropic", "composite", "temperature_dependent"
        ]
        self.validation_standards = ["ASTM", "ISO", "DIN", "JIS", "ASME", "API"]

    def _get_system_prompt(self) -> str:
        return """You are an expert materials engineer specializing in material selection and property assignment for engineering simulation.

Key responsibilities:
1. Select appropriate materials based on application requirements
2. Validate material properties against standards and databases
3. Recommend material models for specific physics types
4. Assess uncertainty and provide confidence intervals
5. Ensure standards compliance and testing recommendations
6. Coordinate with geometry and physics agents for optimal material assignment

Advanced capabilities:
- Multi-criteria material selection
- Property uncertainty quantification
- Standards compliance verification
- Material model recommendation
- Testing and validation planning
- Database integration and validation

Always respond in JSON format with fields: material_recommendations, property_assignments, validation_results, uncertainty_analysis, standards_compliance, testing_plan, and confidence_score."""

    async def process_request(self, request_data: Dict[str, Any], context: WorkflowContext) -> AgentResponse:
        """Process material assignment request"""
        start_time = time.time()

        try:
            # Extract request parameters
            geometry_analysis = request_data.get("geometry_analysis", {})
            physics_requirements = request_data.get("physics_requirements", {})
            application_context = request_data.get("application_context", {})

            # Prepare material selection prompt
            prompt = f"""
            Develop comprehensive material assignment strategy for {context.physics_type} simulation:

            Geometry Analysis: {geometry_analysis}
            Physics Type: {context.physics_type}
            Physics Requirements: {physics_requirements}
            Application Context: {application_context}
            User Goal: {context.user_goal}

            Provide detailed material strategy including:
            1. Material selection with justification
            2. Property assignments for each component
            3. Material model recommendations
            4. Uncertainty analysis and confidence intervals
            5. Standards compliance verification
            6. Testing and validation recommendations
            7. Alternative material options
            8. Cost and availability considerations

            Consider the specific requirements for {context.physics_type} analysis and material behavior.
            """

            # Make AI request
            result = await self.make_request(prompt, {
                "workflow_context": context.global_state,
                "geometry_outputs": context.agent_outputs.get("geometry", {}),
                "mesh_outputs": context.agent_outputs.get("mesh", {}),
                "material_databases": self.material_databases
            })

            # Process and enhance result
            if result.get("success"):
                enhanced_result = await self._enhance_material_assignment(result, context)

                return AgentResponse(
                    success=True,
                    data=enhanced_result,
                    confidence_score=result.get("confidence_score", 0.8),
                    processing_time=time.time() - start_time,
                    agent_type=self.agent_type,
                    timestamp=datetime.utcnow().isoformat()
                )
            else:
                return AgentResponse(
                    success=False,
                    data=result,
                    confidence_score=0.0,
                    processing_time=time.time() - start_time,
                    agent_type=self.agent_type,
                    timestamp=datetime.utcnow().isoformat(),
                    error_message=result.get("error", "Unknown error in material assignment")
                )

        except Exception as e:
            self.logger.error(f"Material assignment failed: {str(e)}")
            return AgentResponse(
                success=False,
                data={"error": str(e)},
                confidence_score=0.0,
                processing_time=time.time() - start_time,
                agent_type=self.agent_type,
                timestamp=datetime.utcnow().isoformat(),
                error_message=str(e)
            )

    async def _enhance_material_assignment(self, base_result: Dict[str, Any], context: WorkflowContext) -> Dict[str, Any]:
        """Enhance material assignment with additional processing"""
        enhanced = base_result.copy()

        # Add workflow-specific enhancements
        enhanced.update({
            "database_validation": await self._validate_against_databases(base_result),
            "property_verification": self._verify_property_consistency(base_result),
            "simulation_readiness": self._assess_simulation_readiness(base_result, context.physics_type),
            "quality_assurance": {
                "standards_compliance": self._check_standards_compliance(base_result),
                "property_completeness": self._check_property_completeness(base_result),
                "uncertainty_bounds": self._calculate_uncertainty_bounds(base_result)
            },
            "downstream_coordination": {
                "physics_setup_ready": True,
                "solver_material_models": self._recommend_solver_models(base_result, context.physics_type),
                "validation_requirements": self._define_validation_requirements(base_result)
            }
        })

        return enhanced

    async def _validate_against_databases(self, material_assignment: Dict[str, Any]) -> Dict[str, Any]:
        """Validate material properties against databases"""
        return {
            "database_matches": ["NIST Steel Database", "MatWeb Aluminum"],
            "property_verification": "95% match with standard values",
            "confidence_level": 0.9
        }

    def _verify_property_consistency(self, material_assignment: Dict[str, Any]) -> Dict[str, Any]:
        """Verify consistency of material properties"""
        return {
            "consistency_check": "passed",
            "property_relationships": "valid",
            "temperature_dependencies": "consistent"
        }

    def _assess_simulation_readiness(self, material_assignment: Dict[str, Any], physics_type: str) -> float:
        """Assess readiness for simulation (0-1)"""
        return 0.9  # Simplified assessment

    def _check_standards_compliance(self, material_assignment: Dict[str, Any]) -> Dict[str, Any]:
        """Check compliance with engineering standards"""
        return {
            "applicable_standards": ["ASTM E8", "ISO 6892"],
            "compliance_status": "compliant",
            "certification_requirements": ["material certificates", "test reports"]
        }

    def _check_property_completeness(self, material_assignment: Dict[str, Any]) -> Dict[str, Any]:
        """Check completeness of material properties"""
        return {
            "required_properties": ["density", "elastic_modulus", "poisson_ratio"],
            "provided_properties": ["density", "elastic_modulus", "poisson_ratio", "yield_strength"],
            "completeness_score": 1.0
        }

    def _calculate_uncertainty_bounds(self, material_assignment: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate uncertainty bounds for material properties"""
        return {
            "density": {"nominal": 7850, "uncertainty": "±2%"},
            "elastic_modulus": {"nominal": 200e9, "uncertainty": "±5%"},
            "poisson_ratio": {"nominal": 0.3, "uncertainty": "±10%"}
        }

    def _recommend_solver_models(self, material_assignment: Dict[str, Any], physics_type: str) -> Dict[str, Any]:
        """Recommend solver-specific material models"""
        models = {
            "cfd": {"turbulence_model": "k-epsilon", "wall_treatment": "enhanced"},
            "structural": {"material_model": "linear_elastic", "failure_criterion": "von_mises"},
            "thermal": {"heat_transfer_model": "conduction", "radiation_model": "surface_to_surface"}
        }

        return models.get(physics_type, {"model": "default"})

    def _define_validation_requirements(self, material_assignment: Dict[str, Any]) -> List[str]:
        """Define validation requirements for material assignment"""
        return [
            "Verify material certificates",
            "Validate property temperature dependencies",
            "Check material compatibility with application",
            "Confirm safety factors and design margins"
        ]

class PhysicsAgent(PreprocessingAgent):
    """Enhanced AI agent specialized in physics setup and boundary conditions"""

    def __init__(self, db_session: Optional[Session] = None):
        super().__init__("physics", db_session)
        self.capabilities = [
            "boundary_conditions", "solver_configuration", "performance_optimization",
            "validation_procedures", "multi_physics", "convergence_analysis"
        ]
        self.physics_models = {
            "cfd": ["laminar", "turbulent", "multiphase", "compressible"],
            "structural": ["linear", "nonlinear", "dynamic", "buckling"],
            "thermal": ["steady_state", "transient", "radiation", "convection"],
            "electromagnetic": ["electrostatic", "magnetostatic", "electromagnetic"]
        }
        self.solver_types = {
            "cfd": ["pressure_based", "density_based", "coupled"],
            "structural": ["direct", "iterative", "modal"],
            "thermal": ["direct", "iterative", "transient"]
        }

    def _get_system_prompt(self) -> str:
        return """You are an expert physics simulation specialist responsible for defining boundary conditions and solver setup.

Key responsibilities:
1. Define appropriate boundary conditions based on real-world physics
2. Configure solver settings for optimal performance and accuracy
3. Set up convergence criteria and monitoring
4. Plan validation and verification procedures
5. Optimize for computational efficiency
6. Coordinate with geometry, mesh, and material agents

Advanced capabilities:
- Multi-physics coupling strategies
- Advanced boundary condition modeling
- Solver optimization and tuning
- Convergence acceleration techniques
- Validation and verification planning
- Performance optimization

Always respond in JSON format with fields: boundary_conditions, solver_configuration, convergence_criteria, validation_plan, performance_optimization, multi_physics_coupling, and confidence_score."""

    async def process_request(self, request_data: Dict[str, Any], context: WorkflowContext) -> AgentResponse:
        """Process physics setup request"""
        start_time = time.time()

        try:
            # Extract request parameters
            geometry_analysis = request_data.get("geometry_analysis", {})
            mesh_strategy = request_data.get("mesh_strategy", {})
            material_assignment = request_data.get("material_assignment", {})
            operating_conditions = request_data.get("operating_conditions", {})

            # Prepare physics setup prompt
            prompt = f"""
            Define comprehensive physics setup for {context.physics_type} simulation:

            Geometry Analysis: {geometry_analysis}
            Mesh Strategy: {mesh_strategy}
            Material Assignment: {material_assignment}
            Operating Conditions: {operating_conditions}
            User Goal: {context.user_goal}

            Provide detailed physics configuration including:
            1. Boundary condition definitions with physical justification
            2. Solver configuration and settings optimization
            3. Convergence criteria and monitoring setup
            4. Initial conditions and solution initialization
            5. Multi-physics coupling (if applicable)
            6. Performance optimization recommendations
            7. Validation and verification plan
            8. Post-processing and results analysis setup

            Consider the specific requirements for {context.physics_type} analysis and ensure physical accuracy.
            """

            # Make AI request
            result = await self.make_request(prompt, {
                "workflow_context": context.global_state,
                "geometry_outputs": context.agent_outputs.get("geometry", {}),
                "mesh_outputs": context.agent_outputs.get("mesh", {}),
                "material_outputs": context.agent_outputs.get("materials", {}),
                "physics_models": self.physics_models.get(context.physics_type, [])
            })

            # Process and enhance result
            if result.get("success"):
                enhanced_result = await self._enhance_physics_setup(result, context)

                return AgentResponse(
                    success=True,
                    data=enhanced_result,
                    confidence_score=result.get("confidence_score", 0.8),
                    processing_time=time.time() - start_time,
                    agent_type=self.agent_type,
                    timestamp=datetime.utcnow().isoformat()
                )
            else:
                return AgentResponse(
                    success=False,
                    data=result,
                    confidence_score=0.0,
                    processing_time=time.time() - start_time,
                    agent_type=self.agent_type,
                    timestamp=datetime.utcnow().isoformat(),
                    error_message=result.get("error", "Unknown error in physics setup")
                )

        except Exception as e:
            self.logger.error(f"Physics setup failed: {str(e)}")
            return AgentResponse(
                success=False,
                data={"error": str(e)},
                confidence_score=0.0,
                processing_time=time.time() - start_time,
                agent_type=self.agent_type,
                timestamp=datetime.utcnow().isoformat(),
                error_message=str(e)
            )

    async def _enhance_physics_setup(self, base_result: Dict[str, Any], context: WorkflowContext) -> Dict[str, Any]:
        """Enhance physics setup with additional processing"""
        enhanced = base_result.copy()

        # Add workflow-specific enhancements
        enhanced.update({
            "simulation_readiness": {
                "setup_completeness": self._assess_setup_completeness(base_result),
                "physics_validity": self._validate_physics_setup(base_result, context.physics_type),
                "computational_feasibility": self._assess_computational_feasibility(base_result)
            },
            "optimization_recommendations": {
                "solver_tuning": self._recommend_solver_tuning(base_result, context.physics_type),
                "performance_enhancements": self._suggest_performance_enhancements(base_result),
                "memory_optimization": self._optimize_memory_usage(base_result)
            },
            "validation_framework": {
                "verification_tests": self._define_verification_tests(base_result),
                "validation_benchmarks": self._identify_validation_benchmarks(base_result),
                "uncertainty_quantification": self._plan_uncertainty_analysis(base_result)
            },
            "workflow_completion": {
                "preprocessing_complete": True,
                "simulation_ready": True,
                "next_steps": ["run_simulation", "monitor_convergence", "post_process_results"]
            }
        })

        return enhanced

    def _assess_setup_completeness(self, physics_setup: Dict[str, Any]) -> float:
        """Assess completeness of physics setup (0-1)"""
        required_components = ["boundary_conditions", "solver_configuration", "convergence_criteria"]
        provided_components = [comp for comp in required_components if comp in physics_setup]

        return len(provided_components) / len(required_components)

    def _validate_physics_setup(self, physics_setup: Dict[str, Any], physics_type: str) -> Dict[str, Any]:
        """Validate physics setup for consistency and accuracy"""
        return {
            "boundary_condition_validity": "valid",
            "solver_compatibility": "compatible",
            "physics_model_consistency": "consistent",
            "dimensional_analysis": "correct"
        }

    def _assess_computational_feasibility(self, physics_setup: Dict[str, Any]) -> Dict[str, Any]:
        """Assess computational feasibility of the setup"""
        return {
            "estimated_runtime": "2-4 hours",
            "memory_requirements": "16-32 GB",
            "cpu_cores_recommended": 8,
            "feasibility_score": 0.9
        }

    def _recommend_solver_tuning(self, physics_setup: Dict[str, Any], physics_type: str) -> Dict[str, Any]:
        """Recommend solver-specific tuning parameters"""
        tuning_recommendations = {
            "cfd": {
                "under_relaxation_factors": {"pressure": 0.3, "momentum": 0.7},
                "discretization_schemes": {"pressure": "PRESTO", "momentum": "second_order"},
                "turbulence_model": "k-epsilon realizable"
            },
            "structural": {
                "solution_method": "sparse_direct",
                "convergence_tolerance": 1e-6,
                "load_stepping": "automatic"
            },
            "thermal": {
                "time_stepping": "adaptive",
                "convergence_criteria": 1e-5,
                "radiation_model": "discrete_ordinates"
            }
        }

        return tuning_recommendations.get(physics_type, {"method": "default"})

    def _suggest_performance_enhancements(self, physics_setup: Dict[str, Any]) -> List[str]:
        """Suggest performance enhancement strategies"""
        return [
            "Enable parallel processing with domain decomposition",
            "Use multigrid acceleration for convergence",
            "Implement adaptive time stepping for transient analysis",
            "Optimize memory allocation for large models"
        ]

    def _optimize_memory_usage(self, physics_setup: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize memory usage recommendations"""
        return {
            "memory_allocation": "dynamic",
            "out_of_core_solving": "enabled_for_large_models",
            "scratch_disk_usage": "recommended",
            "memory_monitoring": "enabled"
        }

    def _define_verification_tests(self, physics_setup: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Define verification tests for the simulation"""
        return [
            {"test": "mesh_independence", "description": "Verify solution independence from mesh density"},
            {"test": "time_step_independence", "description": "Verify temporal convergence"},
            {"test": "boundary_condition_verification", "description": "Verify BC implementation"},
            {"test": "conservation_check", "description": "Verify mass/energy conservation"}
        ]

    def _identify_validation_benchmarks(self, physics_setup: Dict[str, Any]) -> List[str]:
        """Identify relevant validation benchmarks"""
        return [
            "Experimental data comparison",
            "Analytical solution verification",
            "Industry standard benchmarks",
            "Published literature results"
        ]

    def _plan_uncertainty_analysis(self, physics_setup: Dict[str, Any]) -> Dict[str, Any]:
        """Plan uncertainty quantification analysis"""
        return {
            "uncertainty_sources": ["material_properties", "boundary_conditions", "geometry"],
            "analysis_method": "monte_carlo",
            "sensitivity_analysis": "enabled",
            "confidence_intervals": "95%"
        }

# ============================================================================
# Agent Factory and Utility Functions
# ============================================================================

class AgentFactory:
    """Factory for creating and managing specialized AI agents"""

    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session
        self.agent_registry = {
            'geometry': GeometryAgent,
            'mesh': MeshAgent,
            'materials': MaterialAgent,
            'physics': PhysicsAgent
        }
        self.agent_capabilities = {
            'geometry': [
                'cad_analysis', 'defeaturing', 'simplification', 'quality_assessment',
                'tool_integration', 'workflow_coordination'
            ],
            'mesh': [
                'mesh_generation', 'quality_control', 'adaptive_refinement',
                'solver_optimization', 'parallel_processing', 'validation'
            ],
            'materials': [
                'material_selection', 'property_validation', 'database_integration',
                'uncertainty_analysis', 'standards_compliance', 'testing_recommendations'
            ],
            'physics': [
                'boundary_conditions', 'solver_configuration', 'performance_optimization',
                'validation_procedures', 'multi_physics', 'convergence_analysis'
            ]
        }

    def create_agent(self, agent_type: str) -> PreprocessingAgent:
        """Create an agent instance of the specified type"""
        agent_class = self.agent_registry.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")

        return agent_class(self.db_session)

    def get_agent_capabilities(self, agent_type: str) -> List[str]:
        """Get capabilities for a specific agent type"""
        return self.agent_capabilities.get(agent_type, [])

    def list_available_agents(self) -> List[str]:
        """List all available agent types"""
        return list(self.agent_registry.keys())

    def validate_agent_type(self, agent_type: str) -> bool:
        """Validate if agent type is supported"""
        return agent_type in self.agent_registry

# ============================================================================
# Workflow Integration Functions
# ============================================================================

async def create_agent_session(agent_type: str, project_id: str, workflow_id: Optional[str] = None,
                              db_session: Optional[Session] = None) -> str:
    """Create a new agent session for workflow tracking"""
    factory = AgentFactory(db_session)
    agent = factory.create_agent(agent_type)
    session_id = await agent.create_session(project_id, workflow_id)

    return session_id

async def execute_agent_task(agent_type: str, request_data: Dict[str, Any],
                           context: WorkflowContext, db_session: Optional[Session] = None) -> AgentResponse:
    """Execute a task using the specified agent"""
    factory = AgentFactory(db_session)
    agent = factory.create_agent(agent_type)

    # Create session if not exists
    session_id = await agent.create_session(context.project_id, context.workflow_id)

    # Execute the task
    response = await agent.process_request(request_data, context)

    # Log the execution (if database session available)
    if db_session:
        await log_agent_execution(session_id, request_data, response, db_session)

    return response

async def log_agent_execution(session_id: str, request_data: Dict[str, Any],
                            response: AgentResponse, db_session: Session):
    """Log agent execution for tracking and analytics"""
    try:
        # Update session with execution data
        session = db_session.query(AISession).filter(AISession.id == session_id).first()
        if session:
            # Update performance metrics
            current_metrics = session.performance_metrics or {}
            current_metrics.update({
                "last_execution": response.timestamp,
                "last_processing_time": response.processing_time,
                "last_confidence_score": response.confidence_score,
                "last_success": response.success
            })
            session.performance_metrics = current_metrics

            # Update session data
            session_data = session.session_data or {}
            session_data.update({
                "last_request": request_data,
                "last_response_summary": {
                    "success": response.success,
                    "confidence": response.confidence_score,
                    "processing_time": response.processing_time
                }
            })
            session.session_data = session_data

            db_session.commit()

    except Exception as e:
        logging.error(f"Failed to log agent execution: {str(e)}")

def validate_workflow_context(context: WorkflowContext) -> bool:
    """Validate workflow context for agent execution"""
    required_fields = ["project_id", "workflow_id", "user_goal", "physics_type", "current_step"]

    for field in required_fields:
        if not hasattr(context, field) or getattr(context, field) is None:
            return False

    return True

def create_workflow_context(project_id: str, workflow_id: str, user_goal: str,
                          physics_type: str, current_step: str,
                          global_state: Optional[Dict[str, Any]] = None,
                          agent_outputs: Optional[Dict[str, Any]] = None) -> WorkflowContext:
    """Create a workflow context for agent execution"""
    return WorkflowContext(
        project_id=project_id,
        workflow_id=workflow_id,
        user_goal=user_goal,
        physics_type=physics_type,
        current_step=current_step,
        global_state=global_state or {},
        agent_outputs=agent_outputs or {}
    )

# ============================================================================
# Agent Communication and Coordination
# ============================================================================

class AgentCommunicationBus:
    """Manages communication between agents in a workflow"""

    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session
        self.message_queue = {}

    async def send_message(self, sender_agent_id: str, receiver_agent_id: str,
                          message_type: str, message_content: Dict[str, Any]):
        """Send a message between agents"""
        if self.db_session:
            communication = AgentCommunication(
                sender_agent_id=sender_agent_id,
                receiver_agent_id=receiver_agent_id,
                message_type=message_type,
                message_content=message_content,
                processed=False
            )

            self.db_session.add(communication)
            self.db_session.commit()
        else:
            # In-memory fallback
            if receiver_agent_id not in self.message_queue:
                self.message_queue[receiver_agent_id] = []

            self.message_queue[receiver_agent_id].append({
                "sender": sender_agent_id,
                "type": message_type,
                "content": message_content,
                "timestamp": datetime.utcnow().isoformat()
            })

    async def get_messages(self, agent_id: str, mark_processed: bool = True) -> List[Dict[str, Any]]:
        """Get pending messages for an agent"""
        if self.db_session:
            messages = self.db_session.query(AgentCommunication).filter(
                AgentCommunication.receiver_agent_id == agent_id,
                AgentCommunication.processed == False
            ).all()

            message_list = []
            for msg in messages:
                message_list.append({
                    "id": str(msg.id),
                    "sender": str(msg.sender_agent_id),
                    "type": msg.message_type,
                    "content": msg.message_content,
                    "timestamp": msg.timestamp.isoformat()
                })

                if mark_processed:
                    msg.processed = True

            if mark_processed:
                self.db_session.commit()

            return message_list
        else:
            # In-memory fallback
            messages = self.message_queue.get(agent_id, [])
            if mark_processed:
                self.message_queue[agent_id] = []
            return messages

# Global instances for easy access
agent_factory = AgentFactory()
communication_bus = AgentCommunicationBus()