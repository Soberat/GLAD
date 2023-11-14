import logging
import uuid

from PyQt5.QtCore import QSettings

from src.utils.DeviceLoggerAdapter import DeviceLoggerAdapter


class DeviceBase:
    def __init__(self, internal_id: str):
        if not internal_id:
            raise AttributeError(f"No internal ID supplied. Here's one you can use: {uuid.uuid4()}")
        self.internal_id = internal_id

        # Provide settings as a convenience
        self.settings: QSettings = QSettings("Mirosław Wiącek Code", "GLAD")

        self.logger = DeviceLoggerAdapter(logging.getLogger(__name__), extra=self)

    def is_connected(self):
        raise NotImplementedError()

    def connect(self):
        raise NotImplementedError()

    def disconnect(self):
        raise NotImplementedError()

    def device_id(self):
        return f"{self.__class__.__name__} @ {self.internal_id.split('--')[1][:8]}"
