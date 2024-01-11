import re
import time
from enum import Enum

import serial
from PyQt5.QtCore import QObject, pyqtSignal

from src.drivers.SerialDeviceBase import SerialDeviceBase


class StepperControllerAxis(SerialDeviceBase, QObject):
    DEFAULTS = {
        "baudrate": 19200,
        "parity": serial.PARITY_EVEN,
        "bytesize": serial.SEVENBITS,
        "stopbits": serial.STOPBITS_ONE,
        "timeout": 3
    }

    homeSearchStepReady = pyqtSignal(str)
    homeSearchStatusReady = pyqtSignal(str)
    currentOperationReady = pyqtSignal(str)
    velocityReady = pyqtSignal(int)
    actualPositionReady = pyqtSignal(int)

    class StepperOperatingMode(Enum):
        SERVO_MODE = 1
        OPEN_LOOP_STEPPER_MODE = 11
        CHECKING_STEPPER_MODE = 12
        EXTERNAL_LOOP_STEPPER_MODE = 13
        CLOSED_LOOP_STEPPER_MODE = 14

    def __init__(self, internal_id: str):
        SerialDeviceBase.__init__(self, internal_id)
        QObject.__init__(self)

        self.settings.beginGroup(internal_id)

        self.settings.beginGroup("home_search")
        self.home_search_initial_speed = self.settings.value("initial_speed", defaultValue=1000)
        self.home_search_move_away_steps = self.settings.value("move_away_steps", defaultValue=5000)
        self.home_search_slow_speed = self.settings.value("slow_speed", defaultValue=50)
        self.settings.endGroup()  # home search

        self.settings.beginGroup("conversion_function")
        self.conversion_function_coefficient = float(self.settings.value("coefficient", defaultValue=1))
        self.conversion_function_offset = float(self.settings.value("offset", defaultValue=0))
        self.settings.endGroup()  # conversion function

        self.settings.endGroup()  # internal ID

        self.axis_number = 1

    def connect(self):
        """
        Connects to the device by closing the current connection (if open) and then reopening it.
        """
        if self.serial and self.serial.is_open:  # If connection exists and is open
            self.logger.info(f"Closing existing connection for {self.device_id()}")
            self.serial.close()

        self.serial = self.create_serial_from_settings()

        if self.serial and self.serial.port is None:
            raise ValueError(f"No port specified for {self.device_id()}")

        self.logger.info(f"Successfully connected to {self.device_id()} on port {self.serial.port}")

    def write(self, command, value=None):
        if value:
            self.serial.write(f"{self.axis_number}{command}{value}\r".encode())
            self.logger.debug(f"Write command '{self.axis_number}{command}{value}'")
        else:
            self.serial.write(f"{self.axis_number}{command}\r".encode())
            self.logger.debug(f"Write command '{self.axis_number}{command}'")

        readback = self.serial.read_until().decode()
        self.logger.debug(f"Readback: {readback}")
        return "OK" in readback.upper()

    def read(self, command):
        if self.serial.in_waiting:
            self.logger.warning(f"Bytes in waiting before command: {self.serial.read(self.serial.in_waiting)}")

        self.logger.debug(f"Read command: {self.axis_number}{command}")
        self.serial.write(f"{self.axis_number}{command}\r".encode("utf-8"))
        readback = self.serial.read_until()
        self.logger.debug(f"Readback: {readback}")
        return readback.decode()

    def get_steps_from_angle(self, angle: float) -> int:
        return int(angle * self.conversion_function_coefficient + self.conversion_function_offset)

    def get_angle_from_steps(self, position: int) -> float:
        return float((position - self.conversion_function_offset) / self.conversion_function_coefficient)

    def execute_home_search(self, timeout: int = 600) -> bool:
        """
        Try to home position as precisely as possible, by
         Step 1. Moving fast towards the hard limit at init_speed
         Step 2. Moving shift_steps away from the hard limit
         Step 3. Slowly moving towards the hard limit again using creep_speed

        :param init_speed: initial speed moving towards the hard limit, in steps/second
        :param shift_steps: Amount of steps until the target when the controller uses creep speed instead of slew speed
        :param creep_speed: The speed at which the controller approaches the datum
         when there's less than shift_steps remaining, in steps/second
        :param timeout: amount of seconds until the process raises a TimeoutError

        :raises TimeoutError if the process did not complete within the timeout period

        :return: bool whether the process was successful
        """
        init_speed = self.settings.value(f"{self.internal_id}/home_search/initial_speed")
        shift_steps = self.settings.value(f"{self.internal_id}/home_search/move_away_steps")
        creep_speed = self.settings.value(f"{self.internal_id}/home_search/slow_speed")

        start_time = time.time()

        self.logger.info("Step 1: fast home to datum")
        self.homeSearchStepReady.emit("Step 1: fast home to datum")
        self.set_velocity(init_speed)
        self.go_home_to_datum(False)
        current_operation = self.display_current_operation()

        self.logger.debug(f"Current operation: {current_operation}".encode())
        self.homeSearchStatusReady.emit(current_operation)

        while "home" in current_operation.lower() or "datum" in current_operation.lower():
            if time.time() - start_time >= timeout:
                raise TimeoutError("Home search process timed out")
            time.sleep(5)

            current_operation = self.display_current_operation()
            self.currentOperationReady.emit(current_operation)

            current_velocity = self.output_velocity()
            self.velocityReady.emit(current_velocity)

            current_position = self.output_command_position()
            self.actualPositionReady.emit(current_position)

            self.homeSearchStatusReady.emit(current_operation)

        # Step 2
        self.logger.info("Step 2: moving away from the hard limit")
        self.homeSearchStepReady.emit("Step 2: moving away from the hard limit")
        self.set_creep_steps(shift_steps)
        self.set_creep_speed(creep_speed)
        self.move_relative(shift_steps)

        current_operation = self.display_current_operation()
        self.logger.debug(f"Current operation: {current_operation}".encode())
        self.homeSearchStatusReady.emit(current_operation)

        while "idle" not in current_operation.lower():
            if time.time() - start_time >= timeout:
                raise TimeoutError("Home search process timed out")
            time.sleep(5)

            current_operation = self.display_current_operation()
            self.currentOperationReady.emit(current_operation)

            current_velocity = self.output_velocity()
            self.velocityReady.emit(current_velocity)

            current_position = self.output_command_position()
            self.actualPositionReady.emit(current_position)

            self.homeSearchStatusReady.emit(current_operation)

        # Step 3
        self.logger.info("Step 3: slow home to datum")
        self.homeSearchStepReady.emit("Step 3: slow home to datum")
        self.go_home_to_datum(False)
        current_operation = self.display_current_operation()

        self.logger.debug(f"Current operation: {current_operation}".encode())
        self.homeSearchStatusReady.emit(current_operation)

        while "home" in current_operation.lower() or "datum" in current_operation.lower():
            if time.time() - start_time >= timeout:
                raise TimeoutError("Home search process timed out")
            time.sleep(5)

            current_operation = self.display_current_operation()
            self.currentOperationReady.emit(current_operation)

            current_velocity = self.output_velocity()
            self.velocityReady.emit(current_velocity)

            current_position = self.output_command_position()
            self.actualPositionReady.emit(current_position)

            self.homeSearchStatusReady.emit(current_operation)

        self.logger.info("Home search finished")
        self.homeSearchStepReady.emit("Finished")
        return True

    """
    Getting started commands
    """

    def help_pages(self):
        return self.read("HE")

    def display_next_page(self):
        return self.read("HN")

    def display_previous_page(self):
        return self.read("HP")

    def initialize(self):
        return self.read("IN")

    def query_speeds(self):
        return self.read("QS")

    def query_all(self):
        return self.read("QA")

    """
    Abort, Stop & Reset commands
    """

    def hard_stop(self):
        return self.read("\u0003")

    def soft_stop(self):
        return self.read("ST")

    def set_abort_mode(self, a: bool, b: bool, c: bool, d: bool, e: bool, f: bool, g: bool, h: bool):
        """
        :param a: 0 – Abort Stop Input disables control loop
                  1 – Abort Stop Input stops all moves only
        :param b: 0 – Abort Stop Input is latched requiring RS command to reset
                  1 – Abort Stop Input is only momentary
        :param c: 0 – Stall Error disables control loop
                  1 – Stall Error is indicated but control loop remains active
        :param d: 0 – Tracking Error disables control loop
                  1 – Tracking Error is indicated but control loop remains active
        :param e: 0 – Timeout Error disables control loop
                  1 – Timeout Error is indicated but control loop remains active
        :param f: Reserved for future use
        :param g: Reserved for future use
        :param h: 0 – Enable output switched OFF during a disabled control loop
                  1 – Enable output left ON during a control loop abort
        """
        return self.write(
            "AM",
            f"{int(a)}{int(b)}{int(c)}{int(d)}{int(e)}{int(f)}{int(g)}{int(h)}"
        )

    def command_abort(self):
        return self.read("AB")

    def reset(self):
        return self.read("RS")

    def query_modes(self):
        return self.read("QM")

    """
    Information
    """

    def display_current_operation(self):
        return self.read("CO")

    def identify_version(self):
        return self.read("ID")

    def output_command_position(self):
        return int(re.search(r"[0-9]{2}:(Command pos = |)((-|)[0-9]+)", self.read("OC")).group(2))

    def output_actual_position(self):
        return int(re.search(r"[0-9]{2}:(Actual pos = |)((-|)[0-9]+)", self.read("OA")).group(2))

    def output_datum_position(self):
        return self.read("OD")

    def output_velocity(self):
        return int(re.search(r"[0-9]{2}:(Velocity = |)((-|)[0-9]+)", self.read("OV")).group(2))

    def output_status_string(self):
        return self.read("OS")

    def output_following_error(self):
        return self.read("OF")

    def query_positions(self):
        return self.read("QP")

    def query_privilege_level(self):
        return self.read("QL")

    """
    Set Up
    """

    def set_command_mode(self, mode: StepperOperatingMode):
        return self.write("CM", mode.value)

    def set_encoder_ratio(self, numerator: int, denominator: int):
        return self.write("ER", "{}/{}".format(numerator, denominator))

    def set_backoff_steps(self, steps: int):
        # assert -32000 <= steps <= 32000
        return self.write("BO", steps)

    def set_creep_steps(self, steps):
        # assert 0 <= steps <= 2147483647
        return self.write("CR", steps)

    def set_timeout(self, milliseconds):
        # assert 1 <= milliseconds <= 60000
        return self.write("TO", milliseconds)

    def set_settling_time(self, milliseconds):
        # assert 0 <= milliseconds <= 20000
        return self.write("SE", milliseconds)

    def set_settling_window(self, steps):
        # assert 0 <= steps <= 2147483647
        return self.write("WI", steps)

    """
    Fault detection features
    """

    def set_soft_limits(self, enabled: bool):
        return self.write("SL", int(enabled))

    def set_tracking_window(self, steps):
        # assert 0 <= steps <= 2147483647
        return self.write("TR", steps)

    """
    Datuming
    """

    def clear_captured_datum_position(self):
        return self.read("CD")

    def go_home_to_datum(self, positive_direction: bool):
        return self.write("HD", "" if positive_direction else "-1")

    def move_to_datum_position(self):
        return self.read("MD")

    def set_home_position(self, home_position):
        # assert -2147483647 <= home_position <= 2147483647
        return self.write("SH", home_position)

    def set_datum_mode(self, a: int, b: int, c: int, d: int, e: int, f: int, g: int, h: int):
        """
        :param a: 0 – Encoder index input polarity is normal
                  1 – Encoder index input polarity is inverted
        :param b: 0 – Datum point is captured only once (i.e. after HD command)
                  1 – Datum point is captured each time it happens
        :param c: 0 – Datum position is captured but not changed
                  1 – Datum position is set to Home Position (SH) after datum search (HD)
        :param d: 0 – Automatic direction search disabled
                  1 – Automatic direction search enabled
        :param e: 0 – Automatic opposite limit search disabled
                  1 – Automatic opposite limit search enabled
        :param f: Reserved for future use
        :param g: Reserved for future use
        :param h: Reserved for future use
        """
        return self.write(
            "DM",
            f"{int(a)}{int(b)}{int(c)}{int(d)}{int(e)}{int(f)}{int(g)}{int(h)}"
        )

    """
    Position commands
    """

    def set_actual_position(self, position):
        # assert -2147483647 <= position <= 2147483647
        return self.write("AP", position)

    def set_command_position(self, value):
        # assert -2147483647 <= value <= 2147483647
        return self.write("CP", value)

    def difference_actual_position(self, position):
        # assert -2147483647 <= position <= 2147483647
        return self.write("DA", position)

    """
    Speed, acceleration and deceleration
    """

    def constant_velocity_move(self, steps_per_second):
        # assert -1200000 <= steps_per_second <= 1200000
        return self.write("CV", steps_per_second)

    def set_creep_speed(self, steps_per_second):
        # assert 1 <= steps_per_second <= 400000
        return self.write("SC", steps_per_second)

    def set_fast_jog_speed(self, steps_per_second):
        # assert 1 <= steps_per_second <= 200000
        return self.write("SF", steps_per_second)

    def set_slow_jog_speed(self, steps_per_second):
        # assert 1 <= steps_per_second <= 20000
        return self.write("SJ", steps_per_second)

    def set_velocity(self, steps_per_second):
        # assert 1 <= steps_per_second <= 1200000
        return self.write("SV", steps_per_second)

    def set_acceleration(self, acceleration):
        # assert 1 <= acceleration <= 20000000
        return self.write("SA", acceleration)

    def set_deceleration(self, deceleration):
        # assert 1 <= deceleration <= 20000000
        return self.write("SD", deceleration)

    def set_limit_deceleration(self, deceleration):
        # assert 1 <= deceleration <= 20000000
        return self.write("LD", deceleration)

    """
    Moves
    """

    def move_absolute(self, steps):
        # assert -2147483647 <= steps <= 2147483647
        return self.write("MA", steps)

    def move_relative(self, steps):
        # assert -2147483647 <= steps <= 2147483647
        return self.write("MR", steps)

    def set_delay_time(self, milliseconds):
        # assert 1 <= milliseconds <= 2000000
        return self.write("DE", milliseconds)

    """
    Soft limits
    """

    def set_lower_soft_limit(self, position):
        # assert -2147483647 <= position <= 2147483647
        return self.write("LL", position)

    def set_upper_soft_limit(self, position):
        # assert -2147483647 <= position <= 2147483647
        return self.write("UL", position)

    """
    End of move
    """

    def wait_for_end_of_current_move(self):
        return self.read("WE")

    """
    Read & write ports
    """

    def read_port(self):
        return self.read("RP")

    def write_port(self, bit_pattern: str):
        return self.write("WP", bit_pattern)

    def wait_for_input_event(self, bit_pattern: str):
        return self.write("WA", bit_pattern)

    def do_next_command_if_false(self, bit_pattern: str):
        return self.write("IF", bit_pattern)

    def do_next_command_if_true(self, bit_pattern: str):
        return self.write("IT", bit_pattern)

    """
    Jog
    """

    def set_jog_mode(self, a: int, b: int, c: int, d: int, e: int, f: int, g: int, h: int):
        """
        :param a: 0 – Jog switch inputs disabled
                  1 – Jog switch inputs enabled
        :param b: 0 – Joystick input disabled
                  1 – Joystick input enabled
        :param c: 0 – Input encoder jog input disabled
                  1 – Input encoder jog input enabled
        :param d: 0 – Jog Select (channel increment) disabled
                  1 - Jog Select (channel increment) enabled
        :param e: Reserved for future use
        :param f: Reserved for future use
        :param g: Reserved for future use
        :param h: Reserved for future use
        """
        return self.write("JM",
                          "{}{}{}{}{}{}{}{}".format(int(a), int(a), int(b), int(c),
                                                    int(d), int(e), int(f), int(g), int(h)))

    def set_joystick_centre_position(self, position):
        # assert 0 <= position <= 4095
        return self.write("JC", position)

    def set_joystick_range(self, position):
        # assert 100 <= position <= 4095
        return self.write("JS", position)

    def set_joystick_speed(self, steps_per_second):
        # assert 1 <= steps_per_second <= 400000
        return self.write("JS", steps_per_second)

    def set_joystick_threshold(self, value):
        # assert 1 <= value <= 4095
        return self.write("JT", value)

    def query_joystick_settings(self):
        return self.read("QJ")

    """
    Sequences
    """

    def auto_execute_sequence(self, sequence_no: int):
        return self.write("AE", sequence_no)

    def auto_execute_disable(self):
        return self.read("AD")

    def define_sequence(self, sequence_no: int):
        return self.write("DS", sequence_no)

    def end_sequence_definition(self):
        return self.read("ES")

    def list_sequence(self, sequence_no: int):
        return self.write("LS", sequence_no)

    def execute_sequence(self, sequence_no: int):
        return self.write("XS", sequence_no)

    def backup_sequence(self):
        return self.read("BS")

    def undefine_sequence(self, sequence_no: int):
        return self.write("US", sequence_no)

    """
    Help
    """

    def help_with_modes_commands(self):
        return self.read("HM")

    def help_with_status_output_message(self):
        return self.read("HS")

    def help_with_command_modes(self):
        return self.read("HC")

    """
    Privilege level
    """

    def new_pin(self, new_pin: str):
        # assert len(new_pin) == 4 and 0 <= int(new_pin) <= 9999
        return self.write("NP", new_pin)

    def enter_pin(self, pin: str):
        # assert len(pin) == 4 and 0 <= int(pin) <= 9999
        return self.write("PI", pin)

    def set_privilege_level(self, privilege_level: int):
        # assert 0 <= privilege_level <= 9
        return self.write("PL", privilege_level)

    """
    Backup
    """

    def backup_all(self):
        return self.read("BA")

    def backup_sequences(self):
        return self.read("BS")

    def backup_digiloop_parameters(self):
        return self.read("BD")
