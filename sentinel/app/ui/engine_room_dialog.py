#!/usr/bin/env python3
"""
Sentinel 2.0 - Engine Room Dashboard
The revolutionary transparency UI that shows users exactly how their system works
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QWidget, QScrollArea,
    QProgressBar, QTextEdit, QComboBox, QLineEdit,
    QSplitter, QTabWidget, QFrame
)
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

# Add sentinel to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


@dataclass
class WorkerMetrics:
    """Real-time metrics for a worker process."""
    worker_id: str
    worker_type: str  # 'GPU', 'CPU'
    status: str  # 'idle', 'processing', 'waiting', 'error'
    current_batch_size: int
    max_batch_size: int
    files_per_second: float
    gpu_utilization: Optional[float] = None
    cpu_utilization: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    error_message: Optional[str] = None
    last_updated: float = 0.0


@dataclass
class SystemMetrics:
    """Overall system performance metrics."""
    total_throughput: float
    active_workers: int
    total_workers: int
    queue_size: int
    errors_count: int
    files_processed: int
    total_files: int
    estimated_completion: str
    current_bottleneck: str


class WorkerCard(QWidget):
    """Individual worker process visualization card."""
    
    def __init__(self, worker_id: str, parent=None):
        super().__init__(parent)
        self.worker_id = worker_id
        self.current_metrics: Optional[WorkerMetrics] = None
        
        self.setup_ui()
        self.setFixedSize(200, 150)
    
    def setup_ui(self):
        """Setup the worker card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Worker header
        self.header_label = QLabel(self.worker_id)
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(10)
        self.header_label.setFont(header_font)
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.header_label)
        
        # Status indicator
        self.status_label = QLabel("🔄 Initializing")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Batch progress
        batch_layout = QHBoxLayout()
        batch_layout.addWidget(QLabel("Batch:"))
        self.batch_label = QLabel("0/0")
        batch_layout.addWidget(self.batch_label)
        batch_layout.addStretch()
        layout.addLayout(batch_layout)
        
        # Performance metrics
        perf_layout = QHBoxLayout()
        perf_layout.addWidget(QLabel("Speed:"))
        self.speed_label = QLabel("0 fps")
        perf_layout.addWidget(self.speed_label)
        perf_layout.addStretch()
        layout.addLayout(perf_layout)
        
        # Resource utilization
        self.resource_label = QLabel("CPU: 0%")
        self.resource_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.resource_label)
        
        # Error indicator (initially hidden)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #F44336; font-size: 9px;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        
        layout.addStretch()
        
        # Set initial style
        self.update_style("idle")
    
    def update_metrics(self, metrics: WorkerMetrics):
        """Update the worker card with new metrics."""
        self.current_metrics = metrics
        
        # Update header
        self.header_label.setText(f"{metrics.worker_type}-{metrics.worker_id}")
        
        # Update status
        status_icons = {
            'idle': '🟡 Idle',
            'processing': '🟢 Processing',
            'waiting': '🟡 Waiting',
            'error': '🔴 Error'
        }
        self.status_label.setText(status_icons.get(metrics.status, '❓ Unknown'))
        
        # Update batch info
        self.batch_label.setText(f"{metrics.current_batch_size}/{metrics.max_batch_size}")
        
        # Update speed
        self.speed_label.setText(f"{metrics.files_per_second:.0f} fps")
        
        # Update resource utilization
        if metrics.worker_type == 'GPU' and metrics.gpu_utilization is not None:
            self.resource_label.setText(f"GPU: {metrics.gpu_utilization:.0f}%")
        elif metrics.cpu_utilization is not None:
            self.resource_label.setText(f"CPU: {metrics.cpu_utilization:.0f}%")
        else:
            self.resource_label.setText("Resource: N/A")
        
        # Update error message
        if metrics.error_message:
            self.error_label.setText(f"Error: {metrics.error_message}")
            self.error_label.setVisible(True)
        else:
            self.error_label.setVisible(False)
        
        # Update visual style
        self.update_style(metrics.status)
    
    def update_style(self, status: str):
        """Update the visual style based on worker status."""
        style_map = {
            'idle': {
                'background': '#FFF3E0',
                'border': '#FF9800'
            },
            'processing': {
                'background': '#E8F5E8',
                'border': '#4CAF50'
            },
            'waiting': {
                'background': '#FFF8E1',
                'border': '#FFC107'
            },
            'error': {
                'background': '#FFEBEE',
                'border': '#F44336'
            }
        }
        
        style = style_map.get(status, style_map['idle'])
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {style['background']};
                border: 2px solid {style['border']};
                border-radius: 8px;
            }}
        """)


class SystemStatsWidget(QWidget):
    """Widget showing overall system performance statistics."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the system stats UI."""
        layout = QGridLayout(self)
        
        # Create stat labels
        self.stats_labels = {}
        
        stats = [
            ('throughput', 'Total Throughput:', '0 files/sec'),
            ('workers', 'Active Workers:', '0/0'),
            ('queue', 'Queue Size:', '0 files'),
            ('errors', 'Errors:', '0'),
            ('progress', 'Progress:', '0/0 files'),
            ('eta', 'ETA:', 'Calculating...'),
            ('bottleneck', 'Bottleneck:', 'None')
        ]
        
        for i, (key, label_text, default_value) in enumerate(stats):
            row = i // 2
            col = (i % 2) * 2
            
            # Label
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold;")
            layout.addWidget(label, row, col)
            
            # Value
            value_label = QLabel(default_value)
            self.stats_labels[key] = value_label
            layout.addWidget(value_label, row, col + 1)
    
    def update_stats(self, metrics: SystemMetrics):
        """Update system statistics."""
        self.stats_labels['throughput'].setText(f"{metrics.total_throughput:.1f} files/sec")
        self.stats_labels['workers'].setText(f"{metrics.active_workers}/{metrics.total_workers}")
        self.stats_labels['queue'].setText(f"{metrics.queue_size:,} files")
        self.stats_labels['errors'].setText(str(metrics.errors_count))
        self.stats_labels['progress'].setText(f"{metrics.files_processed:,}/{metrics.total_files:,} files")
        self.stats_labels['eta'].setText(metrics.estimated_completion)
        self.stats_labels['bottleneck'].setText(metrics.current_bottleneck)
        
        # Color code bottleneck
        bottleneck_colors = {
            'None': '#4CAF50',
            'CPU': '#FF9800',
            'GPU': '#F44336',
            'Memory': '#9C27B0',
            'Storage': '#607D8B'
        }
        
        color = bottleneck_colors.get(metrics.current_bottleneck, '#666666')
        self.stats_labels['bottleneck'].setStyleSheet(f"color: {color}; font-weight: bold;")


