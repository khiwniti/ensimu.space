"""
Comprehensive monitoring and metrics collection for the simulation preprocessing platform.
Implements Prometheus metrics, custom metrics, and observability features.
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
import threading
from enum import Enum

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary, Info,
        CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Mock classes for when Prometheus is not available
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
    
    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def time(self): return contextmanager(lambda: iter([None]))()
    
    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def dec(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    SUMMARY = "summary"

@dataclass
class MetricEvent:
    """Represents a metric event"""
    name: str
    value: Union[int, float]
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metric_type: MetricType = MetricType.COUNTER

class MetricsCollector:
    """Advanced metrics collection and aggregation"""
    
    def __init__(self, enable_prometheus: bool = True):
        self.enable_prometheus = enable_prometheus and PROMETHEUS_AVAILABLE
        self.registry = CollectorRegistry() if self.enable_prometheus else None
        
        # Internal metrics storage
        self.metrics_history: deque = deque(maxlen=10000)
        self.aggregated_metrics: Dict[str, Any] = defaultdict(dict)
        self.metric_definitions: Dict[str, Dict[str, Any]] = {}
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Initialize core metrics
        self._initialize_core_metrics()
    
    def _initialize_core_metrics(self):
        """Initialize core platform metrics"""
        
        # Workflow metrics
        self.register_metric(
            "workflow_executions_total",
            MetricType.COUNTER,
            "Total number of workflow executions",
            ["project_id", "physics_type", "status"]
        )
        
        self.register_metric(
            "workflow_duration_seconds",
            MetricType.HISTOGRAM,
            "Workflow execution duration in seconds",
            ["project_id", "physics_type", "status"],
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600]
        )
        
        self.register_metric(
            "active_workflows",
            MetricType.GAUGE,
            "Number of currently active workflows",
            ["status"]
        )
        
        # Agent metrics
        self.register_metric(
            "agent_requests_total",
            MetricType.COUNTER,
            "Total number of agent requests",
            ["agent_type", "status"]
        )
        
        self.register_metric(
            "agent_response_time_seconds",
            MetricType.HISTOGRAM,
            "Agent response time in seconds",
            ["agent_type"],
            buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60]
        )
        
        self.register_metric(
            "agent_confidence_score",
            MetricType.HISTOGRAM,
            "Agent confidence scores",
            ["agent_type"],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )
        
        # HITL metrics
        self.register_metric(
            "hitl_checkpoints_total",
            MetricType.COUNTER,
            "Total number of HITL checkpoints",
            ["checkpoint_type", "status"]
        )
        
        self.register_metric(
            "hitl_response_time_seconds",
            MetricType.HISTOGRAM,
            "HITL checkpoint response time in seconds",
            ["checkpoint_type"],
            buckets=[60, 300, 900, 1800, 3600, 7200, 86400]
        )
        
        # System metrics
        self.register_metric(
            "memory_usage_bytes",
            MetricType.GAUGE,
            "Memory usage in bytes",
            ["component"]
        )
        
        self.register_metric(
            "database_connections",
            MetricType.GAUGE,
            "Number of database connections",
            ["pool", "status"]
        )
        
        self.register_metric(
            "cache_operations_total",
            MetricType.COUNTER,
            "Total cache operations",
            ["operation", "result"]
        )
        
        logger.info(f"Initialized {len(self.metric_definitions)} core metrics")
    
    def register_metric(self, name: str, metric_type: MetricType, description: str, 
                       labels: List[str] = None, **kwargs):
        """Register a new metric"""
        labels = labels or []
        
        with self.lock:
            self.metric_definitions[name] = {
                "type": metric_type,
                "description": description,
                "labels": labels,
                "kwargs": kwargs
            }
            
            if self.enable_prometheus:
                self._create_prometheus_metric(name, metric_type, description, labels, **kwargs)
    
    def _create_prometheus_metric(self, name: str, metric_type: MetricType, 
                                description: str, labels: List[str], **kwargs):
        """Create Prometheus metric"""
        try:
            if metric_type == MetricType.COUNTER:
                metric = Counter(name, description, labels, registry=self.registry)
            elif metric_type == MetricType.HISTOGRAM:
                buckets = kwargs.get('buckets')
                metric = Histogram(name, description, labels, registry=self.registry, buckets=buckets)
            elif metric_type == MetricType.GAUGE:
                metric = Gauge(name, description, labels, registry=self.registry)
            elif metric_type == MetricType.SUMMARY:
                metric = Summary(name, description, labels, registry=self.registry)
            else:
                logger.error(f"Unknown metric type: {metric_type}")
                return
            
            # Store reference to the metric
            setattr(self, f"_prometheus_{name}", metric)
            
        except Exception as e:
            logger.error(f"Failed to create Prometheus metric {name}: {e}")
    
    def record_metric(self, name: str, value: Union[int, float], labels: Dict[str, str] = None):
        """Record a metric value"""
        labels = labels or {}
        
        # Create metric event
        event = MetricEvent(
            name=name,
            value=value,
            labels=labels,
            metric_type=self.metric_definitions.get(name, {}).get("type", MetricType.COUNTER)
        )
        
        with self.lock:
            # Store in history
            self.metrics_history.append(event)
            
            # Update aggregated metrics
            self._update_aggregated_metrics(event)
            
            # Update Prometheus metrics
            if self.enable_prometheus:
                self._update_prometheus_metric(event)
    
    def _update_aggregated_metrics(self, event: MetricEvent):
        """Update internal aggregated metrics"""
        key = f"{event.name}:{':'.join(f'{k}={v}' for k, v in sorted(event.labels.items()))}"
        
        if key not in self.aggregated_metrics:
            self.aggregated_metrics[key] = {
                "name": event.name,
                "labels": event.labels,
                "count": 0,
                "sum": 0.0,
                "min": float('inf'),
                "max": float('-inf'),
                "last_value": 0.0,
                "last_updated": event.timestamp
            }
        
        metric = self.aggregated_metrics[key]
        metric["count"] += 1
        metric["sum"] += event.value
        metric["min"] = min(metric["min"], event.value)
        metric["max"] = max(metric["max"], event.value)
        metric["last_value"] = event.value
        metric["last_updated"] = event.timestamp
    
    def _update_prometheus_metric(self, event: MetricEvent):
        """Update Prometheus metric"""
        try:
            prometheus_metric = getattr(self, f"_prometheus_{event.name}", None)
            if not prometheus_metric:
                return
            
            metric_type = self.metric_definitions[event.name]["type"]
            
            if event.labels:
                labeled_metric = prometheus_metric.labels(**event.labels)
            else:
                labeled_metric = prometheus_metric
            
            if metric_type == MetricType.COUNTER:
                labeled_metric.inc(event.value)
            elif metric_type == MetricType.HISTOGRAM:
                labeled_metric.observe(event.value)
            elif metric_type == MetricType.GAUGE:
                labeled_metric.set(event.value)
            elif metric_type == MetricType.SUMMARY:
                labeled_metric.observe(event.value)
                
        except Exception as e:
            logger.error(f"Failed to update Prometheus metric {event.name}: {e}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        with self.lock:
            summary = {
                "total_events": len(self.metrics_history),
                "unique_metrics": len(self.aggregated_metrics),
                "prometheus_enabled": self.enable_prometheus,
                "metrics": {}
            }
            
            for key, metric in self.aggregated_metrics.items():
                summary["metrics"][key] = {
                    "count": metric["count"],
                    "sum": metric["sum"],
                    "avg": metric["sum"] / metric["count"] if metric["count"] > 0 else 0,
                    "min": metric["min"] if metric["min"] != float('inf') else 0,
                    "max": metric["max"] if metric["max"] != float('-inf') else 0,
                    "last_value": metric["last_value"],
                    "last_updated": metric["last_updated"].isoformat()
                }
            
            return summary
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        if not self.enable_prometheus:
            return "# Prometheus not enabled\n"
        
        try:
            return generate_latest(self.registry).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to generate Prometheus metrics: {e}")
            return f"# Error generating metrics: {e}\n"
    
    def get_metric_history(self, name: str, minutes: int = 60) -> List[MetricEvent]:
        """Get metric history for specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        with self.lock:
            return [
                event for event in self.metrics_history
                if event.name == name and event.timestamp >= cutoff_time
            ]

