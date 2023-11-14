from src.drivers.mks_mfc.MksEthMfc import MksEthMfc
from src.drivers.mks_mfc.MockFloatModbusClient import MockFloatModbusClient


class MockMksEthMfc(MksEthMfc):
    def __init__(self, internal_id: str):
        super().__init__(internal_id)
        self.modbus_client = MockFloatModbusClient(host=self.modbus_client.host, port=502, unit_id=1, auto_open=True)

    def is_connected(self) -> bool:
        return True

    def connect(self):
        pass
