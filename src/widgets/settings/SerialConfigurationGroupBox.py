from typing import Dict

import serial
from PyQt5.QtCore import QSettings
from serial.tools.list_ports_windows import comports
from PyQt5.QtWidgets import QComboBox, QFormLayout, QDoubleSpinBox, QGroupBox


class SerialConfigurationGroupBox(QGroupBox):
    def __init__(self, internal_id: str):
        super().__init__("Serial configuration")
        self.internal_id = internal_id

        # Load settings based on internal_id
        settings = QSettings("Mirosław Wiącek Code", "GLAD")
        settings.beginGroup(self.internal_id)
        settings.beginGroup("serial")
        parameters = {
            "port": settings.value("port", defaultValue=None),
            "baudrate": settings.value("baudrate", defaultValue=9600),
            "bytesize": settings.value("bytesize", defaultValue=8),
            "stopbits": settings.value("stopbits", defaultValue=1),
            "parity": settings.value("parity", defaultValue="N"),
            "timeout": float(settings.value("timeout", defaultValue=0))
        }
        settings.endGroup()  # serial group
        settings.endGroup()  # internal_id group

        layout = QFormLayout()

        # Port
        self.comport_dropdown = QComboBox()
        self.comport_dropdown.addItem("None", None)
        for port in sorted(comports(), key=lambda port: (len(port.device), port.device), reverse=False):
            self.comport_dropdown.addItem(port.device, port.device)
        self.comport_dropdown.setCurrentText(parameters.get("port", ""))
        layout.addRow("Port:", self.comport_dropdown)

        # Baud rate
        self.baud_combo = QComboBox()
        for v in serial.Serial.BAUDRATES:
            self.baud_combo.addItem(str(v), v)
        self.baud_combo.setCurrentText(str(parameters.get("baudrate", 9600)))
        layout.addRow("Baudrate:", self.baud_combo)

        # Data bits
        self.data_bits_combo = QComboBox()
        for v in serial.Serial.BYTESIZES:
            self.data_bits_combo.addItem(str(v), v)
        self.data_bits_combo.setCurrentText(str(parameters.get("bytesize", 8)))
        layout.addRow("Data bits:", self.data_bits_combo)

        # Stop bits
        self.stop_bits_combo = QComboBox()
        for v in serial.Serial.STOPBITS:
            self.stop_bits_combo.addItem(str(v), v)
        self.stop_bits_combo.setCurrentText(str(parameters.get("stopbits", 1)))
        layout.addRow("Stop bits:", self.stop_bits_combo)

        # Parity
        self.parity_combo = QComboBox()
        for v in serial.Serial.PARITIES:
            self.parity_combo.addItem(v, v)
        self.parity_combo.setCurrentText(parameters.get("parity", "N"))
        layout.addRow("Parity:", self.parity_combo)

        # Timeout
        self.timeout_spinbox = QDoubleSpinBox()
        self.timeout_spinbox.setRange(0, 9999)
        self.timeout_spinbox.setDecimals(2)
        self.timeout_spinbox.setSingleStep(0.5)
        self.timeout_spinbox.setSuffix(" s")
        self.timeout_spinbox.setValue(parameters.get("timeout", 0))
        layout.addRow("Timeout:", self.timeout_spinbox)

        self.setLayout(layout)

    def get_parameters_as_dict(self) -> Dict:
        return {
            "port": self.comport_dropdown.itemData(self.comport_dropdown.currentIndex()),
            "baudrate": self.baud_combo.itemData(self.baud_combo.currentIndex()),
            "bytesize": self.data_bits_combo.itemData(self.data_bits_combo.currentIndex()),
            "stopbits": self.stop_bits_combo.itemData(self.stop_bits_combo.currentIndex()),
            "parity": self.parity_combo.itemData(self.parity_combo.currentIndex()),
            "timeout": self.timeout_spinbox.value()
        }