class LogViewerWidget(QWidget):
    """Advanced log viewer with filtering and search capabilities."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_entries: List[Dict[str, Any]] = []
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the log viewer UI."""
        layout = QVBoxLayout(self)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        
        # Worker filter
        filter_layout.addWidget(QLabel("Worker:"))
        self.worker_filter = QComboBox()
        self.worker_filter.addItem("All")
        self.worker_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.worker_filter)
        
        # Level filter
        filter_layout.addWidget(QLabel("Level:"))
        self.level_filter = QComboBox()
        self.level_filter.addItems(["All", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.level_filter)
        
        # Search
        filter_layout.addWidget(QLabel("🔍 Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search logs...")
        self.search_input.textChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.search_input)
        
        filter_layout.addStretch()
        
        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_logs)
        filter_layout.addWidget(clear_btn)
        
        layout.addLayout(filter_layout)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_display)
        
        # Auto-scroll checkbox
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        
        # Export button
        export_btn = QPushButton("Export Logs")
        export_btn.clicked.connect(self.export_logs)
        controls_layout.addWidget(export_btn)
        
        layout.addLayout(controls_layout)
    
    def add_log_entry(self, timestamp: str, worker_id: str, level: str, message: str):
        """Add a new log entry."""
        entry = {
            'timestamp': timestamp,
            'worker_id': worker_id,
            'level': level,
            'message': message
        }
        
        self.log_entries.append(entry)
        
        # Update worker filter if new worker
        if worker_id not in [self.worker_filter.itemText(i) for i in range(self.worker_filter.count())]:
            self.worker_filter.addItem(worker_id)
        
        # Keep only last 1000 entries
        if len(self.log_entries) > 1000:
            self.log_entries = self.log_entries[-1000:]
        
        self.apply_filters()
    
    def apply_filters(self):
        """Apply current filters to log display."""
        worker_filter = self.worker_filter.currentText()
        level_filter = self.level_filter.currentText()
        search_text = self.search_input.text().lower()
        
        filtered_entries = []
        
        for entry in self.log_entries:
            # Worker filter
            if worker_filter != "All" and entry['worker_id'] != worker_filter:
                continue
            
            # Level filter
            if level_filter != "All" and entry['level'] != level_filter:
                continue
            
            # Search filter
            if search_text and search_text not in entry['message'].lower():
                continue
            
            filtered_entries.append(entry)
        
        # Update display
        self.update_display(filtered_entries)
    
    def update_display(self, entries: List[Dict[str, Any]]):
        """Update the log display with filtered entries."""
        self.log_display.clear()
        
        for entry in entries[-100:]:  # Show last 100 entries
            level_colors = {
                'DEBUG': '#666666',
                'INFO': '#2196F3',
                'WARNING': '#FF9800',
                'ERROR': '#F44336'
            }
            
            color = level_colors.get(entry['level'], '#000000')
            
            formatted_entry = (
                f"<span style='color: #888888'>{entry['timestamp']}</span> "
                f"<span style='color: #4CAF50'>{entry['worker_id']}</span> "
                f"<span style='color: {color}; font-weight: bold'>{entry['level']}</span> "
                f"<span>{entry['message']}</span>"
            )
            
            self.log_display.append(formatted_entry)
        
        # Auto-scroll to bottom
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_logs(self):
        """Clear all log entries."""
        self.log_entries.clear()
        self.log_display.clear()
    
    def export_logs(self):
        """Export logs to file."""
        # TODO: Implement log export functionality
        pass


