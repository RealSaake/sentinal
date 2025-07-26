import sys
import yaml
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from .db import DatabaseManager
from .ui.main_window import MainWindow
from .logging import LoggerManager, PerformanceMonitor, DebugInfoCollector


def main() -> None:
    """Application entry point."""
    app = QApplication(sys.argv)
    
    # Load configuration
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize logging system
    logger_manager = LoggerManager(config)
    perf_monitor = PerformanceMonitor(logger_manager)
    debug_collector = DebugInfoCollector(config, logger_manager, perf_monitor)
    
    # Get application logger
    app_logger = logger_manager.get_logger('main')
    app_logger.info("🎯 Sentinel Storage Analyzer starting up...")
    
    # Initialize database
    db_manager = DatabaseManager()
    db_manager.init_schema()
    app_logger.info("Database initialized successfully")

    # Create main window with logging components
    window = MainWindow(
        db_manager, 
        logger_manager=logger_manager,
        performance_monitor=perf_monitor,
        debug_collector=debug_collector
    )
    window.show()
    app_logger.info("Main window displayed")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 