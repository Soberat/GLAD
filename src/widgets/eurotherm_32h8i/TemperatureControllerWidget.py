import logging

from datetime import datetime, timedelta
from typing import Iterator, Tuple, List, Dict

import numpy as np
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import QPushButton, QDialog, QHBoxLayout, QVBoxLayout, QLabel, QDoubleSpinBox, QCheckBox, QFrame

from src.dialogs.StartProfileDialog import StartProfileDialog
from src.widgets.DeviceWidgetBase import DeviceWidgetBase
from src.widgets.PlotWidgetWithCrosshair import PlotWidgetWithCrosshair
from src.widgets.ProfileEditor import ProfileEditor
from src.workers.TempControllerWorker import TempControllerWorker


class TemperatureControllerWidget(DeviceWidgetBase):
    def __init__(self, internal_id: str, mock: bool = False):
        super().__init__(internal_id, TempControllerWorker, mock)

        self.worker.processValueReady.connect(self._on_process_value_ready)
        self.worker.setpointReady.connect(self._on_setpoint_value_ready)

        self.lower_temperature_bound: float = 0
        self.upper_temperature_bound: float = 250

        # Profile executor variables
        self.is_profile_executing: bool = False
        self.profile_x_iterator: Iterator[float] = iter([])
        self.profile_y_iterator: Iterator[float] = iter([])
        self.profile_timer: QTimer = QTimer()
        self.profile_x_data = []
        self.profile_y_data = []

        # Font setup
        label_font = QFont()
        label_font.setPointSize(18)

        self.temperature_x_values = []
        self.temperature_y_values = []

        self.setpoint_x_values = []
        self.setpoint_y_values = []

        self.profile_status_label = QLabel("Profile inactive")
        self.profile_status_timer = QTimer()
        self.profile_status_timer.timeout.connect(self.on_profile_status_timer_timeout)
        self.profile_status_timer.start(15000)

        self.plot_widget = PlotWidgetWithCrosshair(internal_id, has_profile=True)
        self.plot_widget.setMaximumHeight(450)

        # Temporary plot for setpoint
        self.setpoint_plot_data = self.plot_widget.plot(
            [],
            pen=QColor("maroon"),
            symbolBrush=QColor("maroon"),
            symbolPen=QColor("maroon"),
            symbol="o",
            symbolSize=5,
            name="Setpoint"
        )

        self.process_value_label = QLabel("PV: N/A ℃")
        self.process_value_label.setFont(label_font)

        self.setpoint_value_label = QLabel("SP: N/A ℃")
        self.setpoint_value_label.setFont(label_font)

        self.setpoint_value_spinbox = QDoubleSpinBox()
        self.setpoint_value_spinbox.setSuffix(" ℃")
        self.setpoint_value_spinbox.setFont(label_font)
        self.setpoint_value_spinbox.setRange(self.lower_temperature_bound, self.upper_temperature_bound)
        self.setpoint_value_spinbox.editingFinished.connect(self._on_setpoint_value_spinbox_editing_finished)

        self.setpoint_control_enabled = QCheckBox("Control enabled")
        self.setpoint_control_enabled.setToolTip("Disabling control will set the setpoint to 0,"
                                                 " and will not allow the app to set any further setpoints")
        self.setpoint_control_enabled.setChecked(False)
        self.setpoint_control_enabled.stateChanged.connect(self._on_setpoint_control_changed)
        self.setpoint_value_spinbox.setEnabled(self.setpoint_control_enabled.isChecked())

        self.profile_editor = ProfileEditor(
            internal_id,
            self.lower_temperature_bound,
            self.upper_temperature_bound,
            "Temperature [℃]",
            " ℃"
        )

        self.collapse_editor_button = QPushButton("▼")
        self.collapse_editor_button.clicked.connect(self._on_collapse_editor_button_clicked)

        self.profile_action_button = QPushButton("Start profile")
        self.profile_action_button.clicked.connect(self.open_start_configuration_dialog)

        # Arrange the widgets and layouts
        # Top section with plot, PV/SP displays and SP spinbox, always visible
        control_panel_layout = QHBoxLayout()

        vbox_layout = QVBoxLayout()  # Create a QVBoxLayout for QLabels
        vbox_layout.addWidget(self.process_value_label)  # Add to QVBoxLayout
        vbox_layout.addWidget(self.setpoint_value_label)  # Add to QVBoxLayout
        vbox_layout.addWidget(self.setpoint_value_spinbox)
        vbox_layout.addWidget(self.setpoint_control_enabled)
        vbox_layout.addStretch(1)

        control_panel_layout.addLayout(vbox_layout)
        control_panel_layout.addWidget(self.plot_widget)

        # Wrap the layout in a QFrame, so we can set size limits
        self.control_panel_widget = QFrame()
        self.control_panel_widget.setLayout(control_panel_layout)
        self.control_panel_widget.setMinimumHeight(300)
        self.control_panel_widget.setMaximumHeight(450)

        self.layout().addWidget(self.profile_status_label)
        self.layout().addWidget(self.control_panel_widget)

        self.layout().addWidget(self.collapse_editor_button)
        self.layout().addWidget(self.profile_editor)

        self.layout().addWidget(self.profile_action_button)

        self.setMinimumWidth(600)

        # Information whether the widget is currently collapsed, used for saving widget geometries
        self.is_collapsed = False

        # After all the setup, start the worker thread
        self.thread.start()

    def get_measured_values(self) -> Dict[str, List[Tuple[int, float]]]:
        return {
            "Temperature": list(zip(self.temperature_x_values, self.temperature_y_values))
        }

    def clear_measured_values(self):
        self.temperature_x_values = []
        self.temperature_y_values = []
        self.plot_widget.measured_values_plot.clear()

        self.setpoint_x_values = []
        self.setpoint_y_values = []
        self.setpoint_plot_data.clear()

    def on_profile_status_timer_timeout(self):
        if self.is_profile_executing:
            self.profile_status_label.setText(f"Next point in {self.profile_editor.profile_plot.float_to_mm_ss(self.profile_timer.remainingTime()/60000)}")
        else:
            self.profile_status_label.setText("Profile inactive")

    def open_start_configuration_dialog(self):
        dialog = StartProfileDialog()
        result = dialog.exec()

        if result == QDialog.Accepted:
            return self.start_temperature_profile(
                scheduled=dialog.scheduled_checkbox.isChecked(),
                # Remove components smaller than minutes, as they are not shown in the dialog
                start_date=dialog.datetime_picker.dateTime().toPyDateTime().replace(second=0, microsecond=0)
            )
        else:
            return False

    def start_temperature_profile(
            self,
            scheduled: bool,
            start_date: datetime = None
    ):
        x, y = self.profile_editor.get_profile_data()

        plot_points = self.profile_editor.get_profile_data_on_plot()
        plot_x_values, plot_y_values = plot_points[:, 0], plot_points[:, 1]

        if scheduled:
            timedelta_until_start: timedelta = start_date - datetime.now()

            # Check for negative time, if so, then the profile should start immediately anyway
            if not timedelta_until_start.total_seconds() < 0:
                # Add a new setpoint at the beginning, which will be the current setpoint, and it will be held until
                # the time the user has set
                x = np.insert(x, 0, timedelta_until_start.total_seconds() / 60)
                y = np.insert(y, 0, self.setpoint_value_spinbox.value())

                # Shift all points in on the profile plot by the start delay
                plot_x_values = [p + timedelta_until_start.total_seconds() / 60 for p in plot_x_values]

        # Is a profile already executing?
        if self.is_profile_executing:
            return False

        # Length check
        if len(x) != len(y) or len(x) <= 1 or len(y) <= 1:
            return False

        # The X input values are relative to the time that they start. Therefore, we want to trigger the first point,
        # which is at t=0, immediately.
        self.profile_x_iterator = iter(x)
        self.profile_y_iterator = iter(y)

        # Convert x_values to be relative to the current timestamp
        current_timestamp = datetime.now().timestamp()

        self.profile_x_data = [60 * x + current_timestamp for x in plot_x_values]
        self.profile_y_data = plot_y_values

        # Draw the profile on the graph
        self.plot_widget.profile_values_plot.setData(self.profile_x_data, plot_y_values)

        self.is_profile_executing = True

        # Restart the timer to have a clean slate
        self.profile_timer = QTimer()
        self.profile_timer.timeout.connect(self.apply_next_profile_point)
        self.profile_timer.start(0)

        self.profile_action_button.setText("Stop profile")
        self.profile_action_button.clicked.disconnect(self.open_start_configuration_dialog)
        self.profile_action_button.clicked.connect(self.stop_temperature_profile)

        self.profile_editor.setEnabled(False)

        self.setpoint_control_enabled.setChecked(True)
        self.setpoint_value_spinbox.setEnabled(False)

    def apply_next_profile_point(self):
        try:
            next_x, next_y = next(self.profile_x_iterator), next(self.profile_y_iterator)
        except StopIteration:
            self.on_profile_finished()
            return

        # Update the spinbox value
        self.setpoint_value_spinbox.blockSignals(True)
        self.setpoint_value_spinbox.setValue(next_y)
        self.setpoint_value_spinbox.blockSignals(False)

        self.worker.add_task(lambda: self.worker.device.set_setpoint_value(next_y))

        logging.info(f"Setting {next_y} deg C, next setpoint in {int(60 * 1000 * next_x)} msec")

        self.profile_timer.setInterval(int(60 * 1000 * next_x))

    def stop_temperature_profile(self):
        # Clear the profile plot
        self.clear_plot_data(clear_measured=False, clear_profile=True)

        self.on_profile_finished()
        logging.info("Profile stopped")

    def on_profile_finished(self):
        # First, stop the timer, so no new setpoints are set
        if self.profile_timer:
            self.profile_timer.stop()

        # Create new empty iterators
        self.profile_x_iterator = iter([])
        self.profile_y_iterator = iter([])

        self.profile_editor.setEnabled(True)
        self.profile_action_button.setText("Start profile")
        try:
            self.profile_action_button.clicked.disconnect(self.stop_temperature_profile)
        except TypeError:
            pass
        self.profile_action_button.clicked.connect(self.open_start_configuration_dialog)
        self.setpoint_value_spinbox.setEnabled(True)

        self.is_profile_executing = False

        logging.info("Profile finished")
        
    def _on_process_value_ready(self, value: float):
        self.process_value_label.setText(f"PV: {value:.2f} ℃")
        self.temperature_x_values.append(datetime.now().timestamp())
        self.temperature_y_values.append(value)

        self.plot_widget.measured_values_plot.setData(
            self.temperature_x_values,
            self.temperature_y_values
        )

    def _on_setpoint_value_ready(self, value: float):
        self.setpoint_x_values.append(datetime.now().timestamp())
        self.setpoint_y_values.append(value)
        self.setpoint_value_label.setText(f"SP: {value:.2f} ℃")

        self.setpoint_plot_data.setData(
            self.setpoint_x_values,
            self.setpoint_y_values
        )

    def _on_setpoint_value_spinbox_editing_finished(self):
        self.worker.add_task(lambda: self.worker.device.set_setpoint_value(self.setpoint_value_spinbox.value()))

    def _on_setpoint_control_changed(self, new_state: Qt.CheckState):
        is_control_enabled = new_state == Qt.Checked

        self.worker.add_task(lambda: self.worker.device.toggle_control(is_control_enabled))
        self.setpoint_value_spinbox.setEnabled(is_control_enabled and not self.is_profile_executing)

        if not is_control_enabled:
            self.setpoint_value_spinbox.setValue(20)
            self.worker.add_task(lambda: self.worker.device.set_setpoint_value(20))

    def _on_collapse_editor_button_clicked(self):
        if not self.profile_editor.isHidden():
            self.profile_editor.setHidden(True)
            self.profile_action_button.setHidden(True)
            self.control_panel_widget.resize(self.control_panel_widget.width(),
                                             self.control_panel_widget.maximumHeight())
            self.resize(self.width(), 0)
            self.collapse_editor_button.setText("▼")
        else:
            self.profile_editor.setHidden(False)
            self.profile_action_button.setHidden(False)
            self.control_panel_widget.resize(self.control_panel_widget.width(),
                                             self.control_panel_widget.minimumHeight())
            self.control_panel_widget.adjustSize()
            self.collapse_editor_button.setText("▼")

        self.is_collapsed = self.profile_editor.isHidden()

        self.adjustSize()
        self.sizeChanged.emit()

    def clear_plot_data(self, clear_measured: bool = True, clear_profile: bool = True):
        if clear_measured:
            self.temperature_x_values = []
            self.temperature_y_values = []
            self.plot_widget.measured_values_plot.clear()

        if clear_profile:
            self.profile_x_data = []
            self.profile_y_data = []
            self.plot_widget.profile_values_plot.clear()
