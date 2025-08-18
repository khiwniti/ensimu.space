"""
Load balancing system for AI agent requests and workflow distribution.
Implements intelligent load balancing strategies for high-concurrency scenarios.
"""

import asyncio
import logging
import random
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple
import threading
import hashlib

logger = logging.getLogger(__name__)

class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_RESPONSE_TIME = "least_response_time"
    RESOURCE_BASED = "resource_based"
    CONSISTENT_HASH = "consistent_hash"

class WorkerStatus(Enum):
    """Worker status states"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"

@dataclass
class WorkerNode:
    """Represents a worker node in the load balancer"""
    node_id: str
    host: str
    port: int
    weight: float = 1.0
    max_connections: int = 100
    current_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_health_check: datetime = field(default_factory=datetime.utcnow)
    status: WorkerStatus = WorkerStatus.HEALTHY
    capabilities: List[str] = field(default_factory=list)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 1.0
        return (self.total_requests - self.failed_requests) / self.total_requests
    
    @property
    def load_factor(self) -> float:
        """Calculate current load factor"""
        connection_load = self.current_connections / self.max_connections
        resource_load = (self.cpu_usage + self.memory_usage) / 2
        return (connection_load + resource_load) / 2
    
    @property
    def is_available(self) -> bool:
        """Check if worker is available for new requests"""
        return (
            self.status in [WorkerStatus.HEALTHY, WorkerStatus.DEGRADED] and
            self.current_connections < self.max_connections
        )

class LoadBalancer:
    """Intelligent load balancer for AI agent requests"""
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_CONNECTIONS):
        self.strategy = strategy
        self.workers: Dict[str, WorkerNode] = {}
        self.request_history: deque = deque(maxlen=10000)
        self.round_robin_index = 0
        self.consistent_hash_ring: Dict[int, str] = {}
        self.lock = threading.RLock()
        
        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "requests_per_second": 0.0
        }
        
        # Health checking
        self.health_check_interval = 30.0
        self.health_check_timeout = 5.0
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
    
    def add_worker(self, worker: WorkerNode):
        """Add a worker node to the load balancer"""
        with self.lock:
            self.workers[worker.node_id] = worker
            self._rebuild_consistent_hash_ring()
            logger.info(f"Added worker {worker.node_id} ({worker.host}:{worker.port})")
    
    def remove_worker(self, node_id: str):
        """Remove a worker node from the load balancer"""
        with self.lock:
            if node_id in self.workers:
                worker = self.workers[node_id]
                del self.workers[node_id]
                self._rebuild_consistent_hash_ring()
                logger.info(f"Removed worker {node_id} ({worker.host}:{worker.port})")
    
    def get_worker(self, request_id: str = None, agent_type: str = None) -> Optional[WorkerNode]:
        """Get the best worker based on the load balancing strategy"""
        with self.lock:
            available_workers = [w for w in self.workers.values() if w.is_available]
            
            if not available_workers:
                logger.warning("No available workers")
                return None
            
            # Filter by capabilities if agent_type specified
            if agent_type:
                capable_workers = [w for w in available_workers if agent_type in w.capabilities or not w.capabilities]
                if capable_workers:
                    available_workers = capable_workers
            
            if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
                return self._round_robin_selection(available_workers)
            elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
                return self._least_connections_selection(available_workers)
            elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
                return self._weighted_round_robin_selection(available_workers)
            elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
                return self._least_response_time_selection(available_workers)
            elif self.strategy == LoadBalancingStrategy.RESOURCE_BASED:
                return self._resource_based_selection(available_workers)
            elif self.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
                return self._consistent_hash_selection(available_workers, request_id)
            else:
                return random.choice(available_workers)
    
    def _round_robin_selection(self, workers: List[WorkerNode]) -> WorkerNode:
        """Round-robin worker selection"""
        worker = workers[self.round_robin_index % len(workers)]
        self.round_robin_index += 1
        return worker
    
    def _least_connections_selection(self, workers: List[WorkerNode]) -> WorkerNode:
        """Select worker with least connections"""
        return min(workers, key=lambda w: w.current_connections)
    
    def _weighted_round_robin_selection(self, workers: List[WorkerNode]) -> WorkerNode:
        """Weighted round-robin selection based on worker weights"""
        total_weight = sum(w.weight for w in workers)
        if total_weight == 0:
            return random.choice(workers)
        
        # Create weighted list
        weighted_workers = []
        for worker in workers:
            count = int(worker.weight * 10)  # Scale weights
            weighted_workers.extend([worker] * count)
        
        if not weighted_workers:
            return random.choice(workers)
        
        return weighted_workers[self.round_robin_index % len(weighted_workers)]
    
    def _least_response_time_selection(self, workers: List[WorkerNode]) -> WorkerNode:
        """Select worker with lowest average response time"""
        return min(workers, key=lambda w: w.avg_response_time)
    
    def _resource_based_selection(self, workers: List[WorkerNode]) -> WorkerNode:
        """Select worker based on resource utilization"""
        return min(workers, key=lambda w: w.load_factor)
    
    def _consistent_hash_selection(self, workers: List[WorkerNode], request_id: str) -> WorkerNode:
        """Consistent hash-based selection"""
        if not request_id:
            return random.choice(workers)
        
        # Hash the request ID
        hash_value = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
        
        # Find the closest worker in the hash ring
        if not self.consistent_hash_ring:
            return random.choice(workers)
        
        # Get sorted hash values
        sorted_hashes = sorted(self.consistent_hash_ring.keys())
        
        # Find the first hash greater than or equal to our hash
        for ring_hash in sorted_hashes:
            if ring_hash >= hash_value:
                worker_id = self.consistent_hash_ring[ring_hash]
                if worker_id in self.workers and self.workers[worker_id].is_available:
                    return self.workers[worker_id]
        
        # Wrap around to the first worker
        worker_id = self.consistent_hash_ring[sorted_hashes[0]]
        if worker_id in self.workers and self.workers[worker_id].is_available:
            return self.workers[worker_id]
        
        return random.choice(workers)
    
    def _rebuild_consistent_hash_ring(self):
        """Rebuild the consistent hash ring"""
        self.consistent_hash_ring.clear()
        
        for worker_id, worker in self.workers.items():
            # Create multiple hash points for better distribution
            for i in range(100):  # 100 virtual nodes per worker
                hash_key = f"{worker_id}:{i}"
                hash_value = int(hashlib.md5(hash_key.encode()).hexdigest(), 16)
                self.consistent_hash_ring[hash_value] = worker_id
    
    async def execute_request(self, request_func: Callable, request_id: str = None, 
                            agent_type: str = None, timeout: float = 30.0) -> Any:
        """Execute a request using load balancing"""
        start_time = time.time()
        worker = self.get_worker(request_id, agent_type)
        
        if not worker:
            raise Exception("No available workers")
        
        # Update worker connection count
        with self.lock:
            worker.current_connections += 1
            worker.total_requests += 1
            self.metrics["total_requests"] += 1
        
        try:
            # Execute the request with timeout
            result = await asyncio.wait_for(request_func(worker), timeout=timeout)
            
            # Update success metrics
            response_time = time.time() - start_time
            with self.lock:
                worker.avg_response_time = (
                    (worker.avg_response_time * (worker.total_requests - 1) + response_time) / 
                    worker.total_requests
                )
                self.metrics["successful_requests"] += 1
                self._update_avg_response_time(response_time)
            
            return result
            
        except Exception as e:
            # Update failure metrics
            with self.lock:
                worker.failed_requests += 1
                self.metrics["failed_requests"] += 1
            
            logger.error(f"Request failed on worker {worker.node_id}: {e}")
            raise
        
        finally:
            # Decrease connection count
            with self.lock:
                worker.current_connections = max(0, worker.current_connections - 1)
    
    def _update_avg_response_time(self, response_time: float):
        """Update average response time metric"""
        total_requests = self.metrics["total_requests"]
        if total_requests > 0:
            self.metrics["avg_response_time"] = (
                (self.metrics["avg_response_time"] * (total_requests - 1) + response_time) / 
                total_requests
            )
    
    def update_worker_health(self, node_id: str, cpu_usage: float, memory_usage: float, 
                           status: WorkerStatus = None):
        """Update worker health metrics"""
        with self.lock:
            if node_id in self.workers:
                worker = self.workers[node_id]
                worker.cpu_usage = cpu_usage
                worker.memory_usage = memory_usage
                worker.last_health_check = datetime.utcnow()
                
                if status:
                    worker.status = status
                else:
                    # Auto-determine status based on metrics
                    if cpu_usage > 90 or memory_usage > 90:
                        worker.status = WorkerStatus.UNHEALTHY
                    elif cpu_usage > 70 or memory_usage > 70:
                        worker.status = WorkerStatus.DEGRADED
                    else:
                        worker.status = WorkerStatus.HEALTHY
    
    def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get comprehensive load balancer statistics"""
        with self.lock:
            worker_stats = {}
            for node_id, worker in self.workers.items():
                worker_stats[node_id] = {
                    "host": worker.host,
                    "port": worker.port,
                    "status": worker.status.value,
                    "current_connections": worker.current_connections,
                    "total_requests": worker.total_requests,
                    "success_rate": worker.success_rate,
                    "avg_response_time": worker.avg_response_time,
                    "load_factor": worker.load_factor,
                    "cpu_usage": worker.cpu_usage,
                    "memory_usage": worker.memory_usage
                }
            
            # Calculate requests per second
            if self.request_history:
                recent_requests = [r for r in self.request_history if r > time.time() - 60]
                self.metrics["requests_per_second"] = len(recent_requests) / 60
            
            return {
                "strategy": self.strategy.value,
                "total_workers": len(self.workers),
                "healthy_workers": len([w for w in self.workers.values() if w.status == WorkerStatus.HEALTHY]),
                "metrics": self.metrics,
                "workers": worker_stats
            }
    
    def start_health_monitoring(self):
        """Start health monitoring for workers"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.stop_event.clear()
        
        def monitor_loop():
            while not self.stop_event.wait(self.health_check_interval):
                try:
                    self._perform_health_checks()
                except Exception as e:
                    logger.error(f"Health check error: {e}")
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Load balancer health monitoring started")
    
    def stop_health_monitoring(self):
        """Stop health monitoring"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        self.stop_event.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        logger.info("Load balancer health monitoring stopped")
    
    def _perform_health_checks(self):
        """Perform health checks on all workers"""
        current_time = datetime.utcnow()
        
        with self.lock:
            for worker in self.workers.values():
                # Check if worker hasn't been updated recently
                time_since_update = current_time - worker.last_health_check
                
                if time_since_update > timedelta(seconds=self.health_check_interval * 2):
                    worker.status = WorkerStatus.OFFLINE
                    logger.warning(f"Worker {worker.node_id} marked as offline")

