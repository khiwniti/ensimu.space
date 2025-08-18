"""
Memory management and resource optimization for AI agents and workflows.
Implements memory monitoring, garbage collection optimization, and resource limits.
"""

import asyncio
import gc
import logging
import psutil
import resource
import threading
import time
import weakref
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import tracemalloc

logger = logging.getLogger(__name__)

@dataclass
class MemoryStats:
    """Memory statistics snapshot"""
    total_memory_mb: float
    available_memory_mb: float
    used_memory_mb: float
    memory_percent: float
    process_memory_mb: float
    process_memory_percent: float
    gc_collections: Dict[int, int]
    tracemalloc_current_mb: Optional[float] = None
    tracemalloc_peak_mb: Optional[float] = None

class MemoryMonitor:
    """Advanced memory monitoring and management"""
    
    def __init__(self, enable_tracemalloc: bool = True):
        self.enable_tracemalloc = enable_tracemalloc
        self.process = psutil.Process()
        self.memory_history: List[MemoryStats] = []
        self.max_history_size = 1000
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Memory thresholds
        self.warning_threshold_percent = 80.0
        self.critical_threshold_percent = 90.0
        self.gc_threshold_mb = 500.0  # Trigger GC when process uses > 500MB
        
        # Callbacks for memory events
        self.warning_callbacks: List[Callable] = []
        self.critical_callbacks: List[Callable] = []
        
        if self.enable_tracemalloc:
            tracemalloc.start()
    
    def get_current_stats(self) -> MemoryStats:
        """Get current memory statistics"""
        # System memory
        memory = psutil.virtual_memory()
        
        # Process memory
        process_memory = self.process.memory_info()
        process_memory_mb = process_memory.rss / 1024 / 1024
        process_memory_percent = self.process.memory_percent()
        
        # Garbage collection stats
        gc_stats = {i: gc.get_count()[i] for i in range(3)}
        
        # Tracemalloc stats
        tracemalloc_current_mb = None
        tracemalloc_peak_mb = None
        
        if self.enable_tracemalloc and tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc_current_mb = current / 1024 / 1024
            tracemalloc_peak_mb = peak / 1024 / 1024
        
        return MemoryStats(
            total_memory_mb=memory.total / 1024 / 1024,
            available_memory_mb=memory.available / 1024 / 1024,
            used_memory_mb=memory.used / 1024 / 1024,
            memory_percent=memory.percent,
            process_memory_mb=process_memory_mb,
            process_memory_percent=process_memory_percent,
            gc_collections=gc_stats,
            tracemalloc_current_mb=tracemalloc_current_mb,
            tracemalloc_peak_mb=tracemalloc_peak_mb
        )
    
    def start_monitoring(self, interval_seconds: float = 30.0):
        """Start continuous memory monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.stop_event.clear()
        
        def monitor_loop():
            while not self.stop_event.wait(interval_seconds):
                try:
                    stats = self.get_current_stats()
                    self._record_stats(stats)
                    self._check_thresholds(stats)
                    self._auto_gc_if_needed(stats)
                except Exception as e:
                    logger.error(f"Memory monitoring error: {e}")
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Memory monitoring started")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        self.stop_event.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        logger.info("Memory monitoring stopped")
    
    def _record_stats(self, stats: MemoryStats):
        """Record memory statistics"""
        self.memory_history.append(stats)
        
        # Limit history size
        if len(self.memory_history) > self.max_history_size:
            self.memory_history = self.memory_history[-self.max_history_size:]
    
    def _check_thresholds(self, stats: MemoryStats):
        """Check memory thresholds and trigger callbacks"""
        if stats.process_memory_percent >= self.critical_threshold_percent:
            logger.critical(f"Critical memory usage: {stats.process_memory_percent:.1f}%")
            for callback in self.critical_callbacks:
                try:
                    callback(stats)
                except Exception as e:
                    logger.error(f"Critical memory callback error: {e}")
        
        elif stats.process_memory_percent >= self.warning_threshold_percent:
            logger.warning(f"High memory usage: {stats.process_memory_percent:.1f}%")
            for callback in self.warning_callbacks:
                try:
                    callback(stats)
                except Exception as e:
                    logger.error(f"Warning memory callback error: {e}")
    
    def _auto_gc_if_needed(self, stats: MemoryStats):
        """Automatically trigger garbage collection if needed"""
        if stats.process_memory_mb > self.gc_threshold_mb:
            logger.info(f"Triggering GC: process memory {stats.process_memory_mb:.1f}MB")
            self.force_garbage_collection()
    
    def force_garbage_collection(self) -> Dict[str, int]:
        """Force garbage collection and return collection counts"""
        before_stats = self.get_current_stats()
        
        # Force collection for all generations
        collected = {}
        for generation in range(3):
            collected[generation] = gc.collect(generation)
        
        after_stats = self.get_current_stats()
        memory_freed = before_stats.process_memory_mb - after_stats.process_memory_mb
        
        logger.info(f"GC freed {memory_freed:.1f}MB, collected: {collected}")
        return collected
    
    def add_warning_callback(self, callback: Callable[[MemoryStats], None]):
        """Add callback for memory warning threshold"""
        self.warning_callbacks.append(callback)
    
    def add_critical_callback(self, callback: Callable[[MemoryStats], None]):
        """Add callback for memory critical threshold"""
        self.critical_callbacks.append(callback)
    
    def get_memory_trend(self, minutes: int = 30) -> Dict[str, Any]:
        """Get memory usage trend over specified time period"""
        if not self.memory_history:
            return {"trend": "no_data"}
        
        # Get recent history
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_stats = self.memory_history[-min(len(self.memory_history), minutes * 2):]  # Approximate
        
        if len(recent_stats) < 2:
            return {"trend": "insufficient_data"}
        
        # Calculate trend
        start_memory = recent_stats[0].process_memory_mb
        end_memory = recent_stats[-1].process_memory_mb
        memory_change = end_memory - start_memory
        
        # Calculate average memory usage
        avg_memory = sum(s.process_memory_mb for s in recent_stats) / len(recent_stats)
        max_memory = max(s.process_memory_mb for s in recent_stats)
        min_memory = min(s.process_memory_mb for s in recent_stats)
        
        return {
            "trend": "increasing" if memory_change > 10 else "decreasing" if memory_change < -10 else "stable",
            "change_mb": memory_change,
            "avg_memory_mb": avg_memory,
            "max_memory_mb": max_memory,
            "min_memory_mb": min_memory,
            "samples": len(recent_stats)
        }

class ResourceLimiter:
    """Resource limiting and management"""
    
    def __init__(self):
        self.active_limits: Dict[str, Any] = {}
    
    def set_memory_limit(self, limit_mb: int):
        """Set memory limit for the process"""
        try:
            limit_bytes = limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
            self.active_limits["memory_mb"] = limit_mb
            logger.info(f"Memory limit set to {limit_mb}MB")
        except Exception as e:
            logger.error(f"Failed to set memory limit: {e}")
    
    def set_cpu_limit(self, limit_seconds: int):
        """Set CPU time limit for the process"""
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (limit_seconds, limit_seconds))
            self.active_limits["cpu_seconds"] = limit_seconds
            logger.info(f"CPU limit set to {limit_seconds} seconds")
        except Exception as e:
            logger.error(f"Failed to set CPU limit: {e}")
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage"""
        try:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return {
                "user_time": usage.ru_utime,
                "system_time": usage.ru_stime,
                "max_memory_kb": usage.ru_maxrss,
                "page_faults": usage.ru_majflt,
                "context_switches": usage.ru_nvcsw + usage.ru_nivcsw,
                "active_limits": self.active_limits
            }
        except Exception as e:
            logger.error(f"Failed to get resource usage: {e}")
            return {"error": str(e)}

