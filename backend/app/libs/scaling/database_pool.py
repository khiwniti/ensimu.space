"""
Enhanced database connection pooling for high-concurrency scenarios.
Implements advanced pooling strategies, connection load balancing, and failover support.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, AsyncGenerator
import threading
import random

try:
    import asyncpg
    from asyncpg.pool import Pool
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

logger = logging.getLogger(__name__)

class PoolStrategy(Enum):
    """Database pool strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    WEIGHTED = "weighted"

class DatabaseRole(Enum):
    """Database role types"""
    PRIMARY = "primary"
    REPLICA = "replica"
    ANALYTICS = "analytics"

@dataclass
class DatabaseNode:
    """Database node configuration"""
    node_id: str
    host: str
    port: int
    database: str
    username: str
    password: str
    role: DatabaseRole
    weight: float = 1.0
    max_connections: int = 20
    current_connections: int = 0
    total_queries: int = 0
    failed_queries: int = 0
    avg_response_time: float = 0.0
    last_health_check: datetime = field(default_factory=datetime.utcnow)
    is_healthy: bool = True
    pool: Optional[Pool] = None
    
    @property
    def connection_url(self) -> str:
        """Get PostgreSQL connection URL"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def load_factor(self) -> float:
        """Calculate current load factor"""
        if self.max_connections == 0:
            return 1.0
        return self.current_connections / self.max_connections
    
    @property
    def success_rate(self) -> float:
        """Calculate query success rate"""
        if self.total_queries == 0:
            return 1.0
        return (self.total_queries - self.failed_queries) / self.total_queries

class DistributedConnectionPool:
    """Distributed database connection pool manager"""
    
    def __init__(self, strategy: PoolStrategy = PoolStrategy.LEAST_CONNECTIONS):
        self.strategy = strategy
        self.nodes: Dict[str, DatabaseNode] = {}
        self.primary_nodes: List[str] = []
        self.replica_nodes: List[str] = []
        self.analytics_nodes: List[str] = []
        self.round_robin_index = 0
        self.lock = threading.RLock()
        
        # Pool configuration
        self.pool_config = {
            "min_size": 5,
            "max_size": 20,
            "command_timeout": 30,
            "server_settings": {
                "application_name": "ensimu_space_distributed",
                "jit": "off"
            }
        }
        
        # Health monitoring
        self.health_check_interval = 30.0
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Metrics
        self.pool_metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_response_time": 0.0
        }
    
    async def add_database_node(self, node: DatabaseNode):
        """Add a database node to the pool"""
        try:
            # Create connection pool for the node
            node.pool = await asyncpg.create_pool(
                node.connection_url,
                min_size=self.pool_config["min_size"],
                max_size=node.max_connections,
                command_timeout=self.pool_config["command_timeout"],
                server_settings=self.pool_config["server_settings"]
            )
            
            # Test connection
            async with node.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            with self.lock:
                self.nodes[node.node_id] = node
                
                # Categorize by role
                if node.role == DatabaseRole.PRIMARY:
                    self.primary_nodes.append(node.node_id)
                elif node.role == DatabaseRole.REPLICA:
                    self.replica_nodes.append(node.node_id)
                elif node.role == DatabaseRole.ANALYTICS:
                    self.analytics_nodes.append(node.node_id)
            
            logger.info(f"Added database node {node.node_id} ({node.role.value})")
            
        except Exception as e:
            logger.error(f"Failed to add database node {node.node_id}: {e}")
            raise
    
    async def remove_database_node(self, node_id: str):
        """Remove a database node from the pool"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                
                # Close the pool
                if node.pool:
                    await node.pool.close()
                
                # Remove from categorized lists
                if node_id in self.primary_nodes:
                    self.primary_nodes.remove(node_id)
                if node_id in self.replica_nodes:
                    self.replica_nodes.remove(node_id)
                if node_id in self.analytics_nodes:
                    self.analytics_nodes.remove(node_id)
                
                del self.nodes[node_id]
                logger.info(f"Removed database node {node_id}")
    
    def _select_node(self, role: DatabaseRole = None, read_only: bool = False) -> Optional[DatabaseNode]:
        """Select the best database node based on strategy"""
        with self.lock:
            # Determine candidate nodes
            if role == DatabaseRole.PRIMARY:
                candidate_ids = self.primary_nodes
            elif role == DatabaseRole.REPLICA or read_only:
                candidate_ids = self.replica_nodes if self.replica_nodes else self.primary_nodes
            elif role == DatabaseRole.ANALYTICS:
                candidate_ids = self.analytics_nodes if self.analytics_nodes else self.replica_nodes
            else:
                # Default: prefer replicas for reads, primary for writes
                if read_only and self.replica_nodes:
                    candidate_ids = self.replica_nodes
                else:
                    candidate_ids = self.primary_nodes
            
            # Filter healthy nodes
            healthy_nodes = [
                self.nodes[node_id] for node_id in candidate_ids
                if node_id in self.nodes and self.nodes[node_id].is_healthy
            ]
            
            if not healthy_nodes:
                logger.warning(f"No healthy nodes available for role {role}")
                return None
            
            # Apply selection strategy
            if self.strategy == PoolStrategy.ROUND_ROBIN:
                node = healthy_nodes[self.round_robin_index % len(healthy_nodes)]
                self.round_robin_index += 1
                return node
            
            elif self.strategy == PoolStrategy.LEAST_CONNECTIONS:
                return min(healthy_nodes, key=lambda n: n.current_connections)
            
            elif self.strategy == PoolStrategy.RANDOM:
                return random.choice(healthy_nodes)
            
            elif self.strategy == PoolStrategy.WEIGHTED:
                # Weighted random selection
                total_weight = sum(n.weight for n in healthy_nodes)
                if total_weight == 0:
                    return random.choice(healthy_nodes)
                
                r = random.uniform(0, total_weight)
                cumulative_weight = 0
                for node in healthy_nodes:
                    cumulative_weight += node.weight
                    if r <= cumulative_weight:
                        return node
                
                return healthy_nodes[-1]  # Fallback
            
            else:
                return random.choice(healthy_nodes)
    
    @asynccontextmanager
    async def get_connection(self, read_only: bool = False, 
                           role: DatabaseRole = None) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a database connection from the pool"""
        node = self._select_node(role, read_only)
        
        if not node or not node.pool:
            raise Exception("No available database connections")
        
        start_time = time.time()
        
        # Update connection count
        with self.lock:
            node.current_connections += 1
            self.pool_metrics["active_connections"] += 1
        
        try:
            async with node.pool.acquire() as connection:
                yield connection
                
                # Update success metrics
                response_time = time.time() - start_time
                with self.lock:
                    node.total_queries += 1
                    node.avg_response_time = (
                        (node.avg_response_time * (node.total_queries - 1) + response_time) /
                        node.total_queries
                    )
                    self.pool_metrics["successful_queries"] += 1
                    self.pool_metrics["total_queries"] += 1
                    self._update_avg_response_time(response_time)
        
        except Exception as e:
            # Update failure metrics
            with self.lock:
                node.failed_queries += 1
                self.pool_metrics["failed_queries"] += 1
                self.pool_metrics["total_queries"] += 1
            
            logger.error(f"Database query failed on node {node.node_id}: {e}")
            raise
        
        finally:
            # Decrease connection count
            with self.lock:
                node.current_connections = max(0, node.current_connections - 1)
                self.pool_metrics["active_connections"] = max(0, self.pool_metrics["active_connections"] - 1)
    
    async def execute_query(self, query: str, *args, read_only: bool = False, 
                          role: DatabaseRole = None) -> List[Dict[str, Any]]:
        """Execute a query using connection pooling"""
        async with self.get_connection(read_only, role) as conn:
            result = await conn.fetch(query, *args)
            return [dict(row) for row in result]
    
    async def execute_command(self, command: str, *args, role: DatabaseRole = None) -> str:
        """Execute a command (INSERT, UPDATE, DELETE)"""
        async with self.get_connection(read_only=False, role=role) as conn:
            return await conn.execute(command, *args)
    
    def _update_avg_response_time(self, response_time: float):
        """Update average response time metric"""
        total_queries = self.pool_metrics["total_queries"]
        if total_queries > 0:
            self.pool_metrics["avg_response_time"] = (
                (self.pool_metrics["avg_response_time"] * (total_queries - 1) + response_time) /
                total_queries
            )
    
    async def health_check_node(self, node: DatabaseNode) -> bool:
        """Perform health check on a database node"""
        try:
            if not node.pool:
                return False
            
            async with node.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                
            node.is_healthy = True
            node.last_health_check = datetime.utcnow()
            return True
            
        except Exception as e:
            logger.warning(f"Health check failed for node {node.node_id}: {e}")
            node.is_healthy = False
            return False
    
    async def perform_health_checks(self):
        """Perform health checks on all nodes"""
        for node in self.nodes.values():
            await self.health_check_node(node)
    
    def start_health_monitoring(self):
        """Start health monitoring for database nodes"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.stop_event.clear()
        
        def monitor_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            while not self.stop_event.wait(self.health_check_interval):
                try:
                    loop.run_until_complete(self.perform_health_checks())
                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")
            
            loop.close()
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Database pool health monitoring started")
    
    def stop_health_monitoring(self):
        """Stop health monitoring"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        self.stop_event.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        logger.info("Database pool health monitoring stopped")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get comprehensive pool statistics"""
        with self.lock:
            node_stats = {}
            for node_id, node in self.nodes.items():
                node_stats[node_id] = {
                    "host": node.host,
                    "port": node.port,
                    "role": node.role.value,
                    "is_healthy": node.is_healthy,
                    "current_connections": node.current_connections,
                    "max_connections": node.max_connections,
                    "total_queries": node.total_queries,
                    "success_rate": node.success_rate,
                    "avg_response_time": node.avg_response_time,
                    "load_factor": node.load_factor,
                    "last_health_check": node.last_health_check.isoformat()
                }
            
            return {
                "strategy": self.strategy.value,
                "total_nodes": len(self.nodes),
                "healthy_nodes": len([n for n in self.nodes.values() if n.is_healthy]),
                "primary_nodes": len(self.primary_nodes),
                "replica_nodes": len(self.replica_nodes),
                "analytics_nodes": len(self.analytics_nodes),
                "pool_metrics": self.pool_metrics,
                "nodes": node_stats
            }
    
    async def close_all_pools(self):
        """Close all database connection pools"""
        for node in self.nodes.values():
            if node.pool:
                await node.pool.close()
        
        self.stop_health_monitoring()
        logger.info("All database pools closed")

