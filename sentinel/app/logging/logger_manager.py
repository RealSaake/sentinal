"""Central logging manager for Sentinel application."""

import logging
import logging.handlers
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import threading
import glob


@dataclass
class LogEntry:
    """Structured log entry for UI display."""
    timestamp: datetime
    level: str
    logger_name: str
    message: str
    module: str
    function: str
    line_number: int
    exception_info: Optional[str] = None


class LoggerManager:
    """Manages all logging operations for the Sentinel application."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the logger manager with configuration."""
        self.config = config.get('logging', {})
        self.log_level = self.config.get('level', 'INFO')
        self.log_file_path = self.config.get('file_path', 'logs/sentinel.log')
        self.max_file_size_mb = self.config.get('max_file_size_mb', 10)
        self.max_files = self.config.get('max_files', 5)
        self.cleanup_days = self.config.get('cleanup_days', 30)
        self.console_output = self.config.get('console_output', True)
        
        self._loggers: Dict[str, logging.Logger] = {}
        self._memory_handler: Optional[logging.handlers.MemoryHandler] = None
        self._lock = threading.Lock()
        
        self._setup_logging()
        self._cleanup_old_logs()
    
    def _setup_logging(self):
        """Set up the logging infrastructure."""
        # Create logs directory if it doesn't exist
        log_dir = Path(self.log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up root logger
        root_logger = logging.getLogger('sentinel')
        root_logger.setLevel(getattr(logging, self.log_level.upper()))
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Set up file handler with rotation
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file_path,
                maxBytes=self.max_file_size_mb * 1024 * 1024,
                backupCount=self.max_files,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)
        
        # Set up console handler if enabled
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # Set up memory handler for UI display (keeps last 1000 records)
        self._memory_handler = logging.handlers.MemoryHandler(
            capacity=1000,
            target=None  # We'll retrieve records manually
        )
        self._memory_handler.setFormatter(formatter)
        root_logger.addHandler(self._memory_handler)
        
        # Log initialization
        logger = self.get_logger('logger_manager')
        logger.info(f"Logging system initialized - Level: {self.log_level}, File: {self.log_file_path}")
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger with the given name."""
        full_name = f'sentinel.{name}'
        
        with self._lock:
            if full_name not in self._loggers:
                logger = logging.getLogger(full_name)
                self._loggers[full_name] = logger
            return self._loggers[full_name]
    
    def set_log_level(self, level: str):
        """Change the logging level for all loggers."""
        try:
            log_level = getattr(logging, level.upper())
            logging.getLogger('sentinel').setLevel(log_level)
            self.log_level = level.upper()
            
            logger = self.get_logger('logger_manager')
            logger.info(f"Log level changed to {level.upper()}")
        except AttributeError:
            logger = self.get_logger('logger_manager')
            logger.error(f"Invalid log level: {level}")
    
    def rotate_logs(self):
        """Manually trigger log rotation."""
        root_logger = logging.getLogger('sentinel')
        for handler in root_logger.handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                handler.doRollover()
                logger = self.get_logger('logger_manager')
                logger.info("Manual log rotation triggered")
                break
    
    def cleanup_old_logs(self):
        """Clean up log files older than the configured number of days."""
        self._cleanup_old_logs()
    
    def _cleanup_old_logs(self):
        """Internal method to clean up old log files."""
        try:
            log_dir = Path(self.log_file_path).parent
            cutoff_date = datetime.now() - timedelta(days=self.cleanup_days)
            
            # Find all log files in the directory
            log_pattern = str(log_dir / "*.log*")
            old_files = []
            
            for log_file in glob.glob(log_pattern):
                file_path = Path(log_file)
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    old_files.append(file_path)
            
            # Delete old files
            for old_file in old_files:
                try:
                    old_file.unlink()
                except OSError:
                    pass  # Ignore errors when deleting old files
            
            if old_files:
                logger = self.get_logger('logger_manager')
                logger.info(f"Cleaned up {len(old_files)} old log files")
                
        except Exception as e:
            # Don't let cleanup errors break the application
            print(f"Warning: Log cleanup failed: {e}", file=sys.stderr)
    
    def get_recent_logs(self, count: int = 100) -> List[LogEntry]:
        """Get recent log entries for UI display."""
        if not self._memory_handler:
            return []
        
        entries = []
        try:
            # Get records from memory handler
            records = self._memory_handler.buffer[-count:] if self._memory_handler.buffer else []
            
            for record in records:
                entry = LogEntry(
                    timestamp=datetime.fromtimestamp(record.created),
                    level=record.levelname,
                    logger_name=record.name,
                    message=record.getMessage(),
                    module=record.module,
                    function=record.funcName,
                    line_number=record.lineno,
                    exception_info=record.exc_text if hasattr(record, 'exc_text') else None
                )
                entries.append(entry)
                
        except Exception as e:
            # Fallback if memory handler fails
            logger = self.get_logger('logger_manager')
            logger.error(f"Failed to retrieve recent logs: {e}")
        
        return entries
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics for debug UI."""
        stats = {
            'current_level': self.log_level,
            'log_file_path': self.log_file_path,
            'total_loggers': len(self._loggers),
            'memory_buffer_size': len(self._memory_handler.buffer) if self._memory_handler else 0,
            'log_file_exists': Path(self.log_file_path).exists(),
            'log_file_size_mb': 0
        }
        
        try:
            if Path(self.log_file_path).exists():
                stats['log_file_size_mb'] = Path(self.log_file_path).stat().st_size / (1024 * 1024)
        except OSError:
            pass
        
        return stats