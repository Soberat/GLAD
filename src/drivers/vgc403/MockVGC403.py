import random
from datetime import datetime

from src.drivers.vgc403.VGC403 import VGC403, VGC403PressureSensorData


class MockVGC403(VGC403):
    def is_connected(self) -> bool:
        return datetime.now().minute % 2 == 0

    def connect(self):
        if datetime.now().minute % 2 != 0:
            raise ValueError("VGC403 is not connected on odd minute values")

    def read_pressure_sensor(self, sensor_number: int):
        assert sensor_number in [1, 2, 3]
        self.logger.info(f"Sending 'PR{sensor_number}'\r")
        # Mock reading response from device
        mock_readback_string = f"0 000.000 00{sensor_number}"
        self.logger.info(f"Readback: {mock_readback_string}")

        return VGC403PressureSensorData(
            int(mock_readback_string[0]),
            round(random.uniform(0, 1), 2),
            int(mock_readback_string[10:13])
        )
