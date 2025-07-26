#!/usr/bin/env python3
"""
Test the Engine Room Dashboard UI
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget

# Add sentinel to path
sys.path.insert(0, str(Path(__file__).parent))

from sentinel.app.ui.engine_room_dialog import EngineRoomDialog


class TestWindow(QMainWindow):
    """Simple test window to launch the Engine Room dashboard."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Engine Room Dashboard Test")
        self.resize(400, 200)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout(central_widget)
        
        # Test button
        test_button = QPushButton("🔧 Launch Engine Room Dashboard")
        test_button.clicked.connect(self.launch_engine_room)
        layout.addWidget(test_button)
        
        # Info label
        info_label = QPushButton("ℹ️ This will show live worker processes, system stats, and logs")
        info_label.setEnabled(False)
        layout.addWidget(info_label)
    
    def launch_engine_room(self):
        """Launch the Engine Room dashboard."""
        self.engine_room = EngineRoomDialog(self)
        self.engine_room.show()
        
        print("🔧 Engine Room dashboard launched!")
        print("   • Check the Workers tab to see live worker process cards")
        print("   • Check the System Stats tab for performance metrics")
        print("   • Check the Logs tab for real-time log streaming")
        print("   • Toggle mock data to see the system in action")


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