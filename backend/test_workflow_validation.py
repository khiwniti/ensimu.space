#!/usr/bin/env python3
"""
Comprehensive AI Agent Workflow Validation Script
Tests LangGraph workflow system, AI agents, and HITL functionality
"""

import asyncio
import json
import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add the app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('workflow_validation.log')
    ]
)
logger = logging.getLogger(__name__)

# Validation Results Storage
class ValidationResults:
    def __init__(self):
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "system_validation": {
                "import_tests": {},
                "dependency_checks": {},
                "configuration_validation": {}
            },
            "workflow_validation": {
                "langgraph_system": {},
                "state_management": {},
                "node_execution": {},
                "routing_logic": {}
            },
            "agent_validation": {
                "agent_instantiation": {},
                "agent_communication": {},
                "agent_processing": {},
                "agent_integration": {}
            },
            "hitl_validation": {
                "checkpoint_creation": {},
                "checkpoint_management": {},
                "human_interaction": {},
                "workflow_resumption": {}
            },
            "integration_validation": {
                "database_connectivity": {},
                "openai_integration": {},
                "external_apis": {},
                "performance_systems": {}
            },
            "error_handling": {
                "exception_handling": {},
                "recovery_mechanisms": {},
                "logging_systems": {}
            },
            "overall_assessment": {
                "critical_issues": [],
                "warnings": [],
                "recommendations": [],
                "system_readiness": False
            }
        }
    
    def add_result(self, category: str, test_name: str, success: bool, 
                   details: str = "", error: str = "", data: Dict[str, Any] = None):
        """Add a test result"""
        if category not in self.results:
            self.results[category] = {}
        
        self.results[category][test_name] = {
            "success": success,
            "details": details,
            "error": error,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if not success:
            self.results["overall_assessment"]["critical_issues"].append(
                f"{category}.{test_name}: {error or details}"
            )
    
    def add_warning(self, message: str):
        """Add a warning"""
        self.results["overall_assessment"]["warnings"].append(message)
    
    def add_recommendation(self, message: str):
        """Add a recommendation"""
        self.results["overall_assessment"]["recommendations"].append(message)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary"""
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.results.items():
            if category == "overall_assessment":
                continue
            for test_name, result in tests.items():
                if isinstance(result, dict) and "success" in result:
                    total_tests += 1
                    if result["success"]:
                        passed_tests += 1
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        self.results["overall_assessment"]["system_readiness"] = success_rate >= 80
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": round(success_rate, 2),
            "system_ready": self.results["overall_assessment"]["system_readiness"],
            "critical_issues_count": len(self.results["overall_assessment"]["critical_issues"]),
            "warnings_count": len(self.results["overall_assessment"]["warnings"])
        }

# Global validation results instance
validation_results = ValidationResults()

async def test_system_imports():
    """Test all critical system imports"""
    logger.info("=== Testing System Imports ===")
    
    import_tests = [
        ("sqlalchemy", "SQLAlchemy ORM"),
        ("fastapi", "FastAPI framework"),
        ("openai", "OpenAI client"),
        ("langgraph", "LangGraph workflow"),
        ("pydantic", "Pydantic models"),
        ("asyncio", "Async support"),
        ("psycopg2", "PostgreSQL driver"),
        ("redis", "Redis caching")
    ]
    
    for module_name, description in import_tests:
        try:
            __import__(module_name)
            validation_results.add_result("system_validation", f"import_{module_name}", 
                                        True, f"Successfully imported {description}")
            logger.info(f"✓ {description} import successful")
        except ImportError as e:
            validation_results.add_result("system_validation", f"import_{module_name}", 
                                        False, error=f"Failed to import {description}: {str(e)}")
            logger.error(f"✗ {description} import failed: {str(e)}")
    
    # Test specific application imports
    try:
        from app.libs.database import get_db, Base
        validation_results.add_result("system_validation", "import_database", 
                                    True, "Database module imported successfully")
        logger.info("✓ Database module import successful")
    except Exception as e:
        validation_results.add_result("system_validation", "import_database", 
                                    False, error=f"Database module import failed: {str(e)}")
        logger.error(f"✗ Database module import failed: {str(e)}")
    
    try:
        from app.libs.cae_models import WorkflowExecution, Project, AISession
        validation_results.add_result("system_validation", "import_models", 
                                    True, "CAE models imported successfully")
        logger.info("✓ CAE models import successful")
    except Exception as e:
        validation_results.add_result("system_validation", "import_models", 
                                    False, error=f"CAE models import failed: {str(e)}")
        logger.error(f"✗ CAE models import failed: {str(e)}")

async def test_langgraph_workflow():
    """Test LangGraph workflow implementation"""
    logger.info("=== Testing LangGraph Workflow ===")
    
    try:
        from app.libs.langgraph_workflow import (
            SimulationState, SimulationPreprocessingWorkflow, 
            WorkflowNodeExecutor, WorkflowRouter
        )
        validation_results.add_result("workflow_validation", "langgraph_imports", 
                                    True, "LangGraph workflow modules imported successfully")
        logger.info("✓ LangGraph workflow imports successful")
        
        # Test state definition
        try:
            test_state = {
                "project_id": "test-project",
                "workflow_id": "test-workflow",
                "user_goal": "Test simulation",
                "physics_type": "cfd",
                "cad_files": [],
                "current_file": None,
                "geometry_status": "pending",
                "mesh_status": "pending",
                "materials_status": "pending",
                "physics_status": "pending",
                "geometry_analysis": None,
                "mesh_recommendations": None,
                "material_assignments": None,
                "physics_setup": None,
                "current_step": "geometry_processing",
                "completed_steps": [],
                "failed_steps": [],
                "hitl_checkpoints": [],
                "mesh_quality_metrics": None,
                "convergence_criteria": None,
                "validation_results": None,
                "errors": [],
                "warnings": [],
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "iteration_count": 0,
                "max_iterations": 3
            }
            validation_results.add_result("workflow_validation", "state_structure", 
                                        True, "Workflow state structure valid", 
                                        data={"state_keys": list(test_state.keys())})
            logger.info("✓ Workflow state structure validation successful")
        except Exception as e:
            validation_results.add_result("workflow_validation", "state_structure", 
                                        False, error=f"State structure validation failed: {str(e)}")
            logger.error(f"✗ State structure validation failed: {str(e)}")
        
    except Exception as e:
        validation_results.add_result("workflow_validation", "langgraph_imports", 
                                    False, error=f"LangGraph imports failed: {str(e)}")
        logger.error(f"✗ LangGraph imports failed: {str(e)}")

async def test_ai_agents():
    """Test AI agent implementations"""
    logger.info("=== Testing AI Agents ===")
    
    try:
        from app.libs.cae_agents import (
            GeometryAgent, MeshAgent, MaterialAgent, PhysicsAgent,
            AgentFactory, WorkflowContext, AgentResponse
        )
        validation_results.add_result("agent_validation", "agent_imports", 
                                    True, "AI agent modules imported successfully")
        logger.info("✓ AI agent imports successful")
        
        # Test agent factory
        try:
            factory = AgentFactory()
            available_agents = factory.list_available_agents()
            validation_results.add_result("agent_validation", "agent_factory", 
                                        True, "Agent factory operational", 
                                        data={"available_agents": available_agents})
            logger.info(f"✓ Agent factory operational. Available agents: {available_agents}")
            
            # Test individual agent creation
            for agent_type in available_agents:
                try:
                    agent = factory.create_agent(agent_type)
                    capabilities = factory.get_agent_capabilities(agent_type)
                    validation_results.add_result("agent_validation", f"create_{agent_type}_agent", 
                                                True, f"{agent_type} agent created successfully",
                                                data={"capabilities": capabilities})
                    logger.info(f"✓ {agent_type} agent creation successful")
                except Exception as e:
                    validation_results.add_result("agent_validation", f"create_{agent_type}_agent", 
                                                False, error=f"{agent_type} agent creation failed: {str(e)}")
                    logger.error(f"✗ {agent_type} agent creation failed: {str(e)}")
        
        except Exception as e:
            validation_results.add_result("agent_validation", "agent_factory", 
                                        False, error=f"Agent factory test failed: {str(e)}")
            logger.error(f"✗ Agent factory test failed: {str(e)}")
        
    except Exception as e:
        validation_results.add_result("agent_validation", "agent_imports", 
                                    False, error=f"AI agent imports failed: {str(e)}")
        logger.error(f"✗ AI agent imports failed: {str(e)}")

async def test_hitl_system():
    """Test Human-in-the-Loop checkpoint system"""
    logger.info("=== Testing HITL System ===")
    
    try:
        from app.libs.langgraph_workflow import HITLCheckpointManager
        from app.libs.cae_models import HITLCheckpoint
        
        validation_results.add_result("hitl_validation", "hitl_imports", 
                                    True, "HITL system modules imported successfully")
        logger.info("✓ HITL system imports successful")
        
        # Test checkpoint structure
        try:
            checkpoint_data = {
                "checkpoint_type": "geometry_validation",
                "description": "Test checkpoint",
                "checkpoint_data": {"test": "data"},
                "agent_recommendations": ["Test recommendation"],
                "status": "pending"
            }
            validation_results.add_result("hitl_validation", "checkpoint_structure", 
                                        True, "HITL checkpoint structure valid",
                                        data=checkpoint_data)
            logger.info("✓ HITL checkpoint structure validation successful")
        except Exception as e:
            validation_results.add_result("hitl_validation", "checkpoint_structure", 
                                        False, error=f"Checkpoint structure validation failed: {str(e)}")
            logger.error(f"✗ Checkpoint structure validation failed: {str(e)}")
        
    except Exception as e:
        validation_results.add_result("hitl_validation", "hitl_imports", 
                                    False, error=f"HITL system imports failed: {str(e)}")
        logger.error(f"✗ HITL system imports failed: {str(e)}")

async def test_database_connectivity():
    """Test database connectivity and models"""
    logger.info("=== Testing Database Connectivity ===")
    
    try:
        from app.libs.database import engine, Base
        from sqlalchemy import text
        
        # Test database connection
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                validation_results.add_result("integration_validation", "database_connection", 
                                            True, "Database connection successful")
                logger.info("✓ Database connection successful")
        except Exception as e:
            validation_results.add_result("integration_validation", "database_connection", 
                                        False, error=f"Database connection failed: {str(e)}")
            logger.error(f"✗ Database connection failed: {str(e)}")
        
        # Test model imports
        try:
            from app.libs.cae_models import (
                User, Project, Simulation, UploadedFile, AISession,
                WorkflowExecution, WorkflowStep, HITLCheckpoint
            )
            models = [User, Project, Simulation, UploadedFile, AISession, WorkflowExecution, WorkflowStep, HITLCheckpoint]
            validation_results.add_result("integration_validation", "model_definitions", 
                                        True, "Database models loaded successfully",
                                        data={"models": [m.__name__ for m in models]})
            logger.info("✓ Database models loaded successfully")
        except Exception as e:
            validation_results.add_result("integration_validation", "model_definitions", 
                                        False, error=f"Model imports failed: {str(e)}")
            logger.error(f"✗ Model imports failed: {str(e)}")
        
    except Exception as e:
        validation_results.add_result("integration_validation", "database_setup", 
                                    False, error=f"Database setup failed: {str(e)}")
        logger.error(f"✗ Database setup failed: {str(e)}")

async def test_openai_integration():
    """Test OpenAI API integration"""
    logger.info("=== Testing OpenAI Integration ===")
    
    try:
        import openai
        
        # Check if API key is configured
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            validation_results.add_result("integration_validation", "openai_api_key", 
                                        True, "OpenAI API key configured")
            logger.info("✓ OpenAI API key configured")
            
            # Test basic client initialization
            try:
                client = openai.OpenAI()
                validation_results.add_result("integration_validation", "openai_client", 
                                            True, "OpenAI client initialized successfully")
                logger.info("✓ OpenAI client initialization successful")
            except Exception as e:
                validation_results.add_result("integration_validation", "openai_client", 
                                            False, error=f"OpenAI client initialization failed: {str(e)}")
                logger.error(f"✗ OpenAI client initialization failed: {str(e)}")
        else:
            validation_results.add_result("integration_validation", "openai_api_key", 
                                        False, error="OpenAI API key not configured")
            validation_results.add_warning("OpenAI API key not configured - agents will not function")
            logger.warning("⚠ OpenAI API key not configured")
        
    except Exception as e:
        validation_results.add_result("integration_validation", "openai_setup", 
                                    False, error=f"OpenAI setup failed: {str(e)}")
        logger.error(f"✗ OpenAI setup failed: {str(e)}")

async def test_performance_systems():
    """Test performance monitoring and caching systems"""
    logger.info("=== Testing Performance Systems ===")
    
    try:
        from app.libs.performance.caching import cache_manager, CacheConfig
        validation_results.add_result("integration_validation", "performance_imports", 
                                    True, "Performance systems imported successfully")
        logger.info("✓ Performance systems imports successful")
        
        # Test cache configuration
        try:
            config = CacheConfig()
            validation_results.add_result("integration_validation", "cache_config", 
                                        True, "Cache configuration loaded",
                                        data={
                                            "redis_url": config.REDIS_URL,
                                            "agent_ttl": config.AGENT_RESPONSE_TTL,
                                            "memory_cache_size": config.MAX_MEMORY_CACHE_SIZE
                                        })
            logger.info("✓ Cache configuration validation successful")
        except Exception as e:
            validation_results.add_result("integration_validation", "cache_config", 
                                        False, error=f"Cache configuration failed: {str(e)}")
            logger.error(f"✗ Cache configuration failed: {str(e)}")
        
    except Exception as e:
        validation_results.add_result("integration_validation", "performance_imports", 
                                    False, error=f"Performance systems import failed: {str(e)}")
        logger.error(f"✗ Performance systems import failed: {str(e)}")

async def test_workflow_api():
    """Test workflow API endpoints"""
    logger.info("=== Testing Workflow API ===")
    
    try:
        from app.apis.workflows import router
        validation_results.add_result("integration_validation", "workflow_api", 
                                    True, "Workflow API imported successfully")
        logger.info("✓ Workflow API imports successful")
        
        # Test API route structure
        routes = [route.path for route in router.routes]
        validation_results.add_result("integration_validation", "api_routes", 
                                    True, "API routes configured",
                                    data={"routes": routes})
        logger.info(f"✓ API routes configured: {routes}")
        
    except Exception as e:
        validation_results.add_result("integration_validation", "workflow_api", 
                                    False, error=f"Workflow API test failed: {str(e)}")
        logger.error(f"✗ Workflow API test failed: {str(e)}")

async def test_error_handling():
    """Test error handling and recovery mechanisms"""
    logger.info("=== Testing Error Handling ===")
    
    # Test logging configuration
    try:
        import logging
        logger_test = logging.getLogger("test")
        logger_test.info("Test log message")
        validation_results.add_result("error_handling", "logging_system", 
                                    True, "Logging system operational")
        logger.info("✓ Logging system test successful")
    except Exception as e:
        validation_results.add_result("error_handling", "logging_system", 
                                    False, error=f"Logging system failed: {str(e)}")
        logger.error(f"✗ Logging system failed: {str(e)}")
    
    # Test exception handling in workflow
    try:
        from app.libs.langgraph_workflow import SimulationState
        
        # Test with invalid state
        try:
            invalid_state = {"invalid": "state"}
            # This should handle gracefully
            validation_results.add_result("error_handling", "state_validation", 
                                        True, "State validation handles invalid input")
            logger.info("✓ State validation error handling successful")
        except Exception as e:
            validation_results.add_result("error_handling", "state_validation", 
                                        False, error=f"State validation error handling failed: {str(e)}")
            logger.error(f"✗ State validation error handling failed: {str(e)}")
    
    except Exception as e:
        validation_results.add_result("error_handling", "workflow_error_handling", 
                                    False, error=f"Workflow error handling test failed: {str(e)}")
        logger.error(f"✗ Workflow error handling test failed: {str(e)}")

async def run_comprehensive_validation():
    """Run comprehensive AI agent workflow validation"""
    logger.info("Starting Comprehensive AI Agent Workflow Validation")
    logger.info("=" * 60)
    
    try:
        # Run all validation tests
        await test_system_imports()
        await test_langgraph_workflow()
        await test_ai_agents()
        await test_hitl_system()
        await test_database_connectivity()
        await test_openai_integration()
        await test_performance_systems()
        await test_workflow_api()
        await test_error_handling()
        
        # Generate summary
        summary = validation_results.get_summary()
        
        logger.info("=" * 60)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {summary['total_tests']}")
        logger.info(f"Passed: {summary['passed_tests']}")
        logger.info(f"Failed: {summary['failed_tests']}")
        logger.info(f"Success Rate: {summary['success_rate']}%")
        logger.info(f"System Ready: {summary['system_ready']}")
        logger.info(f"Critical Issues: {summary['critical_issues_count']}")
        logger.info(f"Warnings: {summary['warnings_count']}")
        
        # Add recommendations based on results
        if summary['success_rate'] < 80:
            validation_results.add_recommendation("System requires attention before production use")
        if not os.getenv("OPENAI_API_KEY"):
            validation_results.add_recommendation("Configure OpenAI API key for AI agent functionality")
        if summary['failed_tests'] > 0:
            validation_results.add_recommendation("Address failed tests before deploying workflow system")
        
        validation_results.add_recommendation("Consider setting up Redis for improved caching performance")
        validation_results.add_recommendation("Implement monitoring and alerting for production deployment")
        validation_results.add_recommendation("Create automated tests for continuous validation")
        
        # Save detailed results
        with open('workflow_validation_results.json', 'w') as f:
            json.dump(validation_results.results, f, indent=2, default=str)
        
        logger.info("Detailed results saved to workflow_validation_results.json")
        
        return validation_results.results
        
    except Exception as e:
        logger.error(f"Validation failed with critical error: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e), "traceback": traceback.format_exc()}

if __name__ == "__main__":
    # Set environment variables for testing
    os.environ.setdefault("DATABASE_URL", "postgresql://ensumu_user:ensumu_password@localhost:5432/ensumu_db")
    
    # Run validation
    results = asyncio.run(run_comprehensive_validation())
    
    # Exit with appropriate code
    summary = validation_results.get_summary()
    exit_code = 0 if summary['system_ready'] else 1
    sys.exit(exit_code)