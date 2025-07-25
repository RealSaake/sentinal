"""Debug dialog for viewing logs and system information."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTextEdit, 
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QScrollArea, QWidget, QSplitter, QHeaderView, QFileDialog,
    QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from datetime import datetime
from pathlib import Path
import json


class DebugDialog(QDialog):
    """Dialog for displaying debug information, logs, and system status."""
    
    def __init__(self, logger_manager=None, performance_monitor=None, debug_collector=None, parent=None):
        super().__init__(parent)
        self.logger_manager = logger_manager
        self.performance_monitor = performance_monitor
        self.debug_collector = debug_collector
        
        self.setWindowTitle("Sentinel - Debug Information")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        self.setup_ui()
        self.setup_auto_refresh()
        self.refresh_all_data()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_logs_tab()
        self.create_system_status_tab()
        self.create_performance_tab()
        self.create_system_info_tab()
        
        # Create bottom buttons
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh All")
        self.refresh_button.clicked.connect(self.refresh_all_data)
        button_layout.addWidget(self.refresh_button)
        
        self.export_button = QPushButton("Export Debug Report")
        self.export_button.clicked.connect(self.export_debug_report)
        button_layout.addWidget(self.export_button)
        
        self.auto_refresh_button = QPushButton("Auto Refresh: ON")
        self.auto_refresh_button.clicked.connect(self.toggle_auto_refresh)
        button_layout.addWidget(self.auto_refresh_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
    
    def create_logs_tab(self):
        """Create the logs viewing tab."""
        logs_widget = QWidget()
        layout = QVBoxLayout(logs_widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.log_count_label = QLabel("Showing last 100 entries")
        controls_layout.addWidget(self.log_count_label)
        
        controls_layout.addStretch()
        
        clear_logs_button = QPushButton("Clear Display")
        clear_logs_button.clicked.connect(self.clear_log_display)
        controls_layout.addWidget(clear_logs_button)
        
        layout.addLayout(controls_layout)
        
        # Log display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)
        
        self.tab_widget.addTab(logs_widget, "📋 Logs")
    
    def create_system_status_tab(self):
        """Create the system status tab."""
        status_widget = QWidget()
        layout = QVBoxLayout(status_widget)
        
        # Status indicators
        self.status_table = QTableWidget(0, 3)
        self.status_table.setHorizontalHeaderLabels(["Component", "Status", "Details"])
        self.status_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.status_table)
        
        self.tab_widget.addTab(status_widget, "🔍 System Status")
    
    def create_performance_tab(self):
        """Create the performance metrics tab."""
        perf_widget = QWidget()
        layout = QVBoxLayout(perf_widget)
        
        # Performance metrics table
        self.perf_table = QTableWidget(0, 6)
        self.perf_table.setHorizontalHeaderLabels([
            "Operation", "Total Calls", "Avg Duration (s)", 
            "Success Rate (%)", "24h Calls", "Recent Errors"
        ])
        self.perf_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.perf_table)
        
        self.tab_widget.addTab(perf_widget, "📊 Performance")
    
    def create_system_info_tab(self):
        """Create the system information tab."""
        info_widget = QWidget()
        layout = QVBoxLayout(info_widget)
        
        # System info display
        self.system_info_text = QTextEdit()
        self.system_info_text.setReadOnly(True)
        self.system_info_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.system_info_text)
        
        self.tab_widget.addTab(info_widget, "💻 System Info")
    
    def setup_auto_refresh(self):
        """Set up automatic refresh timer."""
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.refresh_all_data)
        self.auto_refresh_enabled = True
        self.auto_refresh_timer.start(5000)  # Refresh every 5 seconds
    
    def toggle_auto_refresh(self):
        """Toggle automatic refresh on/off."""
        if self.auto_refresh_enabled:
            self.auto_refresh_timer.stop()
            self.auto_refresh_enabled = False
            self.auto_refresh_button.setText("Auto Refresh: OFF")
        else:
            self.auto_refresh_timer.start(5000)
            self.auto_refresh_enabled = True
            self.auto_refresh_button.setText("Auto Refresh: ON")
    
    def refresh_all_data(self):
        """Refresh all displayed data."""
        self.refresh_logs()
        self.refresh_system_status()
        self.refresh_performance_metrics()
        self.refresh_system_info()
    
    def refresh_logs(self):
        """Refresh the logs display."""
        if not self.logger_manager:
            self.log_text.setText("Logger manager not available")
            return
        
        try:
            recent_logs = self.logger_manager.get_recent_logs(100)
            
            log_text = ""
            for log_entry in recent_logs:
                timestamp = log_entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                log_line = f"{timestamp} - {log_entry.level} - {log_entry.logger_name} - {log_entry.message}\n"
                log_text += log_line
            
            self.log_text.setText(log_text)
            
            # Scroll to bottom
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)
            
            self.log_count_label.setText(f"Showing last {len(recent_logs)} entries")
            
        except Exception as e:
            self.log_text.setText(f"Error loading logs: {e}")
    
    def refresh_system_status(self):
        """Refresh the system status display."""
        if not self.debug_collector:
            self.status_table.setRowCount(1)
            self.status_table.setItem(0, 0, QTableWidgetItem("Debug Collector"))
            self.status_table.setItem(0, 1, QTableWidgetItem("❌ Not Available"))
            self.status_table.setItem(0, 2, QTableWidgetItem("Debug collector not initialized"))
            return
        
        try:
            # Test AI connectivity
            ai_status = self.debug_collector.test_ai_connectivity()
            
            # Test database connectivity
            db_status = self.debug_collector.test_database_connectivity()
            
            # Get application state
            app_state = self.debug_collector.collect_app_state()
            
            # Clear and populate table
            self.status_table.setRowCount(0)
            
            # AI Backend Status
            ai_icon = "✅" if ai_status['status'] == 'connected' else "❌"
            ai_details = f"Response time: {ai_status.get('response_time_ms', 'N/A')}ms"
            if ai_status.get('error'):
                ai_details += f" | Error: {ai_status['error']}"
            
            self.add_status_row("AI Backend", f"{ai_icon} {ai_status['status'].title()}", ai_details)
            
            # Database Status
            db_icon = "✅" if db_status['status'] == 'connected' else "❌"
            db_details = f"Tables: {db_status.get('table_count', 0)} | Size: {db_status.get('file_size_mb', 0):.2f}MB"
            if db_status.get('error'):
                db_details += f" | Error: {db_status['error']}"
            
            self.add_status_row("Database", f"{db_icon} {db_status['status'].title()}", db_details)
            
            # Logging System
            if self.logger_manager:
                log_stats = self.logger_manager.get_log_stats()
                log_details = f"Level: {log_stats['current_level']} | Loggers: {log_stats['total_loggers']}"
                self.add_status_row("Logging System", "✅ Active", log_details)
            
            # Performance Monitoring
            if self.performance_monitor:
                metrics = self.performance_monitor.get_metrics()
                active_ops = self.performance_monitor.get_active_operations()
                perf_details = f"Tracked operations: {len(metrics)} | Active: {len(active_ops)}"
                self.add_status_row("Performance Monitor", "✅ Active", perf_details)
            
        except Exception as e:
            self.add_status_row("System Status", "❌ Error", f"Failed to collect status: {e}")
    
    def add_status_row(self, component, status, details):
        """Add a row to the status table."""
        row = self.status_table.rowCount()
        self.status_table.insertRow(row)
        self.status_table.setItem(row, 0, QTableWidgetItem(component))
        self.status_table.setItem(row, 1, QTableWidgetItem(status))
        self.status_table.setItem(row, 2, QTableWidgetItem(details))
    
    def refresh_performance_metrics(self):
        """Refresh the performance metrics display."""
        if not self.performance_monitor:
            self.perf_table.setRowCount(1)
            self.perf_table.setItem(0, 0, QTableWidgetItem("Performance Monitor"))
            self.perf_table.setItem(0, 1, QTableWidgetItem("Not Available"))
            return
        
        try:
            metrics = self.performance_monitor.get_metrics()
            
            # Clear table
            self.perf_table.setRowCount(0)
            
            for operation_name, data in metrics.items():
                if operation_name.startswith('_'):  # Skip system metrics
                    continue
                
                row = self.perf_table.rowCount()
                self.perf_table.insertRow(row)
                
                self.perf_table.setItem(row, 0, QTableWidgetItem(operation_name))
                self.perf_table.setItem(row, 1, QTableWidgetItem(str(data['total_calls'])))
                self.perf_table.setItem(row, 2, QTableWidgetItem(f"{data['average_duration']:.3f}"))
                self.perf_table.setItem(row, 3, QTableWidgetItem(f"{data['success_rate']:.1f}"))
                self.perf_table.setItem(row, 4, QTableWidgetItem(str(data['last_24h_calls'])))
                
                # Recent errors
                error_count = len(data.get('recent_errors', []))
                error_text = f"{error_count} errors" if error_count > 0 else "None"
                self.perf_table.setItem(row, 5, QTableWidgetItem(error_text))
                
        except Exception as e:
            row = self.perf_table.rowCount()
            self.perf_table.insertRow(row)
            self.perf_table.setItem(row, 0, QTableWidgetItem("Error"))
            self.perf_table.setItem(row, 1, QTableWidgetItem(str(e)))
    
    def refresh_system_info(self):
        """Refresh the system information display."""
        if not self.debug_collector:
            self.system_info_text.setText("Debug collector not available")
            return
        
        try:
            system_info = self.debug_collector.collect_system_info()
            app_state = self.debug_collector.collect_app_state()
            
            # Format system information
            info_text = "=== SYSTEM INFORMATION ===\n\n"
            
            # Platform info
            platform = system_info.get('platform', {})
            info_text += f"System: {platform.get('system')} {platform.get('release')}\n"
            info_text += f"Architecture: {platform.get('machine')}\n"
            info_text += f"Python: {platform.get('python_version', '').split()[0]}\n\n"
            
            # Hardware info
            hardware = system_info.get('hardware', {})
            info_text += f"CPU Cores: {hardware.get('cpu_count')}\n"
            info_text += f"CPU Usage: {hardware.get('cpu_percent')}%\n"
            info_text += f"Memory: {hardware.get('memory_available_gb'):.1f}GB / {hardware.get('memory_total_gb'):.1f}GB\n"
            info_text += f"Memory Usage: {hardware.get('memory_percent')}%\n\n"
            
            # Disk usage
            disk = hardware.get('disk_usage', {})
            if disk:
                info_text += f"Disk: {disk.get('free_gb'):.1f}GB free / {disk.get('total_gb'):.1f}GB total\n"
                info_text += f"Disk Usage: {disk.get('percent')}%\n\n"
            
            # Application info
            info_text += "=== APPLICATION STATE ===\n\n"
            config = app_state.get('configuration', {})
            info_text += f"AI Backend: {config.get('ai_backend_mode')}\n"
            info_text += f"Database: {config.get('database_path')}\n"
            info_text += f"Working Directory: {app_state.get('application', {}).get('working_directory')}\n\n"
            
            # Logging info
            if 'logging' in app_state:
                logging_info = app_state['logging']
                info_text += f"Log Level: {logging_info.get('current_level')}\n"
                info_text += f"Log File: {logging_info.get('log_file_path')}\n"
                info_text += f"Log File Size: {logging_info.get('log_file_size_mb', 0):.2f}MB\n"
            
            self.system_info_text.setText(info_text)
            
        except Exception as e:
            self.system_info_text.setText(f"Error loading system information: {e}")
    
    def clear_log_display(self):
        """Clear the log display."""
        self.log_text.clear()
        self.log_count_label.setText("Log display cleared")
    
    def export_debug_report(self):
        """Export a comprehensive debug report."""
        if not self.debug_collector:
            QMessageBox.warning(self, "Export Error", "Debug collector not available")
            return
        
        try:
            # Generate debug report
            debug_report = self.debug_collector.generate_debug_report()
            
            # Ask user for save location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Debug Report",
                f"sentinel_debug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(debug_report)
                
                QMessageBox.information(
                    self, 
                    "Export Successful", 
                    f"Debug report exported to:\n{file_path}"
                )
        
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export debug report:\n{e}")
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        if self.auto_refresh_timer:
            self.auto_refresh_timer.stop()
        event.accept()