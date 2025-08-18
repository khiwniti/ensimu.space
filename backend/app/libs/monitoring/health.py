"""
Health check system for the simulation preprocessing platform.
Implements comprehensive health monitoring for all system components.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable
import threading
import psutil

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms
        }

class HealthCheck:
    """Base health check class"""
    
    def __init__(self, name: str, timeout: float = 5.0, critical: bool = True):
        self.name = name
        self.timeout = timeout
        self.critical = critical
    
    async def check(self) -> HealthCheckResult:
        """Perform health check"""
        start_time = time.time()
        
        try:
            # Run the check with timeout
            result = await asyncio.wait_for(self._perform_check(), timeout=self.timeout)
            duration_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name=self.name,
                status=result.get("status", HealthStatus.UNKNOWN),
                message=result.get("message", "Check completed"),
                details=result.get("details", {}),
                duration_ms=duration_ms
            )
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout}s",
                duration_ms=duration_ms
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration_ms
            )
    
    async def _perform_check(self) -> Dict[str, Any]:
        """Override this method to implement specific health check logic"""
        raise NotImplementedError

class DatabaseHealthCheck(HealthCheck):
    """Database connectivity health check"""
    
    def __init__(self, database_url: str, name: str = "database"):
        super().__init__(name, timeout=10.0, critical=True)
        self.database_url = database_url
    
    async def _perform_check(self) -> Dict[str, Any]:
        """Check database connectivity"""
        if not ASYNCPG_AVAILABLE:
            return {
                "status": HealthStatus.UNKNOWN,
                "message": "asyncpg not available",
                "details": {"error": "asyncpg library not installed"}
            }
        
        try:
            # Test connection
            conn = await asyncpg.connect(self.database_url)
            
            # Test simple query
            result = await conn.fetchval("SELECT 1")
            
            # Get connection info
            server_version = conn.get_server_version()
            
            await conn.close()
            
            if result == 1:
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": "Database connection successful",
                    "details": {
                        "server_version": f"{server_version.major}.{server_version.minor}.{server_version.micro}",
                        "query_result": result
                    }
                }
            else:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Database query returned unexpected result",
                    "details": {"expected": 1, "actual": result}
                }
                
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Database connection failed",
                "details": {"error": str(e)}
            }

class RedisHealthCheck(HealthCheck):
    """Redis connectivity health check"""
    
    def __init__(self, redis_url: str, name: str = "redis"):
        super().__init__(name, timeout=5.0, critical=False)
        self.redis_url = redis_url
    
    async def _perform_check(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        if not REDIS_AVAILABLE:
            return {
                "status": HealthStatus.UNKNOWN,
                "message": "Redis not available",
                "details": {"error": "redis library not installed"}
            }
        
        try:
            # Create Redis client
            client = redis.Redis.from_url(self.redis_url)
            
            # Test ping
            pong = await client.ping()
            
            # Test set/get
            test_key = "health_check_test"
            test_value = "test_value"
            await client.set(test_key, test_value, ex=60)
            retrieved_value = await client.get(test_key)
            await client.delete(test_key)
            
            # Get Redis info
            info = await client.info()
            
            await client.close()
            
            if pong and retrieved_value.decode() == test_value:
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": "Redis connection successful",
                    "details": {
                        "ping": pong,
                        "version": info.get("redis_version"),
                        "connected_clients": info.get("connected_clients"),
                        "used_memory_human": info.get("used_memory_human")
                    }
                }
            else:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Redis operations failed",
                    "details": {"ping": pong, "test_value_match": retrieved_value == test_value}
                }
                
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Redis connection failed",
                "details": {"error": str(e)}
            }

class SystemResourcesHealthCheck(HealthCheck):
    """System resources health check"""
    
    def __init__(self, name: str = "system_resources", 
                 memory_threshold: float = 90.0, 
                 disk_threshold: float = 90.0,
                 cpu_threshold: float = 95.0):
        super().__init__(name, timeout=5.0, critical=False)
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
        self.cpu_threshold = cpu_threshold
    
    async def _perform_check(self) -> Dict[str, Any]:
        """Check system resources"""
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # CPU usage (average over 1 second)
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Process-specific metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent()
            
            # Determine status
            status = HealthStatus.HEALTHY
            issues = []
            
            if memory_percent > self.memory_threshold:
                status = HealthStatus.DEGRADED if memory_percent < 95 else HealthStatus.UNHEALTHY
                issues.append(f"High memory usage: {memory_percent:.1f}%")
            
            if disk_percent > self.disk_threshold:
                status = HealthStatus.DEGRADED if disk_percent < 95 else HealthStatus.UNHEALTHY
                issues.append(f"High disk usage: {disk_percent:.1f}%")
            
            if cpu_percent > self.cpu_threshold:
                status = HealthStatus.DEGRADED
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            message = "System resources normal"
            if issues:
                message = f"Resource issues detected: {', '.join(issues)}"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "memory": {
                        "total_gb": round(memory.total / (1024**3), 2),
                        "available_gb": round(memory.available / (1024**3), 2),
                        "percent": memory_percent
                    },
                    "disk": {
                        "total_gb": round(disk.total / (1024**3), 2),
                        "free_gb": round(disk.free / (1024**3), 2),
                        "percent": round(disk_percent, 1)
                    },
                    "cpu": {
                        "percent": cpu_percent,
                        "count": psutil.cpu_count()
                    },
                    "process": {
                        "memory_mb": round(process_memory.rss / (1024**2), 2),
                        "cpu_percent": process_cpu
                    }
                }
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Failed to check system resources",
                "details": {"error": str(e)}
            }

class WorkflowHealthCheck(HealthCheck):
    """Workflow system health check"""
    
    def __init__(self, name: str = "workflow_system"):
        super().__init__(name, timeout=10.0, critical=True)
    
    async def _perform_check(self) -> Dict[str, Any]:
        """Check workflow system health"""
        try:
            # Import here to avoid circular imports
            from app.libs.performance.database import db_manager
            from app.libs.performance.caching import cache_manager
            
            issues = []
            details = {}
            
            # Check database connection pool
            if db_manager.engine:
                pool_status = db_manager.get_pool_status()
                details["database_pool"] = pool_status
                
                if pool_status.get("checked_out_connections", 0) > pool_status.get("pool_size", 0) * 0.8:
                    issues.append("Database pool near capacity")
            else:
                issues.append("Database manager not initialized")
            
            # Check cache system
            if cache_manager.redis_client:
                try:
                    await cache_manager.redis_client.ping()
                    cache_stats = cache_manager.get_stats()
                    details["cache"] = cache_stats
                    
                    if cache_stats.get("hit_rate_percent", 0) < 50:
                        issues.append("Low cache hit rate")
                except Exception as e:
                    issues.append(f"Cache system error: {str(e)}")
            else:
                details["cache"] = {"status": "redis_not_available"}
            
            # Determine overall status
            if not issues:
                status = HealthStatus.HEALTHY
                message = "Workflow system operating normally"
            elif len(issues) == 1 and "Low cache hit rate" in issues[0]:
                status = HealthStatus.DEGRADED
                message = f"Workflow system degraded: {', '.join(issues)}"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Workflow system issues: {', '.join(issues)}"
            
            return {
                "status": status,
                "message": message,
                "details": details
            }
            
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Failed to check workflow system",
                "details": {"error": str(e)}
            }

class HealthMonitor:
    """Central health monitoring system"""
    
    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.check_interval = 30.0  # seconds
    
    def register_check(self, check: HealthCheck):
        """Register a health check"""
        self.checks[check.name] = check
        logger.info(f"Registered health check: {check.name}")
    
    def unregister_check(self, name: str):
        """Unregister a health check"""
        if name in self.checks:
            del self.checks[name]
            if name in self.last_results:
                del self.last_results[name]
            logger.info(f"Unregistered health check: {name}")
    
    async def run_check(self, name: str) -> Optional[HealthCheckResult]:
        """Run a specific health check"""
        if name not in self.checks:
            return None
        
        result = await self.checks[name].check()
        self.last_results[name] = result
        return result
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        results = {}
        
        # Run checks concurrently
        tasks = []
        for name, check in self.checks.items():
            task = asyncio.create_task(check.check())
            tasks.append((name, task))
        
        # Collect results
        for name, task in tasks:
            try:
                result = await task
                results[name] = result
                self.last_results[name] = result
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check execution failed: {str(e)}"
                )
        
        return results
    
    def get_overall_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        if not self.last_results:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "message": "No health checks have been run",
                "checks": {}
            }
        
        # Determine overall status
        critical_unhealthy = []
        critical_degraded = []
        non_critical_issues = []
        
        for name, result in self.last_results.items():
            check = self.checks.get(name)
            if not check:
                continue
            
            if result.status == HealthStatus.UNHEALTHY:
                if check.critical:
                    critical_unhealthy.append(name)
                else:
                    non_critical_issues.append(name)
            elif result.status == HealthStatus.DEGRADED:
                if check.critical:
                    critical_degraded.append(name)
                else:
                    non_critical_issues.append(name)
        
        # Determine overall status
        if critical_unhealthy:
            overall_status = HealthStatus.UNHEALTHY
            message = f"Critical systems unhealthy: {', '.join(critical_unhealthy)}"
        elif critical_degraded:
            overall_status = HealthStatus.DEGRADED
            message = f"Critical systems degraded: {', '.join(critical_degraded)}"
        elif non_critical_issues:
            overall_status = HealthStatus.DEGRADED
            message = f"Non-critical issues: {', '.join(non_critical_issues)}"
        else:
            overall_status = HealthStatus.HEALTHY
            message = "All systems healthy"
        
        return {
            "status": overall_status.value,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {name: result.to_dict() for name, result in self.last_results.items()}
        }
    
    def start_monitoring(self, interval: float = 30.0):
        """Start continuous health monitoring"""
        if self.monitoring_active:
            return
        
        self.check_interval = interval
        self.monitoring_active = True
        self.stop_event.clear()
        
        def monitor_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            while not self.stop_event.wait(self.check_interval):
                try:
                    loop.run_until_complete(self.run_all_checks())
                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")
            
            loop.close()
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"Health monitoring started (interval: {interval}s)")
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        self.stop_event.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        logger.info("Health monitoring stopped")

# Global health monitor instance
health_monitor = HealthMonitor()

def initialize_health_checks(database_url: str, redis_url: str = None):
    """Initialize standard health checks"""
    # Database health check
    health_monitor.register_check(DatabaseHealthCheck(database_url))
    
    # Redis health check (if URL provided)
    if redis_url:
        health_monitor.register_check(RedisHealthCheck(redis_url))
    
    # System resources health check
    health_monitor.register_check(SystemResourcesHealthCheck())
    
    # Workflow system health check
    health_monitor.register_check(WorkflowHealthCheck())
    
    logger.info("Standard health checks initialized")

async def get_health_status() -> Dict[str, Any]:
    """Get current health status"""
    return health_monitor.get_overall_status()

async def run_health_check(name: str) -> Optional[Dict[str, Any]]:
    """Run a specific health check"""
    result = await health_monitor.run_check(name)
    return result.to_dict() if result else None
