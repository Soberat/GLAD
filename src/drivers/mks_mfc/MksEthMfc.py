from enum import Enum

from pyModbusTCP.utils import decode_ieee, word_list_to_long

from src.drivers.DeviceBase import DeviceBase
from src.drivers.mks_mfc.FloatModbusClient import FloatModbusClient


class MksEthMfcValveState(Enum):
    NORMAL = 0
    CLOSED = 1
    OPEN = 2


class NothingReturnedError(ValueError):
    pass


class MksEthMfc(DeviceBase):

    def __init__(self, internal_id: str):
        super().__init__(internal_id)
        self.settings.beginGroup(internal_id)
        self.settings.beginGroup("device")
        ip_address = self.settings.value("ip_address", defaultValue="192.168.1.1")
        self.modbus_client = FloatModbusClient(
            host=ip_address,
            port=502,
            unit_id=1,
            auto_open=False,
        )
        self.settings.endGroup()  # device
        self.settings.endGroup()  # internal id
        self.logger.info(f"Initializing MksEthMfc with IP address: {ip_address}")

    def is_connected(self):
        return self.modbus_client.is_open

    def connect(self):
        if not self.is_connected():
            return self.modbus_client.open()

    def disconnect(self):
        if self.modbus_client.is_open:
            return self.modbus_client.close()

    def get_flow(self) -> float:
        self.logger.info("Fetching flow")
        result = self.modbus_client.read_input_registers(0x4000, 2)
        if result is None:
            raise NothingReturnedError("Nothing returned by the MFC on read")
        return decode_ieee(word_list_to_long(result)[0])

    def get_temperature(self) -> float:
        self.logger.info("Fetching temperature")
        result = self.modbus_client.read_input_registers(0x4002, 2)
        if result is None:
            raise NothingReturnedError("Nothing returned by the MFC on read")
        return decode_ieee(word_list_to_long(result)[0])

    def get_valve_position(self) -> float:
        self.logger.info("Fetching valve position")
        result = self.modbus_client.read_input_registers(0x4004, 2)
        if result is None:
            raise NothingReturnedError("Nothing returned by the MFC on read")
        return decode_ieee(word_list_to_long(result)[0])

    def get_flow_hours(self) -> int:
        self.logger.info("Fetching flow hours")
        result = self.modbus_client.read_input_registers(0x4008, 2)
        if result is None:
            raise NothingReturnedError("Nothing returned by the MFC on read")
        return word_list_to_long(result)[0]

    def get_flow_total(self) -> float:
        self.logger.info("Fetching total flow")
        result = self.modbus_client.read_input_registers(0x400A, 2)
        if result is None:
            raise NothingReturnedError("Nothing returned by the MFC on read")
        return word_list_to_long(result)[0]

    def get_setpoint(self) -> float:
        self.logger.info("Fetching setpoint")
        result = self.modbus_client.read_float(0xA000, 2)
        if result is None:
            raise NothingReturnedError("Nothing returned by the MFC on read")
        return result[0]

    def set_setpoint(self, setpoint: float) -> bool:
        self.logger.info(f"Setting setpoint to: {setpoint}")
        return self.modbus_client.write_float(0xA000, [setpoint])

    def get_ramp_rate(self) -> int:
        self.logger.info("Fetching ramp rate")
        result = self.modbus_client.read_holding_registers(0xA002, 2)
        if result is None:
            raise NothingReturnedError("Nothing returned by the MFC on read")
        return result[0]

    def set_ramp_rate(self, ramp_rate: int) -> bool:
        self.logger.info(f"Setting ramp rate to: {ramp_rate}")
        return self.modbus_client.write_float(0xA002, [ramp_rate])

    def get_unit_type(self) -> int:
        self.logger.info("Fetching unit type")
        result = self.modbus_client.read_holding_registers(0xA004, 2)
        if result is None:
            raise NothingReturnedError("Nothing returned by the MFC on read")
        return result[0]

    def set_unit_type(self, unit_type: int) -> bool:
        self.logger.info(f"Setting unit type to: {unit_type}")
        return self.modbus_client.write_multiple_registers(0xA004, [unit_type])

    def reset(self) -> bool:
        self.logger.info("Resetting")
        return self.modbus_client.write_single_coil(0xE000, True)

    def set_valve_state(self, state: MksEthMfcValveState) -> bool:
        self.logger.info(f"Setting valve state to: {state}")
        return self.modbus_client.write_single_coil(0xE001, state == MksEthMfcValveState.OPEN) \
            and self.modbus_client.write_single_coil(0xE002, state == MksEthMfcValveState.CLOSED)

    def get_valve_state(self) -> MksEthMfcValveState:
        self.logger.info("Fetching valve state")
        is_open = self.modbus_client.read_coils(0xE001)
        is_closed = self.modbus_client.read_coils(0xE002)

        if is_open is None or is_closed is None:
            raise NothingReturnedError("Nothing returned by the MFC on read")

        if is_open[0]:
            return MksEthMfcValveState.OPEN
        elif is_closed[0]:
            return MksEthMfcValveState.CLOSED
        else:
            return MksEthMfcValveState.NORMAL

    def set_flow_zero(self, is_zero: bool) -> bool:
        self.logger.debug("Setting flow to zero")
        return self.modbus_client.write_single_coil(0xE003, is_zero)

    def device_id(self):
        return f"MKS ETH MFC @ {self.modbus_client.host}"
