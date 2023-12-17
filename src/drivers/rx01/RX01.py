from enum import Enum
from typing import Union

import serial

from src.drivers.SerialDeviceBase import SerialDeviceBase


class RX01(SerialDeviceBase):
    DEFAULTS = {
        "baudrate": 19200,
        "parity": serial.PARITY_NONE,
        "bytesize": serial.EIGHTBITS,
        "stopbits": serial.STOPBITS_ONE,
        "timeout": 3
    }

    class RX01Model(Enum):
        R301 = "R301"
        R601 = "R601"

    class ControlSource(Enum):
        PANEL = "0"
        ANALOG = "1"
        SERIAL = "2"

    class RfOutRegulationFeedbackSource(Enum):
        INTERNAL_SENSOR = "3"
        EXTERNAL_SENSOR = "0"

    class CommLinkStatus(Enum):
        OK = "0"
        FAULT = "1"

    def __init__(self, internal_id: str):
        super().__init__(internal_id)
        self.settings.beginGroup(internal_id)
        self.model = self.RX01Model(self.settings.value("model", defaultValue="R301"))
        self.settings.endGroup()  # internal id

        self.rf_output_enabled = False

    def __write_and_read(self, command: str, expected_response: Union[str, None] = "\r") -> Union[str, bool]:
        self.logger.debug(f"Writing {command}")
        self.serial.write(f"{command}\r".encode())
        response = self.serial.read_until(b"\r").decode()

        self.logger.debug(f"Response for {command}: {response}")

        if response == "N\r":
            return False

        if not expected_response:
            return response

        if response != expected_response:
            raise ValueError(f"Unexpected response for command {command}: '{response}'")

        return True

    def assert_serial_control(self) -> bool:
        return self.__write_and_read("SERIAL")

    def enable_serial_echo_mode(self) -> bool:
        return self.__write_and_read("ECHO")

    def disable_serial_echo_mode(self) -> bool:
        return self.__write_and_read("NOECHO")

    def assert_analog_control(self) -> bool:
        return self.__write_and_read("ANALOG")

    def assert_panel_control(self) -> bool:
        return self.__write_and_read("PANEL")

    def set_operating_frequency(self, freq_in_mhz: float) -> bool:
        assert 1.7 <= freq_in_mhz <= 2.1

        device_value_string = str(int(round(freq_in_mhz, 1) * 100))

        return self.__write_and_read(f"{device_value_string} FQ")

    def set_exciter_mode_to_master(self) -> bool:
        return self.__write_and_read("MST")

    def set_exciter_mode_to_slave(self) -> bool:
        return self.__write_and_read("SLV")

    def select_forward_power_leveling(self) -> bool:
        return self.__write_and_read("DL")

    def select_load_power_leveling(self) -> bool:
        return self.__write_and_read("EL")

    def select_power_control_mode(self):
        return self.__write_and_read("IR")

    def select_voltage_control_mode(self):
        return self.__write_and_read("DR")

    def set_power_setpoint(self, setpoint_in_watts: int):
        assert setpoint_in_watts <= 9999
        return self.__write_and_read(f"{setpoint_in_watts} W")

    def disable_power_and_rf_output(self):
        status = self.__write_and_read("WS") 

        if status:
            self.rf_output_enabled = False

        return status

    def set_power_setpoint_and_enable_rf_output(self, setpoint_in_watts: int):
        assert setpoint_in_watts <= 9999
        status = self.__write_and_read(f"{setpoint_in_watts} WG", "\r\r")

        if status:
            self.rf_output_enabled = False

        return status

    def set_voltage_setpoint(self, voltage_in_volts: int):
        assert voltage_in_volts <= 9999
        return self.__write_and_read(f"{voltage_in_volts} V")

    def set_process_pulse_duty_cycle(self, duty_cycle: float):
        if self.model == RX01.RX01Model.R301:
            return False

        assert 0 <= duty_cycle <= 1

        device_value_string = str(int(round(duty_cycle, 1) * 100))

        return self.__write_and_read(f"{device_value_string} D")

    def set_process_pulse_frequency(self, frequency_in_hertz: int):
        assert 1 <= frequency_in_hertz <= 1000
        return self.__write_and_read(f"{frequency_in_hertz} PR")

    def set_process_pulse_high_time(self, pulse_high_time_in_ms: int):
        if self.model == RX01.RX01Model.R301:
            return False

        assert 1 <= pulse_high_time_in_ms <= 9999
        return self.__write_and_read(f"{pulse_high_time_in_ms} HT")

    def set_process_pulse_low_power_setpoint(self, pulse_low_power_setpoint_in_watts: int):
        if self.model != RX01.RX01Model.R301:
            return False

        assert 1 <= pulse_low_power_setpoint_in_watts <= 9999
        return self.__write_and_read(f"{pulse_low_power_setpoint_in_watts} LP")

    def enable_pulse_mode(self):
        return self.__write_and_read("+P")

    def disable_pulse_mode(self):
        return self.__write_and_read("-P")

    def set_vft_coarse_trip_ratio(self, ratio: float):
        assert 0 <= ratio <= 1

        device_value_string = str(int(round(ratio, 1) * 100))

        return self.__write_and_read(f"{device_value_string} CR")

    def set_vft_coarse_frequency_step(self, step: int):
        assert 1 <= step <= 10000

        return self.__write_and_read(f"{step:05} CF")

    def set_vft_fine_frequency_step(self, step: int):
        assert 1 <= step <= 10000

        return self.__write_and_read(f"{step:05} FF")

    def set_vft_fine_trip_level(self, level: float):
        assert 0 <= level <= 1

        device_value_string = str(int(round(level, 1) * 100))

        return self.__write_and_read(f"{device_value_string} FT", "\r\r")

    def set_maximum_vft_frequency(self, frequency_in_mhz: int):
        assert 1.7 <= frequency_in_mhz <= 2.1

        device_value_string = str(int(round(frequency_in_mhz, 1) * 100))

        return self.__write_and_read(f"{device_value_string} MAXVF")

    def set_minimum_vft_frequency(self, frequency_in_mhz: int):
        assert 1.7 <= frequency_in_mhz <= 2.1

        device_value_string = str(int(round(frequency_in_mhz, 1) * 100))

        return self.__write_and_read(f"{device_value_string} MINVF")

    def set_vft_strike_frequency(self, frequency_in_mhz: int):
        assert 1.7 <= frequency_in_mhz <= 2.1

        device_value_string = str(int(round(frequency_in_mhz, 1) * 100))

        return self.__write_and_read(f"{device_value_string} SF")

    def enable_variable_frequency_tuning(self):
        return self.__write_and_read("VX")

    def disable_variable_frequency_tuning(self):
        return self.__write_and_read("FX")

    def enable_rf_output(self):
        status = self.__write_and_read("G") 
        
        if status:
            self.rf_output_enabled = True
        
        return status

    def disable_rf_output(self):
        status = self.__write_and_read("S") 
        
        if status:
            self.rf_output_enabled = False
        
        return status

    def enable_rf_output_ramping(self):
        return self.__write_and_read("EU")

    def disable_rf_output_ramping(self):
        return self.__write_and_read("DU")

    def set_rf_output_rampdown_time_interval(self, interval_in_seconds: int):
        assert 1 <= interval_in_seconds <= 9999
        return self.__write_and_read(f"{interval_in_seconds} DN")

    def set_rf_output_rampup_time_interval(self, interval_in_seconds: int):
        assert 1 <= interval_in_seconds <= 9999
        return self.__write_and_read(f"{interval_in_seconds} UP")

    def get_forward_power_output(self) -> float:
        # doc does not list carriage return in command
        return int(self.__write_and_read("W?", None))

    def get_reflected_power(self) -> float:
        # same as above
        return float(self.__write_and_read("R?", None))

    def get_dc_bias_voltage(self) -> int:
        return int(self.__write_and_read("0?", None))

    def get_control_voltage(self):
        return self.__write_and_read("V?", None)

    def get_power_leveling_mode(self):
        response = self.__write_and_read("LVL?", None)

        if response == "0\r":
            return "Forward power leveling"
        elif response == "1\r":
            return "Load (net) power leveling"

        return response

    @staticmethod
    def __parse_status_flag_char4(char):
        ascii_decoded = bin(ord(char))

        return {
            "rf_on": bool(ascii_decoded[-4]),
            "reflected_limit_active": bool(ascii_decoded[-3]),
            "max_power_limit_active": bool(ascii_decoded[-2]),
            "pa_current_limit_active": bool(ascii_decoded[-1])
        }

    @staticmethod
    def __parse_status_flag_char5(char):
        ascii_decoded = bin(ord(char))

        return {
            "ref_power_alarm_threshold_exceeded": not bool(ascii_decoded[-4]),
            "dissipation_limit_active": bool(ascii_decoded[-3]),
            "cex_slave_mode": bool(ascii_decoded[-2]),
            "pulse_mode_active": bool(ascii_decoded[-1])
        }

    @staticmethod
    def __parse_status_flag_char6(char):
        ascii_decoded = bin(ord(char))

        return {
            "external_interlock_ok": bool(ascii_decoded[-2]),
            "temperature_alarm_active": bool(ascii_decoded[-1])
        }

    def get_long_status(self):
        # Returns status in the form of a mapped string, terminated with <cr>. See Serial Command
        # details for string mapping information.
        # XXXXXXX_aaaa_bbbb_ccc_dddd <cr>
        # aaaa is the setpoint, in Watts
        # bbbb is the Forward Power, in Watts
        # ccc is Reflected Power, in Watts
        # dddd is the maximum power, in Watts
        # XXXXXXX is a 7 - character ASCII mapped string as described
        # below (characters are counted left - to - right)
        response = self.__write_and_read("Q", None)
        other, setpoint, forward_power, reflected_power, max_power = response.split(" ")

        return_data = {
            "setpoint": int(setpoint),
            "forward_power": int(forward_power),
            "reflected_power": int(reflected_power),
            "max_power": int(max_power),
            "control_source": self.ControlSource(other[0]),
            "rf_output_regulation_feedback_source": self.RfOutRegulationFeedbackSource(other[1]),
            "setpoint_source": self.ControlSource(other[2]),
            "communication_link_status": self.CommLinkStatus(other[6])
        }

        char4_data = self.__parse_status_flag_char4(other[3])
        char5_data = self.__parse_status_flag_char6(other[4])
        char6_data = self.__parse_status_flag_char6(other[5])

        return_data.update(char4_data)
        return_data.update(char5_data)
        return_data.update(char6_data)

        return return_data

    def get_short_status(self):
        response = self.__write_and_read("R", None)

        return_data = {
            "control_source": self.ControlSource(response[0]),
            "rf_output_regulation_feedback_source": self.RfOutRegulationFeedbackSource(response[1]),
            "setpoint_source": self.ControlSource(response[2]),
            "communication_link_status": self.CommLinkStatus(response[6])
        }

        char4_data = self.__parse_status_flag_char4(response[3])
        char5_data = self.__parse_status_flag_char6(response[4])
        char6_data = self.__parse_status_flag_char6(response[5])

        return_data.update(char4_data)
        return_data.update(char5_data)
        return_data.update(char6_data)

        return return_data

    def get_maximum_power(self):
        return self.__write_and_read("M?", None)
