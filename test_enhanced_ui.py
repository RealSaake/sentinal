#!/usr/bin/env python3
"""
Test the Enhanced Main Window - ONE window with ALL functionality!
"""

import sys
from pathlib import Path

# Add sentinel to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from sentinel.app.db import DatabaseManager
from sentinel.app.logging import LoggerManager, PerformanceMonitor, DebugInfoCollector
from sentinel.app.ui.enhanced_main_window import EnhancedMainWindow

def main():
    """Launch the enhanced Sentinel 2.0 UI."""
    app = QApplication(sys.argv)
    
    # Initialize components
    db_manager = DatabaseManager()
    db_manager.init_schema()
    
    # Initialize logging (optional)
    try:
        logger_manager = LoggerManager({})
        perf_monitor = PerformanceMonitor(logger_manager)
        debug_collector = DebugInfoCollector({}, logger_manager, perf_monitor)
    except:
        logger_manager = None
        perf_monitor = None
        debug_collector = None
    
    # Create enhanced main window
    window = EnhancedMainWindow(
        db_manager=db_manager,
        logger_manager=logger_manager,
        performance_monitor=perf_monitor,
        debug_collector=debug_collector
    )
    
    window.show()
    
    print("🎯 Sentinel 2.0 Enhanced UI launched!")
    print("Features:")
    print("  • ETA display in real-time")
    print("  • All functionality in ONE window")
    print("  • Live progress monitoring")
    print("  • Performance statistics")
    print("  • Configuration controls")
    print("  • Results table")
    print("  • Live log viewer")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()