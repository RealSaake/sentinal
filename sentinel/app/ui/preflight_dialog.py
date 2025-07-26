#!/usr/bin/env python3
"""
Sentinel 2.0 - Pre-Flight Check Dialog
The revolutionary pre-flight interface that gives users full control and transparency
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QProgressBar, QGroupBox, QRadioButton,
    QSlider, QComboBox, QTextEdit, QScrollArea, QWidget,
    QButtonGroup, QSpinBox, QCheckBox, QMessageBox, QFrame
)
from PyQt6.QtGui import QFont, QPalette, QPixmap
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

# Add sentinel to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sentinel.core.preflight_check import PreFlightChecker, PreFlightResults
from sentinel.core.performance_forecaster import PerformanceStrategy


class PreFlightWorker(QThread):
    """Background worker for pre-flight check operations."""
    
    progress_updated = pyqtSignal(str, float)  # message, percentage
    check_completed = pyqtSignal(object)  # PreFlightResults
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self, target_directory: str, parent=None):
        super().__init__(parent)
        self.target_directory = target_directory
        self.checker = None
    
    def run(self):
        """Perform the pre-flight check in background."""
        try:
            self.checker = PreFlightChecker(progress_callback=self.progress_callback)
            results = self.checker.perform_preflight_check(self.target_directory)
            self.check_completed.emit(results)
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def progress_callback(self, message: str, percentage: float):
        """Progress callback for the checker."""
        self.progress_updated.emit(message, percentage)


class StrategyCard(QWidget):
    """Individual strategy selection card with visual styling."""
    
    strategy_selected = pyqtSignal(str)  # strategy name
    
    def __init__(self, strategy_name: str, strategy_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.strategy_name = strategy_name
        self.strategy_data = strategy_data
        self.is_selected = False
        
        self.setup_ui()
        self.setFixedHeight(120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def setup_ui(self):
        """Setup the strategy card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Strategy name
        name_label = QLabel(self.strategy_data['display_name'])
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(12)
        name_label.setFont(name_font)
        layout.addWidget(name_label)
        
        # Description
        desc_label = QLabel(self.strategy_data['description'])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666;")
        layout.addWidget(desc_label)
        
        # Performance info
        perf_layout = QHBoxLayout()
        
        duration_label = QLabel(f"⏱️ {self.strategy_data['duration']}")
        duration_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        perf_layout.addWidget(duration_label)
        
        speed_label = QLabel(f"🚀 {self.strategy_data['files_per_second']:.0f} fps")
        speed_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        perf_layout.addWidget(speed_label)
        
        confidence_label = QLabel(f"📊 {self.strategy_data['confidence']}")
        confidence_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        perf_layout.addWidget(confidence_label)
        
        perf_layout.addStretch()
        layout.addLayout(perf_layout)
        
        # Warning indicator
        if self.strategy_data['warning_count'] > 0:
            warning_label = QLabel(f"⚠️ {self.strategy_data['warning_count']} warnings")
            warning_label.setStyleSheet("color: #F44336; font-size: 10px;")
            layout.addWidget(warning_label)
        
        self.update_style()
    
    def update_style(self):
        """Update the visual style based on selection state."""
        if self.is_selected:
            self.setStyleSheet("""
                QWidget {
                    background-color: #E3F2FD;
                    border: 2px solid #2196F3;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: #F5F5F5;
                    border: 1px solid #CCCCCC;
                    border-radius: 8px;
                }
                QWidget:hover {
                    background-color: #EEEEEE;
                    border: 1px solid #999999;
                }
            """)
    
    def mousePressEvent(self, event):
        """Handle mouse click to select strategy."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.strategy_selected.emit(self.strategy_name)
    
    def set_selected(self, selected: bool):
        """Set the selection state."""
        self.is_selected = selected
        self.update_style()


class CustomParametersWidget(QWidget):
    """Widget for customizing strategy parameters."""
    
    parameters_changed = pyqtSignal(dict)  # parameter changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_params = {}
    
    def setup_ui(self):
        """Setup the custom parameters UI."""
        layout = QFormLayout(self)
        
        # Max Workers
        self.workers_spinbox = QSpinBox()
        self.workers_spinbox.setRange(1, 16)
        self.workers_spinbox.setValue(4)
        self.workers_spinbox.valueChanged.connect(self.on_parameters_changed)
        layout.addRow("Max Workers:", self.workers_spinbox)
        
        # Batch Size
        self.batch_slider = QSlider(Qt.Orientation.Horizontal)
        self.batch_slider.setRange(16, 256)
        self.batch_slider.setValue(64)
        self.batch_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.batch_slider.setTickInterval(32)
        self.batch_slider.valueChanged.connect(self.on_parameters_changed)
        
        self.batch_label = QLabel("64")
        batch_layout = QHBoxLayout()
        batch_layout.addWidget(self.batch_slider)
        batch_layout.addWidget(self.batch_label)
        layout.addRow("Batch Size:", batch_layout)
        
        # AI Complexity
        self.complexity_combo = QComboBox()
        self.complexity_combo.addItems(["simple", "balanced", "complex"])
        self.complexity_combo.setCurrentText("balanced")
        self.complexity_combo.currentTextChanged.connect(self.on_parameters_changed)
        layout.addRow("AI Complexity:", self.complexity_combo)
        
        # Error Handling
        self.error_combo = QComboBox()
        self.error_combo.addItems(["skip", "pause"])
        self.error_combo.setCurrentText("skip")
        self.error_combo.currentTextChanged.connect(self.on_parameters_changed)
        layout.addRow("Error Handling:", self.error_combo)
        
        # Resource Usage
        self.resource_combo = QComboBox()
        self.resource_combo.addItems(["low", "balanced", "max"])
        self.resource_combo.setCurrentText("balanced")
        self.resource_combo.currentTextChanged.connect(self.on_parameters_changed)
        layout.addRow("Resource Usage:", self.resource_combo)
        
        # Connect batch slider to label update
        self.batch_slider.valueChanged.connect(lambda v: self.batch_label.setText(str(v)))
    
    def on_parameters_changed(self):
        """Handle parameter changes."""
        self.current_params = {
            'max_workers': self.workers_spinbox.value(),
            'batch_size': self.batch_slider.value(),
            'ai_complexity': self.complexity_combo.currentText(),
            'error_handling': self.error_combo.currentText(),
            'resource_usage': self.resource_combo.currentText()
        }
        self.parameters_changed.emit(self.current_params)
    
    def update_from_strategy(self, strategy: PerformanceStrategy):
        """Update parameters from a strategy."""
        self.workers_spinbox.setValue(strategy.max_workers)
        self.batch_slider.setValue(strategy.batch_size)
        self.complexity_combo.setCurrentText(strategy.ai_complexity)
        self.error_combo.setCurrentText(strategy.error_handling)
        self.resource_combo.setCurrentText(strategy.resource_usage)
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get current parameters."""
        return self.current_params.copy()


