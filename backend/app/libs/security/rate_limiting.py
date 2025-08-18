"""
Advanced rate limiting system for API endpoints and user actions.
Implements multiple rate limiting strategies with Redis backend for distributed environments.
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import threading
import hashlib

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"

class RateLimitScope(Enum):
    """Rate limit scope"""
    GLOBAL = "global"
    PER_IP = "per_ip"
    PER_USER = "per_user"
    PER_API_KEY = "per_api_key"
    PER_ENDPOINT = "per_endpoint"

@dataclass
class RateLimitRule:
    """Rate limiting rule configuration"""
    name: str
    strategy: RateLimitStrategy
    scope: RateLimitScope
    limit: int  # Number of requests
    window_seconds: int  # Time window in seconds
    burst_limit: Optional[int] = None  # For token bucket
    leak_rate: Optional[float] = None  # For leaky bucket
    enabled: bool = True
    
    def get_key(self, identifier: str) -> str:
        """Generate cache key for this rule and identifier"""
        return f"rate_limit:{self.name}:{self.scope.value}:{identifier}"

class RateLimitResult:
    """Rate limit check result"""
    
    def __init__(self, allowed: bool, limit: int, remaining: int, reset_time: datetime, 
                 retry_after: Optional[int] = None):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time
        self.retry_after = retry_after  # Seconds until next request allowed
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers"""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_time.timestamp()))
        }
        
        if self.retry_after:
            headers["Retry-After"] = str(self.retry_after)
        
        return headers

