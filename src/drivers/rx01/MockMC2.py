import random
from datetime import datetime

from src.drivers.rx01.MC2 import MC2


class MockMC2(MC2):
    def __init__(self, internal_id: str):
        super().__init__(internal_id)
        # Defining instance variables for mock values
        self.load_cap_preset_position = 0
        self.actual_load_cap_position = 0
        self.tune_cap_preset_position = 0
        self.actual_tune_cap_position = 0
        self.phase_voltage = 230
        self.magnitude_voltage = 120
        # Tracking mode: Manual or Automatic
        self.load_cap_mode = "AUTO"
        self.tune_cap_mode = "AUTO"
        # Tracking if the move function was used
        self.load_moved = False
        self.tune_moved = False

    def is_connected(self) -> bool:
        return datetime.now().minute % 2 == 1

    def connect(self):
        if datetime.now().minute % 2 != 1:
            raise ValueError("(Mock) No port defined for RX01")

    def get_mc2_load_cap_preset_position(self):
        if self.load_cap_mode == "AUTO":
            return random.randint(0, 100)
        if not self.load_moved:
            return self.actual_load_cap_position
        else:
            return self.load_cap_preset_position

    def get_mc2_tune_cap_preset_position(self):
        if self.tune_cap_mode == "AUTO":
            return random.randint(0, 100)
        if not self.tune_moved:
            return self.actual_tune_cap_position
        else:
            return self.tune_cap_preset_position

    def set_mc2_load_cap_preset_position(self, position_percentage: int):
        assert 0 <= position_percentage <= 100
        self.load_cap_preset_position = int(position_percentage)
        self.load_moved = False

    def set_mc2_tune_cap_preset_position(self, position_percentage: int):
        assert 0 <= position_percentage <= 100
        self.tune_cap_preset_position = int(position_percentage)
        self.tune_moved = False

    def get_mc2_phase_voltage(self):
        return self.phase_voltage

    def get_mc2_magnitude_voltage(self):
        return self.magnitude_voltage

    def set_mc2_load_cap_auto(self):
        self.load_cap_mode = "AUTO"

    def set_mc2_tune_cap_auto(self):
        self.tune_cap_mode = "AUTO"

    def set_mc2_load_cap_man(self):
        self.load_cap_mode = "MAN"

    def set_mc2_tune_cap_man(self):
        self.tune_cap_mode = "MAN"

    def move_tune_and_load_to_preset(self):
        if self.load_cap_mode == "MAN":
            self.load_moved = True
            self.actual_load_cap_position = self.load_cap_preset_position
        if self.tune_cap_mode == "MAN":
            self.tune_moved = True
            self.actual_tune_cap_position = self.tune_cap_preset_position