class PreFlightDialog(QDialog):
    """
    The revolutionary Pre-Flight Check dialog that transforms the Sentinel experience.
    This is where users get full transparency and control before analysis begins.
    """
    
    analysis_approved = pyqtSignal(str, dict)  # strategy_name, custom_params
    
    def __init__(self, target_directory: str, parent=None):
        super().__init__(parent)
        self.target_directory = target_directory
        self.preflight_results: Optional[PreFlightResults] = None
        self.selected_strategy = "balanced"
        self.custom_params = {}
        
        self.setup_ui()
        self.start_preflight_check()
    
    def setup_ui(self):
        """Setup the complete pre-flight dialog UI."""
        self.setWindowTitle("Pre-Flight Analysis - Sentinel 2.0")
        self.setModal(True)
        self.resize(900, 700)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("🚀 Pre-Flight Analysis")
        header_font = QFont()
        header_font.setPointSize(18)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header_label)
        
        # Target directory info
        target_label = QLabel(f"📁 Target: {self.target_directory}")
        target_label.setStyleSheet("color: #666666; margin-bottom: 10px;")
        main_layout.addWidget(target_label)
        
        # Progress section (initially visible)
        self.progress_widget = self.create_progress_widget()
        main_layout.addWidget(self.progress_widget)
        
        # Results section (initially hidden)
        self.results_widget = self.create_results_widget()
        self.results_widget.setVisible(False)
        main_layout.addWidget(self.results_widget)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        
        self.start_button = QPushButton("🚀 Start Analysis")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.approve_analysis)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        button_layout.addWidget(self.start_button)
        
        main_layout.addLayout(button_layout)
    
    def create_progress_widget(self) -> QWidget:
        """Create the progress widget for the checking phase."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Progress info
        self.progress_label = QLabel("Initializing pre-flight check...")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # Status details
        self.status_label = QLabel("Preparing to analyze directory structure...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666666; font-style: italic;")
        layout.addWidget(self.status_label)
        
        return widget
    
    def create_results_widget(self) -> QWidget:
        """Create the results widget for strategy selection."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Directory analysis summary
        self.summary_group = QGroupBox("📊 Directory Analysis")
        self.summary_layout = QGridLayout(self.summary_group)
        layout.addWidget(self.summary_group)
        
        # Strategy selection
        strategy_group = QGroupBox("🎯 Analysis Strategy")
        strategy_layout = QVBoxLayout(strategy_group)
        
        # Strategy cards container
        self.strategy_container = QWidget()
        self.strategy_layout = QHBoxLayout(self.strategy_container)
        self.strategy_cards = {}
        
        strategy_layout.addWidget(self.strategy_container)
        layout.addWidget(strategy_group)
        
        # Custom parameters
        custom_group = QGroupBox("⚙️ Custom Parameters")
        custom_layout = QVBoxLayout(custom_group)
        
        self.custom_checkbox = QCheckBox("Enable custom parameters")
        self.custom_checkbox.stateChanged.connect(self.toggle_custom_parameters)
        custom_layout.addWidget(self.custom_checkbox)
        
        self.custom_params_widget = CustomParametersWidget()
        self.custom_params_widget.setEnabled(False)
        self.custom_params_widget.parameters_changed.connect(self.on_custom_parameters_changed)
        custom_layout.addWidget(self.custom_params_widget)
        
        layout.addWidget(custom_group)
        
        # Warnings section
        self.warnings_group = QGroupBox("⚠️ Warnings & Recommendations")
        self.warnings_layout = QVBoxLayout(self.warnings_group)
        self.warnings_text = QTextEdit()
        self.warnings_text.setMaximumHeight(100)
        self.warnings_text.setReadOnly(True)
        self.warnings_layout.addWidget(self.warnings_text)
        layout.addWidget(self.warnings_group)
        
        return widget
    
    def start_preflight_check(self):
        """Start the pre-flight check process."""
        self.worker = PreFlightWorker(self.target_directory, self)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.check_completed.connect(self.on_check_completed)
        self.worker.error_occurred.connect(self.on_check_error)
        self.worker.start()
    
    def update_progress(self, message: str, percentage: float):
        """Update the progress display."""
        self.progress_label.setText(message)
        self.progress_bar.setValue(int(percentage))
        
        # Add some dynamic status messages
        if percentage < 20:
            self.status_label.setText("🔍 Scanning directory structure...")
        elif percentage < 50:
            self.status_label.setText("🖥️ Analyzing system capabilities...")
        elif percentage < 80:
            self.status_label.setText("📊 Calculating performance forecasts...")
        else:
            self.status_label.setText("✨ Generating recommendations...")
    
    def on_check_completed(self, results: PreFlightResults):
        """Handle completion of pre-flight check."""
        self.preflight_results = results
        
        # Hide progress, show results
        self.progress_widget.setVisible(False)
        self.results_widget.setVisible(True)
        
        # Populate results
        self.populate_summary(results)
        self.populate_strategies(results)
        self.populate_warnings(results)
        
        # Enable start button
        self.start_button.setEnabled(True)
        
        # Resize dialog to fit content
        self.adjustSize()
    
    def on_check_error(self, error_message: str):
        """Handle pre-flight check error."""
        QMessageBox.critical(self, "Pre-Flight Check Failed", 
                           f"Failed to perform pre-flight check:\n\n{error_message}")
        self.reject()
    
    def populate_summary(self, results: PreFlightResults):
        """Populate the directory analysis summary."""
        summary = results.system_capabilities
        scout = results.scout_metrics
        
        # Clear existing layout
        for i in reversed(range(self.summary_layout.count())):
            self.summary_layout.itemAt(i).widget().setParent(None)
        
        # File statistics
        self.summary_layout.addWidget(QLabel("📁 Files:"), 0, 0)
        self.summary_layout.addWidget(QLabel(f"{scout.total_files:,}"), 0, 1)
        
        self.summary_layout.addWidget(QLabel("📂 Directories:"), 0, 2)
        self.summary_layout.addWidget(QLabel(f"{scout.total_directories:,}"), 0, 3)
        
        self.summary_layout.addWidget(QLabel("💾 Total Size:"), 1, 0)
        self.summary_layout.addWidget(QLabel(f"{scout.total_size_bytes / (1024**3):.2f} GB"), 1, 1)
        
        self.summary_layout.addWidget(QLabel("🏷️ File Types:"), 1, 2)
        self.summary_layout.addWidget(QLabel(f"{len(scout.extension_histogram)}"), 1, 3)
        
        # System info
        self.summary_layout.addWidget(QLabel("🖥️ CPU Cores:"), 2, 0)
        self.summary_layout.addWidget(QLabel(f"{summary.get('cpu_cores', 'Unknown')}"), 2, 1)
        
        self.summary_layout.addWidget(QLabel("🎮 GPU:"), 2, 2)
        gpu_text = "Available" if summary.get('gpu_available', False) else "Not Available"
        self.summary_layout.addWidget(QLabel(gpu_text), 2, 3)
    
    def populate_strategies(self, results: PreFlightResults):
        """Populate the strategy selection cards."""
        # Clear existing cards
        for card in self.strategy_cards.values():
            card.setParent(None)
        self.strategy_cards.clear()
        
        # Get strategy comparison data
        if hasattr(results, 'strategy_forecasts') and results.strategy_forecasts:
            checker = PreFlightChecker()  # Create temporary checker for comparison table
            comparison_data = checker.get_strategy_comparison_table(results.strategy_forecasts)
            
            for strategy_info in comparison_data:
                card = StrategyCard(strategy_info['name'], strategy_info, self)
                card.strategy_selected.connect(self.on_strategy_selected)
                self.strategy_cards[strategy_info['name']] = card
                self.strategy_layout.addWidget(card)
            
            # Select recommended strategy
            if results.recommended_strategy in self.strategy_cards:
                self.on_strategy_selected(results.recommended_strategy)
    
    def populate_warnings(self, results: PreFlightResults):
        """Populate the warnings section."""
        if results.warnings:
            warnings_text = "\n".join(f"• {warning}" for warning in results.warnings)
            self.warnings_text.setPlainText(warnings_text)
            self.warnings_group.setVisible(True)
        else:
            self.warnings_text.setPlainText("✅ No warnings detected. System is ready for analysis.")
            self.warnings_group.setVisible(True)
    
    def on_strategy_selected(self, strategy_name: str):
        """Handle strategy selection."""
        # Update visual selection
        for name, card in self.strategy_cards.items():
            card.set_selected(name == strategy_name)
        
        self.selected_strategy = strategy_name
        
        # Update custom parameters to match strategy
        if (self.preflight_results and 
            strategy_name in self.preflight_results.strategy_forecasts):
            
            forecast = self.preflight_results.strategy_forecasts[strategy_name]
            self.custom_params_widget.update_from_strategy(forecast.recommended_strategy)
    
    def toggle_custom_parameters(self, state):
        """Toggle custom parameters widget."""
        enabled = state == Qt.CheckState.Checked.value
        self.custom_params_widget.setEnabled(enabled)
        
        if enabled:
            # Use current custom parameters
            self.custom_params = self.custom_params_widget.get_parameters()
        else:
            # Clear custom parameters
            self.custom_params = {}
    
    def on_custom_parameters_changed(self, params: Dict[str, Any]):
        """Handle custom parameter changes."""
        if self.custom_checkbox.isChecked():
            self.custom_params = params
    
    def approve_analysis(self):
        """Approve the analysis with selected strategy and parameters."""
        if not self.preflight_results:
            return
        
        # Emit the approval signal with strategy and parameters
        self.analysis_approved.emit(self.selected_strategy, self.custom_params)
        self.accept()
    
    def get_analysis_config(self) -> Dict[str, Any]:
        """Get the final analysis configuration."""
        return {
            'strategy': self.selected_strategy,
            'custom_parameters': self.custom_params,
            'preflight_results': self.preflight_results
        }