import serial
from serial import Serial
from serial.tools import list_ports

from src.drivers.DeviceBase import DeviceBase


class SerialDeviceBase(DeviceBase):
    DEFAULTS = {
        "baudrate": 9600,
        "parity": serial.PARITY_NONE,
        "bytesize": serial.EIGHTBITS,
        "stopbits": serial.STOPBITS_ONE,
        "timeout": 3
    }

    def __init__(self, internal_id: str):
        super().__init__(internal_id)
        self.serial = None  # Serial connection will be stored here
        self.logger.info(f"Initialized serial device {self.device_id()}")

    def create_serial_from_settings(self, key: str = "serial") -> Serial:
        """
        Convenience function to create a Serial object based settings stored in application settings
        :param key: custom group key to access within settings to retrieve the settings for given device

        :return: a Serial object based on values present in settings
        """
        self.settings.beginGroup(self.internal_id)
        self.settings.beginGroup(key)
        s = Serial(
            port=self.settings.value("port", defaultValue=None),
            baudrate=self.settings.value("baudrate", defaultValue=self.DEFAULTS["baudrate"]),
            parity=self.settings.value("parity", defaultValue=self.DEFAULTS["parity"]),
            bytesize=self.settings.value("bytesize", defaultValue=self.DEFAULTS["bytesize"]),
            stopbits=float(self.settings.value("stopbits", defaultValue=self.DEFAULTS["stopbits"])),
            timeout=float(self.settings.value("timeout", defaultValue=self.DEFAULTS["timeout"]))
        )
        self.settings.endGroup()  # key
        self.settings.endGroup()  # internal id

        return s

    def is_connected(self) -> bool:
        """
        Check if the device is connected by verifying if the port is available and if the serial connection is open.

        :return: True if connected, otherwise False.
        """
        available_ports = [port.device for port in list_ports.comports()]
        port_in_settings = self.settings.value(f"{self.internal_id}/serial/port", defaultValue=None)

        if port_in_settings in available_ports:
            if self.serial:
                self.logger.info(f"Device {self.device_id()} is connected on port {port_in_settings}")
                return self.serial.is_open
            self.logger.warning(f"Device {self.device_id()} has no serial connection object")
            return False

        self.logger.warning(f"Port {port_in_settings} not found in available ports for {self.device_id()}")

        return False

    def connect(self):
        """
        Connects to the device by closing the current connection (if open) and then reopening it.
        :returns nothing
        :raises any exception that can happen during connecting, e.g. SerialException
        """
        if self.serial and self.serial.is_open:  # If connection exists and is open
            self.logger.info(f"Closing existing connection for {self.device_id()}")
            self.serial.close()

        self.logger.info(f"Creating serial for {self.device_id()}")
        self.serial = self.create_serial_from_settings()  # Create a new connection from settings

        if self.serial and self.serial.port is None:
            raise ValueError(f"No port specified for {self.device_id()}")

    def disconnect(self):
        if self.serial is not None and self.serial.is_open:
            self.serial.close()
        self.logger.info(f"Disconnected {self.device_id()}")

    def device_id(self):
        return f"{self.__class__.__name__} @ {self.settings.value(f'{self.internal_id}/serial/port')}"

