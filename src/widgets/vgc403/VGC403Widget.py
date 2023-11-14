from datetime import datetime
from typing import Tuple, List, Dict

from PyQt5.QtWidgets import QLabel

from src.drivers.vgc403.VGC403 import VGC403PressureSensorData
from src.widgets.DeviceWidgetBase import DeviceWidgetBase
from src.workers.VGC403Worker import VGC403Worker


class VGC403Widget(DeviceWidgetBase):
    def __init__(self, internal_id: str, mock: bool = False):
        super().__init__(internal_id, VGC403Worker, mock)

        self.measurements_x = [[], [], []]
        self.measurements_y = [[], [], []]

        self.worker.pressureValuesReady.connect(self._on_pressure_values_ready)

        self.labels = {
            i: QLabel(f"Sensor {i + 1}: none") for i in range(0, 3)
        }

        for label in self.labels.values():
            self.layout().addWidget(label)

        self.layout().addStretch(1)

        # After all the setup, start the worker thread
        self.thread.start()

    def get_measured_values(self) -> Dict[str, List[Tuple[int, float]]]:
        return {
            f"Sensor {i+1}": list(zip(self.measurements_x[i], self.measurements_y[i])) for i in range(0, 3)
        }

    def clear_measured_values(self):
        self.measurements_x = [[], [], []]
        self.measurements_y = [[], [], []]

    def _on_pressure_values_ready(self, readouts: List[Tuple[int, VGC403PressureSensorData]]):
        for sensor_n, readout in readouts:
            self.measurements_x[sensor_n-1].append(datetime.now().timestamp())
            self.measurements_y[sensor_n-1].append(readout.as_float())
            if readout.status == 0:
                self.labels[sensor_n-1].setText(f"Sensor {sensor_n}: {round(readout.value, 2)}e{readout.error} mbar")
            else:
                self.labels[sensor_n-1].setText(
                    f"Sensor {sensor_n}: {self.worker.device.PR_STATUS_STRINGS[readout.status]}"
                )
