from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QProgressBar,
    QFileDialog,
    QDialog,
    QFormLayout,
    QComboBox,
    QDialogButtonBox,
    QMessageBox,
    QMenuBar,
    QMenu,
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QAction

from sentinel.app.config_manager import ConfigManager
from sentinel.app.ui.review_dialog import ReviewDialog
from sentinel.app.ui.debug_dialog import DebugDialog

# ---------------------------------------------------------------------------
# Worker thread for background analysis (placeholder implementation)
# ---------------------------------------------------------------------------


class AnalysisWorker(QThread):
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    results_ready = pyqtSignal(list)  # Emits list of result dicts
    finished_success = pyqtSignal()

    def __init__(
        self,
        directory: str,
        *,
        config_mgr: ConfigManager,
        db_manager,
        logger_manager=None,
        performance_monitor=None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.directory = directory
        self.config_mgr = config_mgr
        self.db = db_manager
        self.logger_manager = logger_manager
        self.performance_monitor = performance_monitor
        
        if self.logger_manager:
            self.logger = self.logger_manager.get_logger('analysis_worker')

    # pylint: disable=import-outside-toplevel
    def run(self):
        """Execute scanning → inference pipeline (stub)."""
        # We import lazily to avoid blocking GUI startup.
        from sentinel.app.pipeline import run_analysis

        if self.logger_manager:
            self.logger.info(f"Starting analysis pipeline for directory: {self.directory}")
        
        self.status_changed.emit("Running analysis pipeline…")

        # Use pipeline; progress updates after each file via simple counter
        try:
            results = run_analysis(
                self.directory, 
                db=self.db, 
                config=self.config_mgr.config,
                logger_manager=self.logger_manager,
                performance_monitor=self.performance_monitor
            )
            self.progress_changed.emit(100)
            self.results_ready.emit(results)
            
            if self.logger_manager:
                self.logger.info(f"Analysis pipeline completed successfully with {len(results)} results")
                
        except Exception as exc:  # noqa: BLE001
            error_msg = f"Error: {exc}"
            self.status_changed.emit(error_msg)
            if self.logger_manager:
                self.logger.error(f"Analysis pipeline failed: {exc}", exc_info=True)
        finally:
            self.finished_success.emit()


class SettingsDialog(QDialog):
    """Simple settings dialog allowing AI backend and GPU selection."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)

        form_layout = QFormLayout()

        # Backend mode selection
        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["Local", "Cloud"])
        form_layout.addRow("AI Backend Mode:", self.backend_combo)

        # GPU selection - detect available GPUs
        self.gpu_combo = QComboBox()
        available_gpus = self._detect_gpus()
        self.gpu_combo.addItems(available_gpus)
        form_layout.addRow("GPU:", self.gpu_combo)

        # OK / Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form_layout.addRow(buttons)

        self.setLayout(form_layout)

    def _detect_gpus(self) -> list:
        """Detect available GPUs."""
        gpus = ["Default CPU"]
        
        try:
            import subprocess
            result = subprocess.run([
                'nvidia-smi', 
                '--query-gpu=name,memory.total', 
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split(', ')
                        if len(parts) >= 2:
                            name = parts[0].strip()
                            memory = parts[1].strip()
                            gpus.append(f"{name} ({memory}MB VRAM)")
        except Exception:
            pass
        
        return gpus

    def get_settings(self) -> dict:
        """Return the chosen settings as a dict."""
        return {
            "ai_backend_mode": self.backend_combo.currentText().lower(),
            "gpu": self.gpu_combo.currentText(),
        }


class MainWindow(QMainWindow):
    """Main application window for Sentinel."""

    def __init__(self, db_manager, logger_manager=None, performance_monitor=None, debug_collector=None):
        super().__init__()
        self.setWindowTitle("Sentinel – Storage Analyzer")
        self.resize(600, 300)

        # Config / DB
        self.config_mgr = ConfigManager()
        self.db = db_manager
        
        # Logging components
        self.logger_manager = logger_manager
        self.performance_monitor = performance_monitor
        self.debug_collector = debug_collector
        
        if self.logger_manager:
            self.logger = self.logger_manager.get_logger('main_window')
            self.logger.info("Main window initializing...")

        # Internal state
        self.directory_path: str | None = None

        # UI Elements
        self.select_btn = QPushButton("Select Directory…")
        self.start_btn = QPushButton("Start Analysis")
        self.start_btn.setEnabled(False)  # Disabled until directory chosen
        self.settings_btn = QPushButton("Settings")
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setText(
            f"Backend: {self.config_mgr.config.ai_backend_mode.title()}"
        )

        # Signal connections
        self.select_btn.clicked.connect(self.select_directory)
        self.start_btn.clicked.connect(self.start_analysis)
        self.settings_btn.clicked.connect(self.open_settings)

        # Create menu bar
        self.create_menu_bar()

        # Layout construction
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.select_btn)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.settings_btn)
        main_layout.addLayout(btn_row)

        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
        if self.logger_manager:
            self.logger.info("Main window UI setup completed")

    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        # Engine Room action (Sentinel 2.0 feature)
        engine_room_action = QAction("🔧 Engine Room", self)
        engine_room_action.setStatusTip("Open the Engine Room dashboard for real-time system monitoring")
        engine_room_action.triggered.connect(self.open_engine_room)
        tools_menu.addAction(engine_room_action)
        
        tools_menu.addSeparator()
        
        # Debug Info action
        if self.logger_manager and self.debug_collector:
            debug_action = QAction("Debug Information", self)
            debug_action.setStatusTip("Open debug information dialog")
            debug_action.triggered.connect(self.open_debug_dialog)
            tools_menu.addAction(debug_action)
        
        # Engine Room action
        engine_room_action = QAction("🔧 Engine Room", self)
        engine_room_action.setStatusTip("Open real-time system monitoring")
        engine_room_action.triggered.connect(self.open_engine_room)
        tools_menu.addAction(engine_room_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def open_engine_room(self):
        """Open the Engine Room dashboard."""
        try:
            from sentinel.app.ui.engine_room_dialog import EngineRoomDialog
            
            # Create and show the Engine Room dialog
            engine_room = EngineRoomDialog(self)
            engine_room.show()  # Use show() instead of exec() for non-modal
            
            if self.logger_manager:
                self.logger.info("Engine Room dashboard opened")
                
        except Exception as e:
            if self.logger_manager:
                self.logger.error(f"Failed to open Engine Room: {e}", exc_info=True)
            
            QMessageBox.warning(
                self,
                "Engine Room Unavailable",
                f"Failed to open Engine Room dashboard: {e}"
            )

    def open_debug_dialog(self):
        """Open the debug information dialog."""
        if self.logger_manager and self.debug_collector:
            debug_dialog = DebugDialog(
                logger_manager=self.logger_manager,
                performance_monitor=self.performance_monitor,
                debug_collector=self.debug_collector,
                parent=self
            )
            debug_dialog.exec()
            
            if self.logger_manager:
                self.logger.info("Debug dialog opened")
    
    def open_engine_room(self):
        """Open the real-time engine room monitoring."""
        try:
            from sentinel.app.ui.real_engine_room import RealEngineRoomDialog
            
            engine_room = RealEngineRoomDialog(self)
            engine_room.show()  # Non-modal so user can interact with main window
            
            if self.logger_manager:
                self.logger.info("Engine Room opened")
                
        except Exception as e:
            if self.logger_manager:
                self.logger.error(f"Failed to open Engine Room: {e}", exc_info=True)
            
            QMessageBox.warning(
                self,
                "Engine Room Unavailable",
                f"Failed to open Engine Room: {e}"
            )
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Sentinel 2.0",
            "Sentinel 2.0: The Agentic Architecture\n\n"
            "A revolutionary AI-powered file organization system with radical transparency and user empowerment.\n\n"
            "🚀 Sentinel 2.0 Features:\n"
            "• Pre-Flight Analysis with performance forecasting\n"
            "• Multi-agent AI system for superior results\n"
            "• Engine Room dashboard for complete transparency\n"
            "• Real-time worker process monitoring\n"
            "• Advanced logging and debugging capabilities\n"
            "• GPU acceleration support\n"
            "• Session management with pause/resume\n\n"
            "Experience the future of file organization with full transparency and control."
        )

    # ---------------------------- Callbacks -----------------------------
    def select_directory(self):
        """Open folder picker and store selected path."""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            self.directory_path = dir_path
            self.status_label.setText(f"Selected: {dir_path}")
            self.start_btn.setEnabled(True)
            
            if self.logger_manager:
                self.logger.info(f"Directory selected: {dir_path}")

    def start_analysis(self):
        """Launch the revolutionary Pre-Flight Check dialog."""
        if not self.directory_path:
            return

        if self.logger_manager:
            self.logger.info(f"Opening pre-flight check for directory: {self.directory_path}")

        # Import the pre-flight dialog
        try:
            from sentinel.app.ui.preflight_dialog import PreFlightDialog
            
            # Launch pre-flight dialog
            preflight_dialog = PreFlightDialog(self.directory_path, self)
            preflight_dialog.analysis_approved.connect(self.on_analysis_approved)
            
            # Show the dialog
            if preflight_dialog.exec():
                if self.logger_manager:
                    self.logger.info("Pre-flight check completed, analysis approved")
            else:
                if self.logger_manager:
                    self.logger.info("Pre-flight check cancelled by user")
                    
        except Exception as e:
            if self.logger_manager:
                self.logger.error(f"Failed to open pre-flight dialog: {e}", exc_info=True)
            
            # Fallback to original analysis if pre-flight fails
            QMessageBox.warning(
                self, 
                "Pre-Flight Check Unavailable", 
                f"Pre-flight check failed to load: {e}\n\nFalling back to direct analysis."
            )
            self.start_legacy_analysis()
    
    def on_analysis_approved(self, strategy_name: str, custom_params: dict):
        """Handle analysis approval from pre-flight dialog."""
        if self.logger_manager:
            self.logger.info(f"Analysis approved with strategy: {strategy_name}")
            if custom_params:
                self.logger.info(f"Custom parameters: {custom_params}")

        # Update status to show selected strategy
        self.status_label.setText(f"Starting analysis with {strategy_name} strategy...")
        
        # Prevent multiple concurrent runs
        self.start_btn.setEnabled(False)

        # Launch background worker with strategy information
        self.worker = AnalysisWorker(
            self.directory_path,
            config_mgr=self.config_mgr,
            db_manager=self.db,
            logger_manager=self.logger_manager,
            performance_monitor=self.performance_monitor,
            parent=self,
        )
        
        # Store strategy info for potential use in worker
        self.worker.strategy_name = strategy_name
        self.worker.custom_params = custom_params
        
        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.results_ready.connect(self.show_review_dialog)
        self.worker.finished_success.connect(self.on_analysis_finished)
        self.worker.start()
    
    def start_legacy_analysis(self):
        """Fallback to original analysis method if pre-flight fails."""
        if self.logger_manager:
            self.logger.info(f"Starting legacy analysis for directory: {self.directory_path}")

        # Prevent multiple concurrent runs
        self.start_btn.setEnabled(False)

        # Launch background worker (original method)
        self.worker = AnalysisWorker(
            self.directory_path,
            config_mgr=self.config_mgr,
            db_manager=self.db,
            logger_manager=self.logger_manager,
            performance_monitor=self.performance_monitor,
            parent=self,
        )
        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.results_ready.connect(self.show_review_dialog)
        self.worker.finished_success.connect(self.on_analysis_finished)
        self.worker.start()

    def on_analysis_finished(self):
        self.start_btn.setEnabled(True)
        if self.logger_manager:
            self.logger.info("Analysis workflow completed")

    # ---------------------- Review Dialog -----------------------------
    def show_review_dialog(self, results: list):  # noqa: D401
        """Launch ReviewDialog with provided *results*."""
        if not results:
            QMessageBox.information(self, "Review", "No results to review.")
            return

        dlg = ReviewDialog(results, self.db, self)
        dlg.exec()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):  # noqa: D401
        """Ensure background worker is terminated before window closes."""
        try:
            if hasattr(self, "worker") and self.worker.isRunning():
                self.worker.quit()
                self.worker.wait(3000)  # wait up to 3 seconds
        except Exception:  # noqa: BLE001
            pass
        super().closeEvent(event)

    def open_settings(self):
        dlg = SettingsDialog(self)
        # Preselect current backend mode
        dlg.backend_combo.setCurrentText(self.config_mgr.config.ai_backend_mode.title())
        if dlg.exec():
            settings = dlg.get_settings()
            self.config_mgr.set_backend_mode(settings["ai_backend_mode"])
            self.status_label.setText(
                f"Backend: {self.config_mgr.config.ai_backend_mode.title()}, GPU: {settings['gpu']}"
            ) 