from PyQt5.QtCore import pyqtSignal, pyqtSlot

from src.drivers.etc1103.MockETC1103 import MockETC1103
from src.drivers.etc1103.ETC1103 import ETC1103
from src.workers.GenericWorker import GenericWorker


class ETC1103Worker(GenericWorker):
    statusReady = pyqtSignal(str)
    operationalTimeReady = pyqtSignal(int)
    outputFrequencyReady = pyqtSignal(int)
    failureDetailsReady = pyqtSignal(str)

    DEVICE_CLASS = ETC1103
    MOCK_DEVICE_CLASS = MockETC1103

    @pyqtSlot()
    def function_to_call_periodically(self):
        self.statusReady.emit(self.device.get_pump_status())
        self.operationalTimeReady.emit(self.device.get_operational_time())
        self.outputFrequencyReady.emit(self.device.get_output_frequency())
        self.failureDetailsReady.emit(self.device.get_failure_details())
