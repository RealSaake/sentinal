#!/usr/bin/env python3
"""Test script to verify the debug UI works."""

import sys
import os
import yaml
from pathlib import Path

# Add sentinel to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sentinel'))

from PyQt6.QtWidgets import QApplication
from sentinel.app.logging import LoggerManager, PerformanceMonitor, DebugInfoCollector
from sentinel.app.ui.debug_dialog import DebugDialog

def test_debug_ui():
    """Test the debug UI."""
    print("🔍 Testing Debug UI...")
    
    # Create QApplication
    app = QApplication(sys.argv)
    
    # Load configuration
    config_path = Path('sentinel/config/config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    try:
        # Initialize logging system
        logger_manager = LoggerManager(config)
        perf_monitor = PerformanceMonitor(logger_manager)
        debug_collector = DebugInfoCollector(config, logger_manager, perf_monitor)
        
        # Generate some test data
        logger = logger_manager.get_logger('test_ui')
        logger.info("Testing debug UI with sample log entries")
        logger.warning("This is a test warning message")
        logger.error("This is a test error message")
        
        # Generate some performance data
        op_id = perf_monitor.start_operation('test_ui_operation')
        import time
        time.sleep(0.1)
        perf_monitor.end_operation(op_id, success=True)
        
        perf_monitor.log_ai_request(duration=1.5, success=True, model_name="test_model")
        perf_monitor.log_ai_request(duration=2.1, success=False, error_message="Test error")
        
        # Create and show debug dialog
        debug_dialog = DebugDialog(
            logger_manager=logger_manager,
            performance_monitor=perf_monitor,
            debug_collector=debug_collector
        )
        
        logger.info("Debug UI initialized successfully")
        print("✅ Debug UI created successfully!")
        print("   Opening debug dialog window...")
        
        debug_dialog.show()
        
        # Run the application
        return app.exec()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = test_debug_ui()
    sys.exit(exit_code)