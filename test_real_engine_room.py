#!/usr/bin/env python3
"""
Test the REAL Engine Room UI
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication

# Add sentinel to path
sys.path.insert(0, str(Path(__file__).parent))

from sentinel.app.ui.real_engine_room import RealEngineRoomDialog


def main():
    """Test the real engine room."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Create and show the real engine room
    engine_room = RealEngineRoomDialog()
    engine_room.show()
    
    print("🔧 Real Engine Room launched!")
    print("This shows ACTUAL system performance:")
    print("- Real CPU, GPU, and memory usage")
    print("- Actual bottleneck analysis")
    print("- Live system monitoring")
    print("- Proper dark theme with visible text")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()