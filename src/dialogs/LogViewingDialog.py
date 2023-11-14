import logging
from typing import Set

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListView, QComboBox, QLineEdit, QLabel, QPushButton, QCheckBox
from PyQt5.QtCore import pyqtSignal, QAbstractListModel, Qt, QObject, QModelIndex, QSortFilterProxyModel


class DeviceFilterDialog(QDialog):
    def __init__(self, device_ids: Set[str], current_selected_ids: Set[str], parent=None):
        super().__init__(parent)
        logging.debug("Creating device filter dialog")

        self.selected_device_ids = None

        self.setWindowTitle("Filter devices")

        # Disable "What's this" button
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)
        layout = QVBoxLayout()

        self.checkboxes = {}

        for device_id in device_ids:
            checkbox = QCheckBox(device_id, self)
            # Initialize checkboxes based on the current selection
            checkbox.setChecked(device_id in current_selected_ids)
            self.checkboxes[device_id] = checkbox
            layout.addWidget(checkbox)

        self.select_button = QPushButton("Filter", self)
        self.select_button.clicked.connect(self.select_device_ids)
        layout.addWidget(self.select_button)
        layout.addStretch(1)

        self.setLayout(layout)
        logging.debug("Dialog created")

    def select_device_ids(self):
        self.selected_device_ids = {device_id for device_id, cb in self.checkboxes.items() if cb.isChecked()}
        logging.debug(f"Selected device ids: {self.selected_device_ids}")
        self.accept()


class QtLogHandler(QObject, logging.Handler):
    log_signal = pyqtSignal(logging.LogRecord)

    def emit(self, record: logging.LogRecord):
        self.log_signal.emit(record)


class LogMessageProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.display_level = logging.INFO
        self.selected_device_ids = set()

    def filterAcceptsRow(self, source_row, source_parent):
        record = self.sourceModel().data(
            self.sourceModel().index(source_row, 0, source_parent),
            role=Qt.UserRole
        )
        if record:
            device_id = getattr(record, "device_id", None)
            if self.selected_device_ids and device_id not in self.selected_device_ids:
                return False
            return record.levelno >= self.display_level
        return False

    def lessThan(self, left, right):
        left_record = self.sourceModel().data(left, role=Qt.UserRole)
        right_record = self.sourceModel().data(right, role=Qt.UserRole)
        return left_record.created < right_record.created

    def set_display_level(self, level):
        self.display_level = level
        logging.debug(f"Log display level set to {level}")
        self.invalidateFilter()


class LogMessageModel(QAbstractListModel):
    MAX_RECORDS = 20000  # Maximum number of log records

    def __init__(self):
        super().__init__()
        self.records = []
        self.visible_records = []
        self.device_ids = set()
        self.display_level = logging.DEBUG
        self.formatter_str = "%(asctime)s - %(filename)s:%(lineno)d - %(name)s - %(levelname)s - %(message)s"

    def rowCount(self, parent=None):
        return len(self.visible_records)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.records):
            return None
        record = self.records[index.row()]
        if role == Qt.DisplayRole:
            return self.format_record(record)
        elif role == Qt.UserRole:
            return record
        return None

    def insert_record(self, record: logging.LogRecord):
        if len(self.records) >= self.MAX_RECORDS:
            self.beginRemoveRows(QModelIndex(), len(self.records) - 1, len(self.records) - 1)
            self.records.pop()  # Remove the oldest record
            self.endRemoveRows()
        device_id = getattr(record, "device_id", None)
        if device_id is not None:
            self.device_ids.add(device_id)

        self.beginInsertRows(QModelIndex(), 0, 0)
        self.records.insert(0, record)  # Insert at the beginning
        if record.levelno >= self.display_level:
            self.visible_records.insert(0, record)  # Insert at the beginning
        self.endInsertRows()

    def set_display_level(self, level):
        self.display_level = level
        self.visible_records = [record for record in self.records if record.levelno >= self.display_level]
        self.modelReset.emit()

    def format_record(self, record):
        try:
            if hasattr(record, "device_id"):
                return logging.Formatter(self.formatter_str.replace("%(name)s", "%(device_id)s")).format(record)
            return logging.Formatter(self.formatter_str).format(record)
        except ValueError as ve:
            logging.error(f"Error formatting message: {ve}")

    def set_formatter(self, formatter_str):
        self.formatter_str = formatter_str
        logging.debug(f"Formatter in model changed to {self.formatter_str}")
        self.dataChanged.emit(self.index(0), self.index(self.rowCount() - 1))

    def refresh_visible_records(self):
        self.visible_records = [
            record for record in self.records
            if record.levelno >= self.display_level
        ]
        self.modelReset.emit()


class LogViewingDialog(QDialog):
    def __init__(self):
        super().__init__()
        logging.debug("Creating log viewing dialog")

        # Disable "What's this" button
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)

        self.setWindowTitle("Logs")

        layout = QVBoxLayout()

        self.model = LogMessageModel()
        self.proxy_model = LogMessageProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.view = QListView(self)
        self.view.setModel(self.proxy_model)
        self.view.setAutoScroll(False)
        layout.addWidget(self.view)

        # Dropdown menu that allows changing the visible logs level
        layout.addWidget(QLabel("Log level:"))
        self.level_dropdown = QComboBox(self)
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            self.level_dropdown.addItem(level)
        self.level_dropdown.setCurrentText("INFO")
        self.level_dropdown.currentTextChanged.connect(self.change_log_level)
        layout.addWidget(self.level_dropdown)

        # LineEdit that allows the user to change log format
        layout.addWidget(QLabel("Log format:"))
        self.formatter_edit = QLineEdit(self)
        self.formatter_edit.setText(self.model.formatter_str)
        self.formatter_edit.editingFinished.connect(self.change_formatter)
        layout.addWidget(self.formatter_edit)

        # Add button that allows filtering by device
        self.device_filter_button = QPushButton("Filter by device ID", self)
        self.device_filter_button.clicked.connect(self.show_device_filter_dialog)
        layout.addWidget(self.device_filter_button)

        self.setLayout(layout)

        self.handler = QtLogHandler()
        logging.getLogger().addHandler(self.handler)
        self.handler.log_signal.connect(self.model.insert_record)

        self.setMinimumSize(600, 600)
        self.setModal(False)

        logging.debug("Dialog created")

    def change_log_level(self):
        level = getattr(logging, self.level_dropdown.currentText())
        self.proxy_model.set_display_level(level)

    def change_formatter(self):
        formatter_str = self.formatter_edit.text()
        self.model.set_formatter(formatter_str)

    def show_device_filter_dialog(self):
        dialog = DeviceFilterDialog(self.model.device_ids, self.proxy_model.selected_device_ids, self)
        if dialog.exec():
            self.proxy_model.selected_device_ids = dialog.selected_device_ids
            self.proxy_model.invalidateFilter()
