"""
Database performance optimization module.
Implements connection pooling, query optimization, and database monitoring.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime, timedelta
import psycopg2.pool
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool
import asyncpg

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration for production optimization"""
    
    # Connection pool settings
    POOL_SIZE = 20
    MAX_OVERFLOW = 30
    POOL_TIMEOUT = 30
    POOL_RECYCLE = 3600  # 1 hour
    POOL_PRE_PING = True
    
    # Query optimization settings
    QUERY_TIMEOUT = 30
    SLOW_QUERY_THRESHOLD = 1.0  # seconds
    ENABLE_QUERY_LOGGING = True
    
    # Connection settings
    CONNECT_TIMEOUT = 10
    COMMAND_TIMEOUT = 30
    
    # Async pool settings
    ASYNC_POOL_MIN_SIZE = 10
    ASYNC_POOL_MAX_SIZE = 20

class DatabasePerformanceMonitor:
    """Monitor database performance and query metrics"""
    
    def __init__(self):
        self.query_stats = {
            "total_queries": 0,
            "slow_queries": 0,
            "failed_queries": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "max_time": 0.0,
            "slow_query_log": []
        }
        self.connection_stats = {
            "active_connections": 0,
            "total_connections": 0,
            "failed_connections": 0,
            "pool_size": 0,
            "pool_checked_out": 0
        }
    
    def record_query(self, query: str, duration: float, success: bool = True):
        """Record query execution metrics"""
        self.query_stats["total_queries"] += 1
        
        if success:
            self.query_stats["total_time"] += duration
            self.query_stats["avg_time"] = (
                self.query_stats["total_time"] / self.query_stats["total_queries"]
            )
            self.query_stats["max_time"] = max(self.query_stats["max_time"], duration)
            
            if duration > DatabaseConfig.SLOW_QUERY_THRESHOLD:
                self.query_stats["slow_queries"] += 1
                self.query_stats["slow_query_log"].append({
                    "query": query[:200] + "..." if len(query) > 200 else query,
                    "duration": duration,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Keep only last 100 slow queries
                if len(self.query_stats["slow_query_log"]) > 100:
                    self.query_stats["slow_query_log"] = self.query_stats["slow_query_log"][-100:]
        else:
            self.query_stats["failed_queries"] += 1
    
    def record_connection(self, success: bool = True):
        """Record connection metrics"""
        self.connection_stats["total_connections"] += 1
        if success:
            self.connection_stats["active_connections"] += 1
        else:
            self.connection_stats["failed_connections"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        return {
            "query_stats": self.query_stats.copy(),
            "connection_stats": self.connection_stats.copy(),
            "performance_summary": {
                "queries_per_second": self.query_stats["total_queries"] / max(self.query_stats["total_time"], 1),
                "slow_query_percentage": (
                    self.query_stats["slow_queries"] / max(self.query_stats["total_queries"], 1) * 100
                ),
                "error_rate": (
                    self.query_stats["failed_queries"] / max(self.query_stats["total_queries"], 1) * 100
                )
            }
        }

# Global performance monitor
db_monitor = DatabasePerformanceMonitor()

class OptimizedDatabaseManager:
    """Optimized database manager with connection pooling and monitoring"""
    
    def __init__(self, database_url: str, config: DatabaseConfig = None):
        self.database_url = database_url
        self.config = config or DatabaseConfig()
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[sessionmaker] = None
        self.async_pool: Optional[asyncpg.Pool] = None
        
    def initialize_sync_engine(self):
        """Initialize synchronous SQLAlchemy engine with optimizations"""
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=self.config.POOL_SIZE,
            max_overflow=self.config.MAX_OVERFLOW,
            pool_timeout=self.config.POOL_TIMEOUT,
            pool_recycle=self.config.POOL_RECYCLE,
            pool_pre_ping=self.config.POOL_PRE_PING,
            echo=self.config.ENABLE_QUERY_LOGGING,
            connect_args={
                "connect_timeout": self.config.CONNECT_TIMEOUT,
                "command_timeout": self.config.COMMAND_TIMEOUT,
            }
        )
        
        # Add event listeners for monitoring
        self._setup_event_listeners()
        
        self.session_factory = sessionmaker(bind=self.engine)
        logger.info("Optimized sync database engine initialized")
    
    async def initialize_async_pool(self):
        """Initialize async connection pool"""
        try:
            self.async_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.config.ASYNC_POOL_MIN_SIZE,
                max_size=self.config.ASYNC_POOL_MAX_SIZE,
                command_timeout=self.config.COMMAND_TIMEOUT,
                server_settings={
                    'application_name': 'ensimu_space_backend',
                    'jit': 'off'  # Disable JIT for consistent performance
                }
            )
            logger.info("Async database pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize async pool: {e}")
            raise
    
    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for monitoring"""
        
        @event.listens_for(self.engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
        
        @event.listens_for(self.engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = time.time() - context._query_start_time
            db_monitor.record_query(statement, total_time, success=True)
        
        @event.listens_for(self.engine, "handle_error")
        def handle_error(exception_context):
            if hasattr(exception_context, '_query_start_time'):
                total_time = time.time() - exception_context._query_start_time
                db_monitor.record_query(
                    str(exception_context.statement), 
                    total_time, 
                    success=False
                )
        
        @event.listens_for(self.engine, "connect")
        def connect(dbapi_connection, connection_record):
            db_monitor.record_connection(success=True)
        
        @event.listens_for(self.engine, "checkout")
        def checkout(dbapi_connection, connection_record, connection_proxy):
            db_monitor.connection_stats["pool_checked_out"] += 1
        
        @event.listens_for(self.engine, "checkin")
        def checkin(dbapi_connection, connection_record):
            db_monitor.connection_stats["pool_checked_out"] -= 1
    
    @contextmanager
    def get_session(self):
        """Get optimized database session with automatic cleanup"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize_sync_engine() first.")
        
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get async database connection from pool"""
        if not self.async_pool:
            raise RuntimeError("Async pool not initialized. Call initialize_async_pool() first.")
        
        async with self.async_pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                logger.error(f"Async connection error: {e}")
                raise
    
    async def execute_async_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute async query with performance monitoring"""
        start_time = time.time()
        
        try:
            async with self.get_async_connection() as conn:
                result = await conn.fetch(query, *args)
                
                # Convert to list of dicts
                rows = [dict(row) for row in result]
                
                duration = time.time() - start_time
                db_monitor.record_query(query, duration, success=True)
                
                return rows
        except Exception as e:
            duration = time.time() - start_time
            db_monitor.record_query(query, duration, success=False)
            logger.error(f"Async query failed: {e}")
            raise
    
    async def execute_async_command(self, command: str, *args) -> str:
        """Execute async command (INSERT, UPDATE, DELETE)"""
        start_time = time.time()
        
        try:
            async with self.get_async_connection() as conn:
                result = await conn.execute(command, *args)
                
                duration = time.time() - start_time
                db_monitor.record_query(command, duration, success=True)
                
                return result
        except Exception as e:
            duration = time.time() - start_time
            db_monitor.record_query(command, duration, success=False)
            logger.error(f"Async command failed: {e}")
            raise
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status"""
        if self.engine:
            pool = self.engine.pool
            return {
                "pool_size": pool.size(),
                "checked_out_connections": pool.checkedout(),
                "overflow_connections": pool.overflow(),
                "checked_in_connections": pool.checkedin()
            }
        return {}
    
    async def close(self):
        """Close all connections and cleanup"""
        if self.async_pool:
            await self.async_pool.close()
        
        if self.engine:
            self.engine.dispose()
        
        logger.info("Database connections closed")

class QueryOptimizer:
    """Query optimization utilities"""
    
    @staticmethod
    def optimize_workflow_queries():
        """Optimized queries for workflow operations"""
        return {
            "get_active_workflows": """
                SELECT w.*, p.name as project_name
                FROM workflow_executions w
                JOIN projects p ON w.project_id = p.id
                WHERE w.status IN ('running', 'paused')
                ORDER BY w.updated_at DESC
                LIMIT $1
            """,
            
            "get_workflow_with_steps": """
                SELECT 
                    w.*,
                    json_agg(
                        json_build_object(
                            'id', ws.id,
                            'step_name', ws.step_name,
                            'status', ws.status,
                            'duration_seconds', ws.duration_seconds
                        ) ORDER BY ws.step_order
                    ) as steps
                FROM workflow_executions w
                LEFT JOIN workflow_steps ws ON w.id = ws.workflow_id
                WHERE w.id = $1
                GROUP BY w.id
            """,
            
            "get_project_files": """
                SELECT id, filename, file_type, file_format, upload_status, file_size_bytes
                FROM uploaded_files
                WHERE project_id = $1 AND upload_status = 'completed'
                ORDER BY created_at DESC
            """,
            
            "get_pending_checkpoints": """
                SELECT hc.*, w.project_id
                FROM hitl_checkpoints hc
                JOIN workflow_executions w ON hc.workflow_id = w.id
                WHERE hc.status = 'pending' 
                AND (hc.timeout_at IS NULL OR hc.timeout_at > NOW())
                ORDER BY hc.created_at ASC
            """,
            
            "update_workflow_progress": """
                UPDATE workflow_executions 
                SET 
                    current_step = $2,
                    global_context = $3,
                    updated_at = NOW()
                WHERE id = $1
                RETURNING updated_at
            """
        }
    
    @staticmethod
    def create_performance_indexes():
        """SQL commands to create performance indexes"""
        return [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workflow_status_updated ON workflow_executions(status, updated_at);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workflow_project_status ON workflow_executions(project_id, status);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_workflow_steps_workflow_order ON workflow_steps(workflow_id, step_order);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hitl_checkpoints_status_timeout ON hitl_checkpoints(status, timeout_at);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_uploaded_files_project_status ON uploaded_files(project_id, upload_status);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_metrics_type_timestamp ON agent_metrics(agent_type, created_at);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orchestrator_metrics_workflow ON orchestrator_metrics(workflow_id);"
        ]

# Global database manager instance
db_manager = OptimizedDatabaseManager("")

async def initialize_database_optimizations(database_url: str):
    """Initialize all database optimizations"""
    global db_manager
    
    db_manager = OptimizedDatabaseManager(database_url)
    
    # Initialize sync engine
    db_manager.initialize_sync_engine()
    
    # Initialize async pool
    await db_manager.initialize_async_pool()
    
    # Create performance indexes
    try:
        indexes = QueryOptimizer.create_performance_indexes()
        for index_sql in indexes:
            await db_manager.execute_async_command(index_sql)
        logger.info("Performance indexes created successfully")
    except Exception as e:
        logger.warning(f"Some indexes may already exist: {e}")
    
    logger.info("Database optimizations initialized")

def get_optimized_session():
    """Get optimized database session"""
    return db_manager.get_session()

async def get_async_connection():
    """Get async database connection"""
    return db_manager.get_async_connection()

def get_database_stats():
    """Get comprehensive database statistics"""
    return {
        "performance_monitor": db_monitor.get_stats(),
        "pool_status": db_manager.get_pool_status(),
        "config": {
            "pool_size": DatabaseConfig.POOL_SIZE,
            "max_overflow": DatabaseConfig.MAX_OVERFLOW,
            "slow_query_threshold": DatabaseConfig.SLOW_QUERY_THRESHOLD
        }
    }
