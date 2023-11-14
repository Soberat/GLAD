import random
from typing import Dict, Tuple

from src.drivers.sr201.SR201 import SR201, RelayState, SR201Error


class MockSR201(SR201):
    def __init__(self, internal_id: str):
        super().__init__(internal_id)
        self.states = [random.randint(0, 1) for _ in range(0, 16)]

    def is_connected(self):
        return True

    def connect(self):
        pass

    def disconnect(self):
        pass

    def get_relay_states(self, relay_n: int = -1) -> Dict[int, Tuple[str, RelayState]]:
        states = [RelayState(state) for state in self.states] if relay_n == -1 else [RelayState(self.states[relay_n])]

        result = {}
        for i, state in enumerate(states):
            relay_name = self.settings.value(f"{self.internal_id}/relays/{i}/name", defaultValue=f"Relay {i}")
            result[i] = (relay_name, state)

        return result

    def set_relay_state(self, relay_n: int, state: RelayState, duration: int = -1) -> bool:
        assert 0 <= relay_n <= 15

        if duration != -1:
            raise SR201Error("Duration not supported by mock device")

        self.states[relay_n] = state.value
        self.stateChanged.emit(relay_n, state)

        return True
