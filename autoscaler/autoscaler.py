#!/usr/bin/env python3
"""
Auto-scaling controller for ensimu-space Docker services.
Monitors metrics and automatically scales services based on load.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import docker
import requests
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ScalingRule:
    """Scaling rule configuration"""
    service_name: str
    min_replicas: int
    max_replicas: int
    scale_up_threshold_cpu: float
    scale_up_threshold_memory: float
    scale_down_threshold_cpu: float
    scale_down_threshold_memory: float
    scale_up_cooldown: int  # seconds
    scale_down_cooldown: int  # seconds
    last_scale_action: Optional[datetime] = None

class AutoScaler:
    """Auto-scaling controller for Docker services"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.prometheus_url = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
        
        # Default scaling configuration
        self.scaling_rules = {
            "backend": ScalingRule(
                service_name="backend",
                min_replicas=int(os.getenv("BACKEND_MIN_REPLICAS", "2")),
                max_replicas=int(os.getenv("BACKEND_MAX_REPLICAS", "10")),
                scale_up_threshold_cpu=float(os.getenv("SCALE_UP_THRESHOLD_CPU", "70")),
                scale_up_threshold_memory=float(os.getenv("SCALE_UP_THRESHOLD_MEMORY", "80")),
                scale_down_threshold_cpu=float(os.getenv("SCALE_DOWN_THRESHOLD_CPU", "30")),
                scale_down_threshold_memory=float(os.getenv("SCALE_DOWN_THRESHOLD_MEMORY", "40")),
                scale_up_cooldown=int(os.getenv("SCALE_UP_COOLDOWN", "300")),
                scale_down_cooldown=int(os.getenv("SCALE_DOWN_COOLDOWN", "600"))
            ),
            "celery-worker": ScalingRule(
                service_name="celery-worker",
                min_replicas=int(os.getenv("CELERY_MIN_REPLICAS", "2")),
                max_replicas=int(os.getenv("CELERY_MAX_REPLICAS", "8")),
                scale_up_threshold_cpu=75.0,
                scale_up_threshold_memory=85.0,
                scale_down_threshold_cpu=25.0,
                scale_down_threshold_memory=35.0,
                scale_up_cooldown=240,
                scale_down_cooldown=480
            ),
            "frontend": ScalingRule(
                service_name="frontend",
                min_replicas=int(os.getenv("FRONTEND_MIN_REPLICAS", "2")),
                max_replicas=int(os.getenv("FRONTEND_MAX_REPLICAS", "6")),
                scale_up_threshold_cpu=80.0,
                scale_up_threshold_memory=85.0,
                scale_down_threshold_cpu=20.0,
                scale_down_threshold_memory=30.0,
                scale_up_cooldown=180,
                scale_down_cooldown=360
            )
        }
        
        self.monitoring_interval = int(os.getenv("MONITORING_INTERVAL", "60"))
        self.metrics_history = {}
    
    async def get_service_metrics(self, service_name: str) -> Dict[str, float]:
        """Get service metrics from Prometheus"""
        try:
            # CPU usage query
            cpu_query = f'avg(rate(container_cpu_usage_seconds_total{{container_label_com_docker_swarm_service_name="{service_name}"}}[5m])) * 100'
            cpu_response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": cpu_query},
                timeout=10
            )
            
            # Memory usage query
            memory_query = f'avg(container_memory_usage_bytes{{container_label_com_docker_swarm_service_name="{service_name}"}}) / avg(container_spec_memory_limit_bytes{{container_label_com_docker_swarm_service_name="{service_name}"}}) * 100'
            memory_response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": memory_query},
                timeout=10
            )
            
            # Request rate query (for backend services)
            request_query = f'sum(rate(http_requests_total{{service="{service_name}"}}[5m]))'
            request_response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": request_query},
                timeout=10
            )
            
            # Queue depth query (for Celery workers)
            queue_query = f'sum(celery_queue_length{{service="{service_name}"}})'
            queue_response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": queue_query},
                timeout=10
            )
            
            metrics = {}
            
            # Parse CPU metrics
            if cpu_response.status_code == 200:
                cpu_data = cpu_response.json()
                if cpu_data["data"]["result"]:
                    metrics["cpu_usage"] = float(cpu_data["data"]["result"][0]["value"][1])
                else:
                    metrics["cpu_usage"] = 0.0
            
            # Parse memory metrics
            if memory_response.status_code == 200:
                memory_data = memory_response.json()
                if memory_data["data"]["result"]:
                    metrics["memory_usage"] = float(memory_data["data"]["result"][0]["value"][1])
                else:
                    metrics["memory_usage"] = 0.0
            
            # Parse request rate
            if request_response.status_code == 200:
                request_data = request_response.json()
                if request_data["data"]["result"]:
                    metrics["request_rate"] = float(request_data["data"]["result"][0]["value"][1])
                else:
                    metrics["request_rate"] = 0.0
            
            # Parse queue depth
            if queue_response.status_code == 200:
                queue_data = queue_response.json()
                if queue_data["data"]["result"]:
                    metrics["queue_depth"] = float(queue_data["data"]["result"][0]["value"][1])
                else:
                    metrics["queue_depth"] = 0.0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get metrics for {service_name}: {e}")
            return {"cpu_usage": 0.0, "memory_usage": 0.0, "request_rate": 0.0, "queue_depth": 0.0}
    
    def get_current_replicas(self, service_name: str) -> int:
        """Get current number of replicas for a service"""
        try:
            service = self.docker_client.services.get(service_name)
            return service.attrs["Spec"]["Mode"]["Replicated"]["Replicas"]
        except Exception as e:
            logger.error(f"Failed to get replicas for {service_name}: {e}")
            return 0
    
    def scale_service(self, service_name: str, replicas: int) -> bool:
        """Scale a service to the specified number of replicas"""
        try:
            service = self.docker_client.services.get(service_name)
            service.scale(replicas)
            logger.info(f"Scaled {service_name} to {replicas} replicas")
            return True
        except Exception as e:
            logger.error(f"Failed to scale {service_name}: {e}")
            return False
    
    def should_scale_up(self, service_name: str, metrics: Dict[str, float], rule: ScalingRule) -> bool:
        """Determine if service should be scaled up"""
        current_replicas = self.get_current_replicas(service_name)
        
        # Check if already at max replicas
        if current_replicas >= rule.max_replicas:
            return False
        
        # Check cooldown period
        if rule.last_scale_action:
            time_since_last_scale = datetime.utcnow() - rule.last_scale_action
            if time_since_last_scale.total_seconds() < rule.scale_up_cooldown:
                return False
        
        # Check CPU threshold
        cpu_exceeded = metrics.get("cpu_usage", 0) > rule.scale_up_threshold_cpu
        
        # Check memory threshold
        memory_exceeded = metrics.get("memory_usage", 0) > rule.scale_up_threshold_memory
        
        # Check queue depth for Celery workers
        queue_exceeded = False
        if "celery" in service_name:
            queue_depth = metrics.get("queue_depth", 0)
            queue_exceeded = queue_depth > (current_replicas * 10)  # 10 tasks per worker threshold
        
        # Check request rate for backend services
        request_exceeded = False
        if service_name == "backend":
            request_rate = metrics.get("request_rate", 0)
            request_exceeded = request_rate > (current_replicas * 50)  # 50 requests/sec per replica
        
        # Scale up if any threshold is exceeded
        return cpu_exceeded or memory_exceeded or queue_exceeded or request_exceeded
    
    def should_scale_down(self, service_name: str, metrics: Dict[str, float], rule: ScalingRule) -> bool:
        """Determine if service should be scaled down"""
        current_replicas = self.get_current_replicas(service_name)
        
        # Check if already at min replicas
        if current_replicas <= rule.min_replicas:
            return False
        
        # Check cooldown period
        if rule.last_scale_action:
            time_since_last_scale = datetime.utcnow() - rule.last_scale_action
            if time_since_last_scale.total_seconds() < rule.scale_down_cooldown:
                return False
        
        # Check if all metrics are below thresholds
        cpu_low = metrics.get("cpu_usage", 100) < rule.scale_down_threshold_cpu
        memory_low = metrics.get("memory_usage", 100) < rule.scale_down_threshold_memory
        
        # Check queue depth for Celery workers
        queue_low = True
        if "celery" in service_name:
            queue_depth = metrics.get("queue_depth", 0)
            queue_low = queue_depth < (current_replicas * 2)  # 2 tasks per worker threshold
        
        # Check request rate for backend services
        request_low = True
        if service_name == "backend":
            request_rate = metrics.get("request_rate", 0)
            request_low = request_rate < (current_replicas * 10)  # 10 requests/sec per replica
        
        # Scale down only if all metrics are low
        return cpu_low and memory_low and queue_low and request_low
    
    async def evaluate_scaling(self, service_name: str, rule: ScalingRule):
        """Evaluate and perform scaling for a service"""
        try:
            # Get current metrics
            metrics = await self.get_service_metrics(service_name)
            current_replicas = self.get_current_replicas(service_name)
            
            # Store metrics history
            if service_name not in self.metrics_history:
                self.metrics_history[service_name] = []
            
            self.metrics_history[service_name].append({
                "timestamp": datetime.utcnow(),
                "metrics": metrics,
                "replicas": current_replicas
            })
            
            # Keep only last 24 hours of history
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            self.metrics_history[service_name] = [
                entry for entry in self.metrics_history[service_name]
                if entry["timestamp"] > cutoff_time
            ]
            
            logger.info(f"{service_name}: CPU={metrics.get('cpu_usage', 0):.1f}%, "
                       f"Memory={metrics.get('memory_usage', 0):.1f}%, "
                       f"Replicas={current_replicas}")
            
            # Evaluate scaling decisions
            if self.should_scale_up(service_name, metrics, rule):
                new_replicas = min(current_replicas + 1, rule.max_replicas)
                if self.scale_service(service_name, new_replicas):
                    rule.last_scale_action = datetime.utcnow()
                    logger.info(f"Scaled up {service_name} from {current_replicas} to {new_replicas}")
            
            elif self.should_scale_down(service_name, metrics, rule):
                new_replicas = max(current_replicas - 1, rule.min_replicas)
                if self.scale_service(service_name, new_replicas):
                    rule.last_scale_action = datetime.utcnow()
                    logger.info(f"Scaled down {service_name} from {current_replicas} to {new_replicas}")
            
        except Exception as e:
            logger.error(f"Error evaluating scaling for {service_name}: {e}")
    
    async def run_monitoring_loop(self):
        """Main monitoring and scaling loop"""
        logger.info("Starting auto-scaling monitoring loop")
        
        while True:
            try:
                # Evaluate scaling for each service
                for service_name, rule in self.scaling_rules.items():
                    await self.evaluate_scaling(service_name, rule)
                
                # Wait for next monitoring interval
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Short delay before retrying
    
    def get_scaling_status(self) -> Dict[str, Any]:
        """Get current scaling status and metrics"""
        status = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {}
        }
        
        for service_name, rule in self.scaling_rules.items():
            current_replicas = self.get_current_replicas(service_name)
            
            # Get recent metrics
            recent_metrics = {}
            if service_name in self.metrics_history and self.metrics_history[service_name]:
                recent_metrics = self.metrics_history[service_name][-1]["metrics"]
            
            status["services"][service_name] = {
                "current_replicas": current_replicas,
                "min_replicas": rule.min_replicas,
                "max_replicas": rule.max_replicas,
                "last_scale_action": rule.last_scale_action.isoformat() if rule.last_scale_action else None,
                "recent_metrics": recent_metrics,
                "scaling_rules": {
                    "scale_up_cpu": rule.scale_up_threshold_cpu,
                    "scale_up_memory": rule.scale_up_threshold_memory,
                    "scale_down_cpu": rule.scale_down_threshold_cpu,
                    "scale_down_memory": rule.scale_down_threshold_memory
                }
            }
        
        return status

async def main():
    """Main function"""
    autoscaler = AutoScaler()
    
    # Start monitoring loop
    await autoscaler.run_monitoring_loop()

if __name__ == "__main__":
    asyncio.run(main())
