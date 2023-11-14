class MockFloatModbusClient:

    def __init__(self, host: str, *args, **kwargs):
        self.host = host

    def close(self):
        return True

    def open(self):
        return True

    def read_input_registers(self, address, length):
        # Based on the address, return the expected word list.
        if address == 0x4000:
            return [0, 0]  # Mock flow value
        elif address == 0x4002:
            return [0, 0]  # Mock temperature value
        elif address == 0x4004:
            return [0, 0]  # Mock valve position value
        elif address == 0x4008:
            return [0, 0]  # Mock flow hours value
        elif address == 0x400A:
            return [0, 0]  # Mock flow total value
        else:
            return [0, 0]

    def read_float(self, address, length):
        # Based on the address, return the expected float value.
        if address == 0xA000:
            return [1.0]  # Mock setpoint value
        else:
            return [0.0]

    def write_float(self, address, value):
        # For mocking, just return True to represent successful write.
        return True

    def read_holding_registers(self, address, length):
        # Based on the address, return the expected int value.
        if address == 0xA002:
            return [1]  # Mock ramp rate value
        elif address == 0xA004:
            return [1]  # Mock unit type value
        else:
            return [0]

    def write_multiple_registers(self, address, value):
        # For mocking, just return True to represent successful write.
        return True

    def write_single_coil(self, address, value):
        # For mocking, just return True to represent successful write.
        return True

    def read_coils(self, address):
        # Based on the address, return the expected coil state.
        if address == 0xE001:
            return True  # Mock OPEN valve state
        elif address == 0xE002:
            return False  # Mock CLOSED valve state
        else:
            return False
