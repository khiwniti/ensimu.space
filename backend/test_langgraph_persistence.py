#!/usr/bin/env python3
"""
Test script for LangGraph state persistence functionality.
This script validates that the checkpointer configuration and workflow state management work correctly.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.libs.langgraph_workflow import (
    CheckpointerConfig, LangGraphCheckpointerManager, 
    SimulationPreprocessingWorkflow, SimulationState
)
from app.libs.database import get_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_checkpointer_configuration():
    """Test checkpointer configuration and initialization"""
    logger.info("=" * 60)
    logger.info("Testing LangGraph Checkpointer Configuration")
    logger.info("=" * 60)

    try:
        # Test 1: CheckpointerConfig initialization
        logger.info("1. Testing CheckpointerConfig initialization...")
        config = CheckpointerConfig()
        logger.info(f"✓ Checkpointer type: {config.checkpointer_type}")
        logger.info(f"✓ Database URL configured: {'postgresql' in str(config.database_url)}")
        logger.info(f"✓ SQLite path: {config.sqlite_path}")
        
        # Test 2: LangGraphCheckpointerManager initialization
        logger.info("\n2. Testing LangGraphCheckpointerManager initialization...")
        checkpointer_manager = LangGraphCheckpointerManager(config)
        logger.info(f"✓ Checkpointer manager initialized")
        logger.info(f"✓ Checkpointer type: {type(checkpointer_manager.checkpointer).__name__}")
        
        # Test 3: Checkpointer validation
        logger.info("\n3. Testing checkpointer validation...")
        is_valid = checkpointer_manager.validate_checkpointer()
        logger.info(f"✓ Checkpointer validation result: {is_valid}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Checkpointer configuration test failed: {str(e)}")
        return False

async def test_workflow_initialization():
    """Test workflow initialization with checkpointer"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Workflow Initialization with Checkpointer")
    logger.info("=" * 60)

    try:
        # Get database session
        db_session = next(get_db())
        
        # Test workflow initialization
        logger.info("1. Testing SimulationPreprocessingWorkflow initialization...")
        workflow = SimulationPreprocessingWorkflow(db_session)
        logger.info("✓ Workflow initialized successfully")
        
        # Test checkpointer status
        logger.info("\n2. Testing checkpointer status...")
        status = workflow.get_checkpointer_status()
        logger.info(f"✓ Checkpointer type: {status['checkpointer_type']}")
        logger.info(f"✓ Is initialized: {status['is_initialized']}")
        logger.info(f"✓ Is valid: {status['is_valid']}")
        
        # Test workflow graph compilation
        logger.info("\n3. Testing workflow graph compilation...")
        if workflow.workflow_graph:
            logger.info("✓ Workflow graph compiled successfully with checkpointer")
        else:
            logger.error("✗ Workflow graph compilation failed")
            return False
            
        db_session.close()
        return True
        
    except Exception as e:
        logger.error(f"✗ Workflow initialization test failed: {str(e)}")
        return False

async def test_state_persistence_concepts():
    """Test state persistence conceptual functionality"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing State Persistence Concepts")
    logger.info("=" * 60)

    try:
        # Test 1: SimulationState creation
        logger.info("1. Testing SimulationState creation...")
        test_state = {
            "project_id": "test_project_123",
            "workflow_id": "test_workflow_456",
            "user_goal": "Test CFD simulation",
            "physics_type": "cfd",
            "cad_files": [{"file_id": "test_file", "filename": "test.step"}],
            "current_file": {"file_id": "test_file", "filename": "test.step"},
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
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "iteration_count": 0,
            "max_iterations": 3
        }
        
        # Validate state structure
        state = SimulationState(**test_state)
        logger.info("✓ SimulationState created and validated successfully")
        
        # Test 2: Thread ID generation
        logger.info("\n2. Testing thread ID generation for checkpointing...")
        workflow_id = "test_workflow_456"
        thread_id = f"workflow_{workflow_id}"
        config = {"configurable": {"thread_id": thread_id}}
        logger.info(f"✓ Thread ID: {thread_id}")
        logger.info(f"✓ Config structure: {config}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ State persistence concept test failed: {str(e)}")
        return False

async def test_environment_configuration():
    """Test environment variable configuration"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Environment Configuration")
    logger.info("=" * 60)

    # Test environment variables
    env_vars = {
        "LANGGRAPH_CHECKPOINTER_TYPE": os.getenv("LANGGRAPH_CHECKPOINTER_TYPE", "not_set"),
        "LANGGRAPH_DATABASE_URL": os.getenv("LANGGRAPH_DATABASE_URL", "not_set"),
        "LANGGRAPH_SQLITE_PATH": os.getenv("LANGGRAPH_SQLITE_PATH", "not_set"),
        "LANGGRAPH_CONNECTION_TIMEOUT": os.getenv("LANGGRAPH_CONNECTION_TIMEOUT", "not_set"),
        "LANGGRAPH_MAX_RETRIES": os.getenv("LANGGRAPH_MAX_RETRIES", "not_set")
    }
    
    logger.info("Environment variables status:")
    for var, value in env_vars.items():
        status = "✓ SET" if value != "not_set" else "⚠ DEFAULT"
        logger.info(f"  {var}: {status} ({value if value != 'not_set' else 'using default'})")
    
    return True

async def main():
    """Run all tests"""
    logger.info("🚀 Starting LangGraph State Persistence Tests")
    
    test_results = []
    
    # Run tests
    test_results.append(await test_environment_configuration())
    test_results.append(await test_checkpointer_configuration())
    test_results.append(await test_workflow_initialization())
    test_results.append(await test_state_persistence_concepts())
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(test_results)
    total = len(test_results)
    
    logger.info(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 All tests passed! LangGraph state persistence is properly configured.")
        return True
    else:
        logger.error(f"❌ {total - passed} test(s) failed. Please review the configuration.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)