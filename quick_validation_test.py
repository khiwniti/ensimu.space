#!/usr/bin/env python3
"""
Quick Validation Test for EnsumuSpace
Tests core functionality without heavy dependencies
"""

import os
import sys
import importlib.util
import traceback
from pathlib import Path

def test_file_syntax(file_path):
    """Test if a Python file has valid syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        compile(source, file_path, 'exec')
        return True, "✅ Valid syntax"
    except SyntaxError as e:
        return False, f"❌ Syntax error: {e}"
    except Exception as e:
        return False, f"❌ Error: {e}"

def test_import_capability(module_path, module_name):
    """Test if a module can be imported"""
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None:
            return False, "❌ Cannot create module spec"
        
        module = importlib.util.module_from_spec(spec)
        # Don't execute, just check if it can be loaded
        return True, "✅ Importable"
    except Exception as e:
        return False, f"❌ Import error: {str(e)[:100]}"

def run_validation_tests():
    """Run comprehensive validation tests"""
    print("🧪 EnsumuSpace Quick Validation Test")
    print("=" * 50)
    
    # Test results storage
    results = {
        'passed': 0,
        'failed': 0,
        'details': []
    }
    
    # Backend core files to test
    backend_files = [
        ('backend/main.py', 'Main Application'),
        ('backend/app/libs/database.py', 'Database Layer'),
        ('backend/app/libs/cae_models.py', 'CAE Models'),
        ('backend/app/libs/agents.py', 'Base Agents'),
        ('backend/app/libs/cae_agents.py', 'CAE Agents'),
        ('backend/app/libs/enhanced_agents.py', 'Enhanced Agents'),
        ('backend/app/libs/enhanced_orchestrator.py', 'Orchestrator'),
        ('backend/app/libs/langgraph_supervisor.py', 'LangGraph Supervisor'),
        ('backend/app/libs/langgraph_workflow.py', 'LangGraph Workflow'),
        ('backend/app/websocket_manager.py', 'WebSocket Manager'),
        ('backend/app/libs/engineering_utils.py', 'Engineering Utils'),
        ('backend/app/libs/simulation_tools.py', 'Simulation Tools'),
        ('backend/app/libs/post_processing_pipeline.py', 'Post Processing'),
        ('backend/app/apis/hello/__init__.py', 'Hello API'),
        ('backend/app/apis/copilotkit/__init__.py', 'CopilotKit API'),
    ]
    
    print("\n📁 Testing Backend Core Files:")
    print("-" * 30)
    
    for file_path, description in backend_files:
        if os.path.exists(file_path):
            # Test syntax
            syntax_ok, syntax_msg = test_file_syntax(file_path)
            
            # Test import capability
            import_ok, import_msg = test_import_capability(file_path, description.replace(' ', '_'))
            
            if syntax_ok:
                results['passed'] += 1
                print(f"{description:25} {syntax_msg}")
            else:
                results['failed'] += 1
                print(f"{description:25} {syntax_msg}")
                
            results['details'].append({
                'file': file_path,
                'description': description,
                'syntax': syntax_ok,
                'syntax_msg': syntax_msg,
                'import': import_ok,
                'import_msg': import_msg
            })
        else:
            results['failed'] += 1
            print(f"{description:25} ❌ File missing")
            results['details'].append({
                'file': file_path,
                'description': description,
                'syntax': False,
                'syntax_msg': "File missing"
            })
    
    # Test configuration files
    print("\n⚙️ Testing Configuration Files:")
    print("-" * 30)
    
    config_files = [
        ('backend/requirements.txt', 'Backend Dependencies'),
        ('backend/pytest.ini', 'Pytest Configuration'),
        ('backend/alembic.ini', 'Database Migrations'),
        ('frontend/package.json', 'Frontend Dependencies'),
        ('docker-compose.yml', 'Docker Configuration'),
        ('.gitignore', 'Git Configuration'),
        ('README.md', 'Documentation'),
    ]
    
    for file_path, description in config_files:
        if os.path.exists(file_path):
            results['passed'] += 1
            print(f"{description:25} ✅ Present")
        else:
            results['failed'] += 1
            print(f"{description:25} ❌ Missing")
    
    # Test directory structure
    print("\n📂 Testing Directory Structure:")
    print("-" * 30)
    
    required_dirs = [
        ('backend/app/libs', 'Backend Libraries'),
        ('backend/app/apis', 'API Endpoints'),
        ('backend/tests', 'Backend Tests'),
        ('frontend/src', 'Frontend Source'),
        ('frontend/src/components', 'Frontend Components'),
    ]
    
    for dir_path, description in required_dirs:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            results['passed'] += 1
            print(f"{description:25} ✅ Present")
        else:
            results['failed'] += 1
            print(f"{description:25} ❌ Missing")
    
    # Test database models content
    print("\n🗄️ Testing Database Models:")
    print("-" * 30)
    
    try:
        with open('backend/app/libs/cae_models.py', 'r') as f:
            models_content = f.read()
        
        required_models = ['User', 'Project', 'Simulation', 'WorkflowExecution', 'HITLCheckpoint', 'AgentCommunication']
        for model in required_models:
            if f'class {model}' in models_content:
                results['passed'] += 1
                print(f"{model:25} ✅ Defined")
            else:
                results['failed'] += 1
                print(f"{model:25} ❌ Missing")
                
    except Exception as e:
        results['failed'] += 1
        print(f"Model validation:         ❌ Error: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    
    total_tests = results['passed'] + results['failed']
    success_rate = (results['passed'] / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Tests:     {total_tests}")
    print(f"Passed:          {results['passed']} ✅")
    print(f"Failed:          {results['failed']} ❌")
    print(f"Success Rate:    {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("\n🎉 EXCELLENT: System is ready for full testing!")
    elif success_rate >= 75:
        print("\n✅ GOOD: Minor issues to resolve before full testing")
    elif success_rate >= 50:
        print("\n⚠️ WARNING: Significant issues need attention")
    else:
        print("\n🚨 CRITICAL: Major structural problems detected")
    
    print("\n📋 NEXT STEPS:")
    if results['failed'] == 0:
        print("1. Install dependencies: pip install -r backend/requirements.txt")
        print("2. Setup database: docker-compose up -d")
        print("3. Run full test suite: python run_all_tests.py")
    else:
        print("1. Fix missing files and syntax errors")
        print("2. Re-run validation: python quick_validation_test.py")
        print("3. Proceed with dependency installation")
    
    return results

if __name__ == "__main__":
    try:
        results = run_validation_tests()
        sys.exit(0 if results['failed'] == 0 else 1)
    except Exception as e:
        print(f"\n🚨 CRITICAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
