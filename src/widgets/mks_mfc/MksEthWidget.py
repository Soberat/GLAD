from datetime import datetime
from typing import Tuple, List, Dict

from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator

from PyQt5.QtWidgets import QLabel, QDoubleSpinBox, QGroupBox, QRadioButton, QHBoxLayout, QButtonGroup, QSizePolicy, \
    QWidget, QLineEdit, QFormLayout

from src.drivers.mks_mfc.MksEthMfc import MksEthMfcValveState
from src.widgets.DeviceWidgetBase import DeviceWidgetBase
from src.widgets.PlotWidgetWithCrosshair import PlotWidgetWithCrosshair
from src.workers.MksEthMfcWorker import MksEthMfcWorker


class MksEthWidget(DeviceWidgetBase):
    def __init__(self, internal_id: str, mock: bool = False):
        super().__init__(internal_id, MksEthMfcWorker, mock)

        self.worker.flowValueReady.connect(self._on_flow_value_ready)
        self.worker.valveStateReady.connect(self._on_valve_state_ready)

        self.flow_x_values = []
        self.flow_y_values = []

        self.ip_address_label = QLabel(f"IP address: {self.worker.device.modbus_client.host}")
        self.setpoint_spinbox = QDoubleSpinBox()
        self.setpoint_spinbox.setPrefix("Setpoint ")
        self.setpoint_spinbox.setMaximumWidth(120)
        self.setpoint_spinbox.editingFinished.connect(self._on_setpoint_spinbox_editing_finished)

        self.plot_widget = PlotWidgetWithCrosshair(internal_id, has_profile=False)

        self.valve_state_group = QGroupBox("Valve mode")
        self.valve_state_group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.valve_normal_button = QRadioButton("Normal")
        self.valve_closed_button = QRadioButton("Closed")
        self.valve_open_button = QRadioButton("Open")

        # Add the buttons to a QButtonGroup to ensure their mutual exclusivity, and get 1 convenient signal on change
        self.valve_state_button_group = QButtonGroup()
        self.valve_state_button_group.setExclusive(True)
        self.valve_state_button_group.addButton(self.valve_normal_button)
        self.valve_state_button_group.addButton(self.valve_closed_button)
        self.valve_state_button_group.addButton(self.valve_open_button)

        self.valve_state_button_group.buttonToggled.connect(self._on_valve_state_button_pressed)

        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.ip_address_label)
        self.layout().addLayout(temp_layout)

        self.layout().addWidget(self.plot_widget)

        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.valve_normal_button)
        temp_layout.addWidget(self.valve_closed_button)
        temp_layout.addWidget(self.valve_open_button)
        self.valve_state_group.setLayout(temp_layout)

        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.valve_state_group)
        temp_layout.addWidget(self.setpoint_spinbox)
        temp_layout.addStretch(1)

        self.layout().addLayout(temp_layout)

        # After all the setup, start the worker thread
        self.thread.start()

    def get_measured_values(self) -> Dict[str, List[Tuple[int, float]]]:
        return {
            "Flow": list(zip(self.flow_x_values, self.flow_y_values))
        }

    def clear_measured_values(self):
        self.flow_x_values = []
        self.flow_y_values = []

        self.plot_widget.measured_values_plot.setData([], [])

    def _on_flow_value_ready(self, new_sample: float):
        self.flow_x_values.append(datetime.now().timestamp())
        self.flow_y_values.append(new_sample)

        self.plot_widget.measured_values_plot.setData(
            self.flow_x_values,
            self.flow_y_values
        )

    def _on_valve_state_ready(self, new_valve_state: MksEthMfcValveState):
        # Block the signals, as this is information coming from the device, and the change would trigger their change
        # callbacks, resending that information to the device
        self.valve_state_button_group.blockSignals(True)
        if new_valve_state == MksEthMfcValveState.OPEN:
            self.valve_open_button.setChecked(True)
        elif new_valve_state == MksEthMfcValveState.CLOSED:
            self.valve_closed_button.setChecked(True)
        elif new_valve_state == MksEthMfcValveState.NORMAL:
            self.valve_normal_button.setChecked(True)
        self.valve_state_button_group.blockSignals(False)

    def _on_valve_state_button_pressed(self, button: QRadioButton, is_checked: bool):
        if not is_checked:
            # Ignore when a button has been unchecked - we need only to act on the checked button press
            return

        if button.text() == "Normal":
            self.worker.add_task(lambda: self.worker.device.set_valve_state(MksEthMfcValveState.NORMAL))
        elif button.text() == "Closed":
            self.worker.add_task(lambda: self.worker.device.set_valve_state(MksEthMfcValveState.CLOSED))
        elif button.text() == "Open":
            self.worker.add_task(lambda: self.worker.device.set_valve_state(MksEthMfcValveState.OPEN))

    def _on_setpoint_spinbox_editing_finished(self):
        self.worker.add_task(lambda: self.worker.device.set_setpoint(self.setpoint_spinbox.value()))

    def get_settings_widget(self) -> QWidget:
        widget = super().get_settings_widget()

        temp_layout = QFormLayout()
        ip_address_lineedit = QLineEdit()
        # IP address regex
        ip_address_lineedit.setValidator(
            QRegExpValidator(
                QRegExp("^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")
            )
        )
        ip_address_lineedit.setText(self.worker.device.modbus_client.host)
        temp_layout.addRow("IP address", ip_address_lineedit)

        widget.ip_address_lineedit = ip_address_lineedit
        widget.layout().addLayout(temp_layout)

        # Add a stretch that will overpower the stretch from super()
        widget.layout().addStretch(100)

        return widget

    def update_settings_from_widget(self, settings_widget: QWidget):
        super().update_settings_from_widget(settings_widget)

        # Update IP address
        new_ip_address = settings_widget.ip_address_lineedit.text()
        self.settings.setValue(f"{self.worker.device.internal_id}/device/ip_address", new_ip_address)

    def apply_values_from_settings(self):
        super().apply_values_from_settings()

        # Update IP address
        address = self.settings.value(f"{self.worker.device.internal_id}/device/ip_address", None)
        if address != self.worker.device.modbus_client.host:
            # Close the connection
            self.worker.device.modbus_client.close()

            # Update the host IP
            self.worker.device.modbus_client.host = address

            # Update the label
            self.ip_address_label.setText(f"IP address: {address}")
