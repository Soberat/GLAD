from PyQt5.QtCore import pyqtSignal, pyqtSlot

from src.drivers.rx01.MockRX01 import MockRX01
from src.drivers.rx01.RX01 import RX01
from src.workers.GenericWorker import GenericWorker


class RX01Worker(GenericWorker):
    forwardPowerReady = pyqtSignal(float)
    reflectedPowerReady = pyqtSignal(float)
    dcBiasVoltageReady = pyqtSignal(int)
    loadCapPositionReady = pyqtSignal(int)
    tuneCapPositionReady = pyqtSignal(int)
    rfOutputEnabledReady = pyqtSignal(bool)

    DEVICE_CLASS = RX01
    MOCK_DEVICE_CLASS = MockRX01

    @pyqtSlot()
    def function_to_call_periodically(self):
        self.forwardPowerReady.emit(self.device.get_forward_power_output())
        self.reflectedPowerReady.emit(self.device.get_reflected_power())
        self.dcBiasVoltageReady.emit(self.device.get_dc_bias_voltage())
        self.rfOutputEnabledReady.emit(self.device.rf_output_enabled)
