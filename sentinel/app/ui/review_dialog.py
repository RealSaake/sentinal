from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QMessageBox,
    QCheckBox,
)


class ReviewDialog(QDialog):
    """Dialog for reviewing AI path suggestions and approving/rejecting them."""

    HEADERS = [
        "",  # Checkbox
        "Original Path",
        "AI Suggested Path",
        "Confidence",
        "Justification",
    ]

    def __init__(self, results: list[dict], db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.setWindowTitle("Review AI Suggestions")
        self.resize(900, 500)

        # Main layout
        layout = QVBoxLayout(self)

        # Results table
        self.table = QTableWidget(len(results), len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.populate_table(results)
        layout.addWidget(self.table)

        # Action buttons
        btn_layout = QHBoxLayout()
        self.approve_selected_btn = QPushButton("Approve Selected")
        self.reject_selected_btn = QPushButton("Reject Selected")
        self.approve_all_btn = QPushButton("Approve All")
        self.reject_all_btn = QPushButton("Reject All")
        self.apply_changes_btn = QPushButton("Apply Changes")

        btn_layout.addWidget(self.approve_selected_btn)
        btn_layout.addWidget(self.reject_selected_btn)
        btn_layout.addWidget(self.approve_all_btn)
        btn_layout.addWidget(self.reject_all_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.apply_changes_btn)
        layout.addLayout(btn_layout)

        # Connect signals
        self.approve_selected_btn.clicked.connect(self.approve_selected)
        self.reject_selected_btn.clicked.connect(self.reject_selected)
        self.approve_all_btn.clicked.connect(self.approve_all)
        self.reject_all_btn.clicked.connect(self.reject_all)
        self.apply_changes_btn.clicked.connect(self.apply_changes)

    # ------------------------ Table Helpers ----------------------------
    def populate_table(self, results: list[dict]):
        """Fill table with result rows."""
        for row, res in enumerate(results):
            # Checkbox
            chk = QCheckBox()
            chk.setChecked(True)  # Default select all
            self.table.setCellWidget(row, 0, chk)

            # Store file_id in checkbox property for later lookup
            chk.setProperty("file_id", res.get("file_id", -1))

            # Original Path (read-only)
            item_orig = QTableWidgetItem(res.get("original_path", ""))
            item_orig.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 1, item_orig)

            # AI Suggested Path (editable)
            item_sugg = QTableWidgetItem(res.get("suggested_path", ""))
            item_sugg.setFlags(item_sugg.flags() | Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, item_sugg)

            # Confidence (read-only)
            conf = res.get("confidence", 0.0)
            item_conf = QTableWidgetItem(f"{conf:.2f}")
            item_conf.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 3, item_conf)

            # Justification (read-only)
            item_just = QTableWidgetItem(res.get("justification", ""))
            item_just.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 4, item_just)

    # ------------------------ Action Slots ----------------------------
    def _iterate_checked_rows(self):
        for row in range(self.table.rowCount()):
            chk: QCheckBox = self.table.cellWidget(row, 0)
            if chk and chk.isChecked():
                yield row

    def approve_selected(self):
        # Placeholder implementation: mark background color
        for row in self._iterate_checked_rows():
            self.table.item(row, 2).setBackground(Qt.GlobalColor.green)

    def reject_selected(self):
        for row in self._iterate_checked_rows():
            self.table.item(row, 2).setBackground(Qt.GlobalColor.red)

    def approve_all(self):
        for row in range(self.table.rowCount()):
            self.table.item(row, 2).setBackground(Qt.GlobalColor.green)

    def reject_all(self):
        for row in range(self.table.rowCount()):
            self.table.item(row, 2).setBackground(Qt.GlobalColor.red)

    def apply_changes(self):
        reply = QMessageBox.question(
            self,
            "Apply Changes",
            "Are you sure you want to apply the selected changes? This will move/rename files on disk.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Commit feedback to DB
            for row in range(self.table.rowCount()):
                chk: QCheckBox = self.table.cellWidget(row, 0)
                file_id = chk.property("file_id")
                if file_id == -1:
                    continue  # stub rows, skip

                approved = chk.isChecked()
                suggested_item = self.table.item(row, 2)
                revised_path = suggested_item.text() if suggested_item else None

                try:
                    self.db.save_feedback(file_id, approved=approved, revised_path=revised_path)
                except Exception as exc:  # noqa: BLE001
                    print("DB feedback error:", exc)

            QMessageBox.information(self, "Changes Applied", "Feedback saved to the database.")
            self.accept() 