# Decorators for automatic metric collection
def track_execution_time(metric_name: str, labels: Dict[str, str] = None):
    """Decorator to track function execution time"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                metrics_collector.record_metric(metric_name, duration, labels)
                return result
            except Exception as e:
                duration = time.time() - start_time
                error_labels = (labels or {}).copy()
                error_labels["status"] = "error"
                metrics_collector.record_metric(metric_name, duration, error_labels)
                raise
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metrics_collector.record_metric(metric_name, duration, labels)
                return result
            except Exception as e:
                duration = time.time() - start_time
                error_labels = (labels or {}).copy()
                error_labels["status"] = "error"
                metrics_collector.record_metric(metric_name, duration, error_labels)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def count_calls(metric_name: str, labels: Dict[str, str] = None):
    """Decorator to count function calls"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                success_labels = (labels or {}).copy()
                success_labels["status"] = "success"
                metrics_collector.record_metric(metric_name, 1, success_labels)
                return result
            except Exception as e:
                error_labels = (labels or {}).copy()
                error_labels["status"] = "error"
                metrics_collector.record_metric(metric_name, 1, error_labels)
                raise
        
        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                success_labels = (labels or {}).copy()
                success_labels["status"] = "success"
                metrics_collector.record_metric(metric_name, 1, success_labels)
                return result
            except Exception as e:
                error_labels = (labels or {}).copy()
                error_labels["status"] = "error"
                metrics_collector.record_metric(metric_name, 1, error_labels)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Global metrics collector instance
