#!/usr/bin/env python3
"""
Test runner script for enhanced simulation system
Provides comprehensive testing capabilities with different test categories
"""

import sys
import subprocess
import argparse
from pathlib import Path
import time

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=False)
    end_time = time.time()
    
    duration = end_time - start_time
    
    if result.returncode == 0:
        print(f"\n✅ {description} completed successfully in {duration:.2f}s")
        return True
    else:
        print(f"\n❌ {description} failed (exit code: {result.returncode})")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run enhanced simulation tests")
    
    # Test category options
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--api", action="store_true", help="Run API tests only")
    parser.add_argument("--agents", action="store_true", help="Run agent tests only")
    parser.add_argument("--orchestrator", action="store_true", help="Run orchestrator tests only")
    parser.add_argument("--post-processing", action="store_true", help="Run post-processing tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--slow", action="store_true", help="Include slow tests")
    
    # Coverage options
    parser.add_argument("--no-cov", action="store_true", help="Disable coverage reporting")
    parser.add_argument("--cov-report", choices=["term", "html", "xml"], default="term", 
                       help="Coverage report format")
    
    # Output options
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet output")
    parser.add_argument("--tb", choices=["short", "long", "no"], default="short",
                       help="Traceback format")
    
    # Test selection
    parser.add_argument("--pattern", "-k", help="Run tests matching pattern")
    parser.add_argument("--file", help="Run specific test file")
    parser.add_argument("--failfast", "-x", action="store_true", help="Stop on first failure")
    
    # Parallel execution
    parser.add_argument("--workers", "-n", type=int, help="Number of workers for parallel execution")
    
    # Special modes
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies")
    parser.add_argument("--check-only", action="store_true", help="Check test configuration only")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark tests")
    
    args = parser.parse_args()
    
    # Install dependencies if requested
    if args.install_deps:
        print("Installing test dependencies...")
        deps_cmd = [sys.executable, "-m", "pip", "install", 
                   "pytest", "pytest-cov", "pytest-asyncio", "pytest-xdist", 
                   "pytest-benchmark", "httpx", "pytest-mock"]
        if not run_command(deps_cmd, "Installing test dependencies"):
            return 1
        print("✅ Test dependencies installed successfully")
        return 0
    
    # Check configuration only
    if args.check_only:
        print("Checking test configuration...")
        check_cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
        if not run_command(check_cmd, "Checking test configuration"):
            return 1
        print("✅ Test configuration is valid")
        return 0
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add test markers based on arguments
    markers = []
    if args.unit:
        markers.append("unit")
    if args.integration:
        markers.append("integration")
    if args.api:
        markers.append("api")
    if args.agents:
        markers.append("agents")
    if args.orchestrator:
        markers.append("orchestrator")
    if args.post_processing:
        markers.append("post_processing")
    if args.performance:
        markers.append("performance")
    
    if markers:
        cmd.extend(["-m", " or ".join(markers)])
    
    # Add slow tests if requested
    if not args.slow:
        if markers:
            cmd[-1] += " and not slow"
        else:
            cmd.extend(["-m", "not slow"])
    
    # Coverage options
    if not args.no_cov:
        cmd.extend(["--cov=app", "--cov-report=term-missing"])
        if args.cov_report == "html":
            cmd.append("--cov-report=html:htmlcov")
        elif args.cov_report == "xml":
            cmd.append("--cov-report=xml")
    
    # Output options
    if args.verbose:
        cmd.append("-v")
    if args.quiet:
        cmd.append("-q")
    cmd.extend(["--tb", args.tb])
    
    # Test selection
    if args.pattern:
        cmd.extend(["-k", args.pattern])
    if args.file:
        cmd.append(args.file)
    if args.failfast:
        cmd.append("-x")
    
    # Parallel execution
    if args.workers:
        cmd.extend(["-n", str(args.workers)])
    
    # Benchmark mode
    if args.benchmark:
        cmd.append("--benchmark-only")
    
    # Default to tests directory if no specific file
    if not args.file:
        cmd.append("tests/")
    
    # Run the tests
    success = run_command(cmd, "Enhanced Simulation Tests")
    
    if success:
        print(f"\n🎉 All tests completed successfully!")
        
        # Show coverage report location if generated
        if not args.no_cov and args.cov_report == "html":
            print(f"📊 Coverage report available at: htmlcov/index.html")
        
        # Show test summary
        print(f"\n📋 Test Summary:")
        print(f"   Command: {' '.join(cmd)}")
        
        return 0
    else:
        print(f"\n💥 Tests failed! Check the output above for details.")
        return 1

if __name__ == "__main__":
    # Ensure we're in the correct directory
    script_dir = Path(__file__).parent
    sys.path.insert(0, str(script_dir))
    
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test runner error: {e}")
        sys.exit(1)