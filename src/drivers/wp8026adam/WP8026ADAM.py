from enum import Enum

import pymodbus.exceptions
from pymodbus.client import ModbusSerialClient

from src.drivers.DeviceBase import DeviceBase


class InputState(Enum):
    LOW = 0
    HIGH = 1
    UNKNOWN = 2


class WP8026ADAM(DeviceBase):
    def __init__(self, internal_id: str):
        super().__init__(internal_id)

        self.modbus_client: ModbusSerialClient = None

    def is_connected(self):
        return self.modbus_client is not None and self.modbus_client.is_socket_open()

    def connect(self):
        """
        Connects to the device by closing the current connection (if open) and then reopening it.
        :returns nothing
        :raises any exception that can happen during connecting, e.g. SerialException
        """
        if self.modbus_client and self.modbus_client.is_socket_open():  # If connection exists and is open
            self.logger.info(f"Closing existing connection for {self.device_id()}")
            self.modbus_client.close()

        if self.settings.value(f"{self.internal_id}/serial/port", defaultValue=None) is None:
            raise ValueError(f"No port specified for {self.device_id()}")

        self.logger.info(f"Creating ModbusSerialClient for {self.device_id()}")

        self.modbus_client = ModbusSerialClient(
            port=self.settings.value(f"{self.internal_id}/serial/port"),
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=3
        )

        if not self.modbus_client.connect():
            raise pymodbus.exceptions.ConnectionException(f"Failed to connect to {self.device_id()}")

    def disconnect(self):
        if self.modbus_client is not None and self.modbus_client.is_socket_open():
            self.modbus_client.close()
        self.logger.info(f"Disconnected {self.device_id()}")

    def get_input_states(self, input_n: int = -1) -> dict:
        assert -1 <= input_n <= 15

        # Initialize an empty result dictionary
        result = {}

        # Fetch states as before
        if self.modbus_client.send([0x01, 0x02, 0x00, 0x00, 0x00, 0x10, 0x79, 0xc6]):
            response = self.modbus_client.recv(8)
            if not response:
                states = [InputState.UNKNOWN] * 16 if input_n == -1 else [InputState.UNKNOWN]
            else:
                response = format(int.from_bytes(response[3:5], byteorder="little"), "#018b")[2:]
                states = [InputState(int(state)) for state in response][::-1] if input_n == -1 else [
                    InputState(response[input_n])]
        else:
            states = [InputState.UNKNOWN] * 16 if input_n == -1 else [InputState.UNKNOWN]

        # For each channel, fetch its name from settings and store in the result dictionary
        for i, state in enumerate(states):
            channel_name = self.settings.value(f"{self.internal_id}/channels/{i}/name", defaultValue=f"Channel {i}")
            result[i] = (channel_name, state)

        return result
