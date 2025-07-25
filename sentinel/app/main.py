import sys

from PyQt6.QtWidgets import QApplication

from .db import DatabaseManager
from .ui.main_window import MainWindow


def main() -> None:
    """Application entry point."""
    app = QApplication(sys.argv)
    db_manager = DatabaseManager()
    db_manager.init_schema()

    window = MainWindow(db_manager)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 