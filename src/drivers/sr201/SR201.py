from enum import Enum
from typing import Dict, Union

from PyQt5.QtCore import QObject, pyqtSignal
from pyModbusTCP.client import ModbusClient

from src.drivers.DeviceBase import DeviceBase


class SR201Error(ValueError):
    pass


class RelayState(Enum):
    OPEN = 0
    CLOSED = 1
    UNKNOWN = -1


class SR201(DeviceBase, QObject):
    stateChanged = pyqtSignal(int, RelayState)

    def __init__(self, internal_id: str):
        DeviceBase.__init__(self, internal_id)
        QObject.__init__(self)

        self.settings.beginGroup(internal_id)
        self.settings.beginGroup("device")
        ip_address = self.settings.value("ip_address", defaultValue="192.168.1.1")
        self.modbus_client = ModbusClient(
            host=ip_address,
            port=6724,
            auto_open=False,
            timeout=5
        )
        self.settings.endGroup()  # device
        self.settings.endGroup()  # internal id
        self.logger.info(f"Initializing SR201 with IP address: {ip_address}")

    def is_connected(self):
        return self.modbus_client.is_open

    def connect(self):
        if not self.is_connected():
            return self.modbus_client.open()

    def disconnect(self):
        if self.modbus_client.is_open:
            return self.modbus_client.close()

    def get_relay_states(self, relay_n: int = -1) -> Dict[int, Union[str, RelayState]]:
        response = self.modbus_client.read_coils(0, 16)
        if not response:
            raise SR201Error("Nothing returned by SR201 on read")

        states = [RelayState(state) for state in response] if relay_n == -1 else [RelayState(response[relay_n])]
        result = {}
        for i, state in enumerate(states):
            relay_name = self.settings.value(f"{self.internal_id}/relays/{i}/name", defaultValue=f"Relay {i}")
            result[i] = (relay_name, state)

        return result

    def set_relay_state(self, relay_n: int, state: RelayState, duration: int = -1) -> bool:
        assert 0 <= relay_n <= 15

        if duration == -1:
            if self.modbus_client.write_single_coil(relay_n, state.value):
                self.stateChanged.emit(relay_n, state)
                return True
            else:
                raise SR201Error("Writing single coil failed")

        if self.modbus_client.write_single_register(relay_n, duration):
            self.stateChanged.emit(relay_n, state)
            return True
        else:
            raise SR201Error("Writing single register failed")
