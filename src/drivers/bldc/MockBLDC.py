from src.drivers.SerialDeviceBase import SerialDeviceBase


class MockBLDC(SerialDeviceBase):
    def __init__(self, internal_id: str):
        super().__init__(internal_id)
        self.direction = None
        self.dac_val = 0

    def set_direction_left(self):
        self.direction = "left"

    def set_direction_right(self):
        self.direction = "right"

    def set_dac_val(self, val: int):
        assert 0 <= val <= 4095
        self.dac_val = val
