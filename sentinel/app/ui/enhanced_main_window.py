#!/usr/bin/env python3
"""
Sentinel 2.0 - Enhanced Main Window
ONE window with ALL functionality - no more popup dialogs!
"""

import time
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QProgressBar, QFileDialog, QTextEdit, QTabWidget, QTableWidget, 
    QTableWidgetItem, QComboBox, QSpinBox, QCheckBox, QGroupBox, QFormLayout,
    QSplitter, QFrame, QScrollArea, QGridLayout, QMessageBox
)
from PyQt6.QtGui import QFont, QColor, QPalette

from sentinel.app.config_manager import ConfigManager


class EnhancedAnalysisWorker(QThread):
    """Enhanced worker with detailed progress reporting."""
    
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    eta_changed = pyqtSignal(str)
    throughput_changed = pyqtSignal(str)
    files_processed = pyqtSignal(int, int)  # processed, total
    results_ready = pyqtSignal(list)
    finished_success = pyqtSignal()
    
    def __init__(self, directory, config_mgr, db_manager, logger_manager=None, performance_monitor=None):
        super().__init__()
        self.directory = directory
        self.config_mgr = config_mgr
        self.db = db_manager
        self.logger_manager = logger_manager
        self.performance_monitor = performance_monitor
        self.start_time = None
        self.files_processed_count = 0
        self.total_files = 0
        
        if self.logger_manager:
            self.logger = self.logger_manager.get_logger('enhanced_analysis_worker')
    
    def run(self):
        """Run analysis with detailed progress reporting."""
        from sentinel.app.pipeline import run_analysis
        
        self.start_time = time.time()
        
        try:
            # Start analysis
            self.status_changed.emit("🚀 Starting Sentinel 2.0 Agentic Analysis...")
            
            # Create a custom progress callback
            def progress_callback(processed, total, current_file=""):
                self.files_processed_count = processed
                self.total_files = total
                
                # Calculate progress percentage
                progress = int((processed / total) * 100) if total > 0 else 0
                self.progress_changed.emit(progress)
                
                # Calculate ETA
                elapsed = time.time() - self.start_time
                if processed > 0:
                    rate = processed / elapsed
                    remaining = total - processed
                    eta_seconds = remaining / rate if rate > 0 else 0
                    
                    # Format ETA
                    if eta_seconds < 60:
                        eta_str = f"{eta_seconds:.0f}s"
                    elif eta_seconds < 3600:
                        eta_str = f"{eta_seconds/60:.1f}m"
                    else:
                        eta_str = f"{eta_seconds/3600:.1f}h"
                    
                    self.eta_changed.emit(f"ETA: {eta_str}")
                    self.throughput_changed.emit(f"{rate:.1f} files/sec")
                else:
                    self.eta_changed.emit("ETA: Calculating...")
                    self.throughput_changed.emit("0.0 files/sec")
                
                # Update file count
                self.files_processed.emit(processed, total)
                
                # Update status with current file
                if current_file:
                    self.status_changed.emit(f"Processing: {current_file}")
            
            # Run analysis
            results = run_analysis(
                self.directory,
                db=self.db,
                config=self.config_mgr.config,
                logger_manager=self.logger_manager,
                performance_monitor=self.performance_monitor
            )
            
            # Final updates
            self.progress_changed.emit(100)
            self.status_changed.emit("✅ Analysis Complete!")
            
            elapsed = time.time() - self.start_time
            final_rate = len(results) / elapsed if elapsed > 0 else 0
            self.throughput_changed.emit(f"Final: {final_rate:.1f} files/sec")
            self.eta_changed.emit("Complete!")
            
            self.results_ready.emit(results)
            
            if self.logger_manager:
                self.logger.info(f"Analysis completed: {len(results)} files in {elapsed:.2f}s")
                
        except Exception as e:
            self.status_changed.emit(f"❌ Error: {str(e)}")
            if self.logger_manager:
                self.logger.error(f"Analysis failed: {e}", exc_info=True)
        finally:
            self.finished_success.emit()


