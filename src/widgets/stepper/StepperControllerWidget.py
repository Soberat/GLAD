from typing import Tuple, List, Dict

from PyQt5.QtWidgets import QLabel, QGroupBox, QSpinBox, QFormLayout, QDoubleSpinBox, QPushButton, QWidget

from src.widgets.DeviceWidgetBase import DeviceWidgetBase
from src.workers.StepperControllerWorker import StepperControllerWorker


class StepperControllerWidget(DeviceWidgetBase):
    def __init__(self, internal_id: str, mock: bool = False):
        super().__init__(internal_id, StepperControllerWorker, mock)

        self.worker.currentOperationReady.connect(self._on_current_operation_ready)
        self.worker.velocityReady.connect(self._on_velocity_ready)
        self.worker.actualPositionReady.connect(self._on_actual_position_ready)
        self.worker.device.homeSearchStepReady.connect(self._on_home_search_step_ready)
        self.worker.device.homeSearchStatusReady.connect(self._on_home_search_status_ready)

        self.position_timestamps = []
        self.position_values = []

        # Widget setup
        # Device values group box
        device_values_group_box = QGroupBox("Device values")
        self.current_operation_label = QLabel()
        self.velocity_label = QLabel()
        self.actual_position_label = QLabel()
        self.angle_position_label = QLabel()

        # Speed and position settings
        self.creep_steps_spinbox = QSpinBox()
        self.creep_steps_spinbox.setPrefix("Creep steps ")
        self.creep_steps_spinbox.setSuffix(" steps")
        self.creep_steps_spinbox.setRange(0, 2147483647)
        self.creep_steps_spinbox.editingFinished.connect(self._on_creep_steps_spinbox_editing_finished)

        self.creep_speed_spinbox = QSpinBox()
        self.creep_speed_spinbox.setPrefix("Creep speed ")
        self.creep_speed_spinbox.setSuffix(" st/s")
        self.creep_speed_spinbox.setRange(1, 400000)
        self.creep_speed_spinbox.editingFinished.connect(self._on_creep_speed_spinbox_editing_finished)

        self.angle_position_spinbox = QDoubleSpinBox()
        self.angle_position_spinbox.setPrefix("Angle ")
        self.angle_position_spinbox.setSuffix("°")
        self.angle_position_spinbox.setRange(-359.99, 359.99)
        self.angle_position_spinbox.setSingleStep(0.1)
        self.angle_position_spinbox.editingFinished.connect(self._on_angle_position_spinbox_editing_finished)

        self.velocity_spinbox = QSpinBox()
        self.velocity_spinbox.setPrefix("Velocity ")
        self.velocity_spinbox.setSuffix(" st/s")
        self.velocity_spinbox.setRange(1, 1200000)
        self.velocity_spinbox.editingFinished.connect(self._on_velocity_spinbox_editing_finished)

        # Home search group box
        home_search_group_box = QGroupBox("Home search")
        self.home_search_step_label = QLabel()
        self.home_search_status_label = QLabel()
        self.home_search_button = QPushButton("Start home search")
        self.home_search_button.clicked.connect(self._on_home_search_button_clicked)

        # Arranging layouts and widgets
        device_values_group_box_layout = QFormLayout()
        device_values_group_box_layout.addRow("Current operation: ", self.current_operation_label)
        device_values_group_box_layout.addRow("Velocity (step/s): ", self.velocity_label)
        device_values_group_box_layout.addRow("Position (steps): ", self.actual_position_label)
        device_values_group_box_layout.addRow("Position (deg): ", self.angle_position_label)

        device_values_group_box.setLayout(device_values_group_box_layout)

        home_search_group_box_layout = QFormLayout()
        home_search_group_box_layout.addRow("Current step: ", self.home_search_step_label)
        home_search_group_box_layout.addRow("Current operation: ", self.home_search_status_label)
        home_search_group_box_layout.addRow(self.home_search_button)

        home_search_group_box.setLayout(home_search_group_box_layout)

        self.layout().addWidget(device_values_group_box)
        self.layout().addWidget(self.creep_steps_spinbox)
        self.layout().addWidget(self.creep_speed_spinbox)
        self.layout().addWidget(self.angle_position_spinbox)
        self.layout().addWidget(self.velocity_spinbox)
        self.layout().addWidget(home_search_group_box)
        self.layout().addStretch(1)

        # After all the setup, start the worker thread
        self.thread.start()

    def get_measured_values(self) -> Dict[str, List[Tuple[int, float]]]:
        return {
            f"Position (deg)": list(zip(
                self.position_timestamps,
                [self.worker.device.get_angle_from_position(v) for v in self.position_values])),
            "Position (steps)": list(zip(
                self.position_timestamps,
                self.position_values
            ))
        }

    def clear_measured_values(self):
        self.position_timestamps = []
        self.position_values = []

    def get_settings_widget(self) -> QWidget:
        w = super().get_settings_widget()

        home_search_config_group_box = QGroupBox("Home search configuration")

        # Step 1. fast home to datum
        initial_approach_speed_spinbox = QSpinBox()
        initial_approach_speed_spinbox.setRange(1, 64000)
        initial_approach_speed_spinbox.setSuffix(" step/s")
        initial_approach_speed_spinbox.setValue(self.worker.device.home_search_initial_speed)
        home_search_config_group_box.initial_approach_speed_spinbox = initial_approach_speed_spinbox

        # Step 2. move away from hard limit
        move_away_steps_spinbox = QSpinBox()
        move_away_steps_spinbox.setRange(1, 64000)
        move_away_steps_spinbox.setSuffix(" steps")
        move_away_steps_spinbox.setValue(self.worker.device.home_search_move_away_steps)
        home_search_config_group_box.move_away_steps_spinbox = move_away_steps_spinbox

        # Step 3. slow home to datum
        slow_approach_speed_spinbox = QSpinBox()
        slow_approach_speed_spinbox.setRange(1, 64000)
        slow_approach_speed_spinbox.setSuffix(" step/s")
        slow_approach_speed_spinbox.setValue(self.worker.device.home_search_slow_speed)
        home_search_config_group_box.slow_approach_speed_spinbox = slow_approach_speed_spinbox

        conversion_function_group_box = QGroupBox("Angle-to-steps conversion function configuration")

        conversion_function_coefficient_spinbox = QDoubleSpinBox()
        conversion_function_coefficient_spinbox.setRange(-10e5, 10e5)
        conversion_function_coefficient_spinbox.setDecimals(5)
        conversion_function_coefficient_spinbox.setValue(self.worker.device.conversion_function_coefficient)
        conversion_function_group_box.conversion_function_coefficient_spinbox = conversion_function_coefficient_spinbox

        conversion_function_offset_spinbox = QDoubleSpinBox()
        conversion_function_offset_spinbox.setRange(-10e5, 10e5)
        conversion_function_offset_spinbox.setDecimals(5)
        conversion_function_offset_spinbox.setValue(self.worker.device.conversion_function_offset)
        conversion_function_group_box.conversion_function_offset_spinbox = conversion_function_offset_spinbox

        home_search_config_group_box_layout = QFormLayout()
        home_search_config_group_box_layout.addRow("Initial approach speed", initial_approach_speed_spinbox)
        home_search_config_group_box_layout.addRow("Steps to move away", move_away_steps_spinbox)
        home_search_config_group_box_layout.addRow("Slow approach speed", slow_approach_speed_spinbox)
        home_search_config_group_box.setLayout(home_search_config_group_box_layout)

        conversion_function_group_box_layout = QFormLayout()
        conversion_function_group_box_layout.addRow("Linear coefficient", conversion_function_coefficient_spinbox)
        conversion_function_group_box_layout.addRow("Offset", conversion_function_offset_spinbox)
        conversion_function_group_box.setLayout(conversion_function_group_box_layout)

        w.home_search_config_group_box = home_search_config_group_box
        w.conversion_function_group_box = conversion_function_group_box

        w.layout().addWidget(home_search_config_group_box)
        w.layout().addWidget(conversion_function_group_box)
        w.layout().addStretch(100)

        return w

    def update_settings_from_widget(self, settings_widget: QWidget):
        super().update_settings_from_widget(settings_widget)

        self.worker.device.home_search_initial_speed = settings_widget.home_search_config_group_box.initial_approach_speed_spinbox.value()
        self.worker.device.home_search_move_away_steps = settings_widget.home_search_config_group_box.move_away_steps_spinbox.value()
        self.worker.device.home_search_slow_speed = settings_widget.home_search_config_group_box.slow_approach_speed_spinbox.value()
        self.worker.device.conversion_function_coefficient = settings_widget.conversion_function_group_box.conversion_function_coefficient_spinbox.value()
        self.worker.device.conversion_function_offset = settings_widget.conversion_function_group_box.conversion_function_offset_spinbox.value()

    def apply_values_from_settings(self):
        super().apply_values_from_settings()

        self.settings.beginGroup(self.worker.device.internal_id)

        self.settings.beginGroup("home_search")
        self.settings.setValue("initial_speed", self.worker.device.home_search_initial_speed)
        self.settings.setValue("move_away_steps", self.worker.device.home_search_move_away_steps)
        self.settings.setValue("slow_speed", self.worker.device.home_search_slow_speed)
        self.settings.endGroup()  # home search

        self.settings.beginGroup("conversion_function")
        self.settings.setValue("coefficient", self.worker.device.conversion_function_coefficient)
        self.settings.setValue("offset", self.worker.device.conversion_function_offset)
        self.settings.endGroup()  # conversion function

        self.settings.endGroup()

    def _on_current_operation_ready(self, current_op: str):
        self.current_operation_label.setText(current_op)

    def _on_velocity_ready(self, velocity: int):
        self.velocity_label.setText(str(velocity))

    def _on_actual_position_ready(self, actual_pos: int):
        self.actual_position_label.setText(str(actual_pos))
        self.angle_position_label.setText(f"{self.worker.device.get_angle_from_steps(actual_pos):.3f}")

    def _on_home_search_step_ready(self, step: str):
        self.home_search_step_label.setText(step)

    def _on_home_search_status_ready(self, status: str):
        self.home_search_status_label.setText(status)

    def _on_creep_steps_spinbox_editing_finished(self):
        self.worker.add_task(
            lambda: self.worker.device.set_creep_steps(self.creep_steps_spinbox.value())
        )

    def _on_creep_speed_spinbox_editing_finished(self):
        self.worker.add_task(
            lambda: self.worker.device.set_creep_speed(self.creep_speed_spinbox.value())
        )

    def _on_angle_position_spinbox_editing_finished(self):
        self.worker.add_task(
            lambda: self.worker.device.move_absolute(
                self.worker.device.get_steps_from_angle(self.angle_position_spinbox.value())
            )
        )

    def _on_velocity_spinbox_editing_finished(self):
        self.worker.add_task(
            lambda: self.worker.device.set_velocity(self.velocity_spinbox.value())
        )

    def _on_home_search_button_clicked(self):
        self.worker.add_task(
            lambda: self.worker.device.execute_home_search(1000, 500, 50)
        )