# Global distributed pool instance
distributed_pool = DistributedConnectionPool()

async def initialize_distributed_database_pool(primary_url: str, replica_urls: List[str] = None, 
                                              analytics_urls: List[str] = None):
    """Initialize distributed database connection pool"""
    if not ASYNCPG_AVAILABLE:
        logger.warning("asyncpg not available, using basic connection pooling")
        return
    
    # Parse URLs and create nodes
    def parse_url(url: str) -> Dict[str, str]:
        # Simple URL parsing for postgresql://user:pass@host:port/db
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        return {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "database": parsed.path.lstrip('/'),
            "username": parsed.username,
            "password": parsed.password
        }
    
    # Add primary node
    primary_config = parse_url(primary_url)
    primary_node = DatabaseNode(
        node_id="primary_1",
        role=DatabaseRole.PRIMARY,
        max_connections=30,
        **primary_config
    )
    await distributed_pool.add_database_node(primary_node)
    
    # Add replica nodes
    if replica_urls:
        for i, replica_url in enumerate(replica_urls):
            replica_config = parse_url(replica_url)
            replica_node = DatabaseNode(
                node_id=f"replica_{i+1}",
                role=DatabaseRole.REPLICA,
                max_connections=20,
                **replica_config
            )
            await distributed_pool.add_database_node(replica_node)
    
    # Add analytics nodes
    if analytics_urls:
        for i, analytics_url in enumerate(analytics_urls):
            analytics_config = parse_url(analytics_url)
            analytics_node = DatabaseNode(
                node_id=f"analytics_{i+1}",
                role=DatabaseRole.ANALYTICS,
                max_connections=15,
                **analytics_config
            )
            await distributed_pool.add_database_node(analytics_node)
    
    # Start health monitoring
    distributed_pool.start_health_monitoring()
    
    logger.info("Distributed database pool initialized")

# Convenience functions
async def get_db_connection(read_only: bool = False):
    """Get database connection from distributed pool"""
    return distributed_pool.get_connection(read_only=read_only)

async def execute_read_query(query: str, *args):
    """Execute read-only query on replica if available"""
    return await distributed_pool.execute_query(query, *args, read_only=True)

async def execute_write_query(command: str, *args):
    """Execute write query on primary"""
    return await distributed_pool.execute_command(command, *args)

def get_database_pool_stats():
    """Get database pool statistics"""
    return distributed_pool.get_pool_stats()
