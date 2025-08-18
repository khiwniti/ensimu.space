#!/usr/bin/env python3
"""
Diagnostic validation script to validate key assumptions about workflow issues
"""

import os
import sys
import logging
from typing import Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_langgraph_sqlite_configuration():
    """Check if LangGraph SQLite checkpointing is properly configured"""
    issues = []
    
    try:
        # Check if the workflow properly configures SqliteSaver
        with open('app/libs/langgraph_workflow.py', 'r') as f:
            content = f.read()
            
        # Look for SqliteSaver usage
        if 'SqliteSaver' in content:
            logger.info("✓ SqliteSaver import found")
            
            # Check if it's actually used in workflow compilation
            if 'SqliteSaver()' in content or 'checkpointer=' in content:
                logger.info("✓ SqliteSaver appears to be configured")
            else:
                issues.append("SqliteSaver imported but not configured in workflow compilation")
                logger.warning("⚠ SqliteSaver imported but not used in workflow")
        else:
            issues.append("SqliteSaver not imported - state persistence may not work")
            logger.error("✗ SqliteSaver not found in workflow")
            
    except Exception as e:
        issues.append(f"Error checking LangGraph configuration: {str(e)}")
    
    return issues

def validate_environment_dependencies():
    """Check environment configuration and dependencies"""
    issues = []
    
    # Check OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        issues.append("OPENAI_API_KEY environment variable not set")
        logger.warning("⚠ OpenAI API key not configured")
    else:
        logger.info("✓ OpenAI API key configured")
    
    # Check database URL
    db_url = os.getenv('DATABASE_URL', 'postgresql://ensumu_user:ensumu_password@localhost:5432/ensumu_db')
    if 'localhost' in db_url:
        issues.append("Database URL points to localhost - may not be available in all environments")
        logger.warning("⚠ Database URL uses localhost")
    else:
        logger.info("✓ Database URL configured for external service")
    
    # Check Redis configuration
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    if 'localhost' in redis_url:
        issues.append("Redis URL points to localhost - caching may not work in all environments")
        logger.warning("⚠ Redis URL uses localhost")
    else:
        logger.info("✓ Redis URL configured for external service")
    
    return issues

def check_workflow_compilation_issues():
    """Check for issues in workflow graph compilation"""
    issues = []
    
    try:
        with open('app/libs/langgraph_workflow.py', 'r') as f:
            content = f.read()
        
        # Check if workflow.compile() includes checkpointer
        if 'workflow.compile()' in content:
            if 'checkpointer=' not in content:
                issues.append("Workflow compilation missing checkpointer parameter")
                logger.warning("⚠ Workflow compiled without checkpointer")
            else:
                logger.info("✓ Workflow compilation includes checkpointer")
        
        # Check for proper state management
        if 'await self.state_persistence.save_state' in content:
            logger.info("✓ State persistence calls found")
        else:
            issues.append("State persistence save calls not found")
            logger.warning("⚠ State persistence may not be working")
            
    except Exception as e:
        issues.append(f"Error checking workflow compilation: {str(e)}")
    
    return issues

def validate_agent_error_handling():
    """Check agent error handling and fallbacks"""
    issues = []
    
    try:
        with open('app/libs/cae_agents.py', 'r') as f:
            content = f.read()
        
        # Check for performance imports fallback
        if 'PERFORMANCE_ENABLED = False' in content:
            logger.info("✓ Performance module fallback implemented")
        else:
            issues.append("No fallback for missing performance modules")
        
        # Check for OpenAI error handling
        if 'except Exception as e:' in content and 'openai' in content.lower():
            logger.info("✓ OpenAI error handling found")
        else:
            issues.append("Limited OpenAI error handling in agents")
            
    except Exception as e:
        issues.append(f"Error checking agent error handling: {str(e)}")
    
    return issues

def main():
    """Run diagnostic validation"""
    logger.info("=" * 60)
    logger.info("DIAGNOSTIC VALIDATION FOR AI AGENT WORKFLOW SYSTEM")
    logger.info("=" * 60)
    
    all_issues = []
    
    # Run diagnostics
    logger.info("\n1. Checking LangGraph SQLite Configuration...")
    issues1 = validate_langgraph_sqlite_configuration()
    all_issues.extend(issues1)
    
    logger.info("\n2. Checking Environment Dependencies...")
    issues2 = validate_environment_dependencies()
    all_issues.extend(issues2)
    
    logger.info("\n3. Checking Workflow Compilation...")
    issues3 = check_workflow_compilation_issues()
    all_issues.extend(issues3)
    
    logger.info("\n4. Checking Agent Error Handling...")
    issues4 = validate_agent_error_handling()
    all_issues.extend(issues4)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info("=" * 60)
    
    if all_issues:
        logger.warning(f"Found {len(all_issues)} potential issues:")
        for i, issue in enumerate(all_issues, 1):
            logger.warning(f"{i}. {issue}")
    else:
        logger.info("No critical issues found in static analysis")
    
    # Recommendations
    logger.info("\nRECOMMENDATIONS:")
    logger.info("1. Configure LangGraph with proper SqliteSaver checkpointer")
    logger.info("2. Set up environment validation for external dependencies")
    logger.info("3. Add graceful degradation for missing services")
    logger.info("4. Implement comprehensive error handling and logging")
    
    return all_issues

if __name__ == "__main__":
    try:
        issues = main()
        exit_code = 0 if len(issues) <= 2 else 1  # Allow for minor issues
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Diagnostic validation failed: {str(e)}")
        sys.exit(1)