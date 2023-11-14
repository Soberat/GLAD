import random

from src.drivers.wp8026adam.WP8026ADAM import InputState, WP8026ADAM


class MockWP8026ADAM(WP8026ADAM):
    def is_connected(self):
        return True

    def connect(self):
        pass

    def disconnect(self):
        pass

    def get_input_states(self, input_n: int = -1) -> dict:
        assert -1 <= input_n <= 15

        result = {}

        if input_n == -1:
            states = [InputState(random.randint(0, 2)) for _ in range(0, 16)]
        else:
            states = [InputState(random.randint(0, 2))]

        # For each channel, fetch its name from settings and store in the result dictionary
        for i, state in enumerate(states):
            channel_name = self.settings.value(f"{self.internal_id}/channels/{i}/name", defaultValue=f"Channel {i}")
            result[i] = (channel_name, state)

        return result
