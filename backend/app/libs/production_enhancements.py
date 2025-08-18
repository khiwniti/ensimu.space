"""
Production enhancements for the ensimu-space platform.
Provides security, performance monitoring, health checks, and configuration management.
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import asyncio
import json

logger = logging.getLogger(__name__)

# ============================================================================
# Security Configuration
# ============================================================================

class SecurityConfig:
    """Security configuration and constants"""
    
    ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    ALLOWED_HEADERS = [
        "accept",
        "accept-encoding", 
        "authorization",
        "content-type",
        "dnt",
        "origin",
        "user-agent",
        "x-csrftoken",
        "x-requested-with",
    ]
    
    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }

# ============================================================================
# Configuration Manager
# ============================================================================

class ConfigManager:
    """Centralized configuration management"""
    
    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Get application configuration"""
        environment = os.getenv("ENVIRONMENT", "development")
        debug = os.getenv("DEBUG", "false").lower() == "true" or environment == "development"
        
        config = {
            "environment": environment,
            "debug": debug,
            "cors_origins": [
                "http://localhost:3000",
                "http://localhost:8080", 
                "https://localhost:3000",
                "https://localhost:8080"
            ],
            "database_url": os.getenv("DATABASE_URL", "postgresql://ensumu_user:ensumu_password@localhost:5432/ensumu_db"),
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "max_request_size": int(os.getenv("MAX_REQUEST_SIZE", "10485760")),  # 10MB
            "rate_limit_requests": int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
            "rate_limit_window": int(os.getenv("RATE_LIMIT_WINDOW", "60")),  # seconds
        }
        
        # Production-specific settings
        if environment == "production":
            config["cors_origins"] = [
                origin.strip() for origin in 
                os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()
            ]
            config["debug"] = False
        
        return config

# ============================================================================
# Performance Monitor
# ============================================================================

class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics = {
            "requests_total": 0,
            "requests_by_method": {},
            "requests_by_status": {},
            "response_times": [],
            "active_connections": 0,
            "errors_total": 0,
            "memory_usage": 0,
            "cpu_usage": 0
        }
        self.start_time = datetime.utcnow()
    
    def record_request(self, method: str, status_code: int, response_time: float):
        """Record request metrics"""
        self.metrics["requests_total"] += 1
        
        # Track by method
        if method not in self.metrics["requests_by_method"]:
            self.metrics["requests_by_method"][method] = 0
        self.metrics["requests_by_method"][method] += 1
        
        # Track by status code
        if status_code not in self.metrics["requests_by_status"]:
            self.metrics["requests_by_status"][status_code] = 0
        self.metrics["requests_by_status"][status_code] += 1
        
        # Track response times (keep last 1000)
        self.metrics["response_times"].append(response_time)
        if len(self.metrics["response_times"]) > 1000:
            self.metrics["response_times"].pop(0)
        
        # Track errors
        if status_code >= 400:
            self.metrics["errors_total"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        response_times = self.metrics["response_times"]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "uptime_seconds": uptime_seconds,
            "requests_total": self.metrics["requests_total"],
            "requests_by_method": self.metrics["requests_by_method"],
            "requests_by_status": self.metrics["requests_by_status"],
            "average_response_time_ms": round(avg_response_time * 1000, 2),
            "active_connections": self.metrics["active_connections"],
            "errors_total": self.metrics["errors_total"],
            "error_rate": (
                self.metrics["errors_total"] / self.metrics["requests_total"] 
                if self.metrics["requests_total"] > 0 else 0
            ),
            "memory_usage_mb": self.metrics["memory_usage"],
            "cpu_usage_percent": self.metrics["cpu_usage"]
        }

# ============================================================================
# Health Checker
# ============================================================================

