import time

from src.drivers.eurotherm_32h8i.T32h8i import TempController32h8i


class MockTempController32h8i(TempController32h8i):
    def __init__(self, internal_id: str):
        super().__init__(internal_id)

        self.current_process_value = 0.0
        self.target_process_value = 0.0
        self.last_read_time = time.time()

        self.setpoint_control_enabled = False

    def is_connected(self) -> bool:
        return True

    def connect(self):
        pass

    def toggle_control(self, is_control_enabled: bool):
        if not is_control_enabled:
            self.set_setpoint_value(20)
        self.setpoint_control_enabled = is_control_enabled

    def get_process_value(self) -> float:
        # Calculate the change based on elapsed time and rate
        elapsed_time = time.time() - self.last_read_time
        self.last_read_time = time.time()

        # Calculate the difference between the current and target values
        difference = abs(self.current_process_value - self.target_process_value)

        # Normalize the change based on how close we are to the target
        max_difference = 10.0  # For example, 100 units as the maximum expected difference
        change = (4 * elapsed_time) * (difference / max_difference)

        # Adjust the current value to approach the target
        if self.current_process_value < self.target_process_value:
            self.current_process_value = min(self.current_process_value + change, self.target_process_value)
        elif self.current_process_value > self.target_process_value:
            self.current_process_value = max(self.current_process_value - change, self.target_process_value)

        # Return the value
        return self.current_process_value

    def set_setpoint_value(self, setpoint_value: float) -> bool:
        # Update the target when we set a new setpoint
        if self.setpoint_control_enabled:
            self.target_process_value = setpoint_value
        else:
            return False
        return True

    def get_setpoint_value(self) -> float:
        return self.target_process_value
