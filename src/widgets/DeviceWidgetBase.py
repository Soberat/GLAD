from typing import Type, Tuple, List, Dict

from PyQt5.QtCore import QSettings, QThread, pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QSpinBox, QFrame, QPushButton

from src.drivers.SerialDeviceBase import SerialDeviceBase
from src.widgets.settings.PlotConfigurationGroupBox import PlotConfigurationGroupBox
from src.widgets.settings.SerialConfigurationGroupBox import SerialConfigurationGroupBox
from src.workers.GenericWorker import GenericWorker


from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt5.QtGui import QColor, QPixmap, QPainter
from PyQt5.QtCore import Qt, QTimer


class StatusIndicator(QWidget):
    POSITIVE_COLOR = QColor("forestgreen")
    NEGATIVE_COLOR_LOW = QColor("darkred")
    NEGATIVE_COLOR_HIGH = QColor("red")

    def __init__(self, initial_status_string="Status: OK"):
        super().__init__()
        self.color = self.POSITIVE_COLOR
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.toggle_negative_color)

        # Label to display the status circle
        self.status_indicator_label = QLabel(self)
        self.status_indicator_label.setAlignment(Qt.AlignCenter)

        # Label to display the status text
        self.status_string_label = QLabel(initial_status_string, self)
        self.status_string_label.setAlignment(Qt.AlignCenter)

        layout = QHBoxLayout()
        layout.addWidget(self.status_indicator_label)
        layout.addWidget(self.status_string_label)

        self.draw_circle()

        self.setLayout(layout)

    def on_positive_status(self):
        self.timer.stop()
        self.color = self.POSITIVE_COLOR
        self.status_string_label.setText("Status: OK")
        self.draw_circle()

    def on_negative_status(self, reason: str):
        self.color = self.NEGATIVE_COLOR_LOW
        self.status_string_label.setText(f"Status: {reason}")
        self.draw_circle()
        self.timer.start(500)

    def toggle_negative_color(self):
        # Toggle between the two shades of red to create a flashing effect
        if self.color == self.NEGATIVE_COLOR_LOW:
            self.color = self.NEGATIVE_COLOR_HIGH
        else:
            self.color = self.NEGATIVE_COLOR_LOW
        self.draw_circle()

    def draw_circle(self):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)  # Transparent background

        painter = QPainter(pixmap)
        painter.setBrush(self.color)
        painter.drawEllipse(0, 0, 15, 15)
        painter.end()

        self.status_indicator_label.setPixmap(pixmap)


