from PyQt5.QtCore import pyqtSignal, pyqtSlot

from src.drivers.eurotherm_32h8i.Mock32h8i import MockTempController32h8i
from src.drivers.eurotherm_32h8i.T32h8i import TempController32h8i
from src.workers.GenericWorker import GenericWorker


class TempControllerWorker(GenericWorker):
    processValueReady = pyqtSignal(float)
    setpointReady = pyqtSignal(float)

    DEVICE_CLASS = TempController32h8i
    MOCK_DEVICE_CLASS = MockTempController32h8i

    def __init__(self, internal_id: str, mock: bool):
        super().__init__(internal_id, mock)
        self.device.setpointRefreshNeeded.connect(
            lambda: self.add_task(self.device.set_setpoint_value)
        )

    @pyqtSlot()
    def function_to_call_periodically(self):
        self.processValueReady.emit(self.device.get_process_value())
        self.setpointReady.emit(self.device.get_setpoint_value())
