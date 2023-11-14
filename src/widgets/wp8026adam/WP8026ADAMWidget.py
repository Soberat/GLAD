from typing import Dict, Tuple

from PyQt5.QtWidgets import QLabel, QFormLayout, QLineEdit, QWidget, QComboBox
from serial.tools.list_ports_windows import comports

from src.drivers.wp8026adam.WP8026ADAM import InputState
from src.widgets.DeviceWidgetBase import DeviceWidgetBase
from src.workers.WP8026ADAMWorker import WP8026ADAMWorker


class WP8026ADAMWidget(DeviceWidgetBase):
    def __init__(self, internal_id: str, mock: bool):
        super().__init__(internal_id, WP8026ADAMWorker, mock)

        self.worker.statesReady.connect(self._on_states_ready)

        self.labels: Dict[int, Tuple[QLabel, QLabel]] = {
            i: (
                QLabel(self.settings.value(f"{internal_id}/channels/{i}/name", defaultValue=f"Channel {i}")),
                QLabel("Unknown")
            ) for i in range(0, 16)}

        form_layout = QFormLayout()

        for channel_name_label, state_label in self.labels.values():
            font = state_label.font()
            font.setBold(True)
            state_label.setFont(font)
            form_layout.addRow(channel_name_label, state_label)

        self.layout().addLayout(form_layout)

        self.thread.start()

    def _on_states_ready(self, states_dict: Dict[int, Tuple[str, InputState]]):
        for idx, (name, state) in states_dict.items():
            channel_name_label, state_label = self.labels[idx]
            channel_name_label.setText(name)
            state_label.setText(state.name)

    def get_settings_widget(self) -> QWidget:
        w = super().get_settings_widget()

        form_layout = QFormLayout()

        # Port config
        w.comport_dropdown = QComboBox()
        w.comport_dropdown.addItem("None", None)
        for port in sorted(comports(), key=lambda port: (len(port.device), port.device), reverse=False):
            w.comport_dropdown.addItem(port.device, port.device)
        w.comport_dropdown.setCurrentText(
            self.settings.value(f"{self.worker.device.internal_id}/serial/port", defaultValue=None)
        )

        form_layout.addRow(QLabel("Port"), w.comport_dropdown)

        w.channel_name_edits = [QLineEdit() for _ in range(0, 16)]

        for idx, channel_name_edit in enumerate(w.channel_name_edits):
            channel_name_edit.setText(
                self.settings.value(f"{self.worker.device.internal_id}/channels/{idx}/name", defaultValue=f"Channel {idx}")
            )
            form_layout.addRow(QLabel(f"Channel {idx} name"), channel_name_edit)

        w.layout().addLayout(form_layout)

        return w

    def update_settings_from_widget(self, settings_widget: QWidget):
        super().update_settings_from_widget(settings_widget)
        for idx, edit in enumerate(settings_widget.channel_name_edits):
            self.settings.setValue(f"{self.worker.device.internal_id}/channels/{idx}/name", edit.text())

        # Update port
        port = settings_widget.comport_dropdown.itemData(settings_widget.comport_dropdown.currentIndex())
        self.settings.setValue(f"{self.worker.device.internal_id}/serial/port", port)

    def apply_values_from_settings(self):
        super().apply_values_from_settings()
        for i in range(0, 16):
            self.labels[i][0].setText(
                self.settings.value(f"{self.worker.device.internal_id}/channels/{i}/name", defaultValue=f"Channel {i}")
            )

        self.worker.device.disconnect()
