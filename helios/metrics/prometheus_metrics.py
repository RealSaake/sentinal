#!/usr/bin/env python3
"""
Prometheus Metrics System for Helios
Comprehensive observability and monitoring
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import psutil
import os

# Prometheus client imports
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Info, Enum,
        CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
        start_http_server, MetricsHandler
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# GPU monitoring
try:
    import pynvml
    GPU_MONITORING_AVAILABLE = True
except ImportError:
    GPU_MONITORING_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class MetricsConfig:
    """Configuration for metrics system."""
    enabled: bool = True
    port: int = 9090
    update_interval: float = 1.0
    collect_gpu_metrics: bool = True
    collect_system_metrics: bool = True


class HeliosMetrics:
    """
    Comprehensive Prometheus metrics for Helios system.
    Tracks all aspects of file processing pipeline performance.
    """
    
    def __init__(self, config: MetricsConfig, registry: Optional[CollectorRegistry] = None):
        """Initialize Helios metrics system."""
        if not PROMETHEUS_AVAILABLE:
            raise ImportError("prometheus_client not available. Install with: pip install prometheus-client")
        
        self.config = config
        self.registry = registry or CollectorRegistry()
        self.metrics_server = None
        self.update_thread = None
        self._stop_event = threading.Event()
        
        # GPU monitoring setup
        self.gpu_available = False
        if GPU_MONITORING_AVAILABLE and config.collect_gpu_metrics:
            try:
                pynvml.nvmlInit()
                self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                self.gpu_available = True
                logger.info("✅ GPU monitoring enabled")
            except Exception as e:
                logger.warning(f"⚠️  GPU monitoring unavailable: {e}")
                self.gpu_handle = None
        else:
            self.gpu_handle = None
        
        # Initialize all metrics
        self._init_file_processing_metrics()
        self._init_inference_metrics()
        self._init_worker_metrics()
        self._init_system_metrics()
        self._init_queue_metrics()
        
        logger.info(f"📊 Helios metrics initialized on port {config.port}")
    
    def _init_file_processing_metrics(self) -> None:
        """Initialize file processing metrics."""
        # Files processed counter
        self.files_processed_total = Counter(
            'sentinel_files_processed_total',
            'Total number of files processed by Helios',
            ['worker_id', 'status'],  # status: success, error, skipped
            registry=self.registry
        )
        
        # Files discovered counter
        self.files_discovered_total = Counter(
            'sentinel_files_discovered_total',
            'Total number of files discovered by scanner',
            ['scanner_type'],  # scanner_type: async, simple
            registry=self.registry
        )
        
        # File processing rate
        self.file_processing_rate = Gauge(
            'sentinel_file_processing_rate_per_second',
            'Current file processing rate in files per second',
            registry=self.registry
        )
        
        # Files in queue
        self.files_in_queue = Gauge(
            'sentinel_files_in_queue',
            'Number of files currently in processing queue',
            registry=self.registry
        )
        
        # File size distribution
        self.file_size_bytes = Histogram(
            'sentinel_file_size_bytes',
            'Distribution of file sizes processed',
            buckets=[1024, 10240, 102400, 1048576, 10485760, 104857600, 1073741824],  # 1KB to 1GB
            registry=self.registry
        )
    
    def _init_inference_metrics(self) -> None:
        """Initialize AI inference metrics."""
        # Inference duration histogram
        self.inference_duration_seconds = Histogram(
            'sentinel_inference_duration_seconds',
            'Time spent on AI inference per batch',
            ['worker_id', 'model_type'],
            buckets=[0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )
        
        # Inference batch size
        self.inference_batch_size = Gauge(
            'sentinel_batch_size',
            'Current inference batch size',
            ['worker_id'],
            registry=self.registry
        )
        
        # Model confidence distribution
        self.model_confidence = Histogram(
            'sentinel_model_confidence',
            'Distribution of AI model confidence scores',
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        # Inference errors
        self.inference_errors_total = Counter(
            'sentinel_inference_errors_total',
            'Total number of inference errors',
            ['worker_id', 'error_type'],
            registry=self.registry
        )
    
    def _init_worker_metrics(self) -> None:
        """Initialize worker process metrics."""
        # Active workers
        self.active_workers = Gauge(
            'sentinel_active_workers',
            'Number of active worker processes',
            registry=self.registry
        )
        
        # Worker status
        self.worker_status = Enum(
            'sentinel_worker_status',
            'Status of individual workers',
            ['worker_id'],
            states=['starting', 'running', 'stopping', 'stopped', 'error'],
            registry=self.registry
        )
        
        # Worker uptime
        self.worker_uptime_seconds = Gauge(
            'sentinel_worker_uptime_seconds',
            'Worker process uptime in seconds',
            ['worker_id'],
            registry=self.registry
        )
        
        # Worker restart count
        self.worker_restarts_total = Counter(
            'sentinel_worker_restarts_total',
            'Total number of worker restarts',
            ['worker_id', 'reason'],
            registry=self.registry
        )
    
    def _init_system_metrics(self) -> None:
        """Initialize system resource metrics."""
        # GPU metrics
        if self.gpu_available:
            self.gpu_utilization_percent = Gauge(
                'sentinel_gpu_utilization_percent',
                'GPU utilization percentage',
                registry=self.registry
            )
            
            self.gpu_memory_used_bytes = Gauge(
                'sentinel_gpu_memory_used_bytes',
                'GPU memory usage in bytes',
                registry=self.registry
            )
            
            self.gpu_memory_total_bytes = Gauge(
                'sentinel_gpu_memory_total_bytes',
                'Total GPU memory in bytes',
                registry=self.registry
            )
            
            self.gpu_temperature_celsius = Gauge(
                'sentinel_gpu_temperature_celsius',
                'GPU temperature in Celsius',
                registry=self.registry
            )
        
        # System metrics
        if self.config.collect_system_metrics:
            self.cpu_usage_percent = Gauge(
                'sentinel_cpu_usage_percent',
                'CPU usage percentage',
                registry=self.registry
            )
            
            self.memory_usage_percent = Gauge(
                'sentinel_memory_usage_percent',
                'Memory usage percentage',
                registry=self.registry
            )
            
            self.disk_usage_percent = Gauge(
                'sentinel_disk_usage_percent',
                'Disk usage percentage',
                ['mount_point'],
                registry=self.registry
            )
    
    def _init_queue_metrics(self) -> None:
        """Initialize queue and pipeline metrics."""
        # Queue depth
        self.queue_depth = Gauge(
            'sentinel_queue_depth',
            'Current depth of processing queues',
            ['queue_type'],  # input, output, metrics
            registry=self.registry
        )
        
        # Queue operations
        self.queue_operations_total = Counter(
            'sentinel_queue_operations_total',
            'Total queue operations',
            ['queue_type', 'operation'],  # operation: put, get, full, empty
            registry=self.registry
        )
        
        # Backpressure events
        self.backpressure_events_total = Counter(
            'sentinel_backpressure_events_total',
            'Total backpressure events',
            ['component'],  # scanner, worker
            registry=self.registry
        )
    
    def start_metrics_server(self) -> None:
        """Start Prometheus metrics HTTP server."""
        if not self.config.enabled:
            logger.info("📊 Metrics disabled in configuration")
            return
        
        try:
            # Start HTTP server
            start_http_server(self.config.port, registry=self.registry)
            logger.info(f"🌐 Metrics server started on port {self.config.port}")
            logger.info(f"📊 Metrics available at: http://localhost:{self.config.port}/metrics")
            
            # Start background update thread
            if self.config.update_interval > 0:
                self._start_update_thread()
            
        except Exception as e:
            logger.error(f"❌ Failed to start metrics server: {e}")
            raise
    
    def stop_metrics_server(self) -> None:
        """Stop metrics server and cleanup."""
        logger.info("🛑 Stopping metrics server...")
        
        # Stop update thread
        if self.update_thread:
            self._stop_event.set()
            self.update_thread.join(timeout=5)
        
        # Cleanup GPU monitoring
        if self.gpu_available:
            try:
                pynvml.nvmlShutdown()
            except:
                pass
        
        logger.info("✅ Metrics server stopped")
    
    def _start_update_thread(self) -> None:
        """Start background thread for updating system metrics."""
        def update_loop():
            while not self._stop_event.is_set():
                try:
                    self._update_system_metrics()
                    time.sleep(self.config.update_interval)
                except Exception as e:
                    logger.error(f"Error updating system metrics: {e}")
                    time.sleep(self.config.update_interval)
        
        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()
        logger.info("🔄 System metrics update thread started")
    
    def _update_system_metrics(self) -> None:
        """Update system resource metrics."""
        try:
            # Update GPU metrics
            if self.gpu_available and self.gpu_handle:
                self._update_gpu_metrics()
            
            # Update system metrics
            if self.config.collect_system_metrics:
                self._update_cpu_memory_metrics()
        
        except Exception as e:
            logger.debug(f"System metrics update error: {e}")
    
    def _update_gpu_metrics(self) -> None:
        """Update GPU metrics."""
        try:
            # GPU utilization
            utilization = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
            self.gpu_utilization_percent.set(utilization.gpu)
            
            # GPU memory
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
            self.gpu_memory_used_bytes.set(memory_info.used)
            self.gpu_memory_total_bytes.set(memory_info.total)
            
            # GPU temperature
            try:
                temp = pynvml.nvmlDeviceGetTemperature(self.gpu_handle, pynvml.NVML_TEMPERATURE_GPU)
                self.gpu_temperature_celsius.set(temp)
            except:
                pass  # Temperature might not be available
            
        except Exception as e:
            logger.debug(f"GPU metrics update error: {e}")
    
    def _update_cpu_memory_metrics(self) -> None:
        """Update CPU and memory metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)
            self.cpu_usage_percent.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.memory_usage_percent.set(memory.percent)
            
            # Disk usage for root partition
            disk = psutil.disk_usage('/')
            self.disk_usage_percent.labels(mount_point='/').set(
                (disk.used / disk.total) * 100
            )
            
        except Exception as e:
            logger.debug(f"System metrics update error: {e}")
    
    # Metric recording methods
    def record_file_processed(self, worker_id: int, status: str, processing_time: float, file_size: int) -> None:
        """Record a processed file."""
        self.files_processed_total.labels(worker_id=worker_id, status=status).inc()
        if file_size > 0:
            self.file_size_bytes.observe(file_size)
    
    def record_file_discovered(self, scanner_type: str) -> None:
        """Record a discovered file."""
        self.files_discovered_total.labels(scanner_type=scanner_type).inc()
    
    def record_inference(self, worker_id: int, duration: float, batch_size: int, confidence: float) -> None:
        """Record an inference operation."""
        self.inference_duration_seconds.labels(worker_id=worker_id, model_type='onnx').observe(duration)
        self.inference_batch_size.labels(worker_id=worker_id).set(batch_size)
        if 0 <= confidence <= 1:
            self.model_confidence.observe(confidence)
    
    def record_inference_error(self, worker_id: int, error_type: str) -> None:
        """Record an inference error."""
        self.inference_errors_total.labels(worker_id=worker_id, error_type=error_type).inc()
    
    def update_worker_status(self, worker_id: int, status: str, uptime: float = 0) -> None:
        """Update worker status."""
        self.worker_status.labels(worker_id=worker_id).state(status)
        if uptime > 0:
            self.worker_uptime_seconds.labels(worker_id=worker_id).set(uptime)
    
    def record_worker_restart(self, worker_id: int, reason: str) -> None:
        """Record a worker restart."""
        self.worker_restarts_total.labels(worker_id=worker_id, reason=reason).inc()
    
    def update_queue_depth(self, queue_type: str, depth: int) -> None:
        """Update queue depth."""
        self.queue_depth.labels(queue_type=queue_type).set(depth)
    
    def record_queue_operation(self, queue_type: str, operation: str) -> None:
        """Record a queue operation."""
        self.queue_operations_total.labels(queue_type=queue_type, operation=operation).inc()
    
    def record_backpressure_event(self, component: str) -> None:
        """Record a backpressure event."""
        self.backpressure_events_total.labels(component=component).inc()
    
    def update_processing_rate(self, rate: float) -> None:
        """Update current processing rate."""
        self.file_processing_rate.set(rate)
    
    def update_active_workers(self, count: int) -> None:
        """Update active worker count."""
        self.active_workers.set(count)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'metrics_enabled': self.config.enabled,
            'gpu_available': self.gpu_available,
            'system_metrics_enabled': self.config.collect_system_metrics
        }
        
        # Add current metric values (simplified)
        try:
            summary.update({
                'files_processed': self.files_processed_total._value.sum(),
                'active_workers': self.active_workers._value.get(),
                'processing_rate': self.file_processing_rate._value.get()
            })
        except:
            pass  # Metrics might not be initialized yet
        
        return summary
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        return generate_latest(self.registry).decode('utf-8')


# Convenience functions
def create_metrics_system(port: int = 9090, update_interval: float = 1.0) -> HeliosMetrics:
    """Create and configure metrics system."""
    config = MetricsConfig(
        enabled=True,
        port=port,
        update_interval=update_interval,
        collect_gpu_metrics=True,
        collect_system_metrics=True
    )
    
    return HeliosMetrics(config)


def start_metrics_server(port: int = 9090) -> HeliosMetrics:
    """Start metrics server with default configuration."""
    metrics = create_metrics_system(port=port)
    metrics.start_metrics_server()
    return metrics