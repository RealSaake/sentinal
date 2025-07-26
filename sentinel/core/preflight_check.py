#!/usr/bin/env python3
"""
Sentinel 2.0 - Pre-Flight Check System
Orchestrates scouting, forecasting, and user strategy selection
"""

import logging
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path

from .scout import DirectoryScout, ScoutMetrics
from .performance_forecaster import PerformanceForecaster, PerformanceForecast, PerformanceStrategy

logger = logging.getLogger(__name__)


@dataclass
class PreFlightResults:
    """Complete pre-flight check results."""
    target_directory: str
    scout_metrics: ScoutMetrics
    system_capabilities: Dict[str, Any]
    strategy_forecasts: Dict[str, PerformanceForecast]
    recommended_strategy: str
    user_selected_strategy: Optional[str] = None
    custom_parameters: Optional[Dict[str, Any]] = None
    check_duration_seconds: float = 0.0
    warnings: list = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class PreFlightChecker:
    """
    Orchestrates the complete pre-flight check process.
    This is the main interface between the UI and the core scouting/forecasting logic.
    """
    
    def __init__(self, 
                 progress_callback: Optional[Callable[[str, float], None]] = None,
                 scout_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the pre-flight checker.
        
        Args:
            progress_callback: Function to call with progress updates (message, percentage)
            scout_config: Configuration for the directory scout
        """
        self.progress_callback = progress_callback or self._default_progress_callback
        self.scout_config = scout_config or {}
        
        # Initialize components
        self.scout = DirectoryScout(**self.scout_config)
        self.forecaster = PerformanceForecaster()
        
        logger.info("🚀 Pre-flight checker initialized")
    
    def _default_progress_callback(self, message: str, percentage: float):
        """Default progress callback that just logs."""
        logger.info(f"Progress ({percentage:.0f}%): {message}")
    
    def perform_preflight_check(self, target_directory: str) -> PreFlightResults:
        """
        Perform complete pre-flight check.
        
        Args:
            target_directory: Directory to analyze
            
        Returns:
            PreFlightResults with all analysis data
        """
        start_time = time.time()
        
        try:
            # Validate target directory
            target_path = Path(target_directory)
            if not target_path.exists():
                raise FileNotFoundError(f"Target directory does not exist: {target_directory}")
            
            if not target_path.is_dir():
                raise NotADirectoryError(f"Target is not a directory: {target_directory}")
            
            logger.info(f"🔍 Starting pre-flight check for: {target_directory}")
            
            # Phase 1: Directory Scouting
            self.progress_callback("Scanning directory structure...", 10)
            scout_metrics = self.scout.scout_directory(target_directory)
            
            logger.info(f"Scout found {scout_metrics.total_files:,} files in {scout_metrics.scan_duration_seconds:.2f}s")
            
            # Phase 2: Performance Forecasting
            self.progress_callback("Analyzing system capabilities...", 40)
            
            # Get system capabilities
            system_caps = asdict(self.forecaster.system_caps)
            
            # Phase 3: Strategy Analysis
            self.progress_callback("Calculating performance forecasts...", 70)
            strategy_forecasts = self.forecaster.compare_strategies(scout_metrics)
            
            # Phase 4: Recommendation
            self.progress_callback("Generating recommendations...", 90)
            recommended_strategy = self._select_recommended_strategy(strategy_forecasts)
            
            # Collect warnings
            warnings = self._collect_warnings(scout_metrics, strategy_forecasts)
            
            # Complete
            self.progress_callback("Pre-flight check complete!", 100)
            
            check_duration = time.time() - start_time
            
            results = PreFlightResults(
                target_directory=target_directory,
                scout_metrics=scout_metrics,
                system_capabilities=system_caps,
                strategy_forecasts=strategy_forecasts,
                recommended_strategy=recommended_strategy,
                check_duration_seconds=check_duration,
                warnings=warnings
            )
            
            logger.info(f"✅ Pre-flight check completed in {check_duration:.2f}s")
            logger.info(f"   Recommended strategy: {recommended_strategy}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Pre-flight check failed: {e}")
            raise
    
    def _select_recommended_strategy(self, forecasts: Dict[str, PerformanceForecast]) -> str:
        """Select the best recommended strategy based on forecasts."""
        if not forecasts:
            return 'balanced'
        
        # Score each strategy
        strategy_scores = {}
        
        for name, forecast in forecasts.items():
            score = 0.0
            
            # Favor faster strategies (but not at the expense of everything else)
            if forecast.estimated_duration_seconds > 0:
                time_score = 1.0 / forecast.estimated_duration_seconds
                score += time_score * 0.4
            
            # Favor higher confidence
            score += forecast.confidence_score * 0.3
            
            # Penalize strategies with many warnings
            warning_penalty = len(forecast.warnings) * 0.1
            score -= warning_penalty
            
            # Favor balanced approach for most users
            if name == 'balanced':
                score += 0.2
            
            strategy_scores[name] = score
        
        # Return strategy with highest score
        return max(strategy_scores.items(), key=lambda x: x[1])[0]
    
    def _collect_warnings(self, 
                         scout_metrics: ScoutMetrics, 
                         forecasts: Dict[str, PerformanceForecast]) -> list:
        """Collect all warnings from scout and forecasts."""
        warnings = []
        
        # Scout-based warnings
        if scout_metrics.total_files > 500000:
            warnings.append("Very large number of files - processing may take significant time")
        
        if scout_metrics.total_size_bytes > 100 * 1024**3:  # 100GB
            warnings.append("Large total file size - ensure sufficient disk space for results")
        
        if len(scout_metrics.large_files) > 50:
            warnings.append(f"{len(scout_metrics.large_files)} large files detected - may impact performance")
        
        if len(scout_metrics.problematic_files) > 100:
            warnings.append(f"{len(scout_metrics.problematic_files)} problematic files may cause processing errors")
        
        # Check for unusual file type distributions
        if scout_metrics.extension_histogram:
            no_ext_files = scout_metrics.extension_histogram.get('<no_extension>', 0)
            if no_ext_files > scout_metrics.total_files * 0.2:
                warnings.append("Many files without extensions - classification may be less accurate")
        
        # Forecast-based warnings (collect unique warnings)
        forecast_warnings = set()
        for forecast in forecasts.values():
            forecast_warnings.update(forecast.warnings)
        
        warnings.extend(list(forecast_warnings))
        
        return warnings
    
    def create_custom_strategy(self, 
                              base_strategy: str,
                              custom_params: Dict[str, Any]) -> PerformanceStrategy:
        """
        Create a custom strategy based on user parameters.
        
        Args:
            base_strategy: Base strategy to modify
            custom_params: Custom parameters to apply
            
        Returns:
            Modified PerformanceStrategy
        """
        if base_strategy not in self.forecaster.STRATEGIES:
            raise ValueError(f"Unknown base strategy: {base_strategy}")
        
        # Start with base strategy
        strategy = self.forecaster.STRATEGIES[base_strategy]
        
        # Create a copy and apply custom parameters
        custom_strategy = PerformanceStrategy(
            name=f"Custom ({strategy.name})",
            description="User-customized strategy",
            max_workers=custom_params.get('max_workers', strategy.max_workers),
            batch_size=custom_params.get('batch_size', strategy.batch_size),
            ai_complexity=custom_params.get('ai_complexity', strategy.ai_complexity),
            error_handling=custom_params.get('error_handling', strategy.error_handling),
            resource_usage=custom_params.get('resource_usage', strategy.resource_usage)
        )
        
        return custom_strategy
    
    def validate_custom_parameters(self, params: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate custom parameters and return any errors.
        
        Args:
            params: Parameters to validate
            
        Returns:
            Dictionary of parameter_name -> error_message for invalid params
        """
        errors = {}
        
        # Validate max_workers
        if 'max_workers' in params:
            workers = params['max_workers']
            if not isinstance(workers, int) or workers < 1:
                errors['max_workers'] = "Must be a positive integer"
            elif workers > self.forecaster.system_caps.cpu_threads * 2:
                errors['max_workers'] = f"Exceeds recommended maximum ({self.forecaster.system_caps.cpu_threads * 2})"
        
        # Validate batch_size
        if 'batch_size' in params:
            batch_size = params['batch_size']
            if not isinstance(batch_size, int) or batch_size < 1:
                errors['batch_size'] = "Must be a positive integer"
            elif batch_size > 512:
                errors['batch_size'] = "Very large batch sizes may cause memory issues"
        
        # Validate ai_complexity
        if 'ai_complexity' in params:
            complexity = params['ai_complexity']
            if complexity not in ['simple', 'balanced', 'complex']:
                errors['ai_complexity'] = "Must be 'simple', 'balanced', or 'complex'"
        
        # Validate error_handling
        if 'error_handling' in params:
            handling = params['error_handling']
            if handling not in ['skip', 'pause']:
                errors['error_handling'] = "Must be 'skip' or 'pause'"
        
        # Validate resource_usage
        if 'resource_usage' in params:
            usage = params['resource_usage']
            if usage not in ['low', 'balanced', 'max']:
                errors['resource_usage'] = "Must be 'low', 'balanced', or 'max'"
        
        return errors
    
    def get_strategy_comparison_table(self, forecasts: Dict[str, PerformanceForecast]) -> list:
        """
        Generate a comparison table of strategies for UI display.
        
        Returns:
            List of dictionaries with strategy comparison data
        """
        from .performance_forecaster import format_duration
        
        comparison = []
        
        for name, forecast in forecasts.items():
            comparison.append({
                'name': name,
                'display_name': forecast.recommended_strategy.name,
                'description': forecast.recommended_strategy.description,
                'duration': format_duration(forecast.estimated_duration_seconds),
                'duration_seconds': forecast.estimated_duration_seconds,
                'files_per_second': forecast.estimated_files_per_second,
                'confidence': f"{forecast.confidence_score * 100:.0f}%",
                'confidence_score': forecast.confidence_score,
                'bottleneck': forecast.bottleneck_prediction,
                'memory_gb': forecast.memory_usage_estimate_gb,
                'warning_count': len(forecast.warnings),
                'warnings': forecast.warnings
            })
        
        # Sort by duration (fastest first)
        comparison.sort(key=lambda x: x['duration_seconds'])
        
        return comparison
    
    def get_preflight_summary(self, results: PreFlightResults) -> Dict[str, Any]:
        """
        Generate a summary of pre-flight results for UI display.
        
        Args:
            results: Pre-flight check results
            
        Returns:
            Dictionary with summary information
        """
        from .performance_forecaster import format_duration
        
        recommended_forecast = results.strategy_forecasts[results.recommended_strategy]
        
        return {
            'target_directory': results.target_directory,
            'total_files': results.scout_metrics.total_files,
            'total_size_gb': results.scout_metrics.total_size_bytes / (1024**3),
            'file_types': len(results.scout_metrics.extension_histogram),
            'scan_duration': results.scout_metrics.scan_duration_seconds,
            'recommended_strategy': results.recommended_strategy,
            'estimated_duration': format_duration(recommended_forecast.estimated_duration_seconds),
            'estimated_speed': f"{recommended_forecast.estimated_files_per_second:.1f} files/sec",
            'confidence': f"{recommended_forecast.confidence_score * 100:.0f}%",
            'warning_count': len(results.warnings),
            'system_gpu': results.system_capabilities.get('gpu_available', False),
            'system_cores': results.system_capabilities.get('cpu_cores', 1),
            'system_ram_gb': results.system_capabilities.get('total_ram_gb', 0)
        }