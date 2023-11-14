from src.drivers.stepper.StepperControllerAxis import StepperControllerAxis


class MockStepperControllerAxis(StepperControllerAxis):
    def __init__(self, internal_id: str):
        super().__init__(internal_id)
        self.current_velocity = 0
        self.current_position = 0
        self.target_position = None
        self.creep_speed = None
        self.creep_steps = None
        self.acceleration = 1000  # steps per second squared
        self.deceleration = -1000  # steps per second squared

    def is_connected(self) -> bool:
        return True

    def connect(self):
        pass

    def set_creep_steps(self, steps):
        self.creep_steps = steps

    def set_creep_speed(self, steps_per_second):
        self.creep_speed = steps_per_second

    def move_relative(self, steps: int):
        # Set the target position
        self.target_position = self.current_position + steps

    def go_home_to_datum(self, positive_direction: bool):
        # Based on the direction, choose a value to simulate motion in that direction
        self.target_position = 1e6 if positive_direction else -1e6

    def display_current_operation(self) -> str:
        # If current position is at target, return "idle"
        if self.current_position == self.target_position:
            return "idle"

        # If target position is zero, we're homing
        elif self.target_position == 0:
            return "home"
        else:
            return "moving"

    def output_actual_position(self):
        return self.current_position

    def set_velocity(self, steps_per_second):
        self.current_velocity = steps_per_second

    def output_velocity(self):
        return self.current_velocity

    def update_velocity_and_position(self, time_elapsed: float):
        # Calculate the new velocity considering acceleration
        self.current_velocity += self.acceleration * time_elapsed

        # If we're close to the target and need to creep, adjust the velocity
        if abs(self.target_position - self.current_position) <= self.creep_steps:
            self.current_velocity = min(self.creep_speed, self.current_velocity)

        # Update the current position
        self.current_position += self.current_velocity * time_elapsed

        # Decelerate if necessary
        if (self.current_position - self.target_position) * self.current_velocity > 0:
            self.current_velocity += self.deceleration * time_elapsed