class ObjectTracker:
    """Track object lifecycle and detect memory leaks"""
    
    def __init__(self):
        self.tracked_objects: Dict[str, weakref.WeakSet] = {}
        self.creation_counts: Dict[str, int] = {}
        self.deletion_counts: Dict[str, int] = {}
    
    def track_object(self, obj: Any, category: str = None):
        """Track an object for lifecycle monitoring"""
        if category is None:
            category = obj.__class__.__name__
        
        if category not in self.tracked_objects:
            self.tracked_objects[category] = weakref.WeakSet()
            self.creation_counts[category] = 0
            self.deletion_counts[category] = 0
        
        self.tracked_objects[category].add(obj)
        self.creation_counts[category] += 1
        
        # Add deletion callback
        def on_delete(ref):
            self.deletion_counts[category] += 1
        
        weakref.ref(obj, on_delete)
    
    def get_object_stats(self) -> Dict[str, Dict[str, int]]:
        """Get object tracking statistics"""
        stats = {}
        for category in self.tracked_objects:
            stats[category] = {
                "alive": len(self.tracked_objects[category]),
                "created": self.creation_counts[category],
                "deleted": self.deletion_counts[category],
                "potential_leaks": max(0, self.creation_counts[category] - self.deletion_counts[category] - len(self.tracked_objects[category]))
            }
        return stats

