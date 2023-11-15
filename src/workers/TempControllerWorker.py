from PyQt5.QtCore import pyqtSignal, pyqtSlot

from src.drivers.eurotherm_32h8i.Mock32h8i import MockTempController32h8i
from src.drivers.eurotherm_32h8i.T32h8i import TempController32h8i
from src.workers.GenericWorker import GenericWorker


class TempControllerWorker(GenericWorker):
    processValueReady = pyqtSignal(float)
    setpointReady = pyqtSignal(float)

    DEVICE_CLASS = TempController32h8i
    MOCK_DEVICE_CLASS = MockTempController32h8i

    @pyqtSlot()
    def function_to_call_periodically(self):
        self.device.set_setpoint_value()
        self.processValueReady.emit(self.device.get_process_value())
        self.setpointReady.emit(self.device.get_setpoint_value())
