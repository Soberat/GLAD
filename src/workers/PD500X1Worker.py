from PyQt5.QtCore import pyqtSignal, pyqtSlot

from src.drivers.pd500x1.MockPD500X1 import MockPD500X1
from src.drivers.pd500x1.PD500X1 import PD500X1
from src.workers.GenericWorker import GenericWorker


class PD500X1Worker(GenericWorker):
    activeTargetPowerReady = pyqtSignal(float)
    actualPowerReady = pyqtSignal(float)

    DEVICE_CLASS = PD500X1
    MOCK_DEVICE_CLASS = MockPD500X1

    @pyqtSlot()
    def function_to_call_periodically(self):
        self.activeTargetPowerReady.emit(self.device.read_active_target_power_setpoint_in_Watts())
        self.actualPowerReady.emit(self.device.read_actual_power_in_Watts())
