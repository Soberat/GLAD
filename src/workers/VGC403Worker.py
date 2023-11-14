from PyQt5.QtCore import pyqtSignal, pyqtSlot

from src.drivers.vgc403.MockVGC403 import MockVGC403
from src.drivers.vgc403.VGC403 import VGC403
from src.workers.GenericWorker import GenericWorker


class VGC403Worker(GenericWorker):
    pressureValuesReady = pyqtSignal(object)  # List[Tuple[int, VGC403PressureSensorData]]

    DEVICE_CLASS = VGC403
    MOCK_DEVICE_CLASS = MockVGC403

    @pyqtSlot()
    def function_to_call_periodically(self):
        measurements = []
        for sensor in [1, 2, 3]:
            read_value = self.device.read_pressure_sensor(sensor)
            if read_value:
                measurements.append((sensor, read_value))

        self.pressureValuesReady.emit(measurements)
