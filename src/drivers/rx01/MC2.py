from typing import Union

import serial

from src.drivers.SerialDeviceBase import SerialDeviceBase


class MC2(SerialDeviceBase):
    DEFAULTS = {
        "baudrate": 19200,
        "parity": serial.PARITY_EVEN,
        "bytesize": serial.SEVENBITS,
        "stopbits": serial.STOPBITS_ONE,
        "timeout": 3
    }

    def connect(self):
        """
        Connects to the device by closing the current connection (if open) and then reopening it.

        :returns nothing
        :raises any exception that can happen during connecting, e.g. SerialException
        """
        if self.serial and self.serial.is_open:  # If connection exists and is open
            self.logger.info(f"Closing existing connection for {self.device_id()}")
            self.serial.close()

        self.logger.info(f"Creating serial for {self.device_id()}")
        self.serial = self.create_serial_from_settings(key="mc2_serial")  # Create a new connection from settings

        if self.serial and self.serial.port is None:
            raise ValueError(f"No port specified for {self.device_id()}")

    def device_id(self):
        return f"{self.__class__.__name__} @ {self.settings.value(f'{self.internal_id}/mc2_serial/port')}"

    def __write_and_read(self, command: str, expected_response: Union[str, None] = "\r") -> Union[str, bool]:
        self.logger.debug(f"Writing {command}\r")
        self.serial.write(f"{command}\r".encode())
        response = self.serial.read_until(b"\r").decode()

        self.logger.debug(f"Response for {command}: {response}")

        if response == "N\r":
            return False

        if not expected_response:
            return response

        if response != expected_response:
            self.logger.warning(f"Unexpected response for command {command}: {response}")
            return False

    def get_mc2_load_cap_preset_position(self):
        return int(self.__write_and_read("LPS", None))

    def get_mc2_tune_cap_preset_position(self):
        return int(self.__write_and_read("TPS", None))

    def set_mc2_load_cap_preset_position(self, position_percentage: int):
        assert 0 <= position_percentage <= 100

        device_value_string = str(int(position_percentage))

        return self.__write_and_read(f"{device_value_string}_MPL")

    def set_mc2_tune_cap_preset_position(self, position_percentage: int):
        assert 0 <= position_percentage <= 100

        device_value_string = str(int(position_percentage))

        return self.__write_and_read(f"{device_value_string}_MPT")

    def get_mc2_phase_voltage(self):
        return self.__write_and_read("PHS", None)

    def get_mc2_magnitude_voltage(self):
        return self.__write_and_read("MAG", None)

    def set_mc2_load_cap_auto(self):
        return self.__write_and_read("ALD")

    def set_mc2_tune_cap_auto(self):
        return self.__write_and_read("ATN")

    def set_mc2_load_cap_man(self):
        return self.__write_and_read("MLD")

    def set_mc2_tune_cap_man(self):
        return self.__write_and_read("MTN")

    def move_tune_and_load_to_preset(self):
        return self.__write_and_read("GOTO")
