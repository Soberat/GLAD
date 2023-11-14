from datetime import datetime

import numpy as np

from src.drivers.pd500x1.PD500X1 import PD500X1


class MockPD500X1(PD500X1):
    def __init__(self, internal_id: str):
        super().__init__(internal_id)

        self.ramp_time = 0
        self.previous_setpoint = 0
        self.target_power_setpoint = 0
        self.output_enabled = False
        self.setpoint_timestamp = datetime.now().timestamp()

    def is_connected(self) -> bool:
        return True

    def connect(self):
        pass

    def set_active_target_power_setpoint(self, watts: float):
        self.previous_setpoint = self.target_power_setpoint
        self.setpoint_timestamp = datetime.now().timestamp()
        self.target_power_setpoint = watts

    def set_active_target_ramp_time(self, seconds: float):
        self.ramp_time = seconds

    def enable_output(self):
        self.output_enabled = True

    def disable_output(self):
        self.output_enabled = False

    def read_active_target_power_setpoint_in_Watts(self):
        return self.target_power_setpoint

    def read_actual_power_in_Watts(self):
        if not self.output_enabled:
            return 0

        if self.ramp_time == 0:
            time_coefficient = 1
        else:
            time_coefficient = np.clip(
                (datetime.now().timestamp() - self.setpoint_timestamp) / self.ramp_time,
                a_min=0,
                a_max=1
            )

        return self.previous_setpoint + (self.target_power_setpoint - self.previous_setpoint)*time_coefficient
