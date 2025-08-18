"""
Advanced caching system for AI agents and workflow components.
Implements multi-level caching with Redis, in-memory caching, and intelligent cache invalidation.
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
import redis.asyncio as redis
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class CacheConfig:
    """Configuration for caching system"""
    
    # Redis configuration
    REDIS_URL = "redis://localhost:6379"
    REDIS_DB = 0
    REDIS_PASSWORD = None
    
    # Cache TTL settings (in seconds)
    AGENT_RESPONSE_TTL = 3600  # 1 hour
    GEOMETRY_ANALYSIS_TTL = 7200  # 2 hours
    MESH_STRATEGY_TTL = 1800  # 30 minutes
    MATERIAL_DATA_TTL = 86400  # 24 hours
    PHYSICS_CONFIG_TTL = 3600  # 1 hour
    WORKFLOW_STATE_TTL = 1800  # 30 minutes
    
    # In-memory cache settings
    MAX_MEMORY_CACHE_SIZE = 1000
    MEMORY_CACHE_TTL = 300  # 5 minutes
    
    # Cache key prefixes
    AGENT_PREFIX = "agent"
    WORKFLOW_PREFIX = "workflow"
    GEOMETRY_PREFIX = "geometry"
    MESH_PREFIX = "mesh"
    MATERIAL_PREFIX = "material"
    PHYSICS_PREFIX = "physics"

class CacheManager:
    """Advanced cache manager with Redis and in-memory caching for distributed environments"""

    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.redis_client: Optional[redis.Redis] = None
        self.redis_cluster_client: Optional[redis.RedisCluster] = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "redis_hits": 0,
            "memory_hits": 0,
            "invalidations": 0,
            "cluster_hits": 0,
            "distributed_invalidations": 0
        }
        self.node_id = self._generate_node_id()
        self.distributed_mode = False
        
    def _generate_node_id(self) -> str:
        """Generate unique node ID for distributed caching"""
        import socket
        import uuid
        hostname = socket.gethostname()
        return f"{hostname}_{str(uuid.uuid4())[:8]}"

    async def initialize(self, cluster_nodes: List[str] = None):
        """Initialize Redis connection with cluster support"""
        try:
            if cluster_nodes:
                # Initialize Redis Cluster for distributed caching
                self.redis_cluster_client = redis.RedisCluster(
                    startup_nodes=[{"host": node.split(":")[0], "port": int(node.split(":")[1])}
                                 for node in cluster_nodes],
                    decode_responses=False,
                    skip_full_coverage_check=True
                )
                await self.redis_cluster_client.ping()
                self.distributed_mode = True
                logger.info("Redis cluster cache initialized successfully")
            else:
                # Initialize single Redis instance
                self.redis_client = redis.Redis.from_url(
                    self.config.REDIS_URL,
                    db=self.config.REDIS_DB,
                    password=self.config.REDIS_PASSWORD,
                    decode_responses=False
                )
                await self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}. Using memory cache only.")
            self.redis_client = None
            self.redis_cluster_client = None
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    def _generate_cache_key(self, prefix: str, identifier: str, params: Dict[str, Any] = None) -> str:
        """Generate cache key with optional parameter hashing"""
        key_parts = [prefix, identifier]
        
        if params:
            # Create deterministic hash of parameters
            param_str = json.dumps(params, sort_keys=True, default=str)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            key_parts.append(param_hash)
        
        return ":".join(key_parts)
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for caching"""
        try:
            return pickle.dumps(data)
        except Exception as e:
            logger.error(f"Failed to serialize data: {e}")
            return b""
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize cached data"""
        try:
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"Failed to deserialize data: {e}")
            return None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (memory first, then Redis)"""
        # Check memory cache first
        if key in self.memory_cache:
            cache_entry = self.memory_cache[key]
            if cache_entry["expires_at"] > time.time():
                self.cache_stats["hits"] += 1
                self.cache_stats["memory_hits"] += 1
                return cache_entry["data"]
            else:
                # Expired, remove from memory cache
                del self.memory_cache[key]
        
        # Check Redis cache
        if self.redis_client:
            try:
                data = await self.redis_client.get(key)
                if data:
                    deserialized = self._deserialize_data(data)
                    if deserialized is not None:
                        # Store in memory cache for faster access
                        self.memory_cache[key] = {
                            "data": deserialized,
                            "expires_at": time.time() + self.config.MEMORY_CACHE_TTL
                        }
                        self._cleanup_memory_cache()
                        
                        self.cache_stats["hits"] += 1
                        self.cache_stats["redis_hits"] += 1
                        return deserialized
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        self.cache_stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache"""
        if ttl is None:
            ttl = self.config.MEMORY_CACHE_TTL
        
        # Store in memory cache
        self.memory_cache[key] = {
            "data": value,
            "expires_at": time.time() + min(ttl, self.config.MEMORY_CACHE_TTL)
        }
        self._cleanup_memory_cache()
        
        # Store in Redis cache
        if self.redis_client:
            try:
                serialized = self._serialize_data(value)
                if serialized:
                    await self.redis_client.setex(key, ttl, serialized)
                    return True
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        
        return True  # Memory cache succeeded
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        # Remove from memory cache
        if key in self.memory_cache:
            del self.memory_cache[key]
        
        # Remove from Redis cache
        if self.redis_client:
            try:
                await self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        
        self.cache_stats["invalidations"] += 1
        return True
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        deleted_count = 0
        
        # Remove from memory cache
        keys_to_delete = [k for k in self.memory_cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.memory_cache[key]
            deleted_count += 1
        
        # Remove from Redis cache
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(f"*{pattern}*")
                if keys:
                    deleted_count += await self.redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Redis delete pattern error: {e}")
        
        self.cache_stats["invalidations"] += deleted_count
        return deleted_count
    
    def _cleanup_memory_cache(self):
        """Clean up expired entries and enforce size limits"""
        current_time = time.time()
        
        # Remove expired entries
        expired_keys = [
            k for k, v in self.memory_cache.items()
            if v["expires_at"] <= current_time
        ]
        for key in expired_keys:
            del self.memory_cache[key]
        
        # Enforce size limit (LRU-style)
        if len(self.memory_cache) > self.config.MAX_MEMORY_CACHE_SIZE:
            # Sort by expiration time and remove oldest
            sorted_items = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1]["expires_at"]
            )
            excess_count = len(self.memory_cache) - self.config.MAX_MEMORY_CACHE_SIZE
            for key, _ in sorted_items[:excess_count]:
                del self.memory_cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.cache_stats,
            "hit_rate_percent": round(hit_rate, 2),
            "memory_cache_size": len(self.memory_cache),
            "redis_connected": self.redis_client is not None
        }

# Global cache manager instance
cache_manager = CacheManager()

# Decorator for caching function results
def cached(prefix: str, ttl: int = None, key_func: Callable = None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [str(arg) for arg in args]
                key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
                identifier = hashlib.md5(":".join(key_parts).encode()).hexdigest()[:16]
                cache_key = cache_manager._generate_cache_key(prefix, identifier)
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            if result is not None:
                await cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

# Specialized cache decorators for different components
def cache_agent_response(agent_type: str, ttl: int = None):
    """Cache AI agent responses"""
    if ttl is None:
        ttl = CacheConfig.AGENT_RESPONSE_TTL
    
    def key_func(*args, **kwargs):
        # Extract request data for key generation
        request_data = kwargs.get('request_data', {})
        context = kwargs.get('context', {})
        
        key_data = {
            "agent_type": agent_type,
            "request": request_data,
            "project_id": getattr(context, 'project_id', None)
        }
        
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()[:16]
        return cache_manager._generate_cache_key(CacheConfig.AGENT_PREFIX, f"{agent_type}:{key_hash}")
    
    return cached(CacheConfig.AGENT_PREFIX, ttl, key_func)

def cache_geometry_analysis(ttl: int = None):
    """Cache geometry analysis results"""
    if ttl is None:
        ttl = CacheConfig.GEOMETRY_ANALYSIS_TTL
    
    def key_func(*args, **kwargs):
        file_data = kwargs.get('file_data', {})
        file_hash = file_data.get('file_hash', file_data.get('id', 'unknown'))
        return cache_manager._generate_cache_key(CacheConfig.GEOMETRY_PREFIX, file_hash)
    
    return cached(CacheConfig.GEOMETRY_PREFIX, ttl, key_func)

def cache_mesh_strategy(ttl: int = None):
    """Cache mesh generation strategies"""
    if ttl is None:
        ttl = CacheConfig.MESH_STRATEGY_TTL
    
    def key_func(*args, **kwargs):
        geometry_data = kwargs.get('geometry_analysis', {})
        requirements = kwargs.get('requirements', {})
        
        key_data = {
            "geometry_hash": geometry_data.get('file_hash', 'unknown'),
            "requirements": requirements
        }
        
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()[:16]
        return cache_manager._generate_cache_key(CacheConfig.MESH_PREFIX, key_hash)
    
    return cached(CacheConfig.MESH_PREFIX, ttl, key_func)

# Cache invalidation utilities
class CacheInvalidator:
    """Utilities for intelligent cache invalidation"""
    
    @staticmethod
    async def invalidate_project_cache(project_id: str):
        """Invalidate all cache entries for a project"""
        patterns = [
            f"*{project_id}*",
            f"{CacheConfig.WORKFLOW_PREFIX}:*{project_id}*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await cache_manager.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Invalidated {total_deleted} cache entries for project {project_id}")
        return total_deleted
    
    @staticmethod
    async def invalidate_workflow_cache(workflow_id: str):
        """Invalidate cache entries for a specific workflow"""
        pattern = f"{CacheConfig.WORKFLOW_PREFIX}:*{workflow_id}*"
        deleted = await cache_manager.delete_pattern(pattern)
        
        logger.info(f"Invalidated {deleted} cache entries for workflow {workflow_id}")
        return deleted
    
    @staticmethod
    async def invalidate_agent_cache(agent_type: str, project_id: str = None):
        """Invalidate cache entries for a specific agent type"""
        if project_id:
            pattern = f"{CacheConfig.AGENT_PREFIX}:{agent_type}:*{project_id}*"
        else:
            pattern = f"{CacheConfig.AGENT_PREFIX}:{agent_type}:*"
        
        deleted = await cache_manager.delete_pattern(pattern)
        logger.info(f"Invalidated {deleted} cache entries for {agent_type} agent")
        return deleted
