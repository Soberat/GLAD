import random
from typing import Union

from src.drivers.etc1103.ETC1103 import ETC1103


class MockETC1103(ETC1103):
    def is_connected(self) -> bool:
        return True

    def connect(self):
        pass

    def __write_and_read(self, command: str, expected_response: Union[str, None] = None) -> Union[str, bool]:
        mock_responses = {
            "SCC0": "$",
            "SDR1": "$",
            "SDR0": "$",
            "RDT": random.randint(1, 10),
            "RSS": random.choice(list(self.PUMP_STATUSES.values())),
            "RSA": random.choice(list(self.ALARM_CODES.values())),
            "RRS": random.randint(0, 16),
        }
        self.logger.debug(f"Wrote {command}, readback {mock_responses.get(command, '')}")
        return mock_responses.get(command, "")

    def __disable_crc(self) -> bool:
        return self.__write_and_read("SCC0", "$")

    def start_pump(self) -> bool:
        return self.__write_and_read("SDR1", "$")

    def stop_pump(self) -> bool:
        return self.__write_and_read("SDR0", "$")

    def get_operational_time(self) -> Union[int, str]:
        response = self.__write_and_read("RDT")
        return int(response)

    def get_pump_status(self) -> str:
        response = self.__write_and_read("RSS").replace("\r", "")
        return self.PUMP_STATUSES.get(response, response)

    def get_failure_details(self) -> str:
        response = self.__write_and_read("RSA").replace("\r", "")
        return self.ALARM_CODES.get(response, response)

    def get_output_frequency(self) -> Union[int, str]:
        response = self.__write_and_read("RRS")
        return int(response)
