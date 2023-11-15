from dataclasses import dataclass

from PyQt5.QtCore import QObject, pyqtSlot
from minimalmodbus import Instrument

from src.drivers.SerialDeviceBase import SerialDeviceBase


class TempController32h8i(SerialDeviceBase, QObject):
    @dataclass
    class InstrumentStatus:
        alarm1_status: bool
        alarm2_status: bool
        alarm3_status: bool
        alarm4_status: bool
        sensor_break_status: bool
        pv_overrange_status: bool
        new_alarm_status: bool

    def __init__(self, internal_id: str):
        super().__init__(internal_id)
        self.instrument = None
        self.setpoint_value = 20

        self.setpoint_control_enabled = False

    def connect(self):
        super().connect()
        self.instrument = Instrument(slaveaddress=1, port=self.serial)

    def is_connected(self) -> bool:
        return self.instrument is not None
    
    def toggle_control(self, is_control_enabled: bool):
        if not is_control_enabled:
            self.set_setpoint_value(20)
        self.setpoint_control_enabled = is_control_enabled

    def get_process_value(self) -> float:
        return self.instrument.read_register(1)

    @pyqtSlot()
    def set_setpoint_value(self, setpoint_value: float = None) -> bool:
        print("TIMEOUT")
        if setpoint_value is None:
            setpoint_value = self.setpoint_value
        else:
            self.setpoint_value = setpoint_value

        if self.setpoint_control_enabled:
            self.instrument.write_register(26, int(setpoint_value))
        else:
            self.instrument.write_register(26, 20)
        return True

    def get_setpoint_value(self) -> float:
        return self.instrument.read_register(26)

    def get_input_range_low(self) -> float:
        return self.instrument.read_register(11)

    def set_input_range_low(self, range_limit: float) -> bool:
        self.instrument.write_register(11, int(range_limit*10))
        return True

    def get_input_range_high(self) -> float:
        return self.instrument.read_register(12)

    def set_input_range_high(self, range_limit: float) -> bool:
        self.instrument.write_register(12, int(range_limit*10))
        return True

    def get_instrument_status(self) -> InstrumentStatus:
        bit_values = bin(self.instrument.read_register(75))  # do [::-1] if the order is wrong
        status = self.InstrumentStatus(
            alarm1_status=bool(bit_values[0]),
            alarm2_status=bool(bit_values[1]),
            alarm3_status=bool(bit_values[2]),
            alarm4_status=bool(bit_values[3]),
            sensor_break_status=bool(bit_values[5]),
            pv_overrange_status=bool(bit_values[10]),
            new_alarm_status=bool(bit_values[12]))

        return status

    def get_pv_offset(self) -> float:
        return self.instrument.read_register(141)

    def set_pv_offset(self, pv_offset: float):
        self.instrument.write_register(141, int(pv_offset*10))
        return True
