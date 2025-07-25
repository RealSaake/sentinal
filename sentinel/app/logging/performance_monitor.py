"""Performance monitoring and metrics collection for Sentinel."""

import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid


@dataclass
class PerformanceMetrics:
    """Performance metrics for a specific operation type."""
    operation_name: str
    total_calls: int = 0
    total_duration: float = 0.0
    success_count: int = 0
    error_count: int = 0
    last_24h_calls: int = 0
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=50))
    
    @property
    def average_duration(self) -> float:
        """Calculate average duration."""
        return self.total_duration / self.total_calls if self.total_calls > 0 else 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        return (self.success_count / self.total_calls * 100) if self.total_calls > 0 else 0.0
    
    @property
    def recent_average_duration(self) -> float:
        """Calculate average duration for recent operations."""
        return sum(self.recent_durations) / len(self.recent_durations) if self.recent_durations else 0.0


@dataclass
class ActiveOperation:
    """Represents an active operation being timed."""
    operation_id: str
    operation_name: str
    start_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """Monitors and tracks performance metrics for various operations."""
    
    def __init__(self, logger_manager=None):
        """Initialize the performance monitor."""
        self.logger_manager = logger_manager
        self._metrics: Dict[str, PerformanceMetrics] = {}
        self._active_operations: Dict[str, ActiveOperation] = {}
        self._lock = threading.Lock()
        
        # Initialize common operation types
        self._init_operation_types()
        
        if self.logger_manager:
            self.logger = self.logger_manager.get_logger('performance_monitor')
            self.logger.info("Performance monitoring initialized")
    
    def _init_operation_types(self):
        """Initialize common operation types with default metrics."""
        operation_types = [
            'ai_inference',
            'database_query',
            'file_scan',
            'content_extraction',
            'pipeline_analysis'
        ]
        
        for op_type in operation_types:
            self._metrics[op_type] = PerformanceMetrics(operation_name=op_type)
    
    def start_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start timing an operation and return an operation ID."""
        operation_id = str(uuid.uuid4())
        start_time = time.perf_counter()
        
        with self._lock:
            self._active_operations[operation_id] = ActiveOperation(
                operation_id=operation_id,
                operation_name=operation_name,
                start_time=start_time,
                metadata=metadata or {}
            )
        
        if self.logger_manager:
            self.logger.debug(f"Started operation {operation_name} with ID {operation_id}")
        
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True, error_message: Optional[str] = None):
        """End timing an operation and record the metrics."""
        end_time = time.perf_counter()
        
        with self._lock:
            if operation_id not in self._active_operations:
                if self.logger_manager:
                    self.logger.warning(f"Attempted to end unknown operation ID: {operation_id}")
                return
            
            operation = self._active_operations.pop(operation_id)
            duration = end_time - operation.start_time
            
            # Update metrics
            if operation.operation_name not in self._metrics:
                self._metrics[operation.operation_name] = PerformanceMetrics(operation_name=operation.operation_name)
            metrics = self._metrics[operation.operation_name]
            metrics.total_calls += 1
            metrics.total_duration += duration
            metrics.recent_durations.append(duration)
            
            if success:
                metrics.success_count += 1
            else:
                metrics.error_count += 1
                if error_message:
                    metrics.recent_errors.append({
                        'timestamp': datetime.now(),
                        'error': error_message,
                        'duration': duration
                    })
            
            # Update 24h counter (simplified - in production, you'd want proper time-based tracking)
            metrics.last_24h_calls += 1
        
        if self.logger_manager:
            status = "SUCCESS" if success else "FAILED"
            self.logger.info(f"Operation {operation.operation_name} {status} in {duration:.3f}s")
            if not success and error_message:
                self.logger.error(f"Operation {operation.operation_name} failed: {error_message}")
    
    def log_ai_request(self, duration: float, success: bool, model_name: Optional[str] = None, 
                      error_message: Optional[str] = None):
        """Log an AI inference request with performance data."""
        with self._lock:
            if 'ai_inference' not in self._metrics:
                self._metrics['ai_inference'] = PerformanceMetrics(operation_name='ai_inference')
            metrics = self._metrics['ai_inference']
            metrics.total_calls += 1
            metrics.total_duration += duration
            metrics.recent_durations.append(duration)
            metrics.last_24h_calls += 1
            
            if success:
                metrics.success_count += 1
            else:
                metrics.error_count += 1
                if error_message:
                    metrics.recent_errors.append({
                        'timestamp': datetime.now(),
                        'error': error_message,
                        'duration': duration,
                        'model': model_name
                    })
        
        if self.logger_manager:
            status = "SUCCESS" if success else "FAILED"
            model_info = f" (model: {model_name})" if model_name else ""
            self.logger.info(f"AI inference {status} in {duration:.3f}s{model_info}")
    
    def log_scan_operation(self, file_count: int, duration: float, directory_path: str):
        """Log a file scanning operation with performance data."""
        files_per_second = file_count / duration if duration > 0 else 0
        
        with self._lock:
            if 'file_scan' not in self._metrics:
                self._metrics['file_scan'] = PerformanceMetrics(operation_name='file_scan')
            metrics = self._metrics['file_scan']
            metrics.total_calls += 1
            metrics.total_duration += duration
            metrics.recent_durations.append(duration)
            metrics.success_count += 1  # Assume scans that complete are successful
            metrics.last_24h_calls += 1
        
        if self.logger_manager:
            self.logger.info(f"File scan completed: {file_count} files in {duration:.3f}s "
                           f"({files_per_second:.1f} files/sec) - Path: {directory_path}")
    
    def log_database_operation(self, operation_type: str, duration: float, affected_rows: int = 0,
                             success: bool = True, error_message: Optional[str] = None):
        """Log a database operation with performance data."""
        with self._lock:
            if 'database_query' not in self._metrics:
                self._metrics['database_query'] = PerformanceMetrics(operation_name='database_query')
            metrics = self._metrics['database_query']
            metrics.total_calls += 1
            metrics.total_duration += duration
            metrics.recent_durations.append(duration)
            metrics.last_24h_calls += 1
            
            if success:
                metrics.success_count += 1
            else:
                metrics.error_count += 1
                if error_message:
                    metrics.recent_errors.append({
                        'timestamp': datetime.now(),
                        'error': error_message,
                        'operation': operation_type,
                        'duration': duration
                    })
        
        if self.logger_manager:
            status = "SUCCESS" if success else "FAILED"
            rows_info = f" ({affected_rows} rows)" if affected_rows > 0 else ""
            self.logger.info(f"Database {operation_type} {status} in {duration:.3f}s{rows_info}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all performance metrics for display."""
        with self._lock:
            metrics_data = {}
            
            for operation_name, metrics in self._metrics.items():
                if metrics.total_calls > 0:  # Only include operations that have been used
                    metrics_data[operation_name] = {
                        'total_calls': metrics.total_calls,
                        'average_duration': metrics.average_duration,
                        'recent_average_duration': metrics.recent_average_duration,
                        'success_rate': metrics.success_rate,
                        'last_24h_calls': metrics.last_24h_calls,
                        'total_errors': metrics.error_count,
                        'recent_errors': list(metrics.recent_errors)[-5:]  # Last 5 errors
                    }
            
            # Add system-wide stats
            metrics_data['_system'] = {
                'active_operations': len(self._active_operations),
                'total_operation_types': len([m for m in self._metrics.values() if m.total_calls > 0]),
                'monitoring_start_time': datetime.now().isoformat()  # Simplified
            }
            
            return metrics_data
    
    def get_operation_summary(self, operation_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed summary for a specific operation type."""
        with self._lock:
            if operation_name not in self._metrics:
                return None
            
            metrics = self._metrics[operation_name]
            
            return {
                'operation_name': operation_name,
                'total_calls': metrics.total_calls,
                'total_duration': metrics.total_duration,
                'average_duration': metrics.average_duration,
                'recent_average_duration': metrics.recent_average_duration,
                'success_rate': metrics.success_rate,
                'success_count': metrics.success_count,
                'error_count': metrics.error_count,
                'last_24h_calls': metrics.last_24h_calls,
                'recent_durations': list(metrics.recent_durations),
                'recent_errors': list(metrics.recent_errors)
            }
    
    def reset_metrics(self, operation_name: Optional[str] = None):
        """Reset metrics for a specific operation or all operations."""
        with self._lock:
            if operation_name:
                if operation_name in self._metrics:
                    self._metrics[operation_name] = PerformanceMetrics(operation_name=operation_name)
            else:
                # Reset all metrics
                for op_name in list(self._metrics.keys()):
                    self._metrics[op_name] = PerformanceMetrics(operation_name=op_name)
        
        if self.logger_manager:
            target = operation_name or "all operations"
            self.logger.info(f"Performance metrics reset for {target}")
    
    def get_active_operations(self) -> List[Dict[str, Any]]:
        """Get list of currently active operations."""
        with self._lock:
            current_time = time.perf_counter()
            active_ops = []
            
            for op_id, operation in self._active_operations.items():
                elapsed = current_time - operation.start_time
                active_ops.append({
                    'operation_id': op_id,
                    'operation_name': operation.operation_name,
                    'elapsed_time': elapsed,
                    'metadata': operation.metadata
                })
            
            return active_ops