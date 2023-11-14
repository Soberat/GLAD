import random
from datetime import datetime

import numpy as np

from src.drivers.rx01.RX01 import RX01


class MockRX01(RX01):
    def __init__(self, internal_id: str):
        super().__init__(internal_id)
        self.power_setpoint = 0
        self.target_power_setpoint = 0
        self.previous_setpoint = 0
        self.voltage_setpoint = 0
        self.rf_output_enabled = False
        self.rf_output_ramping_enabled = False
        self.rf_output_rampup_interval = 0
        self.rf_output_rampdown_interval = 0
        self.setpoint_timestamp = 0
        self.load_cap_preset_position = 0
        self.tune_cap_preset_position = 0

    def is_connected(self) -> bool:
        return datetime.now().minute % 2 == 1

    def connect(self):
        if datetime.now().minute % 2 != 1:
            raise ValueError("(Mock) No port defined for RX01")

    def set_power_setpoint(self, setpoint_in_watts: int):
        assert setpoint_in_watts <= 9999
        self.previous_setpoint = self.target_power_setpoint
        self.target_power_setpoint = setpoint_in_watts
        self.setpoint_timestamp = datetime.now().timestamp()
        return self.target_power_setpoint

    def disable_power_and_rf_output(self):
        self.rf_output_enabled = False
        return self.rf_output_enabled

    def set_power_setpoint_and_enable_rf_output(self, setpoint_in_watts: int):
        assert setpoint_in_watts <= 9999
        self.previous_setpoint = self.target_power_setpoint
        self.target_power_setpoint = setpoint_in_watts
        self.setpoint_timestamp = datetime.now().timestamp()
        self.rf_output_enabled = True
        return self.target_power_setpoint, self.rf_output_enabled

    def set_voltage_setpoint(self, voltage_in_volts: int):
        assert voltage_in_volts <= 9999
        self.voltage_setpoint = voltage_in_volts
        return self.voltage_setpoint

    def enable_rf_output(self):
        self.rf_output_enabled = True
        return self.rf_output_enabled

    def disable_rf_output(self):
        self.rf_output_enabled = False
        return self.rf_output_enabled

    def enable_rf_output_ramping(self):
        self.rf_output_ramping_enabled = True
        return True

    def disable_rf_output_ramping(self):
        self.rf_output_ramping_enabled = False
        return True

    def set_rf_output_rampdown_time_interval(self, interval_in_seconds: int):
        assert 1 <= interval_in_seconds <= 9999
        self.rf_output_rampdown_interval = interval_in_seconds

    def set_rf_output_rampup_time_interval(self, interval_in_seconds: int):
        assert 1 <= interval_in_seconds <= 9999
        self.rf_output_rampup_interval = interval_in_seconds

    def get_forward_power_output(self):
        if not self.rf_output_enabled:
            return False

        if self.rf_output_ramping_enabled:
            if self.target_power_setpoint > self.power_setpoint:
                time_coefficient = np.clip(
                    (datetime.now().timestamp() - self.setpoint_timestamp) / self.rf_output_rampup_interval,
                    a_min=0,
                    a_max=1
                )
            elif self.target_power_setpoint < self.power_setpoint:
                time_coefficient = np.clip(
                    (datetime.now().timestamp() - self.setpoint_timestamp) / self.rf_output_rampdown_interval,
                    a_min=0,
                    a_max=1
                )
            else:
                time_coefficient = 1
            self.power_setpoint = self.previous_setpoint + \
                                  (self.target_power_setpoint - self.previous_setpoint) * time_coefficient
            return self.power_setpoint
        else:
            return self.target_power_setpoint

    def get_reflected_power(self):
        return random.randint(40, 60)

    def get_dc_bias_voltage(self):
        return 0

    def get_mc2_load_cap_preset_position(self):
        return self.load_cap_preset_position

    def get_mc2_tune_cap_preset_position(self):
        return self.tune_cap_preset_position

    def set_mc2_load_cap_preset_position(self, position_percentage: float):
        assert 0 <= position_percentage <= 100
        self.load_cap_preset_position = position_percentage
        return self.load_cap_preset_position

    def set_mc2_tune_cap_preset_position(self, position_percentage: float):
        assert 0 <= position_percentage <= 100
        self.tune_cap_preset_position = position_percentage
        return self.tune_cap_preset_position