class DeviceWidgetBase(QWidget):
    sizeChanged = pyqtSignal()  # Signal to notify that the widget changed size, and any host window should adjust

    def __init__(self, internal_id: str, worker_class: Type[GenericWorker], mock: bool = False):
        super().__init__()
        # Provide settings as a convenience
        self.settings: QSettings = QSettings("Mirosław Wiącek Code", "GLAD")

        # Create the worker for the widget
        self.worker: worker_class = worker_class(internal_id, mock)

        # Setup separate thread for the worker
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

        # All widgets use a vertical layout by default
        self.setLayout(QVBoxLayout())

        # Set up the main_label at the top of the widget, as well as the status indicator
        self.settings.beginGroup(self.worker.device.internal_id)
        main_label_text = self.settings.value("main_label_text", defaultValue="")
        self.settings.endGroup()

        # Set up the QLabel regardless of the is text defined, as it might be changed via settings
        self.main_label = QLabel(main_label_text)
        font = self.main_label.font()
        font.setPixelSize(24)
        font.setBold(True)
        self.main_label.setFont(font)

        self.status_indicator = StatusIndicator()

        self.worker.periodic_function_failed.connect(self.status_indicator.on_negative_status)
        self.worker.periodic_function_successful.connect(self.status_indicator.on_positive_status)

        self.worker.task_failed.connect(self.status_indicator.on_negative_status)
        self.worker.task_successful.connect(self.status_indicator.on_positive_status)

        self.wipe_measurements_button = QPushButton("Wipe measurements")
        self.wipe_measurements_button.clicked.connect(self.clear_measured_values)

        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.main_label)
        temp_layout.addWidget(self.status_indicator)
        temp_layout.addStretch(1)
        temp_layout.addWidget(self.wipe_measurements_button)

        self.layout().addLayout(temp_layout)

        self.main_label.setVisible(str(main_label_text).strip() != "")

    def get_measured_values(self) -> Dict[str, List[Tuple[int, float]]]:
        """

        :return list of a dict of all measurements, where the dict key is the name of the measure, and the value
         is a list of pairs (x, y), where x is the UNIX timestamp, and y is the measured value
        """
        raise NotImplementedError()

    def clear_measured_values(self):
        """
        Erase the contents of the sample buffers
        :return:
        """
        raise NotImplementedError()

    def get_settings_widget(self) -> QWidget:
        """
        Get a widget that will allow the user to configure the widgets parameters (not the device parameters)

        :return: a QWidget that allows the user to configure the device widget and/or device parameters
        """
        widget = QFrame()
        widget.setLayout(QVBoxLayout())

        widget.layout().addWidget(QLabel(f"Internal ID: {self.worker.device.internal_id}"))

        # Widget label editor
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Widget label"))

        widget.widget_label_lineedit = QLineEdit()
        widget.widget_label_lineedit.setText(self.main_label.text())
        temp_layout.addWidget(widget.widget_label_lineedit)

        widget.layout().addLayout(temp_layout)

        # Polling interval editor
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Polling interval"))

        widget.polling_interval_spinbox = QSpinBox()
        widget.polling_interval_spinbox.setRange(1, 1000)
        widget.polling_interval_spinbox.setSuffix(" s")
        widget.polling_interval_spinbox.setValue(int(self.worker.current_interval / 1000))
        temp_layout.addWidget(widget.polling_interval_spinbox)

        widget.layout().addLayout(temp_layout)

        # Add serial settings if the widget device has a "serial" variable defined
        if hasattr(self.worker.device, "serial"):
            widget.serial_configuration_group_box = SerialConfigurationGroupBox(self.worker.device.internal_id)
            widget.layout().addWidget(widget.serial_configuration_group_box)

        # Add pyqtgraph plot configuration if the widget has "plot_widget" defined
        if hasattr(self, "plot_widget"):
            widget.plot_configuration_widget = self.plot_widget.get_settings_widget()
            widget.layout().addWidget(widget.plot_configuration_widget)

        if hasattr(self, "profile_editor"):
            # Editor plot configuration
            widget.editor_plot_configuration_group_box = PlotConfigurationGroupBox(
                initial_color_picker_color=QColor(self.profile_editor.profile_plot.plot_color),
                initial_line_width=self.profile_editor.profile_plot.plot_line_width,
                initial_symbol_size=self.profile_editor.profile_plot.symbol_size,
                group_title="Editor plot settings"
            )
            widget.layout().addWidget(widget.editor_plot_configuration_group_box)

            if not hasattr(self.profile_editor, "interpolation_disabled"):
                widget.interpolated_editor_plot_configuration_group_box = PlotConfigurationGroupBox(
                    initial_color_picker_color=QColor(self.profile_editor.profile_plot.interpolated_plot_color),
                    initial_line_width=self.profile_editor.profile_plot.interpolated_plot_line_width,
                    initial_symbol_size=self.profile_editor.profile_plot.interpolated_symbol_size,
                    group_title="Editor interpolated plot settings"
                )
                widget.layout().addWidget(widget.interpolated_editor_plot_configuration_group_box)

        # Add a stretch, which can be overwritten with a higher value by sub-implementations
        widget.layout().addStretch(1)

        return widget

    def update_settings_from_widget(self, settings_widget: QWidget):
        """
        Given a settings widget generated by self.get_settings_widget(),
        update the device settings based on the widget values.

        :param settings_widget: settings widget generated by self.get_settings_widget()
        :return: None
        """
        widget_label = settings_widget.widget_label_lineedit.text()
        interval_ms = settings_widget.polling_interval_spinbox.value() * 1000

        self.settings.beginGroup(self.worker.device.internal_id)

        # Update settings with widget label
        self.settings.setValue("main_label_text", widget_label)

        # Update settings with worker interval
        self.settings.setValue("worker/poll_interval_ms", interval_ms)

        # Update settings with serial parameters
        if isinstance(self.worker.device, SerialDeviceBase) and hasattr(settings_widget,
                                                                        "serial_configuration_group_box"):
            serial_parameters = settings_widget.serial_configuration_group_box.get_parameters_as_dict()
            self.settings.beginGroup("serial")
            for key, value in serial_parameters.items():
                self.settings.setValue(key, value)
            self.settings.endGroup()  # serial group

        # Update settings with plot_widget parameters
        if hasattr(self, "plot_widget") and hasattr(settings_widget, "plot_configuration_widget"):
            plot_parameters = settings_widget.plot_configuration_widget.plot_configuration_group_box.get_parameters_as_dict()
            profile_plot_parameters = {}
            if hasattr(settings_widget.plot_configuration_widget, "profile_plot_configuration_group_box"):
                profile_plot_parameters = settings_widget.plot_configuration_widget.profile_plot_configuration_group_box.get_parameters_as_dict()
            self.plot_widget.apply_values_from_config(plot_parameters, profile_plot_parameters)

        self.settings.endGroup()  # internal id

    def apply_values_from_settings(self):
        """
        Apply the values from the device settings to the device widget and/or device.

        :return: None
        """
        # Apply main label text and visibility
        self.settings.beginGroup(self.worker.device.internal_id)

        widget_label = self.settings.value("main_label_text", "")
        self.main_label.setText(widget_label)
        self.main_label.setVisible(str(widget_label).strip() != "")

        # Apply worker interval
        interval_ms = self.settings.value("worker/poll_interval_ms", type=int)
        if self.worker.current_interval != interval_ms:
            self.worker.set_interval(interval_ms)

        # Apply serial settings
        if hasattr(self.worker.device, "serial"):
            # Close the connection, forcing renewal on next poll
            self.worker.close_connection()

        # Apply plot_widget settings
        if hasattr(self, "plot_widget"):
            self.plot_widget.update_settings()

        # Update the window title with (possibly) new ID
        self.setWindowTitle(self.worker.device.device_id())

        self.settings.endGroup()  # internal id

    def erase_settings(self):
        self.settings.remove(self.worker.device.internal_id)

    def __str__(self):
        return self.worker.device.device_id()
