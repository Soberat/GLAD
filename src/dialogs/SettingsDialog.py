import logging
from typing import List

from PyQt5.QtCore import Qt, QItemSelection, QSettings
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTreeView, QMdiSubWindow, QAbstractItemView, QWidget, \
    QPushButton, QStackedWidget, QMessageBox

from src.widgets.DeviceWidgetBase import DeviceWidgetBase
from src.widgets.settings.GeneralSettingsWidget import GeneralSettingsWidget
from src.widgets.settings.LayoutSettingsWidget import LayoutSettingsWidget


class SettingsDialog(QDialog):

    def __init__(self, subwindows: List[QMdiSubWindow], parent=None):
        super().__init__(parent)

        logging.debug("Creating settings dialog")

        # Disable "What's this" button
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)

        self.settings = QSettings("Mirosław Wiącek Code", "GLAD")

        self.setWindowTitle("Settings")

        # Set up the tree view
        self.tree_view = QTreeView()
        self.tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree_view.setFixedWidth(300)
        self.model = QStandardItemModel()
        self.tree_view.setModel(self.model)
        self.tree_view.selectionModel().selectionChanged.connect(self._on_tree_view_selection_changed)
        self.tree_view.setHeaderHidden(True)

        # Create "General" node
        self.general_settings_widget = GeneralSettingsWidget()
        self.general_node = QStandardItem("General")
        self.general_node.setData(self.general_settings_widget, Qt.UserRole)
        self.model.appendRow(self.general_node)

        # Create "Layouts" node
        self.layout_settings_widget = LayoutSettingsWidget()
        self.layouts_node = QStandardItem("Layouts")
        self.layouts_node.setData(self.layout_settings_widget, Qt.UserRole)
        self.model.appendRow(self.layouts_node)

        # Create and populate the "Widgets and devices" node
        self.widgets_node = QStandardItem("Widgets and devices")
        for subwindow in subwindows:
            item = QStandardItem(subwindow.windowTitle())
            item.setData(subwindow.widget(), Qt.UserRole)
            self.widgets_node.appendRow(item)
        self.model.appendRow(self.widgets_node)
        self.tree_view.setExpanded(self.widgets_node.index(), True)

        # Add button to wipe settings
        self.wipe_settings_button = QPushButton("Wipe settings")
        self.wipe_settings_button.clicked.connect(self._on_wipe_settings_clicked)

        # Set up the stacked widget
        self.stacked_widget = QStackedWidget()
        self.widget_cache = {}

        # Add all settings widgets to stacked widget
        self.stacked_widget.addWidget(self.general_settings_widget)
        self.stacked_widget.addWidget(self.layout_settings_widget)
        for subwindow in subwindows:
            widget = subwindow.widget().get_settings_widget()
            self.stacked_widget.addWidget(widget)

        # Arrange the widgets and layouts
        main_layout = QHBoxLayout()

        temp_layout = QVBoxLayout()
        temp_layout.addWidget(self.tree_view)
        temp_layout.addWidget(self.wipe_settings_button)
        main_layout.addLayout(temp_layout)

        temp_layout = QVBoxLayout()
        temp_layout.addWidget(self.stacked_widget)
        temp_layout.addStretch(1)

        # Button layout
        button_layout = QHBoxLayout()

        self.restore_defaults_button = QPushButton("Restore defaults")
        self.restore_defaults_button.clicked.connect(self._on_restore_defaults_clicked)
        button_layout.addWidget(self.restore_defaults_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel_clicked)

        button_layout.addWidget(self.cancel_button)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self._on_apply_clicked)
        button_layout.addWidget(self.apply_button)

        temp_layout.addLayout(button_layout)

        main_layout.addLayout(temp_layout)

        self.setLayout(main_layout)
        self.setFixedSize(800, 1000)

        # Move the focus away from "Wipe settings" button
        self.apply_button.setFocus()

        # Hide the buttons initially, because the general page is open
        self.restore_defaults_button.setHidden(True)
        self.cancel_button.setHidden(True)
        self.apply_button.setHidden(True)

        logging.debug("Dialog created")

    def _get_or_create_widget(self, identifier, creation_func, force_create: bool = False):
        if force_create or identifier not in self.widget_cache:
            logging.debug(f"{identifier} not in widget cache, creating")
            widget = creation_func()
            self.widget_cache[identifier] = widget
            self.stacked_widget.addWidget(widget)
        return self.widget_cache[identifier]

    def _on_tree_view_selection_changed(self, selected: QItemSelection, _deselected: QItemSelection):
        selected_item = selected.first().indexes()[0]
        data = selected_item.data(Qt.UserRole)

        if isinstance(data, DeviceWidgetBase):
            identifier = data.worker.device.internal_id
            widget = self._get_or_create_widget(identifier, data.get_settings_widget)
            self.stacked_widget.setCurrentWidget(widget)

            self.restore_defaults_button.setHidden(False)
            self.cancel_button.setHidden(False)
            self.apply_button.setHidden(False)
        elif isinstance(data, GeneralSettingsWidget):
            self.stacked_widget.setCurrentWidget(self.general_settings_widget)

            # Hide the buttons, as changes take immediate effect
            self.restore_defaults_button.setHidden(True)
            self.cancel_button.setHidden(True)
            self.apply_button.setHidden(True)
        elif isinstance(data, LayoutSettingsWidget):
            self.stacked_widget.setCurrentWidget(self.layout_settings_widget)

            # Hide the buttons, as changes take immediate effect
            self.restore_defaults_button.setHidden(True)
            self.cancel_button.setHidden(True)
            self.apply_button.setHidden(True)

        logging.debug(f"Current settings selection: {selected_item.data(Qt.DisplayRole)}")

    def _on_wipe_settings_clicked(self):
        # Ask the user for confirmation
        logging.info("Creating confirmation dialog for wiping settings")
        reply = QMessageBox.question(self, "Confirm action", "Are you sure you want to wipe all settings?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            logging.info(f"Wiping settings confirmed by user")
            # Clear all keys from settings
            self.settings.clear()

            QMessageBox(
                text="Settings wiped, restart the application for the changes to take effect",
                parent=self
            ).show()

    def _on_restore_defaults_clicked(self):
        selected_item = self.tree_view.selectionModel().currentIndex()
        data = selected_item.data(Qt.UserRole)
        logging.info(f"Restoring defaults for {selected_item.data(Qt.DisplayRole)}")
        if isinstance(data, DeviceWidgetBase):
            # Wipe the exising settings, which will force default values to be loaded on next startup
            data.erase_settings()
            message_box = QMessageBox(text="Defaults will be loaded on next application startup", parent=self)
            message_box.show()
        else:
            logging.error(f"No restore defaults for {type(data)}")

    def _on_cancel_clicked(self):
        selected_item = self.tree_view.selectionModel().currentIndex()
        data = selected_item.data(Qt.UserRole)

        if isinstance(data, DeviceWidgetBase):
            item_text = selected_item.data(Qt.DisplayRole)
            widget = self._get_or_create_widget(item_text, data.get_settings_widget, force_create=True)
            self.stacked_widget.setCurrentWidget(widget)
        elif isinstance(data, GeneralSettingsWidget):
            self.general_settings_widget = GeneralSettingsWidget()  # Recreate the widget
            self.stacked_widget.addWidget(self.general_settings_widget)
            self.stacked_widget.setCurrentWidget(self.general_settings_widget)
        elif isinstance(data, LayoutSettingsWidget):
            # Recreate the layout widget if necessary
            self.layout_settings_widget = LayoutSettingsWidget()  # Recreate the widget
            self.stacked_widget.addWidget(self.layout_settings_widget)
            self.stacked_widget.setCurrentWidget(self.layout_settings_widget)

        logging.debug(f"Cancel clicked for {selected_item.data(Qt.DisplayRole)}")

    def _on_apply_clicked(self):
        selected_item = self.tree_view.selectionModel().currentIndex()
        data: QWidget = selected_item.data(Qt.UserRole)

        if isinstance(data, DeviceWidgetBase):
            data.update_settings_from_widget(self.stacked_widget.currentWidget())
            data.apply_values_from_settings()
            self.model.setData(selected_item, data.worker.device.device_id(), Qt.DisplayRole)
        else:
            logging.error(
                f"Apply clicked, but '{type(data)}' doesn't have update_settings_from_widget or apply_values_from_settings"
            )
