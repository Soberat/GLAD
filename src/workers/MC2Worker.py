from PyQt5.QtCore import pyqtSignal, pyqtSlot

from src.drivers.rx01.MC2 import MC2
from src.drivers.rx01.MockMC2 import MockMC2

from src.workers.GenericWorker import GenericWorker


class MC2Worker(GenericWorker):
    loadCapPositionReady = pyqtSignal(int)
    tuneCapPositionReady = pyqtSignal(int)

    DEVICE_CLASS = MC2
    MOCK_DEVICE_CLASS = MockMC2

    @pyqtSlot()
    def function_to_call_periodically(self):
        self.loadCapPositionReady.emit(self.device.get_mc2_load_cap_preset_position())
        self.tuneCapPositionReady.emit(self.device.get_mc2_tune_cap_preset_position())
