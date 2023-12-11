import logging
from typing import Union

from PyQt5.QtCore import pyqtSignal, Qt, QSettings, QRect
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QMainWindow, QMdiArea, QAction, QMenu, QMessageBox, QInputDialog, QErrorMessage

from src.dialogs.LogViewingDialog import LogViewingDialog
from src.dialogs.MeasurementViewingDialog import MeasurementDialog
from src.dialogs.SettingsDialog import SettingsDialog
from src.widgets.bldc.BLDCWidget import BLDCWidget
from src.widgets.etc1103.ETC1103Widget import ETC1103Widget
from src.widgets.eurotherm_32h8i.TemperatureControllerWidget import TemperatureControllerWidget
from src.widgets.mks_mfc.MksEthWidget import MksEthWidget
from src.widgets.pd500x1.PD500X1Widget import PD500X1Widget
from src.widgets.rx01.RX01Widget import RX01Widget
from src.widgets.sr201.SR201Widget import SR201Widget
from src.widgets.stepper.StepperControllerWidget import StepperControllerWidget
from src.widgets.vgc403.VGC403Widget import VGC403Widget
from src.widgets.wp8026adam.WP8026ADAMWidget import WP8026ADAMWidget


class GLADMainWindow(QMainWindow):
    # Signal that the layouts, residing in the QSettings, have been updated
    layoutListUpdated = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.mdi = QMdiArea()

        self.setCentralWidget(self.mdi)

        self.setWindowTitle("GLAD")
        self.setGeometry(100, 100, 800, 600)

        self.view_measurements_action = QAction("View measurements", self)
        self.view_measurements_action.triggered.connect(self._on_view_measurements_action_triggered)

        self.clear_measurements_action = QAction("Clear measurements", self)
        self.clear_measurements_action.triggered.connect(self._on_clear_measurements_action_triggered)

        self.view_logs_dialog = LogViewingDialog()
        self.view_logs_action = QAction("View logs", self)
        self.view_logs_action.triggered.connect(self.view_logs_dialog.show)

        # View menu setup
        self.view_menu = QMenu(self)
        self.view_menu.setTitle("View")

        self.view_reset_positions_action = QAction("Reset window positions", self)
        self.view_reset_positions_action.triggered.connect(self._on_view_reset_positions_action_triggered)
        self.view_menu.addAction(self.view_reset_positions_action)

        self.view_layouts_menu = QMenu(self.view_menu)
        self.view_layouts_menu.setTitle("Layouts")

        self.view_menu.addMenu(self.view_layouts_menu)

        # Settings setup
        self.settings_action = QAction("Settings", self)
        self.settings_action.triggered.connect(self._on_settings_action_triggered)

        self.menuBar().addAction(self.clear_measurements_action)
        self.menuBar().addAction(self.view_measurements_action)
        self.menuBar().addAction(self.view_logs_action)
        self.menuBar().addMenu(self.view_menu)
        self.menuBar().addAction(self.settings_action)

        for widget in [
            # VGC403Widget("MockVGC403--63857dce-704a-11ee-8df0-e0d4e8da970a", mock=True),
            # ETC1103Widget("MockETC1103--28f0ffc0-704b-11ee-872d-e0d4e8da970a", mock=True),
            # RX01Widget("MockRX01--862d8c5d-704b-11ee-8d3c-e0d4e8da970a", mock=True),
            # RX01Widget("MockRX01--9f4221da-704b-11ee-9459-e0d4e8da970a", mock=True),
            # TemperatureControllerWidget("MockTempController32h8i--7d00b3cc-704e-11ee-9adb-e0d4e8da970a", mock=True),
            # MksEthWidget("MockMksEthMfc--0463a0e7-704e-11ee-a05a-e0d4e8da970a", mock=True),
            # MksEthWidget("MockMksEthMfc--0f099dd3-704e-11ee-8823-e0d4e8da970a", mock=True),
            # PD500X1Widget("MockPD500X1--f834dfec-0019-4d27-8778-dd80913a1a8e", mock=True),
            # StepperControllerWidget("MockStepper--842daf7e-c236-4368-9102-1a2b4a8ae9f8", mock=True),
            # WP8026ADAMWidget("MockWP8026ADAM--9f99058b-bbd3-46e7-88af-5139ca4d23dc", mock=True),
            # SR201Widget("MockSR201--5f9eebc0-5d0b-489d-b142-2c5d3bec5fc8", mock=True),
            BLDCWidget("MockBLDC--646b9cce-0504-4700-a7cf-8f481a2dd114", mock=True),
            # VGC403Widget("VGC403--bcb7c326-dff5-4a21-8732-5f220b17fffb", mock=False),
            # ETC1103Widget("ETC1103--8c55fad3-70fb-11ee-9a31-e0d4e8da970a", mock=False),
            # RX01Widget("RX01--e043db01-647c-47fb-8e92-ba44ee4bed43", mock=False),
            # RX01Widget("RX01--f3800f60-0029-46d6-9b06-5214b9cf471b", mock=False),
            # TemperatureControllerWidget("TempController32h8i--c832a0b7-9c41-43db-91b0-6a2d3", mock=False),
            # MksEthWidget("MksEthMfc--dfe480e9-2dfc-443b-81a1-364178321974", mock=False),
            # MksEthWidget("MksEthMfc--73f5ae1a-27b7-442a-837b-abf725ce2acb", mock=False),
            # PD500X1Widget("PD500X1--e5beac89-e62d-4722-b1cc-c604240db7d0", mock=False),
            # StepperControllerWidget("Stepper--0b98b204-e225-424a-91f9-d2a6aeeffc25", mock=False),
            # WP8026ADAMWidget("WP8026ADAM--05f87033-fa59-441f-baa1-3ed976431938", mock=False),
            # SR201Widget("SR201--82554b18-e3a3-4ac3-983b-88812b010e4f", mock=False),
            # BLDCWidget("BLDC--13c87134-d309-4e95-9b4b-988308aba46c", mock=False),
        ]:
            # Disable the close button on every subwindow
            subwindow = self.mdi.addSubWindow(widget, Qt.WindowType.WindowMinMaxButtonsHint)
            subwindow.setWindowTitle(str(widget))

            widget.sizeChanged.connect(subwindow.adjustSize)

        self._update_layout_list()
        self.load_saved_geometries()

        self.layoutListUpdated.connect(self._update_layout_list)

    def closeEvent(self, event: QCloseEvent):
        self.save_geometries()

        # Check if a 32h8i widget is defined, and if yes, warn the user that the setpoint might change
        if any([isinstance(subwindow.widget(), TemperatureControllerWidget) for subwindow in self.mdi.subWindowList()]):
            result = QMessageBox.question(
                self,
                "Ensure 32h8i panel setpoint",
                "When you close the application, the 32h8i heater will revert to the setpoint on the panel. "
                "Close the application?"
            )

            if result == QMessageBox.No:
                event.ignore()
                return

        event.accept()

    def _update_layout_list(self):
        for action in self.view_layouts_menu.actions():
            self.view_layouts_menu.removeAction(action)

        self.view_layouts_save_layout_action = QAction("Save current layout", self.view_layouts_menu)
        self.view_layouts_save_layout_action.triggered.connect(self._on_save_layout_action_triggered)

        self.view_layouts_menu.addAction(self.view_layouts_save_layout_action)

        layout_name_list = self._get_layout_name_list()
        if layout_name_list:
            # If any layouts exist, add a separator before listing them
            self.view_layouts_menu.addSeparator()
            for name in layout_name_list:
                change_layout_action = QAction(name, self.view_layouts_menu)
                # name=name captures the iteration value, rather than iterator variable reference
                change_layout_action.triggered.connect(
                    lambda _, name=name: self._on_change_layout_action_triggered(name)
                )
                self.view_layouts_menu.addAction(change_layout_action)

    def save_geometries(self):
        settings = QSettings("Mirosław Wiącek Code", "GLAD")
        # Save the main window maximized state
        settings.setValue("window_maximized", self.isMaximized())
        # Save the main window geometry
        settings.setValue("window_geometry", self.geometry())

        # Save QMdiSubWindow positions and sizes
        for subwindow in self.mdi.subWindowList():
            key = subwindow.widget().worker.device.internal_id
            settings.beginGroup(key)
            settings.setValue("geometry", subwindow.geometry())
            settings.setValue("minimized", subwindow.isMinimized())
            settings.setValue("maximized", subwindow.isMaximized())
            if hasattr(subwindow.widget(), "is_collapsed"):
                settings.setValue("collapsed", subwindow.widget().is_collapsed)
            settings.endGroup()

    def load_saved_geometries(self):
        settings = QSettings("Mirosław Wiącek Code", "GLAD")
        # Restore window's maximized state
        wasMaximized = settings.value("window_maximized", defaultValue=False, type=bool)
        if wasMaximized:
            self.showMaximized()
        else:
            self.setGeometry(settings.value("window_geometry", defaultValue=self.geometry()))

        # Restore QMdiSubWindow positions and sizes
        for subwindow in self.mdi.subWindowList():
            key = subwindow.widget().worker.device.internal_id
            settings.beginGroup(key)

            geometry: QRect = settings.value("geometry", defaultValue=subwindow.geometry())
            minimized: Union[bool, str] = settings.value("minimized", defaultValue=False)
            maximized: Union[bool, str] = settings.value("maximized", defaultValue=False)
            collapsed = settings.value("collapsed", defaultValue=None)

            subwindow.setGeometry(geometry)
            if minimized is True:
                subwindow.showMinimized()
            elif maximized is True:
                subwindow.showMaximized()
            else:
                subwindow.showNormal()

            if collapsed == "true" and not subwindow.widget().is_collapsed:
                subwindow.widget()._on_collapse_editor_button_clicked()

            settings.endGroup()

    def _on_view_measurements_action_triggered(self):
        dialog = MeasurementDialog([subwindow.widget() for subwindow in self.mdi.subWindowList()], parent=self)
        dialog.show()

    def _on_clear_measurements_action_triggered(self):
        # Ask the user for confirmation
        reply = QMessageBox.question(self, "Confirm action", "Are you sure you want to wipe all measurements?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            for subwindow in self.mdi.subWindowList():
                subwindow.widget().clear_measured_values()

    def _on_view_reset_positions_action_triggered(self):
        for subwindow in self.mdi.subWindowList():
            subwindow.showNormal()
            subwindow.move(0, 0)
            subwindow.resize(0, 0)
            subwindow.adjustSize()

    @staticmethod
    def _get_layout_name_list():
        settings = QSettings("Mirosław Wiącek Code", "GLAD")
        settings.beginGroup("layouts")
        layout_list = {name.split(sep="/")[0] for name in settings.allKeys()}
        settings.endGroup()
        return layout_list

    def _on_save_layout_action_triggered(self):
        settings = QSettings("Mirosław Wiącek Code", "GLAD")
        text, ok = QInputDialog.getText(self, "Choose layout name", "Name")

        if ok:
            # Check if the user typed in any text
            if not text:
                QErrorMessage().showMessage("Choose a layout name!")
                return

            # check if name exists
            if text in self._get_layout_name_list():
                QErrorMessage().showMessage("Layout already exists with this name!")
                return

            settings.beginGroup("layouts")
            settings.beginGroup(text)
            for subwindow in self.mdi.subWindowList():
                key = subwindow.widget().worker.device.internal_id
                settings.beginGroup(key)
                settings.setValue("geometry", subwindow.geometry())
                if hasattr(subwindow.widget(), "is_collapsed"):
                    settings.setValue("collapsed", subwindow.widget().is_collapsed)
                settings.endGroup()

            settings.endGroup()
            settings.endGroup()

            self.layoutListUpdated.emit()

    def _on_change_layout_action_triggered(self, layout_name: str):
        settings = QSettings("Mirosław Wiącek Code", "GLAD")
        if layout_name not in self._get_layout_name_list():
            logging.error(f"Layout {layout_name} not in layouts")
            return

        settings.beginGroup("layouts")
        settings.beginGroup(layout_name)

        layout_window_internal_ids = settings.childGroups()

        if len(layout_window_internal_ids) == 0:
            logging.error(f"Layout {layout_name} has no window geometries defined")

        for subwindow in self.mdi.subWindowList():
            key = subwindow.widget().worker.device.internal_id
            if key in layout_window_internal_ids:
                settings.beginGroup(key)
                subwindow.setGeometry(settings.value("geometry"))
                if settings.value("collapsed", defaultValue=None) == "true" and not subwindow.widget().is_collapsed:
                    subwindow.widget()._on_collapse_editor_button_clicked()
                settings.endGroup()

        settings.endGroup()
        settings.endGroup()

    def _on_settings_action_triggered(self):
        # Creating the dialog everytime it is requested ensures that it has up-to-date information
        settings_dialog = SettingsDialog(self.mdi.subWindowList(), parent=self)
        settings_dialog.layout_settings_widget.layoutListUpdated.connect(self._update_layout_list)
        settings_dialog.show()
