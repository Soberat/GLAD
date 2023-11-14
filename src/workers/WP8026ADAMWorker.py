from PyQt5.QtCore import pyqtSignal, pyqtSlot

from src.drivers.wp8026adam.MockWP8026ADAM import MockWP8026ADAM
from src.drivers.wp8026adam.WP8026ADAM import WP8026ADAM
from src.workers.GenericWorker import GenericWorker


class WP8026ADAMWorker(GenericWorker):
    statesReady = pyqtSignal(dict)

    DEVICE_CLASS = WP8026ADAM
    MOCK_DEVICE_CLASS = MockWP8026ADAM

    @pyqtSlot()
    def function_to_call_periodically(self):
        self.statesReady.emit(self.device.get_input_states())