class EngineRoomDialog(QDialog):
    """
    The revolutionary Engine Room dashboard that provides complete transparency
    into the Sentinel 2.0 processing system.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker_cards: Dict[str, WorkerCard] = {}
        self.update_timer = QTimer()
        self.mock_data_enabled = True  # For demonstration
        
        self.setup_ui()
        self.setup_mock_data()
        self.start_updates()
    
    def setup_ui(self):
        """Setup the complete Engine Room UI."""
        self.setWindowTitle("🔧 Engine Room - Sentinel 2.0")
        self.setModal(False)  # Allow interaction with main window
        self.resize(1200, 800)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("🔧 Engine Room")
        header_font = QFont()
        header_font.setPointSize(18)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header_label)
        
        # Create tabbed interface
        tab_widget = QTabWidget()
        
        # Workers tab
        workers_tab = self.create_workers_tab()
        tab_widget.addTab(workers_tab, "👥 Workers")
        
        # System stats tab
        stats_tab = self.create_stats_tab()
        tab_widget.addTab(stats_tab, "📊 System Stats")
        
        # Logs tab
        logs_tab = self.create_logs_tab()
        tab_widget.addTab(logs_tab, "📋 Logs")
        
        main_layout.addWidget(tab_widget)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        # Mock data toggle (for demo)
        self.mock_toggle = QPushButton("🎭 Toggle Mock Data")
        self.mock_toggle.clicked.connect(self.toggle_mock_data)
        button_layout.addWidget(self.mock_toggle)
        
        button_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
    
    def create_workers_tab(self) -> QWidget:
        """Create the workers visualization tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # System overview
        self.system_stats = SystemStatsWidget()
        layout.addWidget(self.system_stats)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Workers grid
        workers_group = QGroupBox("Worker Processes")
        workers_layout = QVBoxLayout(workers_group)
        
        # Scrollable area for worker cards
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.workers_grid = QGridLayout(scroll_widget)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(300)
        
        workers_layout.addWidget(scroll_area)
        layout.addWidget(workers_group)
        
        return tab
    
    def create_stats_tab(self) -> QWidget:
        """Create the system statistics tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Detailed system metrics would go here
        # For now, show a placeholder
        placeholder = QLabel("📊 Detailed system statistics and performance charts will be displayed here.")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #666666; font-style: italic; padding: 50px;")
        layout.addWidget(placeholder)
        
        return tab
    
    def create_logs_tab(self) -> QWidget:
        """Create the logs viewer tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.log_viewer = LogViewerWidget()
        layout.addWidget(self.log_viewer)
        
        return tab
    
    def setup_mock_data(self):
        """Setup mock data for demonstration."""
        # Create mock worker cards
        worker_configs = [
            ('GPU-Worker-1', 'GPU'),
            ('GPU-Worker-2', 'GPU'),
            ('CPU-Worker-1', 'CPU'),
            ('CPU-Worker-2', 'CPU'),
            ('CPU-Worker-3', 'CPU'),
            ('CPU-Worker-4', 'CPU')
        ]
        
        for i, (worker_id, worker_type) in enumerate(worker_configs):
            card = WorkerCard(worker_id)
            self.worker_cards[worker_id] = card
            
            # Add to grid (3 columns)
            row = i // 3
            col = i % 3
            self.workers_grid.addWidget(card, row, col)
    
    def start_updates(self):
        """Start the real-time update timer."""
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # Update every second
    
    def update_display(self):
        """Update the entire display with current data."""
        if self.mock_data_enabled:
            self.update_mock_data()
    
    def update_mock_data(self):
        """Update with mock data for demonstration."""
        import random
        import time
        
        # Mock worker metrics
        statuses = ['idle', 'processing', 'waiting']
        
        total_throughput = 0
        active_workers = 0
        
        for worker_id, card in self.worker_cards.items():
            worker_type = 'GPU' if 'GPU' in worker_id else 'CPU'
            status = random.choice(statuses)
            
            if status == 'processing':
                active_workers += 1
            
            # Generate realistic metrics
            if worker_type == 'GPU':
                fps = random.uniform(80, 150) if status == 'processing' else 0
                gpu_util = random.uniform(70, 95) if status == 'processing' else random.uniform(5, 20)
                batch_size = random.randint(45, 64) if status == 'processing' else 0
                max_batch = 64
            else:
                fps = random.uniform(25, 45) if status == 'processing' else 0
                gpu_util = None
                cpu_util = random.uniform(60, 85) if status == 'processing' else random.uniform(5, 15)
                batch_size = random.randint(20, 32) if status == 'processing' else 0
                max_batch = 32
            
            total_throughput += fps
            
            metrics = WorkerMetrics(
                worker_id=worker_id.split('-')[-1],
                worker_type=worker_type,
                status=status,
                current_batch_size=batch_size,
                max_batch_size=max_batch,
                files_per_second=fps,
                gpu_utilization=gpu_util,
                cpu_utilization=cpu_util if worker_type == 'CPU' else None,
                memory_usage_mb=random.uniform(500, 1500),
                last_updated=time.time()
            )
            
            card.update_metrics(metrics)
        
        # Update system stats
        system_metrics = SystemMetrics(
            total_throughput=total_throughput,
            active_workers=active_workers,
            total_workers=len(self.worker_cards),
            queue_size=random.randint(50, 500),
            errors_count=random.randint(0, 3),
            files_processed=random.randint(1000, 5000),
            total_files=10000,
            estimated_completion=f"{random.randint(2, 8)} minutes",
            current_bottleneck=random.choice(['None', 'CPU', 'GPU Memory', 'Storage'])
        )
        
        self.system_stats.update_stats(system_metrics)
        
        # Add mock log entries occasionally
        if random.random() < 0.3:  # 30% chance each update
            worker_id = random.choice(list(self.worker_cards.keys()))
            level = random.choice(['INFO', 'DEBUG', 'WARNING'])
            messages = [
                "Processed batch of 32 files",
                "GPU memory usage at 78%",
                "Batch processing completed",
                "Worker ready for next batch",
                "Performance optimization applied"
            ]
            message = random.choice(messages)
            
            timestamp = time.strftime("%H:%M:%S")
            self.log_viewer.add_log_entry(timestamp, worker_id, level, message)
    
    def toggle_mock_data(self):
        """Toggle mock data generation."""
        self.mock_data_enabled = not self.mock_data_enabled
        
        if self.mock_data_enabled:
            self.mock_toggle.setText("🎭 Disable Mock Data")
        else:
            self.mock_toggle.setText("🎭 Enable Mock Data")
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        self.update_timer.stop()
        super().closeEvent(event)