metrics_collector = MetricsCollector()

# Convenience functions
def record_workflow_start(project_id: str, physics_type: str):
    """Record workflow start"""
    metrics_collector.record_metric(
        "workflow_executions_total",
        1,
        {"project_id": project_id, "physics_type": physics_type, "status": "started"}
    )

def record_workflow_completion(project_id: str, physics_type: str, duration: float, success: bool):
    """Record workflow completion"""
    status = "success" if success else "failed"
    
    metrics_collector.record_metric(
        "workflow_executions_total",
        1,
        {"project_id": project_id, "physics_type": physics_type, "status": status}
    )
    
    metrics_collector.record_metric(
        "workflow_duration_seconds",
        duration,
        {"project_id": project_id, "physics_type": physics_type, "status": status}
    )

def record_agent_request(agent_type: str, response_time: float, confidence: float, success: bool):
    """Record agent request metrics"""
    status = "success" if success else "failed"
    
    metrics_collector.record_metric(
        "agent_requests_total",
        1,
        {"agent_type": agent_type, "status": status}
    )
    
    if success:
        metrics_collector.record_metric(
            "agent_response_time_seconds",
            response_time,
            {"agent_type": agent_type}
        )
        
        metrics_collector.record_metric(
            "agent_confidence_score",
            confidence,
            {"agent_type": agent_type}
        )

def record_hitl_checkpoint(checkpoint_type: str, response_time: Optional[float] = None):
    """Record HITL checkpoint metrics"""
    metrics_collector.record_metric(
        "hitl_checkpoints_total",
        1,
        {"checkpoint_type": checkpoint_type, "status": "created"}
    )
    
    if response_time is not None:
        metrics_collector.record_metric(
            "hitl_response_time_seconds",
            response_time,
            {"checkpoint_type": checkpoint_type}
        )

def update_system_metrics(memory_usage: float, db_connections: int, cache_hit_rate: float):
    """Update system-level metrics"""
    metrics_collector.record_metric(
        "memory_usage_bytes",
        memory_usage,
        {"component": "backend"}
    )
    
    metrics_collector.record_metric(
        "database_connections",
        db_connections,
        {"pool": "main", "status": "active"}
    )
    
    metrics_collector.record_metric(
        "cache_operations_total",
        1,
        {"operation": "hit", "result": "success"} if cache_hit_rate > 0.5 else {"operation": "miss", "result": "cache_miss"}
    )