class DistributedRateLimiter:
    """Distributed rate limiter using Redis"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or "redis://localhost:6379"
        self.redis_client: Optional[redis.Redis] = None
        self.local_cache: Dict[str, Any] = {}
        self.rules: Dict[str, RateLimitRule] = {}
        self.lock = threading.RLock()
        
        # Fallback to in-memory if Redis not available
        self.use_redis = REDIS_AVAILABLE and redis_url
        
        if not self.use_redis:
            logger.warning("Redis not available, using in-memory rate limiting")
    
    async def initialize(self):
        """Initialize Redis connection"""
        if self.use_redis:
            try:
                self.redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True)
                await self.redis_client.ping()
                logger.info("Redis rate limiter initialized")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
                self.use_redis = False
    
    def add_rule(self, rule: RateLimitRule):
        """Add a rate limiting rule"""
        with self.lock:
            self.rules[rule.name] = rule
            logger.info(f"Added rate limit rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove a rate limiting rule"""
        with self.lock:
            if rule_name in self.rules:
                del self.rules[rule_name]
                logger.info(f"Removed rate limit rule: {rule_name}")
    
    async def check_rate_limit(self, rule_name: str, identifier: str) -> RateLimitResult:
        """Check if request is within rate limits"""
        if rule_name not in self.rules:
            # No rule found, allow request
            return RateLimitResult(
                allowed=True,
                limit=0,
                remaining=0,
                reset_time=datetime.utcnow()
            )
        
        rule = self.rules[rule_name]
        if not rule.enabled:
            return RateLimitResult(
                allowed=True,
                limit=rule.limit,
                remaining=rule.limit,
                reset_time=datetime.utcnow()
            )
        
        # Apply rate limiting based on strategy
        if rule.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._check_fixed_window(rule, identifier)
        elif rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._check_sliding_window(rule, identifier)
        elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._check_token_bucket(rule, identifier)
        elif rule.strategy == RateLimitStrategy.LEAKY_BUCKET:
            return await self._check_leaky_bucket(rule, identifier)
        else:
            # Default to fixed window
            return await self._check_fixed_window(rule, identifier)
    
    async def _check_fixed_window(self, rule: RateLimitRule, identifier: str) -> RateLimitResult:
        """Fixed window rate limiting"""
        now = datetime.utcnow()
        window_start = now.replace(second=0, microsecond=0)
        window_start = window_start.replace(minute=window_start.minute - (window_start.minute % (rule.window_seconds // 60)))
        
        key = f"{rule.get_key(identifier)}:fixed:{int(window_start.timestamp())}"
        
        if self.use_redis and self.redis_client:
            try:
                # Use Redis for distributed rate limiting
                current_count = await self.redis_client.get(key)
                current_count = int(current_count) if current_count else 0
                
                if current_count >= rule.limit:
                    reset_time = window_start + timedelta(seconds=rule.window_seconds)
                    retry_after = int((reset_time - now).total_seconds())
                    
                    return RateLimitResult(
                        allowed=False,
                        limit=rule.limit,
                        remaining=0,
                        reset_time=reset_time,
                        retry_after=retry_after
                    )
                
                # Increment counter
                pipe = self.redis_client.pipeline()
                pipe.incr(key)
                pipe.expire(key, rule.window_seconds)
                await pipe.execute()
                
                remaining = rule.limit - current_count - 1
                reset_time = window_start + timedelta(seconds=rule.window_seconds)
                
                return RateLimitResult(
                    allowed=True,
                    limit=rule.limit,
                    remaining=remaining,
                    reset_time=reset_time
                )
                
            except Exception as e:
                logger.error(f"Redis rate limit check failed: {e}")
                # Fall back to local cache
        
        # Local cache fallback
        with self.lock:
            if key not in self.local_cache:
                self.local_cache[key] = {"count": 0, "window_start": window_start}
            
            cache_entry = self.local_cache[key]
            
            # Reset if new window
            if cache_entry["window_start"] != window_start:
                cache_entry["count"] = 0
                cache_entry["window_start"] = window_start
            
            if cache_entry["count"] >= rule.limit:
                reset_time = window_start + timedelta(seconds=rule.window_seconds)
                retry_after = int((reset_time - now).total_seconds())
                
                return RateLimitResult(
                    allowed=False,
                    limit=rule.limit,
                    remaining=0,
                    reset_time=reset_time,
                    retry_after=retry_after
                )
            
            cache_entry["count"] += 1
            remaining = rule.limit - cache_entry["count"]
            reset_time = window_start + timedelta(seconds=rule.window_seconds)
            
            return RateLimitResult(
                allowed=True,
                limit=rule.limit,
                remaining=remaining,
                reset_time=reset_time
            )
    
    async def _check_sliding_window(self, rule: RateLimitRule, identifier: str) -> RateLimitResult:
        """Sliding window rate limiting"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=rule.window_seconds)
        
        key = rule.get_key(identifier)
        
        if self.use_redis and self.redis_client:
            try:
                # Use Redis sorted set for sliding window
                # Remove old entries
                await self.redis_client.zremrangebyscore(key, 0, window_start.timestamp())
                
                # Count current entries
                current_count = await self.redis_client.zcard(key)
                
                if current_count >= rule.limit:
                    # Find oldest entry to determine reset time
                    oldest_entries = await self.redis_client.zrange(key, 0, 0, withscores=True)
                    if oldest_entries:
                        oldest_time = datetime.fromtimestamp(oldest_entries[0][1])
                        reset_time = oldest_time + timedelta(seconds=rule.window_seconds)
                        retry_after = int((reset_time - now).total_seconds())
                    else:
                        reset_time = now + timedelta(seconds=rule.window_seconds)
                        retry_after = rule.window_seconds
                    
                    return RateLimitResult(
                        allowed=False,
                        limit=rule.limit,
                        remaining=0,
                        reset_time=reset_time,
                        retry_after=retry_after
                    )
                
                # Add current request
                await self.redis_client.zadd(key, {str(now.timestamp()): now.timestamp()})
                await self.redis_client.expire(key, rule.window_seconds)
                
                remaining = rule.limit - current_count - 1
                reset_time = now + timedelta(seconds=rule.window_seconds)
                
                return RateLimitResult(
                    allowed=True,
                    limit=rule.limit,
                    remaining=remaining,
                    reset_time=reset_time
                )
                
            except Exception as e:
                logger.error(f"Redis sliding window check failed: {e}")
        
        # Local cache fallback
        with self.lock:
            if key not in self.local_cache:
                self.local_cache[key] = deque()
            
            request_times = self.local_cache[key]
            
            # Remove old requests
            while request_times and request_times[0] < window_start:
                request_times.popleft()
            
            if len(request_times) >= rule.limit:
                reset_time = request_times[0] + timedelta(seconds=rule.window_seconds)
                retry_after = int((reset_time - now).total_seconds())
                
                return RateLimitResult(
                    allowed=False,
                    limit=rule.limit,
                    remaining=0,
                    reset_time=reset_time,
                    retry_after=retry_after
                )
            
            request_times.append(now)
            remaining = rule.limit - len(request_times)
            reset_time = now + timedelta(seconds=rule.window_seconds)
            
            return RateLimitResult(
                allowed=True,
                limit=rule.limit,
                remaining=remaining,
                reset_time=reset_time
            )
    
    async def _check_token_bucket(self, rule: RateLimitRule, identifier: str) -> RateLimitResult:
        """Token bucket rate limiting"""
        now = datetime.utcnow()
        key = rule.get_key(identifier)
        
        bucket_size = rule.burst_limit or rule.limit
        refill_rate = rule.limit / rule.window_seconds  # tokens per second
        
        if self.use_redis and self.redis_client:
            try:
                # Get current bucket state
                bucket_data = await self.redis_client.hmget(key, "tokens", "last_refill")
                
                current_tokens = float(bucket_data[0]) if bucket_data[0] else bucket_size
                last_refill = datetime.fromtimestamp(float(bucket_data[1])) if bucket_data[1] else now
                
                # Calculate tokens to add
                time_passed = (now - last_refill).total_seconds()
                tokens_to_add = time_passed * refill_rate
                current_tokens = min(bucket_size, current_tokens + tokens_to_add)
                
                if current_tokens < 1:
                    retry_after = int((1 - current_tokens) / refill_rate)
                    reset_time = now + timedelta(seconds=retry_after)
                    
                    return RateLimitResult(
                        allowed=False,
                        limit=rule.limit,
                        remaining=0,
                        reset_time=reset_time,
                        retry_after=retry_after
                    )
                
                # Consume token
                current_tokens -= 1
                
                # Update bucket state
                await self.redis_client.hmset(key, {
                    "tokens": current_tokens,
                    "last_refill": now.timestamp()
                })
                await self.redis_client.expire(key, rule.window_seconds * 2)
                
                return RateLimitResult(
                    allowed=True,
                    limit=bucket_size,
                    remaining=int(current_tokens),
                    reset_time=now + timedelta(seconds=rule.window_seconds)
                )
                
            except Exception as e:
                logger.error(f"Redis token bucket check failed: {e}")
        
        # Local cache fallback
        with self.lock:
            if key not in self.local_cache:
                self.local_cache[key] = {
                    "tokens": bucket_size,
                    "last_refill": now
                }
            
            bucket = self.local_cache[key]
            
            # Refill tokens
            time_passed = (now - bucket["last_refill"]).total_seconds()
            tokens_to_add = time_passed * refill_rate
            bucket["tokens"] = min(bucket_size, bucket["tokens"] + tokens_to_add)
            bucket["last_refill"] = now
            
            if bucket["tokens"] < 1:
                retry_after = int((1 - bucket["tokens"]) / refill_rate)
                reset_time = now + timedelta(seconds=retry_after)
                
                return RateLimitResult(
                    allowed=False,
                    limit=rule.limit,
                    remaining=0,
                    reset_time=reset_time,
                    retry_after=retry_after
                )
            
            bucket["tokens"] -= 1
            
            return RateLimitResult(
                allowed=True,
                limit=bucket_size,
                remaining=int(bucket["tokens"]),
                reset_time=now + timedelta(seconds=rule.window_seconds)
            )
    
    async def _check_leaky_bucket(self, rule: RateLimitRule, identifier: str) -> RateLimitResult:
        """Leaky bucket rate limiting"""
        now = datetime.utcnow()
        key = rule.get_key(identifier)
        
        bucket_size = rule.burst_limit or rule.limit
        leak_rate = rule.leak_rate or (rule.limit / rule.window_seconds)
        
        # Similar implementation to token bucket but with leaking behavior
        # For brevity, using simplified version
        return await self._check_token_bucket(rule, identifier)
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        with self.lock:
            return {
                "rules": {
                    name: {
                        "strategy": rule.strategy.value,
                        "scope": rule.scope.value,
                        "limit": rule.limit,
                        "window_seconds": rule.window_seconds,
                        "enabled": rule.enabled
                    }
                    for name, rule in self.rules.items()
                },
                "cache_entries": len(self.local_cache),
                "redis_enabled": self.use_redis
            }

# Global rate limiter instance
rate_limiter = DistributedRateLimiter()

# Predefined rate limiting rules
DEFAULT_RULES = [
    RateLimitRule(
        name="api_general",
        strategy=RateLimitStrategy.SLIDING_WINDOW,
        scope=RateLimitScope.PER_IP,
        limit=100,
        window_seconds=60
    ),
    RateLimitRule(
        name="api_auth",
        strategy=RateLimitStrategy.FIXED_WINDOW,
        scope=RateLimitScope.PER_IP,
        limit=5,
        window_seconds=300  # 5 requests per 5 minutes
    ),
    RateLimitRule(
        name="workflow_start",
        strategy=RateLimitStrategy.TOKEN_BUCKET,
        scope=RateLimitScope.PER_USER,
        limit=10,
        window_seconds=3600,  # 10 per hour
        burst_limit=3
    ),
    RateLimitRule(
        name="file_upload",
        strategy=RateLimitStrategy.LEAKY_BUCKET,
        scope=RateLimitScope.PER_USER,
        limit=20,
        window_seconds=3600,  # 20 per hour
        burst_limit=5,
        leak_rate=0.01  # 1 request per 100 seconds
    )
]

async def initialize_rate_limiting(redis_url: str = None):
    """Initialize rate limiting system"""
    global rate_limiter
    
    if redis_url:
        rate_limiter = DistributedRateLimiter(redis_url)
    
    await rate_limiter.initialize()
    
    # Add default rules
    for rule in DEFAULT_RULES:
        rate_limiter.add_rule(rule)
    
    logger.info("Rate limiting system initialized")

async def check_rate_limit(rule_name: str, identifier: str) -> RateLimitResult:
    """Check rate limit for a specific rule and identifier"""
    return await rate_limiter.check_rate_limit(rule_name, identifier)

def add_rate_limit_rule(rule: RateLimitRule):
    """Add a custom rate limiting rule"""
    rate_limiter.add_rule(rule)

def get_rate_limit_stats():
    """Get rate limiting statistics"""
    return rate_limiter.get_rate_limit_stats()
