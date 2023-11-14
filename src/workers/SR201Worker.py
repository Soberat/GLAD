from PyQt5.QtCore import pyqtSignal, pyqtSlot

from src.drivers.sr201.MockSR201 import MockSR201
from src.drivers.sr201.SR201 import SR201
from src.workers.GenericWorker import GenericWorker


class SR201Worker(GenericWorker):
    statesReady = pyqtSignal(dict)

    DEVICE_CLASS = SR201
    MOCK_DEVICE_CLASS = MockSR201

    @pyqtSlot()
    def function_to_call_periodically(self):
        self.statesReady.emit(self.device.get_relay_states())
