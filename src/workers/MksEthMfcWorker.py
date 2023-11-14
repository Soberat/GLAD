from PyQt5.QtCore import pyqtSignal, pyqtSlot

from src.drivers.mks_mfc.MksEthMfc import MksEthMfc, MksEthMfcValveState
from src.drivers.mks_mfc.MockMksEthMfc import MockMksEthMfc
from src.workers.GenericWorker import GenericWorker


class MksEthMfcWorker(GenericWorker):
    flowValueReady = pyqtSignal(float)
    valveStateReady = pyqtSignal(MksEthMfcValveState)

    DEVICE_CLASS = MksEthMfc
    MOCK_DEVICE_CLASS = MockMksEthMfc

    @pyqtSlot()
    def function_to_call_periodically(self):
        self.flowValueReady.emit(self.device.get_flow())