# Context manager for memory-limited operations
@contextmanager
def memory_limit(limit_mb: int):
    """Context manager to temporarily limit memory usage"""
    limiter = ResourceLimiter()
    original_limit = None
    
    try:
        # Get current limit
        try:
            original_limit = resource.getrlimit(resource.RLIMIT_AS)
        except:
            pass
        
        # Set new limit
        limiter.set_memory_limit(limit_mb)
        yield
    finally:
        # Restore original limit
        if original_limit:
            try:
                resource.setrlimit(resource.RLIMIT_AS, original_limit)
            except:
                pass

# Global instances
memory_monitor = MemoryMonitor()
resource_limiter = ResourceLimiter()
object_tracker = ObjectTracker()

def initialize_memory_management():
    """Initialize memory management system"""
    # Start memory monitoring
    memory_monitor.start_monitoring(interval_seconds=30.0)
    
    # Add default callbacks
    def warning_callback(stats: MemoryStats):
        logger.warning(f"Memory warning: {stats.process_memory_mb:.1f}MB ({stats.process_memory_percent:.1f}%)")
        # Trigger garbage collection
        memory_monitor.force_garbage_collection()
    
    def critical_callback(stats: MemoryStats):
        logger.critical(f"Critical memory usage: {stats.process_memory_mb:.1f}MB ({stats.process_memory_percent:.1f}%)")
        # Force aggressive garbage collection
        memory_monitor.force_garbage_collection()
        # Could also trigger workflow pausing or other emergency measures
    
    memory_monitor.add_warning_callback(warning_callback)
    memory_monitor.add_critical_callback(critical_callback)
    
    logger.info("Memory management system initialized")

def get_memory_stats() -> Dict[str, Any]:
    """Get comprehensive memory statistics"""
    current_stats = memory_monitor.get_current_stats()
    trend = memory_monitor.get_memory_trend()
    resource_usage = resource_limiter.get_resource_usage()
    object_stats = object_tracker.get_object_stats()
    
    return {
        "current": current_stats.__dict__,
        "trend": trend,
        "resource_usage": resource_usage,
        "object_tracking": object_stats,
        "monitoring_active": memory_monitor.monitoring_active
    }

def cleanup_memory_management():
    """Cleanup memory management system"""
    memory_monitor.stop_monitoring()
    if memory_monitor.enable_tracemalloc and tracemalloc.is_tracing():
        tracemalloc.stop()
    logger.info("Memory management system cleaned up")