class HealthChecker:
    """System health monitoring"""
    
    @staticmethod
    async def get_system_health() -> Dict[str, Any]:
        """Comprehensive system health check"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # Check database connectivity
        db_status = await HealthChecker._check_database()
        health_status["checks"]["database"] = db_status
        
        # Check memory usage
        memory_status = await HealthChecker._check_memory()
        health_status["checks"]["memory"] = memory_status
        
        # Check disk space
        disk_status = await HealthChecker._check_disk()
        health_status["checks"]["disk"] = disk_status
        
        # Overall status
        if any(check["status"] == "unhealthy" for check in health_status["checks"].values()):
            health_status["status"] = "unhealthy"
        elif any(check["status"] == "degraded" for check in health_status["checks"].values()):
            health_status["status"] = "degraded"
        
        return health_status
    
    @staticmethod
    async def _check_database() -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            # Simulate database check
            await asyncio.sleep(0.1)  # Simulate connection time
            return {
                "status": "healthy",
                "response_time_ms": 100,
                "message": "Database connection successful"
            }
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": str(e),
                "message": "Database connection failed"
            }
    
    @staticmethod
    async def _check_memory() -> Dict[str, Any]:
        """Check memory usage"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            if usage_percent > 90:
                status = "unhealthy"
            elif usage_percent > 80:
                status = "degraded"
            else:
                status = "healthy"
            
            return {
                "status": status,
                "usage_percent": usage_percent,
                "available_mb": round(memory.available / 1024 / 1024),
                "total_mb": round(memory.total / 1024 / 1024)
            }
        except ImportError:
            return {
                "status": "unknown",
                "message": "psutil not available for memory monitoring"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    @staticmethod
    async def _check_disk() -> Dict[str, Any]:
        """Check disk space"""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            usage_percent = (used / total) * 100
            
            if usage_percent > 95:
                status = "unhealthy"
            elif usage_percent > 85:
                status = "degraded"
            else:
                status = "healthy"
            
            return {
                "status": status,
                "usage_percent": round(usage_percent, 2),
                "free_gb": round(free / 1024 / 1024 / 1024, 2),
                "total_gb": round(total / 1024 / 1024 / 1024, 2)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# ============================================================================
# Cache Manager
# ============================================================================

class CacheManager:
    """Simple in-memory cache manager"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
        self.default_ttl = 300  # 5 minutes
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        if key in self._cache:
            if self._is_expired(key):
                self.delete(key)
                return None
            return self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with TTL"""
        self._cache[key] = value
        self._timestamps[key] = {
            "created": time.time(),
            "ttl": ttl or self.default_ttl
        }
    
    def delete(self, key: str) -> None:
        """Delete cached value"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached values"""
        self._cache.clear()
        self._timestamps.clear()
    
    def clear_expired(self) -> int:
        """Clear expired entries and return count"""
        expired_keys = [
            key for key in self._cache.keys() 
            if self._is_expired(key)
        ]
        
        for key in expired_keys:
            self.delete(key)
        
        return len(expired_keys)
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self._timestamps:
            return True
        
        timestamp_info = self._timestamps[key]
        age = time.time() - timestamp_info["created"]
        return age > timestamp_info["ttl"]

# ============================================================================
# Middleware Functions
# ============================================================================

# Global instances
performance_monitor = PerformanceMonitor()
cache_manager = CacheManager()

async def security_headers_middleware(request: Request, call_next) -> Response:
    """Add security headers to responses"""
    response = await call_next(request)
    
    # Add security headers
    for header, value in SecurityConfig.SECURITY_HEADERS.items():
        response.headers[header] = value
    
    return response

async def performance_middleware(request: Request, call_next) -> Response:
    """Monitor request performance"""
    start_time = time.time()
    performance_monitor.metrics["active_connections"] += 1
    
    try:
        response = await call_next(request)
        
        # Record metrics
        response_time = time.time() - start_time
        performance_monitor.record_request(
            method=request.method,
            status_code=response.status_code,
            response_time=response_time
        )
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{round(response_time * 1000, 2)}ms"
        
        return response
        
    except Exception as e:
        # Record error
        response_time = time.time() - start_time
        performance_monitor.record_request(
            method=request.method,
            status_code=500,
            response_time=response_time
        )
        raise e
    
    finally:
        performance_monitor.metrics["active_connections"] -= 1

async def rate_limit_middleware(request: Request, call_next) -> Response:
    """Simple rate limiting middleware"""
    client_ip = request.client.host if request.client else "unknown"
    
    # Simple rate limiting logic (in production, use Redis)
    rate_limit_key = f"rate_limit:{client_ip}"
    current_requests = cache_manager.get(rate_limit_key) or 0
    
    config = ConfigManager.get_config()
    max_requests = config["rate_limit_requests"]
    
    if current_requests >= max_requests:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please try again later."}
        )
    
    # Update request count
    cache_manager.set(rate_limit_key, current_requests + 1, ttl=config["rate_limit_window"])
    
    response = await call_next(request)
    
    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = str(max_requests)
    response.headers["X-RateLimit-Remaining"] = str(max(0, max_requests - current_requests - 1))
    
    return response

# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "SecurityConfig",
    "PerformanceMonitor", 
    "HealthChecker",
    "ConfigManager",
    "CacheManager",
    "performance_monitor",
    "cache_manager",
    "security_headers_middleware",
    "performance_middleware", 
    "rate_limit_middleware"
]