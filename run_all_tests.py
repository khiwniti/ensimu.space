#!/usr/bin/env python3
"""
Comprehensive test runner for the AgentSim → ensimu-space merger project.
Runs backend unit tests, integration tests, frontend component tests, and end-to-end tests.
"""

import sys
import subprocess
import time
import os
from pathlib import Path

def run_command(cmd, description, cwd=None):
    """Run a command and return success status"""
    print(f"\n{'='*80}")
    print(f"🧪 {description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(cmd)}")
    print(f"Working Directory: {cwd or 'current'}")
    print("-" * 60)
    
    start_time = time.time()
    result = subprocess.run(cmd, cwd=cwd, capture_output=False)
    end_time = time.time()
    
    duration = end_time - start_time
    
    if result.returncode == 0:
        print(f"\n✅ {description} - PASSED ({duration:.2f}s)")
        return True
    else:
        print(f"\n❌ {description} - FAILED (exit code: {result.returncode})")
        return False

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    # Check backend dependencies
    backend_deps = ["pytest", "pytest-asyncio", "sqlalchemy", "fastapi"]
    missing_backend = []
    
    for dep in backend_deps:
        try:
            subprocess.run([sys.executable, "-c", f"import {dep}"], 
                         check=True, capture_output=True)
        except subprocess.CalledProcessError:
            missing_backend.append(dep)
    
    if missing_backend:
        print(f"❌ Missing backend dependencies: {', '.join(missing_backend)}")
        print("Run: pip install -r backend/requirements.txt")
        return False
    
    # Check if frontend dependencies are installed
    frontend_path = Path("ensumu-space/frontend")
    if not (frontend_path / "node_modules").exists():
        print("❌ Frontend dependencies not installed")
        print("Run: cd ensumu-space/frontend && npm install")
        return False
    
    print("✅ All dependencies are available")
    return True

def run_backend_tests():
    """Run all backend tests"""
    backend_path = Path("ensumu-space/backend")
    
    test_suites = [
        {
            "cmd": [sys.executable, "run_unit_tests.py"],
            "description": "Backend Unit Tests (AI Agents, Models, Workflows)",
        },
        {
            "cmd": [sys.executable, "-m", "pytest", "tests/test_integration_workflow.py", "-v"],
            "description": "Backend Integration Tests",
        },
        {
            "cmd": [sys.executable, "-m", "pytest", "tests/test_end_to_end.py", "-v"],
            "description": "Backend End-to-End Tests",
        },
    ]
    
    results = []
    for suite in test_suites:
        success = run_command(suite["cmd"], suite["description"], cwd=backend_path)
        results.append((suite["description"], success))
    
    return results

def run_frontend_tests():
    """Run frontend tests"""
    frontend_path = Path("ensumu-space/frontend")
    
    test_suites = [
        {
            "cmd": ["npm", "run", "test:run"],
            "description": "Frontend Component Tests",
        },
    ]
    
    results = []
    for suite in test_suites:
        success = run_command(suite["cmd"], suite["description"], cwd=frontend_path)
        results.append((suite["description"], success))
    
    return results

def run_coverage_analysis():
    """Run coverage analysis for both backend and frontend"""
    print("\n📊 Running Coverage Analysis...")
    
    # Backend coverage
    backend_path = Path("ensumu-space/backend")
    backend_coverage = run_command(
        [sys.executable, "run_unit_tests.py", "coverage"],
        "Backend Coverage Analysis",
        cwd=backend_path
    )
    
    # Frontend coverage
    frontend_path = Path("ensumu-space/frontend")
    frontend_coverage = run_command(
        ["npm", "run", "test:coverage"],
        "Frontend Coverage Analysis",
        cwd=frontend_path
    )
    
    return [
        ("Backend Coverage", backend_coverage),
        ("Frontend Coverage", frontend_coverage)
    ]

def print_summary(all_results):
    """Print comprehensive test summary"""
    print("\n" + "="*100)
    print("📋 COMPREHENSIVE TEST SUMMARY - AgentSim → ensimu-space Merger")
    print("="*100)
    
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        print(f"\n🔸 {category}")
        print("-" * 60)
        
        for description, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"  {description:<50} {status}")
            total_tests += 1
            if success:
                passed_tests += 1
    
    print("\n" + "="*100)
    print(f"📊 OVERALL RESULTS")
    print("="*100)
    print(f"Total Test Suites: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! The AgentSim → ensimu-space merger is working correctly.")
        print("✨ The integrated AI-powered simulation platform is ready for production!")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test suite(s) failed.")
        print("🔧 Please review the output above and fix any issues before deployment.")
        return 1

def main():
    """Main test execution function"""
    print("🚀 Starting Comprehensive Test Suite for AgentSim → ensimu-space Merger")
    print("Testing AI Agents, LangGraph Workflows, Database Models, Frontend Components, and E2E Integration")
    
    # Check if we're in the right directory
    if not Path("ensumu-space").exists():
        print("❌ Error: ensumu-space directory not found")
        print("Please run this script from the repository root directory")
        return 1
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    total_start_time = time.time()
    
    # Run all test suites
    all_results = {}
    
    # Backend tests
    print("\n🔧 Running Backend Tests...")
    backend_results = run_backend_tests()
    all_results["Backend Tests"] = backend_results
    
    # Frontend tests
    print("\n🎨 Running Frontend Tests...")
    frontend_results = run_frontend_tests()
    all_results["Frontend Tests"] = frontend_results
    
    # Coverage analysis (optional)
    if "--coverage" in sys.argv:
        coverage_results = run_coverage_analysis()
        all_results["Coverage Analysis"] = coverage_results
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # Print comprehensive summary
    exit_code = print_summary(all_results)
    
    print(f"\n⏱️  Total execution time: {total_duration:.2f} seconds")
    
    if "--coverage" in sys.argv:
        print("\n📊 Coverage reports generated:")
        print("  Backend: ensumu-space/backend/htmlcov/index.html")
        print("  Frontend: ensumu-space/frontend/coverage/index.html")
    
    return exit_code

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python run_all_tests.py [--coverage]")
        print("")
        print("Options:")
        print("  --coverage    Include coverage analysis")
        print("  --help        Show this help message")
        sys.exit(0)
    
    sys.exit(main())
