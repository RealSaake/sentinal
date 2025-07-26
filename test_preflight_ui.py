#!/usr/bin/env python3
"""
Test the Pre-Flight Dialog UI
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget

# Add sentinel to path
sys.path.insert(0, str(Path(__file__).parent))

from sentinel.app.ui.preflight_dialog import PreFlightDialog


class TestWindow(QMainWindow):
    """Simple test window to launch the pre-flight dialog."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pre-Flight Dialog Test")
        self.resize(400, 200)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout(central_widget)
        
        # Test button
        test_button = QPushButton("🚀 Launch Pre-Flight Check")
        test_button.clicked.connect(self.launch_preflight)
        layout.addWidget(test_button)
    
    def launch_preflight(self):
        """Launch the pre-flight dialog."""
        # Use current directory as test target
        target_dir = str(Path.cwd())
        
        dialog = PreFlightDialog(target_dir, self)
        dialog.analysis_approved.connect(self.on_analysis_approved)
        
        result = dialog.exec()
        if result:
            print("✅ Pre-flight check completed and approved!")
        else:
            print("❌ Pre-flight check cancelled")
    
    def on_analysis_approved(self, strategy_name: str, custom_params: dict):
        """Handle analysis approval."""
        print(f"🎯 Strategy selected: {strategy_name}")
        if custom_params:
            print(f"⚙️ Custom parameters: {custom_params}")
        else:
            print("📋 Using default parameters")


def main():
    """Run the test application."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show test window
    window = TestWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()