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
)
from PyQt6.QtCore import QThread, pyqtSignal

from sentinel.app.config_manager import ConfigManager
from sentinel.app.ui.review_dialog import ReviewDialog

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
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.directory = directory
        self.config_mgr = config_mgr
        self.db = db_manager

    # pylint: disable=import-outside-toplevel
    def run(self):
        """Execute scanning → inference pipeline (stub)."""
        # We import lazily to avoid blocking GUI startup.
        from sentinel.app.pipeline import run_analysis

        self.status_changed.emit("Running analysis pipeline…")

        # Use pipeline; progress updates after each file via simple counter
        try:
            results = run_analysis(self.directory, db=self.db, config=self.config_mgr.config)
            self.progress_changed.emit(100)
            self.results_ready.emit(results)
        except Exception as exc:  # noqa: BLE001
            self.status_changed.emit(f"Error: {exc}")
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

        # GPU selection (placeholder; populated dynamically in future)
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems(["Default CPU"])  # TODO: Detect GPUs
        form_layout.addRow("GPU:", self.gpu_combo)

        # OK / Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form_layout.addRow(buttons)

        self.setLayout(form_layout)

    def get_settings(self) -> dict:
        """Return the chosen settings as a dict."""
        return {
            "ai_backend_mode": self.backend_combo.currentText().lower(),
            "gpu": self.gpu_combo.currentText(),
        }


class MainWindow(QMainWindow):
    """Main application window for Sentinel."""

    def __init__(self, db_manager):
        super().__init__()
        self.setWindowTitle("Sentinel – Storage Analyzer")
        self.resize(600, 300)

        # Config / DB
        self.config_mgr = ConfigManager()
        self.db = db_manager

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

    # ---------------------------- Callbacks -----------------------------
    def select_directory(self):
        """Open folder picker and store selected path."""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            self.directory_path = dir_path
            self.status_label.setText(f"Selected: {dir_path}")
            self.start_btn.setEnabled(True)

    def start_analysis(self):
        """Placeholder for starting directory scan & AI analysis."""
        if not self.directory_path:
            return

        # Prevent multiple concurrent runs
        self.start_btn.setEnabled(False)

        # Launch background worker
        self.worker = AnalysisWorker(
            self.directory_path,
            config_mgr=self.config_mgr,
            db_manager=self.db,
            parent=self,
        )
        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.results_ready.connect(self.show_review_dialog)
        self.worker.finished_success.connect(self.on_analysis_finished)
        self.worker.start()

    def on_analysis_finished(self):
        self.start_btn.setEnabled(True)
        # Future: open ReviewDialog with real results
        QMessageBox.information(self, "Analysis", "Analysis completed (stub)")

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