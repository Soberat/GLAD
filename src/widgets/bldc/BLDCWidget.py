from typing import Type

from PyQt5.QtWidgets import QPushButton, QSpinBox, QHBoxLayout

from src.widgets.DeviceWidgetBase import DeviceWidgetBase
from src.workers.BLDCWorker import BLDCWorker
from src.workers.GenericWorker import GenericWorker


class BLDCWidget(DeviceWidgetBase):
    def __init__(self, internal_id: str, mock: bool = False):
        super().__init__(internal_id, BLDCWorker, mock)

        self.direction_left_button = QPushButton("◀")
        self.direction_right_button = QPushButton("▶")

        self.dac_val_spinbox = QSpinBox()
        self.dac_val_spinbox.setRange(0, 4095)
        self.dac_val_spinbox.setPrefix("DAC value ")
        self.dac_val_spinbox.editingFinished.connect(self.on_dac_val_spinbox_editing_finished)

        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.direction_left_button)
        temp_layout.addWidget(self.direction_right_button)

        self.layout().addLayout(temp_layout)
        self.layout().addWidget(self.dac_val_spinbox)

    def on_direction_left_button_clicked(self):
        self.worker.add_task(self.worker.device.set_direction_left)

    def on_direction_right_button_clicked(self):
        self.worker.add_task(self.worker.device.set_direction_right)

    def on_dac_val_spinbox_editing_finished(self):
        self.worker.add_task(lambda: self.worker.device.set_dac_val(
            self.dac_val_spinbox.value()
        ))