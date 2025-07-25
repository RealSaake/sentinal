#!/usr/bin/env python3
"""Test script to verify the logging and debug system."""

import sys
import os
import yaml
from pathlib import Path

# Add sentinel to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sentinel'))

from sentinel.app.logging import LoggerManager, PerformanceMonitor, DebugInfoCollector

def test_logging_system():
    """Test the complete logging system."""
    print("🔍 Testing Sentinel Logging & Debug System...")
    
    # Load configuration
    config_path = Path('sentinel/config/config.yaml')
    if not config_path.exists():
        print("❌ Config file not found")
        return False
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    try:
        # Initialize logging system
        print("\n1. Initializing LoggerManager...")
        logger_manager = LoggerManager(config)
        logger = logger_manager.get_logger('test')
        logger.info("✅ LoggerManager initialized successfully")
        
        # Initialize performance monitor
        print("2. Initializing PerformanceMonitor...")
        perf_monitor = PerformanceMonitor(logger_manager)
        logger.info("✅ PerformanceMonitor initialized successfully")
        
        # Initialize debug collector
        print("3. Initializing DebugInfoCollector...")
        debug_collector = DebugInfoCollector(config, logger_manager, perf_monitor)
        logger.info("✅ DebugInfoCollector initialized successfully")
        
        # Test performance monitoring
        print("4. Testing performance monitoring...")
        op_id = perf_monitor.start_operation('test_operation')
        import time
        time.sleep(0.1)  # Simulate work
        perf_monitor.end_operation(op_id, success=True)
        
        # Test AI request logging
        perf_monitor.log_ai_request(duration=0.5, success=True, model_name="test_model")
        perf_monitor.log_ai_request(duration=1.2, success=False, error_message="Test error")
        
        logger.info("✅ Performance monitoring test completed")
        
        # Test debug info collection
        print("5. Testing debug info collection...")
        system_info = debug_collector.collect_system_info()
        app_state = debug_collector.collect_app_state()
        ai_connectivity = debug_collector.test_ai_connectivity()
        db_connectivity = debug_collector.test_database_connectivity()
        
        logger.info("✅ Debug info collection completed")
        
        # Test log retrieval
        print("6. Testing log retrieval...")
        recent_logs = logger_manager.get_recent_logs(10)
        print(f"   Retrieved {len(recent_logs)} recent log entries")
        
        # Test metrics retrieval
        print("7. Testing metrics retrieval...")
        metrics = perf_monitor.get_metrics()
        print(f"   Retrieved metrics for {len(metrics)} operation types")
        
        # Generate debug report
        print("8. Generating debug report...")
        debug_report = debug_collector.generate_debug_report()
        
        # Save debug report to file
        report_path = Path('debug_report.json')
        with open(report_path, 'w') as f:
            f.write(debug_report)
        
        print(f"   Debug report saved to: {report_path}")
        logger.info("✅ Debug report generated successfully")
        
        # Display summary
        print("\n📊 System Status Summary:")
        print(f"   • AI Backend: {ai_connectivity['status']}")
        print(f"   • Database: {db_connectivity['status']}")
        print(f"   • Log Level: {logger_manager.log_level}")
        print(f"   • Performance Metrics: {len(metrics)} operation types tracked")
        print(f"   • Recent Logs: {len(recent_logs)} entries")
        
        print("\n✅ All logging system tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_logging_system()
    sys.exit(0 if success else 1)