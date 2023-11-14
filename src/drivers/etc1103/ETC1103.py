import re
from typing import Union

from src.drivers.SerialDeviceBase import SerialDeviceBase


class ETC1103(SerialDeviceBase):
    ERROR_CODES = {
        "#00": "There is no such command.",
        "#01": "The set parameter is irregular.",
        "#02": "The set parameter is beyond the available range.",
        "#03": "Despite failure, the operation command is inputted.",
        "#05": "The “operation mode select switch” is not set to SERIAL.",
        "#06": "The CRC code is irregular."
    }

    ALARM_CODES = {
        "1": "Normal",
        "#03": "Change Bearing warning",
        "#12": "Protection signal error",
        "#20": "External fan disconnected",
        "#23": "System error",
        "#30": "Input voltage low",
        "#31": "Driver temperature error",
        "#32": "Motor temperature error",
        "#33": "Excessive current",
        "#34": "Excessive rotation speed",
        "#35": "Acceleration time over",
        "#55": "P/S Fan stop error",
        "#60": "Reacceleration time over",
        "#61": "No load"
    }

    PUMP_STATUSES = {
        "1": "Standby",
        "2": "Acceleration",
        "3": "Normal",
        "4": "Brake",
        "6": "Reacceleration",
        "7": "Failure"
    }

    def connect(self):
        super().connect()

        self.__disable_crc()

    def __write_and_read(self, command: str, expected_response: Union[str, None] = None) -> Union[str, bool]:
        self.logger.debug(f"Writing {command}")
        self.serial.write(f"{command}\r".encode())
        response = self.serial.read_until(b"\r").decode()

        self.logger.debug(f"Response: {response}")

        if response in self.ERROR_CODES:
            return self.__handle_command_failure(command, response)

        if not expected_response:
            return response

        if response != f"{expected_response}\r":
            self.logger.error(f"Unexpected response for command {command}: '{response}'")
            return False

        return True

    def __disable_crc(self) -> bool:
        return self.__write_and_read("SCC0", "$")

    @staticmethod
    def __handle_command_failure(source_command: str, error_code: str):
        if error_code == "#00":
            raise ValueError(f"Invalid command: {source_command}")
        if error_code == "#01":
            raise ValueError(f"Invalid set parameter: {source_command}")
        if error_code == "#02":
            raise ValueError(f"Set parameter beyond range: {source_command}")
        if error_code == "#03":
            raise ValueError(f"Despite failure, the operation command is inputted: {source_command}")
        if error_code == "#05":
            raise ValueError(f"Serial mode not selected")
        if error_code == "#06":
            raise ValueError(f"CRC code was wrong")

    def start_pump(self) -> bool:
        return self.__write_and_read("SDR1", "$")

    def stop_pump(self) -> bool:
        return self.__write_and_read("SDR0", "$")

    def get_operational_time(self) -> Union[int, str]:
        response = self.__write_and_read("RDT")
        if not re.search("[0-9]+", response):
            self.logger.error(f"Unexpected response getting operational time: {response}")
            return -1

        return int(response)

    def get_pump_status(self) -> str:
        response = self.__write_and_read("RSS", None).replace("\r", "")

        if response not in self.PUMP_STATUSES:
            self.logger.error(f"Unexpected status returned: '{response}'")
            return response

        return self.PUMP_STATUSES[response]

    def get_failure_details(self) -> str:
        response = self.__write_and_read("RSA").replace("\r", "")

        if response not in self.ALARM_CODES:
            self.logger.error(f"Unexpected alarm code returned: {response}")
            return response

        return self.ALARM_CODES[response]

    def get_output_frequency(self) -> Union[int, str]:
        response = self.__write_and_read("RRS")
        if not re.search("[0-9]+", response):
            self.logger.error(f"Unexpected response getting rotational frequency: {response}")
            return -1

        return int(response)
