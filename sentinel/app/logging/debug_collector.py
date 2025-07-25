"""Debug information collection for Sentinel application."""

import platform
import sys
import os
import psutil
import sqlite3
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import json
import traceback


class DebugInfoCollector:
    """Collects system information and application state for debugging."""
    
    def __init__(self, config: Dict[str, Any], logger_manager=None, performance_monitor=None):
        """Initialize the debug info collector."""
        self.config = config
        self.logger_manager = logger_manager
        self.performance_monitor = performance_monitor
        
        if self.logger_manager:
            self.logger = self.logger_manager.get_logger('debug_collector')
    
    def collect_system_info(self) -> Dict[str, Any]:
        """Collect system information for debugging."""
        try:
            system_info = {
                'platform': {
                    'system': platform.system(),
                    'release': platform.release(),
                    'version': platform.version(),
                    'machine': platform.machine(),
                    'processor': platform.processor(),
                    'architecture': platform.architecture(),
                    'python_version': sys.version,
                    'python_executable': sys.executable
                },
                'hardware': {
                    'cpu_count': psutil.cpu_count(),
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                    'memory_available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': {}
                },
                'environment': {
                    'working_directory': os.getcwd(),
                    'python_path': sys.path[:5],  # First 5 entries to avoid clutter
                    'environment_variables': {
                        key: value for key, value in os.environ.items() 
                        if key.startswith(('SENTINEL_', 'PYTHON', 'PATH'))
                    }
                }
            }
            
            # Get disk usage for current directory
            try:
                disk_usage = psutil.disk_usage('.')
                system_info['hardware']['disk_usage'] = {
                    'total_gb': round(disk_usage.total / (1024**3), 2),
                    'used_gb': round(disk_usage.used / (1024**3), 2),
                    'free_gb': round(disk_usage.free / (1024**3), 2),
                    'percent': round((disk_usage.used / disk_usage.total) * 100, 1)
                }
            except Exception:
                system_info['hardware']['disk_usage'] = {'error': 'Unable to retrieve disk usage'}
            
            return system_info
            
        except Exception as e:
            error_info = {
                'error': f"Failed to collect system info: {str(e)}",
                'traceback': traceback.format_exc()
            }
            if self.logger_manager:
                self.logger.error(f"System info collection failed: {e}")
            return error_info
    
    def collect_app_state(self) -> Dict[str, Any]:
        """Collect application state information."""
        try:
            app_state = {
                'configuration': {
                    'ai_backend_mode': self.config.get('ai_backend_mode', 'unknown'),
                    'database_path': self.config.get('database_path', 'unknown'),
                    'default_scan_directory': self.config.get('default_scan_directory', 'unknown'),
                    'logging_config': self.config.get('logging', {})
                },
                'file_system': {
                    'config_file_exists': Path('sentinel/config/config.yaml').exists(),
                    'database_exists': Path(self.config.get('database_path', 'sentinel.db')).exists(),
                    'logs_directory_exists': Path('logs').exists(),
                    'current_log_files': []
                },
                'application': {
                    'startup_time': datetime.now().isoformat(),
                    'process_id': os.getpid(),
                    'working_directory': os.getcwd()
                }
            }
            
            # Check for log files
            try:
                logs_dir = Path('logs')
                if logs_dir.exists():
                    log_files = list(logs_dir.glob('*.log*'))
                    app_state['file_system']['current_log_files'] = [
                        {
                            'name': f.name,
                            'size_mb': round(f.stat().st_size / (1024**2), 2),
                            'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                        }
                        for f in log_files
                    ]
            except Exception:
                app_state['file_system']['current_log_files'] = ['Error reading log directory']
            
            # Add logging statistics if available
            if self.logger_manager:
                app_state['logging'] = self.logger_manager.get_log_stats()
            
            # Add performance metrics if available
            if self.performance_monitor:
                app_state['performance'] = self.performance_monitor.get_metrics()
            
            return app_state
            
        except Exception as e:
            error_info = {
                'error': f"Failed to collect app state: {str(e)}",
                'traceback': traceback.format_exc()
            }
            if self.logger_manager:
                self.logger.error(f"App state collection failed: {e}")
            return error_info
    
    def test_ai_connectivity(self) -> Dict[str, Any]:
        """Test connectivity to the AI backend."""
        ai_config = self.config.get('ai_backend_mode', 'local')
        
        if ai_config == 'local':
            return self._test_local_ai_connectivity()
        else:
            return self._test_cloud_ai_connectivity()
    
    def _test_local_ai_connectivity(self) -> Dict[str, Any]:
        """Test local AI backend connectivity (Ollama)."""
        test_result = {
            'backend_type': 'local',
            'endpoint': 'http://127.0.0.1:11434',
            'status': 'unknown',
            'response_time_ms': None,
            'error': None,
            'model_info': None
        }
        
        try:
            start_time = datetime.now()
            
            # Test basic connectivity
            response = requests.get('http://127.0.0.1:11434/api/tags', timeout=5)
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                test_result['status'] = 'connected'
                test_result['response_time_ms'] = round(response_time, 2)
                
                # Get model information
                try:
                    models_data = response.json()
                    test_result['model_info'] = {
                        'available_models': [model.get('name', 'unknown') for model in models_data.get('models', [])],
                        'model_count': len(models_data.get('models', []))
                    }
                except Exception:
                    test_result['model_info'] = {'error': 'Could not parse model information'}
            else:
                test_result['status'] = 'error'
                test_result['error'] = f"HTTP {response.status_code}: {response.text}"
                
        except requests.exceptions.ConnectionError:
            test_result['status'] = 'connection_refused'
            test_result['error'] = 'Connection refused - Ollama server may not be running'
        except requests.exceptions.Timeout:
            test_result['status'] = 'timeout'
            test_result['error'] = 'Request timed out after 5 seconds'
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
        
        if self.logger_manager:
            self.logger.info(f"AI connectivity test: {test_result['status']}")
        
        return test_result
    
    def _test_cloud_ai_connectivity(self) -> Dict[str, Any]:
        """Test cloud AI backend connectivity."""
        test_result = {
            'backend_type': 'cloud',
            'endpoint': self.config.get('cloud_endpoint', 'not_configured'),
            'status': 'unknown',
            'response_time_ms': None,
            'error': None
        }
        
        cloud_endpoint = self.config.get('cloud_endpoint')
        cloud_api_key = self.config.get('cloud_api_key')
        
        if not cloud_endpoint:
            test_result['status'] = 'not_configured'
            test_result['error'] = 'Cloud endpoint not configured'
            return test_result
        
        try:
            start_time = datetime.now()
            headers = {'Authorization': f'Bearer {cloud_api_key}'} if cloud_api_key else {}
            
            # Simple connectivity test
            response = requests.get(cloud_endpoint, headers=headers, timeout=10)
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            test_result['response_time_ms'] = round(response_time, 2)
            
            if response.status_code == 200:
                test_result['status'] = 'connected'
            else:
                test_result['status'] = 'error'
                test_result['error'] = f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
        
        if self.logger_manager:
            self.logger.info(f"Cloud AI connectivity test: {test_result['status']}")
        
        return test_result
    
    def test_database_connectivity(self) -> Dict[str, Any]:
        """Test database connectivity and basic operations."""
        db_path = self.config.get('database_path', 'sentinel.db')
        
        test_result = {
            'database_path': db_path,
            'status': 'unknown',
            'file_exists': False,
            'file_size_mb': 0,
            'connection_test': False,
            'table_count': 0,
            'error': None
        }
        
        try:
            # Check if database file exists
            db_file = Path(db_path)
            test_result['file_exists'] = db_file.exists()
            
            if db_file.exists():
                test_result['file_size_mb'] = round(db_file.stat().st_size / (1024**2), 3)
            
            # Test database connection
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Test basic query
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                test_result['table_count'] = len(tables)
                test_result['connection_test'] = True
                test_result['status'] = 'connected'
                
                # Get table information
                test_result['tables'] = [table[0] for table in tables]
                
        except sqlite3.Error as e:
            test_result['status'] = 'error'
            test_result['error'] = f"SQLite error: {str(e)}"
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
        
        if self.logger_manager:
            self.logger.info(f"Database connectivity test: {test_result['status']}")
        
        return test_result
    
    def generate_debug_report(self) -> str:
        """Generate a comprehensive debug report."""
        try:
            report_data = {
                'report_generated': datetime.now().isoformat(),
                'system_info': self.collect_system_info(),
                'application_state': self.collect_app_state(),
                'ai_connectivity': self.test_ai_connectivity(),
                'database_connectivity': self.test_database_connectivity()
            }
            
            # Add recent logs if available
            if self.logger_manager:
                recent_logs = self.logger_manager.get_recent_logs(50)
                report_data['recent_logs'] = [
                    {
                        'timestamp': log.timestamp.isoformat(),
                        'level': log.level,
                        'logger': log.logger_name,
                        'message': log.message,
                        'location': f"{log.module}:{log.line_number}:{log.function}"
                    }
                    for log in recent_logs
                ]
            
            # Format as JSON for easy reading
            report_json = json.dumps(report_data, indent=2, default=str)
            
            if self.logger_manager:
                self.logger.info("Debug report generated successfully")
            
            return report_json
            
        except Exception as e:
            error_report = {
                'error': f"Failed to generate debug report: {str(e)}",
                'traceback': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            }
            
            if self.logger_manager:
                self.logger.error(f"Debug report generation failed: {e}")
            
            return json.dumps(error_report, indent=2)