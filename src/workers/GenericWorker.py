from typing import Type

from PyQt5.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot, QSettings
from retry import retry_call

from src.drivers.DeviceBase import DeviceBase


class GenericWorker(QObject):
    task_received = pyqtSignal(object)
    task_failed = pyqtSignal(str)
    task_successful = pyqtSignal()

    periodic_function_failed = pyqtSignal(str)
    periodic_function_successful = pyqtSignal()

    set_interval_requested = pyqtSignal(int)
    close_connection_requested = pyqtSignal()

    # Define the class that the worker is designed for
    DEVICE_CLASS: Type[DeviceBase] = DeviceBase
    MOCK_DEVICE_CLASS: Type[DeviceBase] = DeviceBase

    def __init__(self, internal_id: str, mock: bool, poll_interval: int = 10000):
        """
        Create a generic worker, that based on the implementation values will create a device from the internal ID.
        The worker executes 'function_to_call_periodically' every self.current_interval milliseconds,
        and asynchronously executes tasks passed using add_task.

        :param internal_id: The ID identifying the unique instance
        :param mock: whether the created device is supposed to be an instance of the real device, or the mock device
        :param poll_interval: initial interval of periodic polling, used only if there is no value defined in settings
        """

        super().__init__()
        if mock:
            self.device = self.MOCK_DEVICE_CLASS(internal_id)
        else:
            self.device = self.DEVICE_CLASS(internal_id)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.function_to_call_periodically_wrapper)
        self.task_received.connect(self.execute_task)

        self.set_interval_requested.connect(self._handle_set_interval)
        self.close_connection_requested.connect(self._handle_close_connection)

        settings = QSettings("Mirosław Wiącek Code", "GLAD")

        settings.beginGroup(self.device.internal_id)
        settings.beginGroup("worker")
        self.current_interval = settings.value("poll_interval_ms", poll_interval)
        settings.endGroup()  # worker
        settings.endGroup()  # device ID

    def close_connection(self):
        self.close_connection_requested.emit()

    @pyqtSlot()
    def _handle_close_connection(self):
        self.device.disconnect()

    @pyqtSlot()
    def function_to_call_periodically_wrapper(self):
        self.device.logger.debug("Worker starting periodic call")
        try:
            if not self.device.is_connected():
                # Indefinitely try to reconnect
                retry_call(
                    f=self.device.connect,
                    delay=30,
                    max_delay=300,
                    jitter=30,
                    logger=self.device.logger,
                    on_exception=lambda v: self.periodic_function_failed.emit(str(v))
                )
            self.device.logger.debug("Device connected for periodic call")
            self.function_to_call_periodically()
            self.device.logger.debug("Periodic call successful")
            self.periodic_function_successful.emit()
        except Exception as e:
            self.device.logger.error(f"Error executing periodic function: {e}")
            self.periodic_function_failed.emit(str(e))
        finally:
            self.timer.start()

    @pyqtSlot()
    def function_to_call_periodically(self):
        """
        Adding the pyqtSlot decorator makes the function run properly in the worker thread.
        Without it, it was running in the UI thread

        :return:
        """
        raise NotImplementedError()

    @pyqtSlot()
    def run(self):
        self.timer.start(self.current_interval)

    @pyqtSlot(object)
    def execute_task(self, task_function):
        """Execute a received task."""
        try:
            if not self.device.is_connected():
                # Indefinitely try to reconnect
                retry_call(
                    f=self.device.connect,
                    delay=5,
                    max_delay=10,
                    jitter=5,
                    logger=self.device.logger,
                    on_exception=lambda v: self.task_failed.emit(str(v))
                )

            task_function()
            self.task_successful.emit()
        except Exception as e:
            self.device.logger.error(f"Error executing task: {str(e)}")

    def add_task(self, task_function):
        """
        Enqueue a task to be executed by the worker asynchronously

        :param task_function: any callable
        :return: nothing
        """
        self.task_received.emit(task_function)

    @pyqtSlot(int)
    def _handle_set_interval(self, interval_ms: int):
        """
        Internal slot to handle timer interval updates in a thread-safe manner.

        :param interval_ms: new interval in milliseconds
        """
        # Check for an actual change, since start will restart the timer
        if interval_ms != self.current_interval:
            self.current_interval = interval_ms
            self.timer.stop()
            self.timer.start(self.current_interval)

    def set_interval(self, interval_ms: int):
        """
        Emit a signal to set a new periodic polling interval value.

        :param interval_ms: new interval in milliseconds
        """
        self.set_interval_requested.emit(interval_ms)
