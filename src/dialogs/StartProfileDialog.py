import logging

from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QDateTimeEdit, QDialogButtonBox


class StartProfileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        logging.debug("Creating start profile dialog")

        # Disable "What's this" button
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)

        self.setWindowTitle("Start profile")

        layout = QVBoxLayout()

        self.scheduled_checkbox = QCheckBox("Scheduled")
        self.scheduled_checkbox.stateChanged.connect(
            lambda state: self.datetime_picker.setEnabled(state == Qt.Checked)
        )
        layout.addWidget(self.scheduled_checkbox)

        self.datetime_picker = QDateTimeEdit()
        self.datetime_picker.setEnabled(self.scheduled_checkbox.isChecked())
        self.datetime_picker.setDateTime(QDateTime.currentDateTime())
        layout.addWidget(self.datetime_picker)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

        self.setFixedSize(250, 125)

        logging.debug("Dialog created")
