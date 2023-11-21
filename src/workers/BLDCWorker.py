from src.drivers.bldc.BLDC import BLDC
from src.drivers.bldc.MockBLDC import MockBLDC
from src.workers.GenericWorker import GenericWorker


class BLDCWorker(GenericWorker):
    DEVICE_CLASS = BLDC
    MOCK_DEVICE_CLASS = MockBLDC

    def function_to_call_periodically(self):
        pass
