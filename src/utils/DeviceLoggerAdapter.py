import logging


class DeviceLoggerAdapter(logging.LoggerAdapter):
    """
    A logging adapter used in device classes that adds the device ID to the message
    """
    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        extra["device_id"] = self.extra.device_id()
        kwargs["extra"] = extra

        return msg, kwargs