class EnhancedMainWindow(QMainWindow):
    """Enhanced main window with ALL functionality in ONE place."""
    
    def __init__(self, db_manager, logger_manager=None, performance_monitor=None, debug_collector=None):
        super().__init__()
        self.setWindowTitle("🎯 Sentinel 2.0 - Agentic File Analysis System")
        self.resize(1200, 800)
        
        # Components
        self.config_mgr = ConfigManager()
        self.db = db_manager
        self.logger_manager = logger_manager
        self.performance_monitor = performance_monitor
        self.debug_collector = debug_collector
        
        if self.logger_manager:
            self.logger = self.logger_manager.get_logger('enhanced_main_window')
            self.logger.info("Enhanced main window initializing...")
        
        # State
        self.directory_path = None
        self.worker = None
        self.analysis_results = []
        
        # Setup UI
        self.setup_ui()
        self.setup_timer()
        
        if self.logger_manager:
            self.logger.info("Enhanced main window initialized")
    
    def setup_ui(self):
        """Setup the complete UI in one window."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Header section
        header_layout = self.create_header_section()
        main_layout.addLayout(header_layout)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Controls and Configuration
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Progress and Results
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 800])
        main_layout.addWidget(splitter)
        
        # Status bar
        self.statusBar().showMessage("Ready - Select directory to begin")
    
    def create_header_section(self):
        """Create the header with title and key metrics."""
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("🎯 Sentinel 2.0 - Agentic File Analysis")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Key metrics
        self.throughput_label = QLabel("Throughput: 0 files/sec")
        self.eta_label = QLabel("ETA: --")
        self.files_count_label = QLabel("Files: 0/0")
        
        for label in [self.throughput_label, self.eta_label, self.files_count_label]:
            label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; border-radius: 3px; }")
            header_layout.addWidget(label)
        
        return header_layout
    
    def create_left_panel(self):
        """Create the left control panel."""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Directory selection
        dir_group = QGroupBox("📁 Directory Selection")
        dir_layout = QVBoxLayout(dir_group)
        
        self.select_btn = QPushButton("Select Directory...")
        self.select_btn.clicked.connect(self.select_directory)
        dir_layout.addWidget(self.select_btn)
        
        self.dir_label = QLabel("No directory selected")
        self.dir_label.setWordWrap(True)
        self.dir_label.setStyleSheet("QLabel { background-color: #f9f9f9; padding: 8px; border: 1px solid #ddd; }")
        dir_layout.addWidget(self.dir_label)
        
        left_layout.addWidget(dir_group)
        
        # Configuration
        config_group = QGroupBox("⚙️ Configuration")
        config_layout = QFormLayout(config_group)
        
        # AI Backend
        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["Local", "Cloud"])
        self.backend_combo.setCurrentText(self.config_mgr.config.ai_backend_mode.title())
        config_layout.addRow("AI Backend:", self.backend_combo)
        
        # Performance settings
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 32)
        self.max_workers_spin.setValue(8)
        config_layout.addRow("Max Workers:", self.max_workers_spin)
        
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(16, 256)
        self.batch_size_spin.setValue(128)
        config_layout.addRow("Batch Size:", self.batch_size_spin)
        
        # Optimization options
        self.enable_caching = QCheckBox("Smart Caching")
        self.enable_caching.setChecked(True)
        config_layout.addRow("", self.enable_caching)
        
        self.max_speed_mode = QCheckBox("Maximum Speed Mode")
        self.max_speed_mode.setChecked(True)
        config_layout.addRow("", self.max_speed_mode)
        
        left_layout.addWidget(config_group)
        
        # Analysis control
        control_group = QGroupBox("🚀 Analysis Control")
        control_layout = QVBoxLayout(control_group)
        
        self.start_btn = QPushButton("🚀 Start Agentic Analysis")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_analysis)
        self.start_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop Analysis")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_analysis)
        self.stop_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }")
        control_layout.addWidget(self.stop_btn)
        
        left_layout.addWidget(control_group)
        
        # System info
        system_group = QGroupBox("💻 System Info")
        system_layout = QVBoxLayout(system_group)
        
        self.system_info_label = QLabel(self.get_system_info())
        self.system_info_label.setWordWrap(True)
        self.system_info_label.setStyleSheet("QLabel { font-family: monospace; font-size: 10px; }")
        system_layout.addWidget(self.system_info_label)
        
        left_layout.addWidget(system_group)
        
        left_layout.addStretch()
        
        return left_widget
    
    def create_right_panel(self):
        """Create the right panel with progress and results."""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Progress section
        progress_group = QGroupBox("📊 Analysis Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        # Status
        self.status_label = QLabel("Ready to start analysis")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("QLabel { background-color: #e3f2fd; padding: 8px; border-radius: 4px; }")
        progress_layout.addWidget(self.status_label)
        
        right_layout.addWidget(progress_group)
        
        # Tabs for different views
        self.tab_widget = QTabWidget()
        
        # Log tab
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.tab_widget.addTab(self.log_text, "📝 Live Log")
        
        # Results tab
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Original Path", "Suggested Path", "Category", "Tags", "Confidence", "Status"
        ])
        self.tab_widget.addTab(self.results_table, "📋 Results")
        
        # Performance tab
        self.performance_text = QTextEdit()
        self.performance_text.setReadOnly(True)
        self.performance_text.setFont(QFont("Consolas", 9))
        self.tab_widget.addTab(self.performance_text, "⚡ Performance")
        
        right_layout.addWidget(self.tab_widget)
        
        return right_widget
    
    def setup_timer(self):
        """Setup timer for real-time updates."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # Update every second
    
    def get_system_info(self):
        """Get system information."""
        import psutil
        import platform
        
        try:
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            
            info = f"OS: {platform.system()}\n"
            info += f"CPU: {cpu_count} cores\n"
            info += f"RAM: {memory_gb:.1f} GB\n"
            
            # Try to detect GPU
            try:
                import subprocess
                result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                                      capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    gpu_name = result.stdout.strip()
                    info += f"GPU: {gpu_name}\n"
                else:
                    info += "GPU: Not detected\n"
            except:
                info += "GPU: Not detected\n"
            
            info += f"Backend: {self.config_mgr.config.ai_backend_mode.title()}"
            
            return info
        except:
            return "System info unavailable"
    
    def select_directory(self):
        """Select directory for analysis."""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory for Analysis")
        if dir_path:
            self.directory_path = dir_path
            self.dir_label.setText(f"Selected: {dir_path}")
            self.start_btn.setEnabled(True)
            self.log_message(f"📁 Directory selected: {dir_path}")
            
            if self.logger_manager:
                self.logger.info(f"Directory selected: {dir_path}")
    
    def start_analysis(self):
        """Start the agentic analysis."""
        if not self.directory_path:
            return
        
        # Update UI state
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("🚀 Initializing Agentic Analysis...")
        
        # Clear previous results
        self.results_table.setRowCount(0)
        self.analysis_results.clear()
        
        # Update configuration
        self.config_mgr.config.ai_backend_mode = self.backend_combo.currentText().lower()
        
        # Log start
        self.log_message("🚀 Starting Sentinel 2.0 Agentic Analysis")
        self.log_message(f"📁 Directory: {self.directory_path}")
        self.log_message(f"⚙️ Backend: {self.config_mgr.config.ai_backend_mode}")
        self.log_message(f"🔧 Max Workers: {self.max_workers_spin.value()}")
        self.log_message(f"📦 Batch Size: {self.batch_size_spin.value()}")
        self.log_message(f"🧠 Smart Caching: {'Enabled' if self.enable_caching.isChecked() else 'Disabled'}")
        self.log_message(f"⚡ Max Speed Mode: {'Enabled' if self.max_speed_mode.isChecked() else 'Disabled'}")
        
        # Create and start worker
        self.worker = EnhancedAnalysisWorker(
            self.directory_path,
            self.config_mgr,
            self.db,
            self.logger_manager,
            self.performance_monitor
        )
        
        # Connect signals
        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.eta_changed.connect(self.eta_label.setText)
        self.worker.throughput_changed.connect(self.throughput_label.setText)
        self.worker.files_processed.connect(self.update_files_count)
        self.worker.results_ready.connect(self.on_results_ready)
        self.worker.finished_success.connect(self.on_analysis_finished)
        
        # Start analysis
        self.worker.start()
        
        if self.logger_manager:
            self.logger.info("Analysis started")
    
    def stop_analysis(self):
        """Stop the current analysis."""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("⏹️ Analysis Stopped")
        self.log_message("⏹️ Analysis stopped by user")
        
        if self.logger_manager:
            self.logger.info("Analysis stopped by user")
    
    def update_files_count(self, processed, total):
        """Update files count display."""
        self.files_count_label.setText(f"Files: {processed}/{total}")
    
    def on_results_ready(self, results):
        """Handle analysis results."""
        self.analysis_results = results
        self.populate_results_table(results)
        self.update_performance_stats()
        
        self.log_message(f"✅ Analysis complete! Processed {len(results)} files")
        
        if self.logger_manager:
            self.logger.info(f"Analysis completed with {len(results)} results")
    
    def on_analysis_finished(self):
        """Handle analysis completion."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if self.analysis_results:
            self.tab_widget.setCurrentIndex(1)  # Switch to results tab
    
    def populate_results_table(self, results):
        """Populate the results table."""
        self.results_table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            # Original path
            self.results_table.setItem(row, 0, QTableWidgetItem(result.get('original_path', '')))
            
            # Suggested path
            self.results_table.setItem(row, 1, QTableWidgetItem(result.get('suggested_path', '')))
            
            # Category
            self.results_table.setItem(row, 2, QTableWidgetItem(result.get('category', 'N/A')))
            
            # Tags
            tags = result.get('tags', [])
            tags_str = ', '.join(tags[:3]) if tags else 'None'
            self.results_table.setItem(row, 3, QTableWidgetItem(tags_str))
            
            # Confidence
            confidence = result.get('confidence', 0)
            self.results_table.setItem(row, 4, QTableWidgetItem(f"{confidence:.2f}"))
            
            # Status
            status = "✅ Success" if result.get('success', True) else "❌ Failed"
            self.results_table.setItem(row, 5, QTableWidgetItem(status))
        
        # Auto-resize columns
        self.results_table.resizeColumnsToContents()
    
    def update_performance_stats(self):
        """Update performance statistics."""
        if not self.analysis_results:
            return
        
        total_files = len(self.analysis_results)
        successful = len([r for r in self.analysis_results if r.get('success', True)])
        
        # Calculate category distribution
        categories = {}
        for result in self.analysis_results:
            category = result.get('category', 'Unknown')
            categories[category] = categories.get(category, 0) + 1
        
        # Calculate average confidence
        confidences = [r.get('confidence', 0) for r in self.analysis_results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Build performance report
        stats = f"📊 PERFORMANCE STATISTICS\n"
        stats += f"{'='*50}\n\n"
        stats += f"Total Files Processed: {total_files}\n"
        stats += f"Successful: {successful} ({(successful/total_files)*100:.1f}%)\n"
        stats += f"Average Confidence: {avg_confidence:.2f}\n\n"
        
        stats += f"📋 CATEGORY DISTRIBUTION\n"
        stats += f"{'-'*30}\n"
        for category, count in sorted(categories.items()):
            percentage = (count / total_files) * 100
            stats += f"{category}: {count} files ({percentage:.1f}%)\n"
        
        if self.worker and hasattr(self.worker, 'start_time'):
            elapsed = time.time() - self.worker.start_time
            throughput = total_files / elapsed if elapsed > 0 else 0
            stats += f"\n⚡ PERFORMANCE METRICS\n"
            stats += f"{'-'*30}\n"
            stats += f"Total Time: {elapsed:.2f}s\n"
            stats += f"Throughput: {throughput:.1f} files/sec\n"
            stats += f"Avg Time per File: {(elapsed/total_files)*1000:.1f}ms\n"
        
        self.performance_text.setText(stats)
    
    def log_message(self, message):
        """Add message to log."""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.append(formatted_message)
        
        # Auto-scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
    
    def update_display(self):
        """Update display with real-time information."""
        # This runs every second to update any real-time displays
        pass
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, 
                'Confirm Exit', 
                'Analysis is still running. Do you want to stop it and exit?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.terminate()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()