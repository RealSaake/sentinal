#!/usr/bin/env python3
"""
Sentinel 2.0 - Performance Forecaster
Predicts analysis performance and ETA based on scout data and system capabilities
"""

import logging
import time
import psutil
import platform
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from .scout import ScoutMetrics

logger = logging.getLogger(__name__)


@dataclass
class SystemCapabilities:
    """System hardware and capability information."""
    cpu_cores: int
    cpu_threads: int
    total_ram_gb: float
    available_ram_gb: float
    gpu_available: bool
    gpu_memory_gb: float
    gpu_name: str
    storage_type: str  # 'SSD', 'HDD', 'Unknown'
    platform: str


@dataclass
class PerformanceStrategy:
    """Performance strategy configuration."""
    name: str
    description: str
    max_workers: int
    batch_size: int
    ai_complexity: str  # 'simple', 'balanced', 'complex'
    error_handling: str  # 'skip', 'pause'
    resource_usage: str  # 'low', 'balanced', 'max'


@dataclass
class PerformanceForecast:
    """Performance forecast results."""
    estimated_duration_seconds: float
    estimated_files_per_second: float
    recommended_strategy: PerformanceStrategy
    confidence_score: float  # 0.0 to 1.0
    bottleneck_prediction: str
    memory_usage_estimate_gb: float
    warnings: list


