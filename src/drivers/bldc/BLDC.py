from src.drivers.SerialDeviceBase import SerialDeviceBase


class BLDC(SerialDeviceBase):
    def set_direction_left(self):
        self.serial.write("BLDC_DIRECTION_LEFT\r\n".encode())
        self.serial.read(16)

    def set_direction_right(self):
        self.serial.write("BLDC_DIRECTION_RIGHT\r\n".encode())
        self.serial.read(16)

    def set_dac_val(self, val: int):
        assert 0 <= val <= 4095
        self.serial.write(f"BLDC_DAC_VAL_{val}\r\n".encode())
        self.serial.read(16)