#!/usr/bin/env python3
"""
Health check script for Docker container health monitoring.
Performs comprehensive health checks and returns appropriate exit codes.
"""

import asyncio
import json
import os
import sys
import time
import traceback
from typing import Dict, Any

try:
    import httpx
    import asyncpg
    import redis.asyncio as redis
    import psutil
except ImportError as e:
    print(f"Missing required dependency: {e}")
    sys.exit(1)

class HealthChecker:
    """Comprehensive health checker for the application"""
    
    def __init__(self):
        self.checks = []
        self.timeout = 10.0
        
    async def check_http_endpoint(self) -> Dict[str, Any]:
        """Check HTTP endpoint health"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:8000/health")
                
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "message": "HTTP endpoint responding",
                        "details": {
                            "status_code": response.status_code,
                            "response_time_ms": response.elapsed.total_seconds() * 1000
                        }
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "message": f"HTTP endpoint returned status {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"HTTP endpoint check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            return {
                "status": "unknown",
                "message": "DATABASE_URL not configured",
                "details": {}
            }
        
        try:
            conn = await asyncpg.connect(database_url)
            result = await conn.fetchval("SELECT 1")
            await conn.close()
            
            if result == 1:
                return {
                    "status": "healthy",
                    "message": "Database connection successful",
                    "details": {"query_result": result}
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Database query returned unexpected result",
                    "details": {"expected": 1, "actual": result}
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            return {
                "status": "unknown",
                "message": "REDIS_URL not configured",
                "details": {}
            }
        
        try:
            client = redis.Redis.from_url(redis_url)
            pong = await client.ping()
            await client.close()
            
            if pong:
                return {
                    "status": "healthy",
                    "message": "Redis connection successful",
                    "details": {"ping": pong}
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Redis ping failed",
                    "details": {"ping": pong}
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Redis connection failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Process-specific metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent()
            
            # Determine status
            issues = []
            if memory_percent > 90:
                issues.append(f"High memory usage: {memory_percent:.1f}%")
            if disk_percent > 90:
                issues.append(f"High disk usage: {disk_percent:.1f}%")
            if cpu_percent > 95:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            status = "unhealthy" if issues else "healthy"
            message = "System resources normal" if not issues else f"Resource issues: {', '.join(issues)}"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "memory_percent": memory_percent,
                    "disk_percent": round(disk_percent, 1),
                    "cpu_percent": cpu_percent,
                    "process_memory_mb": round(process_memory.rss / (1024**2), 2),
                    "process_cpu_percent": process_cpu
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"System resource check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def check_file_system(self) -> Dict[str, Any]:
        """Check file system health"""
        try:
            required_dirs = ["/app/logs", "/app/uploads", "/app/tmp"]
            issues = []
            
            for directory in required_dirs:
                if not os.path.exists(directory):
                    issues.append(f"Missing directory: {directory}")
                elif not os.access(directory, os.W_OK):
                    issues.append(f"Directory not writable: {directory}")
            
            # Check log file rotation
            log_files = ["/app/logs/access.log", "/app/logs/error.log"]
            for log_file in log_files:
                if os.path.exists(log_file):
                    stat = os.stat(log_file)
                    size_mb = stat.st_size / (1024**2)
                    if size_mb > 100:  # Log file larger than 100MB
                        issues.append(f"Large log file: {log_file} ({size_mb:.1f}MB)")
            
            status = "unhealthy" if issues else "healthy"
            message = "File system healthy" if not issues else f"File system issues: {', '.join(issues)}"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "required_directories": required_dirs,
                    "issues": issues
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"File system check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        start_time = time.time()
        
        checks = {
            "http_endpoint": await self.check_http_endpoint(),
            "database": await self.check_database(),
            "redis": await self.check_redis(),
            "system_resources": self.check_system_resources(),
            "file_system": self.check_file_system()
        }
        
        # Determine overall status
        critical_failures = []
        warnings = []
        
        for check_name, result in checks.items():
            if result["status"] == "unhealthy":
                if check_name in ["http_endpoint", "database"]:
                    critical_failures.append(check_name)
                else:
                    warnings.append(check_name)
        
        if critical_failures:
            overall_status = "unhealthy"
            overall_message = f"Critical failures: {', '.join(critical_failures)}"
        elif warnings:
            overall_status = "degraded"
            overall_message = f"Non-critical issues: {', '.join(warnings)}"
        else:
            overall_status = "healthy"
            overall_message = "All systems healthy"
        
        duration = time.time() - start_time
        
        return {
            "status": overall_status,
            "message": overall_message,
            "timestamp": time.time(),
            "duration_seconds": round(duration, 3),
            "checks": checks
        }

async def main():
    """Main health check function"""
    try:
        checker = HealthChecker()
        result = await checker.run_all_checks()
        
        # Print result for debugging
        if os.environ.get("HEALTH_CHECK_VERBOSE", "false").lower() == "true":
            print(json.dumps(result, indent=2))
        
        # Exit with appropriate code
        if result["status"] == "healthy":
            print("✅ Health check passed")
            sys.exit(0)
        elif result["status"] == "degraded":
            print(f"⚠️  Health check degraded: {result['message']}")
            # Exit 0 for degraded state (container should continue running)
            sys.exit(0)
        else:
            print(f"❌ Health check failed: {result['message']}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        if os.environ.get("HEALTH_CHECK_VERBOSE", "false").lower() == "true":
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
