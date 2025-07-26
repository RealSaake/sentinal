#!/usr/bin/env python3
"""
Test the Scout and Performance Forecaster modules
"""

import sys
import time
from pathlib import Path

# Add sentinel to path
sys.path.insert(0, str(Path(__file__).parent))

def test_directory_scout():
    """Test the directory scout functionality."""
    print("🔍 Testing Directory Scout...")
    print("=" * 50)
    
    try:
        from sentinel.core.scout import DirectoryScout, quick_scout
        
        # Test with current directory
        test_dir = "."
        print(f"Scouting directory: {test_dir}")
        
        # Create scout instance
        scout = DirectoryScout(
            large_file_threshold_mb=10,  # Lower threshold for testing
            max_workers=2,
            skip_hidden=True
        )
        
        # Perform scouting
        start_time = time.time()
        metrics = scout.scout_directory(test_dir)
        end_time = time.time()
        
        print(f"\n✅ Scout completed in {end_time - start_time:.2f} seconds")
        
        # Display results
        print(scout.get_summary_report(metrics))
        
        # Test quick scout function
        print("\n🚀 Testing quick scout...")
        quick_metrics = quick_scout(test_dir, max_workers=1)
        print(f"Quick scout found {quick_metrics.total_files} files")
        
        return metrics
        
    except Exception as e:
        print(f"❌ Scout test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_performance_forecaster(scout_metrics):
    """Test the performance forecaster."""
    print("\n\n🔧 Testing Performance Forecaster...")
    print("=" * 50)
    
    try:
        from sentinel.core.performance_forecaster import PerformanceForecaster, format_forecast_report
        
        # Create forecaster
        forecaster = PerformanceForecaster()
        
        # Display system report
        print(forecaster.get_system_report())
        
        print("\n📊 Strategy Comparison:")
        print("-" * 30)
        
        # Compare all strategies
        forecasts = forecaster.compare_strategies(scout_metrics)
        
        for strategy_name, forecast in forecasts.items():
            print(f"\n{strategy_name.upper()}:")
            print(f"  Duration: {forecast.estimated_duration_seconds:.1f}s")
            print(f"  Speed: {forecast.estimated_files_per_second:.1f} files/sec")
            print(f"  Confidence: {forecast.confidence_score * 100:.0f}%")
            print(f"  Bottleneck: {forecast.bottleneck_prediction}")
            
            if forecast.warnings:
                print(f"  Warnings: {len(forecast.warnings)}")
        
        # Detailed forecast for balanced strategy
        print("\n" + "=" * 50)
        balanced_forecast = forecaster.forecast_performance(scout_metrics, 'balanced')
        print(format_forecast_report(balanced_forecast))
        
        return forecasts
        
    except Exception as e:
        print(f"❌ Forecaster test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_integration():
    """Test the integration of scout and forecaster."""
    print("\n\n🚀 Testing Integration...")
    print("=" * 50)
    
    try:
        from sentinel.core.scout import DirectoryScout
        from sentinel.core.performance_forecaster import PerformanceForecaster, format_duration
        
        # Simulate the pre-flight check workflow
        target_dir = "."
        
        print(f"🎯 Target Directory: {target_dir}")
        print("\n1️⃣ Scouting phase...")
        
        scout = DirectoryScout()
        scout_metrics = scout.scout_directory(target_dir)
        
        print(f"   Found {scout_metrics.total_files:,} files")
        print(f"   Total size: {scout_metrics.total_size_bytes / (1024**2):.1f} MB")
        print(f"   Scan time: {scout_metrics.scan_duration_seconds:.2f}s")
        
        print("\n2️⃣ Performance forecasting...")
        
        forecaster = PerformanceForecaster()
        
        # Get forecasts for all strategies
        forecasts = forecaster.compare_strategies(scout_metrics)
        
        print("\n📋 Pre-Flight Summary:")
        print("-" * 30)
        
        for strategy_name, forecast in forecasts.items():
            duration_str = format_duration(forecast.estimated_duration_seconds)
            print(f"{strategy_name:15} | {duration_str:>12} | {forecast.estimated_files_per_second:>6.1f} fps")
        
        # Recommend best strategy
        best_strategy = min(forecasts.items(), key=lambda x: x[1].estimated_duration_seconds)
        print(f"\n🏆 Recommended: {best_strategy[0]} ({format_duration(best_strategy[1].estimated_duration_seconds)})")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🧪 Sentinel 2.0 - Scout & Forecaster Tests")
    print("=" * 60)
    
    # Test scout
    scout_metrics = test_directory_scout()
    
    if scout_metrics:
        # Test forecaster
        forecasts = test_performance_forecaster(scout_metrics)
        
        if forecasts:
            # Test integration
            test_integration()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()