class PerformanceForecaster:
    """
    Analyzes system capabilities and scout data to predict performance
    and recommend optimal processing strategies.
    """
    
    # Predefined strategies
    STRATEGIES = {
        'speed_demon': PerformanceStrategy(
            name='Speed Demon',
            description='Maximum speed with simplified AI logic',
            max_workers=0,  # Will be set based on system
            batch_size=128,
            ai_complexity='simple',
            error_handling='skip',
            resource_usage='max'
        ),
        'balanced': PerformanceStrategy(
            name='Balanced',
            description='Good balance of speed and quality',
            max_workers=0,  # Will be set based on system
            batch_size=64,
            ai_complexity='balanced',
            error_handling='skip',
            resource_usage='balanced'
        ),
        'deep_analysis': PerformanceStrategy(
            name='Deep Analysis',
            description='Highest quality with detailed AI analysis',
            max_workers=0,  # Will be set based on system
            batch_size=32,
            ai_complexity='complex',
            error_handling='pause',
            resource_usage='balanced'
        )
    }
    
    def __init__(self):
        """Initialize the performance forecaster."""
        self.system_caps = self._detect_system_capabilities()
        self.historical_data = self._load_historical_data()
        
        # Update strategies with system-appropriate worker counts
        self._update_strategy_workers()
        
        logger.info(f"🔧 Performance forecaster initialized")
        logger.info(f"   System: {self.system_caps.cpu_cores}C/{self.system_caps.cpu_threads}T, "
                   f"{self.system_caps.total_ram_gb:.1f}GB RAM, GPU: {self.system_caps.gpu_available}")
    
    def _detect_system_capabilities(self) -> SystemCapabilities:
        """Detect system hardware capabilities."""
        try:
            # CPU information
            cpu_cores = psutil.cpu_count(logical=False) or 1
            cpu_threads = psutil.cpu_count(logical=True) or 1
            
            # Memory information
            memory = psutil.virtual_memory()
            total_ram_gb = memory.total / (1024**3)
            available_ram_gb = memory.available / (1024**3)
            
            # GPU detection (basic)
            gpu_available = False
            gpu_memory_gb = 0.0
            gpu_name = "None"
            
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_available = True
                    gpu_memory_gb = gpus[0].memoryTotal / 1024  # Convert MB to GB
                    gpu_name = gpus[0].name
            except ImportError:
                # Try nvidia-ml-py if available
                try:
                    import pynvml
                    pynvml.nvmlInit()
                    if pynvml.nvmlDeviceGetCount() > 0:
                        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                        gpu_name = pynvml.nvmlDeviceGetName(handle).decode()
                        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        gpu_memory_gb = mem_info.total / (1024**3)
                        gpu_available = True
                except:
                    pass
            
            # Storage type detection (simplified)
            storage_type = "Unknown"
            try:
                # This is a simplified detection - in reality, you'd want more sophisticated detection
                disk_usage = psutil.disk_usage('/')
                # For now, assume SSD if available space operations are fast
                storage_type = "SSD"  # Default assumption for modern systems
            except:
                pass
            
            return SystemCapabilities(
                cpu_cores=cpu_cores,
                cpu_threads=cpu_threads,
                total_ram_gb=total_ram_gb,
                available_ram_gb=available_ram_gb,
                gpu_available=gpu_available,
                gpu_memory_gb=gpu_memory_gb,
                gpu_name=gpu_name,
                storage_type=storage_type,
                platform=platform.system()
            )
            
        except Exception as e:
            logger.warning(f"Error detecting system capabilities: {e}")
            # Return conservative defaults
            return SystemCapabilities(
                cpu_cores=2,
                cpu_threads=4,
                total_ram_gb=8.0,
                available_ram_gb=4.0,
                gpu_available=False,
                gpu_memory_gb=0.0,
                gpu_name="Unknown",
                storage_type="Unknown",
                platform="Unknown"
            )
    
    def _load_historical_data(self) -> Dict[str, Any]:
        """Load historical performance data for better predictions."""
        # In a real implementation, this would load from a database or file
        # For now, return baseline performance metrics
        return {
            'baseline_files_per_second': {
                'cpu_only': 50.0,
                'gpu_accelerated': 150.0
            },
            'complexity_multipliers': {
                'simple': 1.0,
                'balanced': 0.7,
                'complex': 0.4
            },
            'batch_size_efficiency': {
                32: 0.8,
                64: 1.0,
                128: 1.1,
                256: 1.05
            }
        }
    
    def _update_strategy_workers(self):
        """Update strategy worker counts based on system capabilities."""
        # Conservative worker count calculation
        max_workers = min(self.system_caps.cpu_threads, 8)  # Cap at 8 for stability
        
        for strategy in self.STRATEGIES.values():
            if strategy.resource_usage == 'low':
                strategy.max_workers = max(1, max_workers // 2)
            elif strategy.resource_usage == 'balanced':
                strategy.max_workers = max(2, int(max_workers * 0.75))
            else:  # 'max'
                strategy.max_workers = max_workers
    
    def _estimate_base_performance(self, scout_metrics: ScoutMetrics) -> float:
        """Estimate base files per second performance."""
        # Start with baseline performance
        if self.system_caps.gpu_available:
            base_fps = self.historical_data['baseline_files_per_second']['gpu_accelerated']
        else:
            base_fps = self.historical_data['baseline_files_per_second']['cpu_only']
        
        # Adjust for file characteristics
        avg_file_size_mb = scout_metrics.total_size_bytes / scout_metrics.total_files / (1024**2)
        
        # Larger files are slower to process
        if avg_file_size_mb > 10:
            base_fps *= 0.5
        elif avg_file_size_mb > 1:
            base_fps *= 0.8
        
        # Adjust for file type complexity
        complex_extensions = {'.pdf', '.docx', '.xlsx', '.pptx', '.zip', '.rar'}
        simple_extensions = {'.txt', '.log', '.csv', '.json', '.xml'}
        
        complex_files = sum(
            count for ext, count in scout_metrics.extension_histogram.items() 
            if ext in complex_extensions
        )
        simple_files = sum(
            count for ext, count in scout_metrics.extension_histogram.items() 
            if ext in simple_extensions
        )
        
        if scout_metrics.total_files > 0:
            complexity_ratio = complex_files / scout_metrics.total_files
            if complexity_ratio > 0.5:
                base_fps *= 0.6
            elif complexity_ratio > 0.2:
                base_fps *= 0.8
        
        return base_fps
    
    def _calculate_strategy_performance(self, 
                                      base_fps: float, 
                                      strategy: PerformanceStrategy) -> Tuple[float, str]:
        """Calculate performance for a specific strategy."""
        fps = base_fps
        bottleneck = "CPU"
        
        # Apply complexity multiplier
        complexity_mult = self.historical_data['complexity_multipliers'][strategy.ai_complexity]
        fps *= complexity_mult
        
        # Apply batch size efficiency
        batch_efficiency = self.historical_data['batch_size_efficiency'].get(strategy.batch_size, 1.0)
        fps *= batch_efficiency
        
        # Apply worker scaling (with diminishing returns)
        worker_scaling = min(strategy.max_workers * 0.8, strategy.max_workers)
        fps *= worker_scaling
        
        # Check for potential bottlenecks
        if strategy.max_workers > self.system_caps.cpu_cores:
            fps *= 0.9  # CPU bottleneck
            bottleneck = "CPU"
        
        if not self.system_caps.gpu_available and strategy.ai_complexity != 'simple':
            fps *= 0.7  # No GPU for complex AI
            bottleneck = "GPU (not available)"
        
        # Memory bottleneck check
        estimated_memory_per_worker = 0.5  # GB per worker (rough estimate)
        total_memory_needed = strategy.max_workers * estimated_memory_per_worker
        
        if total_memory_needed > self.system_caps.available_ram_gb * 0.8:
            fps *= 0.6  # Memory bottleneck
            bottleneck = "Memory"
        
        return fps, bottleneck
    
    def forecast_performance(self, 
                           scout_metrics: ScoutMetrics, 
                           strategy_name: str = 'balanced') -> PerformanceForecast:
        """
        Generate a performance forecast for the given scout data and strategy.
        
        Args:
            scout_metrics: Results from directory scouting
            strategy_name: Name of the strategy to use
            
        Returns:
            PerformanceForecast with predictions and recommendations
        """
        if strategy_name not in self.STRATEGIES:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        strategy = self.STRATEGIES[strategy_name]
        
        # Calculate base performance
        base_fps = self._estimate_base_performance(scout_metrics)
        
        # Calculate strategy-specific performance
        estimated_fps, bottleneck = self._calculate_strategy_performance(base_fps, strategy)
        
        # Calculate duration
        if estimated_fps > 0:
            estimated_duration = scout_metrics.total_files / estimated_fps
        else:
            estimated_duration = float('inf')
        
        # Calculate confidence score
        confidence = self._calculate_confidence(scout_metrics, strategy)
        
        # Estimate memory usage
        memory_estimate = strategy.max_workers * 0.5 + (strategy.batch_size * 0.001)
        
        # Generate warnings
        warnings = []
        if scout_metrics.total_files > 100000:
            warnings.append("Large number of files may require significant processing time")
        
        if len(scout_metrics.large_files) > 10:
            warnings.append(f"{len(scout_metrics.large_files)} large files detected - may slow processing")
        
        if len(scout_metrics.problematic_files) > 0:
            warnings.append(f"{len(scout_metrics.problematic_files)} problematic files may cause errors")
        
        if memory_estimate > self.system_caps.available_ram_gb * 0.8:
            warnings.append("High memory usage predicted - consider reducing batch size")
        
        if not self.system_caps.gpu_available and strategy.ai_complexity != 'simple':
            warnings.append("No GPU detected - complex AI analysis will be slower")
        
        return PerformanceForecast(
            estimated_duration_seconds=estimated_duration,
            estimated_files_per_second=estimated_fps,
            recommended_strategy=strategy,
            confidence_score=confidence,
            bottleneck_prediction=bottleneck,
            memory_usage_estimate_gb=memory_estimate,
            warnings=warnings
        )
    
    def _calculate_confidence(self, scout_metrics: ScoutMetrics, strategy: PerformanceStrategy) -> float:
        """Calculate confidence score for the forecast."""
        confidence = 0.8  # Base confidence
        
        # Reduce confidence for edge cases
        if scout_metrics.total_files < 100:
            confidence *= 0.7  # Small datasets are harder to predict
        
        if scout_metrics.total_files > 1000000:
            confidence *= 0.8  # Very large datasets have more variables
        
        if len(scout_metrics.problematic_files) > scout_metrics.total_files * 0.1:
            confidence *= 0.6  # Many problematic files reduce predictability
        
        # Increase confidence for well-understood scenarios
        if self.system_caps.gpu_available and strategy.ai_complexity == 'simple':
            confidence *= 1.1
        
        return min(1.0, confidence)
    
    def compare_strategies(self, scout_metrics: ScoutMetrics) -> Dict[str, PerformanceForecast]:
        """Compare all available strategies for the given scout data."""
        forecasts = {}
        
        for strategy_name in self.STRATEGIES:
            try:
                forecast = self.forecast_performance(scout_metrics, strategy_name)
                forecasts[strategy_name] = forecast
            except Exception as e:
                logger.error(f"Error forecasting strategy {strategy_name}: {e}")
        
        return forecasts
    
    def get_system_report(self) -> str:
        """Generate a system capabilities report."""
        gpu_info = f"{self.system_caps.gpu_name} ({self.system_caps.gpu_memory_gb:.1f}GB)" if self.system_caps.gpu_available else "None"
        
        return f"""🖥️  System Capabilities Report
{'=' * 40}
CPU: {self.system_caps.cpu_cores} cores / {self.system_caps.cpu_threads} threads
RAM: {self.system_caps.total_ram_gb:.1f}GB total, {self.system_caps.available_ram_gb:.1f}GB available
GPU: {gpu_info}
Storage: {self.system_caps.storage_type}
Platform: {self.system_caps.platform}

📊 Available Strategies:
{chr(10).join(f"  {name}: {strategy.description}" for name, strategy in self.STRATEGIES.items())}"""


def format_duration(seconds: float) -> str:
    """Format duration in a human-readable way."""
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"


def format_forecast_report(forecast: PerformanceForecast) -> str:
    """Format a forecast into a human-readable report."""
    lines = [
        f"⏱️  Performance Forecast",
        f"{'=' * 30}",
        f"Strategy: {forecast.recommended_strategy.name}",
        f"Estimated Duration: {format_duration(forecast.estimated_duration_seconds)}",
        f"Processing Rate: {forecast.estimated_files_per_second:.1f} files/second",
        f"Confidence: {forecast.confidence_score * 100:.0f}%",
        f"Predicted Bottleneck: {forecast.bottleneck_prediction}",
        f"Memory Usage: {forecast.memory_usage_estimate_gb:.1f}GB",
    ]
    
    if forecast.warnings:
        lines.extend([
            "",
            "⚠️  Warnings:",
            *[f"  • {warning}" for warning in forecast.warnings]
        ])
    
    return "\n".join(lines)