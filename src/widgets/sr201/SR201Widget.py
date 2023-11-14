from typing import Dict, Tuple

from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QLabel, QFormLayout, QHBoxLayout, QVBoxLayout, QPushButton, QLineEdit, QWidget

from src.drivers.sr201.SR201 import RelayState
from src.drivers.wp8026adam.WP8026ADAM import InputState
from src.widgets.DeviceWidgetBase import DeviceWidgetBase
from src.workers.SR201Worker import SR201Worker


class SR201Widget(DeviceWidgetBase):
    def __init__(self, internal_id: str, mock: bool):
        super().__init__(internal_id, SR201Worker, mock)

        self.worker.statesReady.connect(self._on_states_ready)
        self.worker.device.stateChanged.connect(self._on_state_changed)

        self.labels: Dict[int, Tuple[QLabel, QLabel]] = {
            i: (
                QLabel(self.settings.value(f"{internal_id}/channels/{i}/name", defaultValue=f"Channel {i}")),
                QLabel("Unknown")
            ) for i in range(0, 16)}

        channels_layout = QVBoxLayout()

        for idx, (channel_name_label, state_label) in enumerate(self.labels.values()):
            font = state_label.font()
            font.setBold(True)
            state_label.setFont(font)

            channel_layout = QHBoxLayout()
            channel_layout.addWidget(channel_name_label)
            channel_layout.addWidget(state_label)

            open_button = QPushButton("Open")
            open_button.clicked.connect(lambda _, idx=idx: self._on_open_button_clicked(idx))

            close_button = QPushButton("Close")
            close_button.clicked.connect(lambda _, idx=idx: self._on_close_button_clicked(idx))

            channel_layout.addWidget(open_button)
            channel_layout.addWidget(close_button)

            channels_layout.addLayout(channel_layout)

        self.layout().addLayout(channels_layout)

        self.thread.start()

    def _on_states_ready(self, states_dict: Dict[int, Tuple[str, InputState]]):
        for idx, (name, state) in states_dict.items():
            channel_name_label, state_label = self.labels[idx]
            channel_name_label.setText(name)
            state_label.setText(state.name)

    def _on_state_changed(self, relay_n: int, state: RelayState):
        self.labels[relay_n][1].setText(state.name)

    def _on_open_button_clicked(self, idx: int):
        self.worker.add_task(lambda: self.worker.device.set_relay_state(idx, RelayState.OPEN))

    def _on_close_button_clicked(self, idx: int):
        self.worker.add_task(lambda: self.worker.device.set_relay_state(idx, RelayState.CLOSED))

    def get_settings_widget(self) -> QWidget:
        w = super().get_settings_widget()

        form_layout = QFormLayout()

        # Add an edit for the IP address
        ip_address_lineedit = QLineEdit()
        # IP address regex
        ip_address_lineedit.setValidator(
            QRegExpValidator(
                QRegExp("^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")
            )
        )
        ip_address_lineedit.setText(self.worker.device.modbus_client.host)
        form_layout.addRow("IP address", ip_address_lineedit)
        w.ip_address_lineedit = ip_address_lineedit

        w.channel_name_edits = [QLineEdit() for _ in range(0, 16)]

        for idx, channel_name_edit in enumerate(w.channel_name_edits):
            channel_name_edit.setText(
                self.settings.value(f"{self.worker.device.internal_id}/relays/{idx}/name", defaultValue=f"Relay {idx}")
            )
            form_layout.addRow(QLabel(f"Relay {idx} name"), channel_name_edit)

        w.layout().addLayout(form_layout)

        return w

    def update_settings_from_widget(self, settings_widget: QWidget):
        super().update_settings_from_widget(settings_widget)
        for idx, edit in enumerate(settings_widget.channel_name_edits):
            self.settings.setValue(f"{self.worker.device.internal_id}/relays/{idx}/name", edit.text())

        # Update IP address
        new_ip_address = settings_widget.ip_address_lineedit.text()
        self.settings.setValue(f"{self.worker.device.internal_id}/device/ip_address", new_ip_address)

    def apply_values_from_settings(self):
        super().apply_values_from_settings()
        for i in range(0, 16):
            self.labels[i][0].setText(
                self.settings.value(f"{self.worker.device.internal_id}/relays/{i}/name", defaultValue=f"Relay {i}")
            )

        # Update IP address
        address = self.settings.value(f"{self.worker.device.internal_id}/device/ip_address", None)
        if address != self.worker.device.modbus_client.host:
            # Close the connection
            self.worker.device.modbus_client.close()

            # Update the host IP
            self.worker.device.modbus_client.host = address

            # Update the label
            self.ip_address_label.setText(f"IP address: {address}")
