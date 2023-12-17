import logging

from datetime import datetime, timedelta
from typing import Iterator, Dict, List, Tuple

import numpy as np
from PyQt5.QtCore import QTimer, QThread
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QGroupBox, QPushButton, QHBoxLayout, QSpinBox, QDialog, QWidget, \
    QComboBox, QFrame, QFormLayout
from serial.tools.list_ports_windows import comports

from src.dialogs.StartProfileDialog import StartProfileDialog
from src.drivers.rx01.RX01 import RX01
from src.widgets.DeviceWidgetBase import DeviceWidgetBase
from src.widgets.PlotWidgetWithCrosshair import PlotWidgetWithCrosshair
from src.widgets.SlopeProfileEditor import SlopeProfileEditor
from src.workers.MC2Worker import MC2Worker
from src.workers.RX01Worker import RX01Worker


class RX01Widget(DeviceWidgetBase):

    def __init__(self, internal_id: str, mock: bool = False):
        super().__init__(internal_id, RX01Worker, mock)

        self.worker.forwardPowerReady.connect(self._on_forward_power_ready)
        self.worker.reflectedPowerReady.connect(self._on_reflected_power_ready)
        self.worker.dcBiasVoltageReady.connect(self._on_dc_bias_voltage_ready)
        self.worker.rfOutputEnabledReady.connect(self._on_rf_output_enabled_ready)

        # Additional setup for MC2, as this widget represents a combination of those
        self.mc2_worker: MC2Worker = MC2Worker(internal_id, mock)

        # Setup separate thread for the MC2 worker
        self.mc2_thread = QThread()
        self.mc2_worker.moveToThread(self.mc2_thread)
        self.mc2_thread.started.connect(self.mc2_worker.run)

        self.mc2_worker.periodic_function_failed.connect(self.status_indicator.on_negative_status)
        self.mc2_worker.periodic_function_successful.connect(self.status_indicator.on_positive_status)
        self.mc2_worker.task_failed.connect(self.status_indicator.on_negative_status)
        self.mc2_worker.task_successful.connect(self.status_indicator.on_positive_status)
        self.mc2_worker.loadCapPositionReady.connect(self._on_load_cap_position_ready)
        self.mc2_worker.tuneCapPositionReady.connect(self._on_tune_cap_position_ready)

        # Information whether the widget is currently collapsed, used for saving widget geometries
        self.is_collapsed = False

        # Profile executor variables
        self.current_setpoint_value = 0
        self.is_profile_executing: bool = False
        self.profile_x_iterator: Iterator[float] = iter([])
        self.profile_y_iterator: Iterator[float] = iter([])
        self.profile_timer: QTimer = QTimer()
        self.profile_x_data = []
        self.profile_y_data = []

        self.power_x_values = []
        self.power_y_values = []

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

        # RX01 value labels
        self.forward_power_label = QLabel("N/A W")
        self.reflected_power_label = QLabel("N/A W")
        self.dc_bias_label = QLabel("N/A V")

        # MC2 value labels
        self.tune_label = QLabel("N/A %")
        self.load_label = QLabel("N/A %")

        # Spinbox for power setpoint
        self.power_setpoint_spinbox = QSpinBox()
        self.power_setpoint_spinbox.setFont(spinbox_font)
        self.power_setpoint_spinbox.setRange(0, 9999)
        self.power_setpoint_spinbox.setPrefix("Setpoint ")
        self.power_setpoint_spinbox.setSuffix(" W")
        self.power_setpoint_spinbox.editingFinished.connect(self._on_power_setpoint_spinbox_editing_finished)

        # RF output toggle button
        self.rf_output_button = QPushButton("ENABLE RF")
        self.rf_output_button.setFont(button_font)
        self.rf_output_button.setFixedHeight(50)
        self.rf_output_button.clicked.connect(self._on_rf_output_button_clicked)

        # Tune preset spinbox
        self.tune_spinbox = QSpinBox()
        self.tune_spinbox.setFont(spinbox_font)
        self.tune_spinbox.setRange(0, 100)
        self.tune_spinbox.setPrefix("Tune preset ")
        self.tune_spinbox.setSuffix(" %")
        self.tune_spinbox.editingFinished.connect(self._on_tune_spinbox_editing_finished)

        # Load preset spinbox
        self.load_spinbox = QSpinBox()
        self.load_spinbox.setFont(spinbox_font)
        self.load_spinbox.setRange(0, 100)
        self.load_spinbox.setPrefix("Load preset ")
        self.load_spinbox.setSuffix(" %")
        self.load_spinbox.editingFinished.connect(self._on_load_spinbox_editing_finished)

        # Automatic/manual tune/load toggle button
        self.auto_manual_button = QPushButton("ASSERT AUTO")
        self.auto_manual_button.setFont(button_font)
        self.auto_manual_button.setFixedHeight(50)
        self.auto_manual_button.clicked.connect(self._on_auto_manual_button_clicked)

        self.plot_widget = PlotWidgetWithCrosshair(internal_id, has_profile=True)
        self.plot_widget.setMaximumHeight(450)

        self.collapse_editor_button = QPushButton("▼")
        self.collapse_editor_button.clicked.connect(self._on_collapse_editor_button_clicked)

        self.profile_editor = SlopeProfileEditor(self.worker.device.internal_id, 0, 300, "Power [W]", "W")

        self.profile_action_button = QPushButton("Start profile")
        logging.critical("Connect start in init")
        self.profile_action_button.clicked.connect(self.open_start_configuration_dialog)

        # Construct and arrange the widgets and layouts
        measurements_layout = QFormLayout()

        # RX01 measurements
        for static_text, value_label in [
            ("Forward power: ", self.forward_power_label),
            ("Reflected: ", self.reflected_power_label),
            ("DC bias: ", self.dc_bias_label),
            ("Tune: ", self.tune_label),
            ("Load: ", self.load_label)
        ]:
            temp_label = QLabel(static_text)
            temp_label.setFont(label_font)

            value_label.setFont(label_font)

            measurements_layout.addRow(temp_label, value_label)

        measurement_group_box.setLayout(measurements_layout)

        left_layout = QVBoxLayout()

        left_layout.addWidget(measurement_group_box)
        left_layout.addWidget(self.rf_output_button)
        left_layout.addWidget(self.auto_manual_button)
        left_layout.addWidget(self.power_setpoint_spinbox)
        left_layout.addWidget(self.load_spinbox)
        left_layout.addWidget(self.tune_spinbox)

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

        # After all the setup, start the worker threads
        self.thread.start()
        self.mc2_thread.start()

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

    def open_start_configuration_dialog(self):
        dialog = StartProfileDialog()
        result = dialog.exec()

        if result == QDialog.Accepted:
            return self.start_power_profile(
                scheduled=dialog.scheduled_checkbox.isChecked(),
                # Remove components smaller than minutes, as they are not shown in the dialog
                start_date=dialog.datetime_picker.dateTime().toPyDateTime().replace(second=0, microsecond=0)
            )
        else:
            return False

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
        logging.critical("Disconnect start in start_profile")
        self.profile_action_button.clicked.disconnect(self.open_start_configuration_dialog)
        self.profile_action_button.clicked.connect(self.stop_power_profile)

        # Enable RF output ramping
        self.worker.add_task(self.worker.device.enable_rf_output_ramping)

        # Enable RF output, firstly at 0
        self.worker.add_task(lambda: self.worker.device.set_power_setpoint_and_enable_rf_output(0))
        self.rf_output_button.setText("DISABLE RF")

        # Restart the timer to have a clean slate
        self.profile_timer = QTimer()
        self.profile_timer.timeout.connect(self.apply_next_profile_point)
        self.profile_timer.start(0)

        # Process starting successful
        return True

    def apply_next_profile_point(self):
        try:
            # Round off the y value, since RX01 does not accept decimal values
            next_x, next_y = next(self.profile_x_iterator), int(next(self.profile_y_iterator))
        except StopIteration:
            self.on_profile_finished()
            return

        # Update the spinbox value
        self.power_setpoint_spinbox.blockSignals(True)
        self.power_setpoint_spinbox.setValue(int(next_y))
        self.power_setpoint_spinbox.blockSignals(False)

        # Depending on the sign of the slope, we have to set different parameters
        if next_y - self.current_setpoint_value > 0:
            self.worker.add_task(lambda: self.worker.device.set_rf_output_rampup_time_interval(int(next_x * 60)))
            logging.info(f"Setting RF output ramp up time = {int(next_x * 60)} seconds")
        elif next_y - self.current_setpoint_value < 0:
            self.worker.add_task(lambda: self.worker.device.set_rf_output_rampdown_time_interval(int(next_x * 60)))
            logging.info(f"Setting RF output ramp down time = {int(next_x * 60)} seconds")

        logging.info(f"Setting {next_y} W, next setpoint in {int(next_x * 60 * 1000)} msec")
        self.worker.add_task(lambda: self.worker.device.set_power_setpoint(next_y))
        self.current_setpoint_value = next_y

        self.profile_timer.setInterval(int(next_x * 60 * 1000))

    def stop_power_profile(self):
        # Clear the profile plot
        self.clear_plot_data(clear_measured=False, clear_profile=True)

        # Disable RF output
        self.worker.add_task(self.worker.device.disable_power_and_rf_output)

        logging.info("Profile stopped")
        self.on_profile_finished()

    def on_profile_finished(self):
        # First, stop the timer and create a clean, new one, so no new setpoints are set
        if self.profile_timer:
            self.profile_timer.stop()

        # Create new empty iterators
        self.profile_x_iterator = iter([])
        self.profile_y_iterator = iter([])

        # Disable RF output ramping
        self.worker.add_task(self.worker.device.disable_rf_output_ramping)

        # Disable RF output and set setpoint to 0W
        self.worker.add_task(self.worker.device.disable_rf_output)
        self.worker.add_task(lambda: self.worker.device.set_power_setpoint(0))

        self.profile_editor.setEnabled(True)
        self.profile_action_button.setText("Start profile")
        try:
            self.profile_action_button.clicked.disconnect(self.stop_power_profile)
        except TypeError:
            pass
        logging.critical("Connect start in on_profile_finished")
        self.profile_action_button.clicked.connect(self.open_start_configuration_dialog)
        self.power_setpoint_spinbox.setEnabled(True)

        self.is_profile_executing = False

        self.worker.add_task(self.worker.device.disable_rf_output_ramping)

        logging.info("Profile finished")

    def _on_forward_power_ready(self, forward_power: float):
        self.forward_power_label.setText(f"{round(forward_power, 2)} W")
        self.power_x_values.append(datetime.now().timestamp())
        self.power_y_values.append(forward_power)

        self.plot_widget.measured_values_plot.setData(
            self.power_x_values,
            self.power_y_values
        )

    def _on_reflected_power_ready(self, reflected_power: float):
        self.reflected_power_label.setText(f"{reflected_power} W")

    def _on_dc_bias_voltage_ready(self, dc_bias_voltage: int):
        self.dc_bias_label.setText(f"{dc_bias_voltage} V")

    def _on_load_cap_position_ready(self, load_cap_position: int):
        self.load_label.setText(f"{load_cap_position} %")

    def _on_tune_cap_position_ready(self, tune_cap_position: int):
        self.tune_label.setText(f"{tune_cap_position} %")

    def _on_rf_output_enabled_ready(self, rf_output_enabled: bool):
        self.rf_output_button.setText("DISABLE RF" if rf_output_enabled else "ENABLE RF")

    def _on_power_setpoint_spinbox_editing_finished(self):
        self.worker.add_task(lambda: self.worker.device.set_power_setpoint(self.power_setpoint_spinbox.value()))

    def _on_load_spinbox_editing_finished(self):
        self.mc2_worker.add_task(lambda: self.mc2_worker.device.set_mc2_load_cap_preset_position(self.load_spinbox.value()))
        self.mc2_worker.add_task(self.mc2_worker.device.move_tune_and_load_to_preset)

    def _on_tune_spinbox_editing_finished(self):
        self.mc2_worker.add_task(lambda: self.mc2_worker.device.set_mc2_tune_cap_preset_position(self.tune_spinbox.value()))
        self.mc2_worker.add_task(self.mc2_worker.device.move_tune_and_load_to_preset)

    def _on_rf_output_button_clicked(self):
        if self.worker.device.rf_output_enabled:
            self.worker.add_task(self.worker.device.disable_rf_output)
            self.rf_output_button.setText("ENABLE RF")
        else:
            self.worker.add_task(self.worker.device.enable_rf_output)
            self.rf_output_button.setText("DISABLE RF")

    def _on_auto_manual_button_clicked(self):
        if self.auto_manual_button.text() == "ASSERT AUTO" or self.auto_manual_button.text() == "ENABLE AUTO":
            self.mc2_worker.add_task(self.mc2_worker.device.set_mc2_tune_cap_auto)
            self.mc2_worker.add_task(self.mc2_worker.device.set_mc2_load_cap_auto)
            self.auto_manual_button.setText("ENABLE MANUAL")
        elif self.auto_manual_button.text() == "ENABLE MANUAL":
            self.mc2_worker.add_task(self.mc2_worker.device.set_mc2_tune_cap_man)
            self.mc2_worker.add_task(self.mc2_worker.device.set_mc2_load_cap_man)
            self.auto_manual_button.setText("ENABLE AUTO")

    def _on_collapse_editor_button_clicked(self):
        if not self.profile_editor.isHidden():
            self.profile_editor.setHidden(True)
            self.profile_action_button.setHidden(True)
            self.control_panel_widget.resize(self.control_panel_widget.width(),
                                             self.control_panel_widget.maximumHeight())
            self.resize(self.width(), 0)
            self.collapse_editor_button.setText("▲")
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

    def get_settings_widget(self) -> QWidget:
        widget = super().get_settings_widget()

        # Port config for MC2, assume the same settings as RX01
        widget.mc2_comport_dropdown = QComboBox()
        widget.mc2_comport_dropdown.addItem("None", None)
        for port in sorted(comports(), key=lambda port: (len(port.device), port.device), reverse=False):
            widget.mc2_comport_dropdown.addItem(port.device, port.device)
        widget.mc2_comport_dropdown.setCurrentText(
            self.settings.value(f"{self.mc2_worker.device.internal_id}/mc2_serial/port", defaultValue=None)
        )

        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("MC2 port"))
        temp_layout.addWidget(widget.mc2_comport_dropdown)
        widget.layout().addLayout(temp_layout)

        temp_layout = QHBoxLayout()
        widget.model_combo_box = QComboBox()
        for model in RX01.RX01Model:
            widget.model_combo_box.addItem(model.value, model.name)

        widget.model_combo_box.setCurrentText(self.worker.device.model.value)

        temp_layout.addWidget(QLabel("Device model"))
        temp_layout.addWidget(widget.model_combo_box)

        widget.layout().addLayout(temp_layout)

        widget.layout().addStretch(100)

        return widget

    def update_settings_from_widget(self, settings_widget: QWidget):
        super().update_settings_from_widget(settings_widget)
        editor_plot_parameters = settings_widget.editor_plot_configuration_group_box.get_parameters_as_dict()
        mc2_comport_value = settings_widget.mc2_comport_dropdown.itemData(settings_widget.mc2_comport_dropdown.currentIndex())

        # Update device model
        model = RX01.RX01Model(settings_widget.model_combo_box.currentText())
        self.worker.device.model = model

        # Update MC2 worker interval
        self.mc2_worker.set_interval(self.worker.current_interval)

        # Copy the values from RX01 serial to MC2 serial
        serial_parameters = settings_widget.serial_configuration_group_box.get_parameters_as_dict()
        self.settings.beginGroup(self.mc2_worker.device.internal_id)
        self.settings.beginGroup("mc2_serial")
        for key, value in serial_parameters.items():
            self.settings.setValue(key, value)
        # Update MC2 port value
        self.settings.setValue("port", mc2_comport_value)
        self.settings.endGroup()  # serial group
        self.settings.endGroup()  # internal id

        # Update editor parameters
        self.profile_editor.update_parameters(
            editor_plot_parameters,
            editor_plot_parameters
        )

    def apply_values_from_settings(self):
        super().apply_values_from_settings()
        self.plot_widget.update_settings()

        # Force disconnect MC2
        self.mc2_worker.device.disconnect()

        # Update the values in the appropriate group
        self.settings.beginGroup(self.worker.device.internal_id)

        # Device model
        self.settings.setValue("model", self.worker.device.model.value)

        # Editor plot settings
        self.settings.beginGroup("editor_plot")
        self.settings.setValue("pen_color", self.profile_editor.profile_plot.plot_color),
        self.settings.setValue("pen_width", self.profile_editor.profile_plot.plot_line_width)
        self.settings.setValue("symbol_size", self.profile_editor.profile_plot.symbol_size)
        self.settings.endGroup()  # profile plot group

        self.settings.endGroup()  # internal_id group

    def clear_plot_data(self, clear_measured: bool = True, clear_profile: bool = True):
        if clear_measured:
            self.power_x_values = []
            self.power_y_values = []
            self.plot_widget.measured_values_plot.clear()

        if clear_profile:
            self.profile_x_data = []
            self.profile_y_data = []
            self.plot_widget.profile_values_plot.clear()
