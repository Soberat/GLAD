import logging
from dataclasses import dataclass
from typing import Union

from src.drivers.SerialDeviceBase import SerialDeviceBase


@dataclass
class VGC403PressureSensorData:
    status: int
    value: float
    error: float

    def as_float(self) -> Union[bool, float]:
        if self.status != 0:
            return False

        return round(float(f"{self.value}e{self.error}"), 2)


class VGC403(SerialDeviceBase):
    PR_STATUS_STRINGS = {
        0: "OK",
        1: "underrange",
        2: "overrange",
        3: "sensor error",
        4: "sensor switched off",
        5: "no sensor",
        6: "identification error",
        7: "BPG/HPG error"
    }

    def read_pressure_sensor(self, sensor_number: int):
        assert sensor_number in [1, 2, 3]

        self.logger.info(f"Sending 'PR{sensor_number}'\r")
        self.serial.write(f"PR{sensor_number}\r".encode())
        self.logger.info(f"Readback: {self.serial.readline()}")

        self.logger.info(f"Sending '{chr(0x05)}'")
        self.serial.write(f"{chr(0x05)}".encode())
        readback_string = self.serial.readline().decode()
        if not readback_string:
            logging.error("Timed out")
            return
        self.logger.info(f"Readback: {readback_string}")

        return VGC403PressureSensorData(
            int(readback_string[0]),
            float(readback_string[2:9]),
            int(readback_string[10:13])
        )
