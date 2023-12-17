from typing import Dict, List, Tuple

from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QGroupBox, QLabel, QHBoxLayout

from src.widgets.DeviceWidgetBase import DeviceWidgetBase
from src.workers.ETC1103Worker import ETC1103Worker


class ETC1103Widget(DeviceWidgetBase):
    def __init__(self, internal_id: str, mock: bool = False):
        super().__init__(internal_id, ETC1103Worker, mock)
        self.wipe_measurements_button.hide()

        self.worker.statusReady.connect(self._on_status_ready)
        self.worker.operationalTimeReady.connect(self._on_operational_time_ready)
        self.worker.outputFrequencyReady.connect(self._on_output_frequency_ready)
        self.worker.failureDetailsReady.connect(self._on_failure_details_ready)

        self.device_groupbox = QGroupBox()
        self.device_groupbox.setLayout(QVBoxLayout())

        self.status_label = QLabel("Status: unknown")
        self.operational_time_label = QLabel("Operational time: unknown")
        self.output_frequency_label = QLabel("Output frequency: unknown")
        self.failure_details_label = QLabel("Failures: normal")

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self._on_start_button_clicked)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._on_stop_button_clicked)

        self.device_groupbox.layout().addWidget(self.status_label)
        self.device_groupbox.layout().addWidget(self.operational_time_label)
        self.device_groupbox.layout().addWidget(self.output_frequency_label)
        self.device_groupbox.layout().addWidget(self.failure_details_label)

        temp_layout = QHBoxLayout()

        temp_layout.addWidget(self.start_button)
        temp_layout.addWidget(self.stop_button)

        self.device_groupbox.layout().addLayout(temp_layout)
        self.layout().addWidget(self.device_groupbox)
        self.layout().addStretch(1)

        # After all the setup, start the worker thread
        self.thread.start()

    def get_measured_values(self) -> Dict[str, List[Tuple[int, float]]]:
        return {}

    def clear_measured_values(self):
        return

    def _on_start_button_clicked(self):
        self.worker.add_task(self.worker.device.start_pump)

    def _on_stop_button_clicked(self):
        self.worker.add_task(self.worker.device.stop_pump)

    def _on_status_ready(self, status: str):
        self.status_label.setText(f"Status: {status}")

    def _on_operational_time_ready(self, operational_time: int):
        self.operational_time_label.setText(f"Operational time: {operational_time} h")

    def _on_output_frequency_ready(self, output_frequency: int):
        self.output_frequency_label.setText(f"Output frequency: {output_frequency} Hz")

    def _on_failure_details_ready(self, failure_details: str):
        self.failure_details_label.setText(f"Failures: {failure_details}")