# Agent-specific load balancer
class AgentLoadBalancer(LoadBalancer):
    """Specialized load balancer for AI agents"""
    
    def __init__(self):
        super().__init__(LoadBalancingStrategy.RESOURCE_BASED)
        self.agent_pools: Dict[str, List[str]] = defaultdict(list)
    
    def add_agent_worker(self, worker: WorkerNode, agent_types: List[str]):
        """Add a worker with specific agent capabilities"""
        worker.capabilities = agent_types
        self.add_worker(worker)
        
        # Update agent pools
        for agent_type in agent_types:
            self.agent_pools[agent_type].append(worker.node_id)
    
    def get_agent_worker(self, agent_type: str, request_id: str = None) -> Optional[WorkerNode]:
        """Get the best worker for a specific agent type"""
        return self.get_worker(request_id, agent_type)
    
    async def execute_agent_request(self, agent_type: str, request_func: Callable, 
                                  request_id: str = None, timeout: float = 60.0) -> Any:
        """Execute an agent request with specialized load balancing"""
        return await self.execute_request(request_func, request_id, agent_type, timeout)

# Global load balancer instances
main_load_balancer = LoadBalancer(LoadBalancingStrategy.LEAST_CONNECTIONS)
agent_load_balancer = AgentLoadBalancer()

def initialize_load_balancing():
    """Initialize load balancing system"""
    main_load_balancer.start_health_monitoring()
    agent_load_balancer.start_health_monitoring()
    logger.info("Load balancing system initialized")

def cleanup_load_balancing():
    """Cleanup load balancing system"""
    main_load_balancer.stop_health_monitoring()
    agent_load_balancer.stop_health_monitoring()
    logger.info("Load balancing system cleaned up")
