import logging
from datetime import datetime, timedelta
from typing import Iterator, Dict, List, Tuple

import numpy as np
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel, QDoubleSpinBox, QPushButton, QDialog, QFrame, QVBoxLayout, QHBoxLayout, QGroupBox, \
    QFormLayout

from src.dialogs.StartProfileDialog import StartProfileDialog
from src.widgets.DeviceWidgetBase import DeviceWidgetBase
from src.widgets.PlotWidgetWithCrosshair import PlotWidgetWithCrosshair
from src.widgets.SlopeProfileEditor import SlopeProfileEditor
from src.workers.PD500X1Worker import PD500X1Worker


class PD500X1Widget(DeviceWidgetBase):
    def __init__(self, internal_id: str, mock: bool = False):
        super().__init__(internal_id, PD500X1Worker, mock)

        self.worker.activeTargetPowerReady.connect(self._on_active_target_power_ready)
        self.worker.actualPowerReady.connect(self._on_actual_power_ready)

        # Information whether the widget is currently collapsed, used for saving widget geometries
        self.is_collapsed = False

        self.power_x_values = []
        self.power_y_values = []

        # Profile executor variables
        self.is_profile_executing: bool = False
        self.profile_x_iterator: Iterator[float] = iter([])
        self.profile_y_iterator: Iterator[float] = iter([])
        self.profile_timer: QTimer = QTimer()
        self.profile_x_data = []
        self.profile_y_data = []

        self.profile_status_label = QLabel("Profile inactive")
        self.profile_status_timer = QTimer()
        self.profile_status_timer.timeout.connect(self.on_profile_status_timer_timeout)
        self.profile_status_timer.start(15000)

        # Set up fonts
        label_font = QFont()
        label_font.setPointSize(18)

        spinbox_font = QFont()
        spinbox_font.setPixelSize(20)

        button_font = QFont()
        button_font.setPixelSize(22)
        button_font.setBold(True)

        measurement_group_box = QGroupBox("Measurements")

        # measurement labels
        self.active_target_power_label = QLabel("0 W")
        self.active_target_power_label.setFont(label_font)
        self.actual_power_label = QLabel("0 W")
        self.actual_power_label.setFont(label_font)

        # Spinbox for power setpoint
        self.power_setpoint_spinbox = QDoubleSpinBox()
        self.power_setpoint_spinbox.setFont(spinbox_font)
        self.power_setpoint_spinbox.setRange(0, 9999)
        self.power_setpoint_spinbox.setPrefix("Setpoint ")
        self.power_setpoint_spinbox.setSuffix(" W")
        self.power_setpoint_spinbox.editingFinished.connect(self._on_power_setpoint_spinbox_editing_finished)

        # DC output toggle button
        self.dc_output_button = QPushButton("ENABLE DC")
        self.dc_output_button.setFont(button_font)
        self.dc_output_button.setFixedHeight(50)
        self.dc_output_button.clicked.connect(self._on_dc_output_button_clicked)

        self.plot_widget = PlotWidgetWithCrosshair(internal_id, has_profile=True)
        self.plot_widget.setMinimumHeight(200)
        self.plot_widget.setMaximumHeight(400)

        self.collapse_editor_button = QPushButton("▼")
        self.collapse_editor_button.clicked.connect(self._on_collapse_editor_button_clicked)

        self.profile_editor = SlopeProfileEditor(internal_id, 0, 500, "Power [W]", "W")

        self.profile_action_button = QPushButton("Start profile")
        self.profile_action_button.clicked.connect(self.open_start_configuration_dialog)

        # Construct and arrange the widgets and layouts
        measurements_layout = QFormLayout()

        # RX01 measurements
        temp_label = QLabel("Target: ")
        temp_label.setFont(label_font)
        measurements_layout.addRow(temp_label, self.active_target_power_label)
        temp_label = QLabel("Actual: ")
        temp_label.setFont(label_font)
        measurements_layout.addRow(temp_label, self.actual_power_label)

        measurement_group_box.setLayout(measurements_layout)

        left_layout = QVBoxLayout()

        left_layout.addWidget(measurement_group_box)
        left_layout.addWidget(self.dc_output_button)
        left_layout.addWidget(self.power_setpoint_spinbox)

        top_layout = QHBoxLayout()
        top_layout.addLayout(left_layout)
        top_layout.addWidget(self.plot_widget)

        # Wrap the top section in a frame to set minimum sizes
        self.control_panel_widget = QFrame()
        self.control_panel_widget.setLayout(top_layout)
        self.control_panel_widget.setMinimumSize(650, 400)

        self.layout().addWidget(self.profile_status_label)
        self.layout().addWidget(self.control_panel_widget)
        self.layout().addWidget(self.collapse_editor_button)
        self.layout().addWidget(self.profile_editor)
        self.layout().addWidget(self.profile_action_button)
        self.layout().addStretch(1)

        # After all the setup, start the worker thread
        self.thread.start()

    def get_measured_values(self) -> Dict[str, List[Tuple[int, float]]]:
        return {
            "Power": list(zip(self.power_x_values, self.power_y_values))
        }

    def clear_measured_values(self):
        self.power_x_values = []
        self.power_y_values = []

        self.plot_widget.measured_values_plot.setData([], [])

    def on_profile_status_timer_timeout(self):
        if self.is_profile_executing:
            self.profile_status_label.setText(f"Next point in {self.profile_editor.profile_plot.float_to_mm_ss(self.profile_timer.remainingTime()/60000)}")
        else:
            self.profile_status_label.setText("Profile inactive")

    def _on_dc_output_button_clicked(self):
        if self.worker.device.dc_output_enabled:
            self.worker.add_task(self.worker.device.disable_output)
            self.dc_output_button.setText("ENABLE DC")
        else:
            self.worker.add_task(self.worker.device.enable_output)
            self.dc_output_button.setText("DISABLE DC")

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

    def open_start_configuration_dialog(self):
        dialog = StartProfileDialog()
        result = dialog.exec()

        if result == QDialog.Accepted:
            self.start_power_profile(
                scheduled=dialog.scheduled_checkbox.isChecked(),
                # Remove components smaller than minutes, as they are not shown in the dialog
                start_date=dialog.datetime_picker.dateTime().toPyDateTime().replace(second=0, microsecond=0)
            )

    def start_power_profile(
            self,
            scheduled: bool,
            start_date: datetime = None
    ):
        # In this case, the values computed for the plot are what's important for the profile,
        # since they calculate the wanted power at given time point
        plot_points = self.profile_editor.get_profile_data_on_plot()
        plot_x_values, plot_y_values = plot_points[:, 0], plot_points[:, 1]
        profile_x_values, profile_y_values = plot_points[:, 0], plot_points[1:, 1]

        # convert profile_x_values into relative values for timers
        profile_x_values = np.diff(profile_x_values)

        if scheduled:
            timedelta_until_start: timedelta = start_date - datetime.now()

            # Check for negative time, if so, then the profile should start immediately anyway
            if not timedelta_until_start.total_seconds() < 0:
                # Add a new setpoint at the beginning with value 0 which will be held until the time the user has set
                profile_x_values = np.insert(profile_x_values, 0, timedelta_until_start.total_seconds() / 60)
                profile_y_values = np.insert(profile_y_values, 0, 0)

                # Shift all points in on the profile plot by the start delay
                plot_x_values = [p + timedelta_until_start.total_seconds() / 60 for p in plot_x_values]

        # Is a profile already executing?
        if self.is_profile_executing:
            return False

        # Length check
        if len(profile_x_values) != len(profile_y_values) or len(profile_x_values) < 1 or len(profile_y_values) < 1:
            return False

        # The X input values are relative to the time that they start. Therefore, we want to trigger the first point,
        # which is at t=0, immediately.
        self.profile_x_iterator = iter(profile_x_values)
        self.profile_y_iterator = iter(profile_y_values)

        # Draw the profile on the graph and convert x values to be relative to the current timestamp
        current_timestamp = datetime.now().timestamp()
        self.profile_x_data = [60 * x + current_timestamp for x in plot_x_values]
        self.profile_y_data = plot_y_values
        self.plot_widget.profile_values_plot.setData(self.profile_x_data, self.profile_y_data)

        self.is_profile_executing = True

        # Configure the UI
        self.profile_editor.setEnabled(False)
        self.power_setpoint_spinbox.setEnabled(False)
        self.profile_action_button.setText("Stop profile")
        self.profile_action_button.clicked.disconnect(self.open_start_configuration_dialog)
        self.profile_action_button.clicked.connect(self.stop_power_profile)

        # Enable DC output, firstly at 0
        self.worker.add_task(lambda: self.worker.device.set_active_target_power_setpoint(0))
        self.worker.add_task(self.worker.device.enable_output)
        self.dc_output_button.setText("DISABLE DC")

        # Restart the timer to have a clean slate
        self.profile_timer = QTimer()
        self.profile_timer.timeout.connect(self.apply_next_profile_point)
        self.profile_timer.start(0)

    def apply_next_profile_point(self):
        try:
            next_x, next_y = next(self.profile_x_iterator), next(self.profile_y_iterator)
        except StopIteration:
            self.on_profile_finished()
            return

        # Update the spinbox value
        self.power_setpoint_spinbox.blockSignals(True)
        self.power_setpoint_spinbox.setValue(int(next_y))
        self.power_setpoint_spinbox.blockSignals(False)

        self.worker.add_task(lambda: self.worker.device.set_active_target_ramp_time(next_x * 60))
        logging.info(f"Setting DC output ramp time = {next_x * 60} seconds")

        logging.info(f"Setting {next_y} W, next setpoint in {int(next_x * 60 * 1000)} msec")
        self.worker.add_task(lambda: self.worker.device.set_active_target_power_setpoint(next_y))

        self.profile_timer.setInterval(int(next_x * 60 * 1000))

    def stop_power_profile(self):
        # Clear the profile plot
        self.clear_plot_data(clear_measured=False, clear_profile=True)

        logging.info("Profile stopped")
        self.on_profile_finished()

    def on_profile_finished(self):
        # First, stop the timer and create a clean, new one, so no new setpoints are set
        if self.profile_timer:
            self.profile_timer.stop()

        # Create new empty iterators
        self.profile_x_iterator = iter([])
        self.profile_y_iterator = iter([])

        # Disable ramping
        self.worker.add_task(lambda: self.worker.device.set_active_target_ramp_time(0))

        # Disable DC output and set setpoint to 0W
        self.worker.add_task(self.worker.device.disable_output)
        self.worker.add_task(lambda: self.worker.device.set_active_target_power_setpoint(0))

        self.profile_editor.setEnabled(True)
        self.profile_action_button.setText("Start profile")
        try:
            self.profile_action_button.clicked.disconnect(self.stop_power_profile)
        except TypeError:
            pass
        self.profile_action_button.clicked.connect(self.open_start_configuration_dialog)
        self.power_setpoint_spinbox.setEnabled(True)

        self.is_profile_executing = False

        logging.info("Profile finished")

    def _on_power_setpoint_spinbox_editing_finished(self):
        self.worker.add_task(
            lambda: self.worker.device.set_active_target_power_setpoint(self.power_setpoint_spinbox.value())
        )

    def _on_active_target_power_ready(self, active_target_power: float):
        self.active_target_power_label.setText(f"{active_target_power:.2f} W")

    def _on_actual_power_ready(self, actual_power: float):
        self.actual_power_label.setText(f"{actual_power:.2f} W")
        self.power_x_values.append(datetime.now().timestamp())
        self.power_y_values.append(actual_power)

        self.plot_widget.measured_values_plot.setData(
            self.power_x_values,
            self.power_y_values
        )

    def clear_plot_data(self, clear_measured: bool = True, clear_profile: bool = True):
        if clear_measured:
            self.power_x_values = []
            self.power_y_values = []
            self.plot_widget.measured_values_plot.clear()

        if clear_profile:
            self.profile_x_data = []
            self.profile_y_data = []
            self.plot_widget.profile_values_plot.clear()
