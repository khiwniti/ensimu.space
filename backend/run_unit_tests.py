#!/usr/bin/env python3
"""
Unit test runner for the AgentSim → ensimu-space merger project.
Runs the newly created unit tests for AI agents, database models, and LangGraph workflows.
"""

import sys
import subprocess
import time
from pathlib import Path

def run_test_suite(test_file, description):
    """Run a specific test suite and return success status"""
    print(f"\n{'='*60}")
    print(f"🧪 Running: {description}")
    print(f"{'='*60}")
    
    cmd = [
        sys.executable, "-m", "pytest", 
        f"tests/{test_file}",
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure for quick feedback
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print("-" * 40)
    
    start_time = time.time()
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    end_time = time.time()
    
    duration = end_time - start_time
    
    if result.returncode == 0:
        print(f"\n✅ {description} - ALL TESTS PASSED ({duration:.2f}s)")
        return True
    else:
        print(f"\n❌ {description} - TESTS FAILED (exit code: {result.returncode})")
        return False

def run_all_unit_tests():
    """Run all unit tests for the new components"""
    print("🚀 Starting Unit Test Suite for AgentSim → ensimu-space Merger")
    print("Testing AI Agents, Database Models, and LangGraph Workflows")
    
    test_suites = [
        ("test_ai_agents.py", "AI Agents Unit Tests"),
        ("test_database_models.py", "Database Models Unit Tests"),
        ("test_langgraph_workflow.py", "LangGraph Workflow Unit Tests")
    ]
    
    results = []
    total_start_time = time.time()
    
    for test_file, description in test_suites:
        success = run_test_suite(test_file, description)
        results.append((description, success))
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # Print summary
    print("\n" + "="*80)
    print("📊 UNIT TEST SUMMARY")
    print("="*80)
    
    passed_count = 0
    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{description:<40} {status}")
        if success:
            passed_count += 1
    
    print("-" * 80)
    print(f"Total Test Suites: {len(results)}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {len(results) - passed_count}")
    print(f"Total Duration: {total_duration:.2f} seconds")
    
    if passed_count == len(results):
        print("\n🎉 ALL UNIT TESTS PASSED! The merger components are working correctly.")
        return 0
    else:
        print(f"\n⚠️  {len(results) - passed_count} test suite(s) failed. Please review the output above.")
        return 1

def run_with_coverage():
    """Run all unit tests with coverage reporting"""
    print("🧪 Running Unit Tests with Coverage Analysis...")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_ai_agents.py",
        "tests/test_database_models.py", 
        "tests/test_langgraph_workflow.py",
        "-v",
        "--cov=app.libs",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=80"
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    
    if result.returncode == 0:
        print("\n✅ All tests passed with adequate coverage!")
        print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("\n❌ Tests failed or coverage below threshold")
    
    return result.returncode

def run_specific_test(test_name):
    """Run a specific test or test class"""
    print(f"🎯 Running specific test: {test_name}")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",
        "-k", test_name,
        "tests/"
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print("-" * 40)
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode

def main():
    """Main function with command line argument handling"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "coverage":
            exit_code = run_with_coverage()
        elif command == "agents":
            exit_code = 0 if run_test_suite("test_ai_agents.py", "AI Agents Unit Tests") else 1
        elif command == "models":
            exit_code = 0 if run_test_suite("test_database_models.py", "Database Models Unit Tests") else 1
        elif command == "workflow":
            exit_code = 0 if run_test_suite("test_langgraph_workflow.py", "LangGraph Workflow Unit Tests") else 1
        elif command.startswith("test_"):
            exit_code = run_specific_test(command)
        else:
            print(f"Unknown command: {command}")
            print("Available commands:")
            print("  (no args)  - Run all unit tests")
            print("  coverage   - Run with coverage analysis")
            print("  agents     - Run AI agents tests only")
            print("  models     - Run database models tests only")
            print("  workflow   - Run LangGraph workflow tests only")
            print("  test_*     - Run specific test matching pattern")
            exit_code = 1
    else:
        # Run all unit tests
        exit_code = run_all_unit_tests()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
