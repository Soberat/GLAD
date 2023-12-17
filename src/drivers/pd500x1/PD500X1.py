from typing import Union


from src.drivers.SerialDeviceBase import SerialDeviceBase


class PD500X1(SerialDeviceBase):
    ERROR_CODES = {
        "Error 10": "Invalid Match(Repeat is active, use S97 to disable)",
        "Error 11": "Data Invalid",
        "Error 12": "Command Invalid",
        "Error 13": "Needs to be in standby for this command",
        "Error 14": "Needs to be in RS232 control for this command",
        "Error 15": "Data out of range (Check supply min-max settings)"
    }

    def __write_and_read(self, command: str, expected_response: Union[str, None] = "OK") -> Union[str, bool]:
        self.logger.debug(f"Writing {command}")
        self.serial.write(f"{command}\r".encode())
        response = self.serial.read_until(b"\r\n").decode().replace("\r\n", "")

        self.logger.debug(f"Response for {command}: {response}")

        if not expected_response:
            return response

        if response in self.ERROR_CODES:
            return self.ERROR_CODES[response]

        if response != expected_response:
            raise ValueError(f"Unexpected response for command {command}: '{response}'")

        return True

    # Help commands
    def set_commands_help(self):
        return self.__write_and_read("H00", None)

    def query_commands_help(self):
        return self.__write_and_read("H01", None)

    # Set commands
    def set_analog_control(self):
        return self.__write_and_read("S00")

    def set_rs232_control(self):
        return self.__write_and_read("S01")

    def enable_output(self):
        return self.__write_and_read("S02")

    def disable_output(self):
        return self.__write_and_read("S03")

    def set_active_target_number(self, target_number: int):
        if target_number not in list(range(1, 8, 1)):
            return "Target number not in range"
        return self.__write_and_read(f"S04 {target_number}")

    def set_heartbeat_timeout(self, timeout_in_seconds: float):
        if not 0.0 <= timeout_in_seconds <= 65.535:
            return "Heartbeat timeout value not in range"

        return self.__write_and_read(f"S09 {timeout_in_seconds:.3f}")

    def set_active_target_power_setpoint(self, watts: float):
        if not 0.0 <= watts <= 500:
            return "Active target power setpoint not in range"

        return self.__write_and_read(f"S10 {watts:.1f}")

    def set_active_target_current_setpoint(self, amps: float):
        if not 0.0 <= amps < 10:
            return "Active target current setpoint not in range"

        return self.__write_and_read(f"S11 {amps:.3f}")

    def set_active_target_voltage_setpoint(self, volts: float):
        if not 0.0 <= volts < 10000:
            return "Active target voltage setpoint not in range"

        return self.__write_and_read(f"S12 {volts:.1f}")

    def set_active_target_arc_detect_delay(self, delay_in_us: float):
        if not 0.0 <= delay_in_us <= 999.9:
            return "Active target arc detect delay not in range"

        return self.__write_and_read(f"S13 {delay_in_us:.1f}")

    def set_active_target_arc_off_time(self, time_in_us: int):
        if not 32 <= time_in_us <= 65535 or time_in_us == 0:
            return "Active target arc off time not in range"

        return self.__write_and_read(f"S14 {time_in_us}")

    def set_active_target_kwh_limit(self, kwh_limit: float):
        if not 0.0 <= kwh_limit <= 655.35:
            return "Active target kWh limit not in range"

        return self.__write_and_read(f"S15 {kwh_limit:.2f}")

    def clear_active_target_kwh_count(self):
        return self.__write_and_read("S16")

    def set_active_target_ramp_time(self, seconds: float):
        if not 0.0 <= seconds <= 65.535:
            return "Active target ramp time setpoint not in range"

        return self.__write_and_read(f"S17 {seconds:02.3f}")

    def set_active_target_run_time(self, seconds: float):
        if not 0.0 <= seconds <= 6553.5:
            return "Active target power setpoint not in range"

        return self.__write_and_read(f"S18 {seconds:.1f}")

    def reset_factory_defaults(self):
        return self.__write_and_read("S67")

    def enable_repeat_mode(self):
        return self.__write_and_read("S96") is True and self.__write_and_read("S96") is True

    def disable_repeat_mode(self):
        return self.__write_and_read("S97")

    def enable_echo_mode(self):
        return self.__write_and_read("S99")

    def disable_echo_mode(self):
        return self.__write_and_read("S99")

    # Query commands
    def read_fault_bits(self):
        response = self.__write_and_read("Q00", None).split(",")
        interlock_open = bool(int(response[0]))
        bus_fault = bool(int(response[1]))
        ac_line_current_limit = bool(int(response[2]))
        thermal_sensor_fault = bool(int(response[3]))
        overtemp_fault = bool(int(response[4]))
        heartbeat_timeout_fault = bool(int(response[5]))

        return ",".join([
            "Interlock open" if interlock_open else "Interlock OK",
            "Bus fault" if bus_fault else "Bus OK",
            "AC Line Current Limit" if ac_line_current_limit else "AC Line Current OK",
            "Thermal sensor fault" if thermal_sensor_fault else "Thermal sensor OK",
            "Overtemp fault" if overtemp_fault else "No overtemp",
            "Heartbeat timeout fault" if heartbeat_timeout_fault else "Heartbeat OK"
        ])

    def read_status_bits(self):
        output_enabled, rs232_control = self.__write_and_read("Q01", None).split(",")

        return ",".join([
            "Output enabled" if int(output_enabled) == 1 else "Output disabled",
            "RS232 control active" if int(rs232_control) == 1 else "RS232 control disabled"
        ])

    def read_hard_arc_count(self):
        return self.__write_and_read("Q02", None)

    def read_micro_arc_count(self):
        return self.__write_and_read("Q03", None)

    def read_active_target_Number(self):
        return self.__write_and_read("Q04", None)

    def read_actual_power_in_Watts(self):
        return self.__write_and_read("Q05", None)

    def read_actual_current_in_amps(self):
        return self.__write_and_read("Q06", None)

    def read_actual_voltage_in_volts(self):
        return self.__write_and_read("Q07", None)

    def read_arc_rate_in_arcs_per_second(self):
        return self.__write_and_read("Q08", None)

    def read_heartbeat_timeout_in_seconds(self):
        return self.__write_and_read("Q09", None)

    def read_active_target_power_setpoint_in_Watts(self):
        return self.__write_and_read("Q10", None)

    def read_active_target_current_setpoint_in_amps(self):
        return self.__write_and_read("Q11", None)

    def read_active_target_voltage_setpoint_in_volts(self):
        return self.__write_and_read("Q12", None)

    def read_active_target_arc_Detect_Delay_time_in_us(self):
        return self.__write_and_read("Q13", None)

    def read_active_target_arc_Off_time_in_us(self):
        return self.__write_and_read("Q14", None)

    def read_active_target_kilowatthour_Limit_in_kWh(self):
        return self.__write_and_read("Q15", None)

    def read_active_target_kilowatthour_count_in_kWh(self):
        return self.__write_and_read("Q16", None)

    def read_active_target_ramp_time_in_s(self):
        return self.__write_and_read("Q17", None)

    def read_active_target_run_time_in_s(self):
        return self.__write_and_read("Q18", None)

    def report_all_output_and_arc_parameters(self):
        # comma delimited power, current, voltage, arc rate, hard arc count and micro arc count
        return self.__write_and_read("Q19", None)
