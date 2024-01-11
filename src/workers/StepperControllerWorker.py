from PyQt5.QtCore import pyqtSignal, pyqtSlot

from src.drivers.stepper.MockStepperControllerAxis import MockStepperControllerAxis
from src.drivers.stepper.StepperControllerAxis import StepperControllerAxis
from src.workers.GenericWorker import GenericWorker


class StepperControllerWorker(GenericWorker):
    DEVICE_CLASS = StepperControllerAxis
    MOCK_DEVICE_CLASS = MockStepperControllerAxis

    @pyqtSlot()
    def function_to_call_periodically(self):
        self.device.currentOperationReady.emit(self.device.display_current_operation())
        self.device.velocityReady.emit(self.device.output_velocity())
        self.device.actualPositionReady.emit(self.device.output_command_position())
