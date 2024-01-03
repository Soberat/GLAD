import csv
import logging
import os
from types import NoneType
from typing import Union, List, Tuple, Dict

import matplotlib.pyplot as plt
import numpy as np

from PyQt5.QtWidgets import QVBoxLayout, QWidget, QPushButton, QDoubleSpinBox, QFileDialog, \
    QLabel, QHBoxLayout, QLayout, QScrollArea, QTimeEdit, QCheckBox, QSpinBox, QStyle
from matplotlib import patches
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtCore import Qt, QTime, QSettings
from matplotlib.lines import Line2D


class ProfilePlot:
    def __init__(self, internal_id: str, ax, lower_bound: float, upper_bound: float, y_label: str):
        self.lower_y_bound = lower_bound
        self.upper_y_bound = upper_bound

        self.ax = ax

        settings = QSettings("Mirosław Wiącek Code", "GLAD")
        settings.beginGroup(internal_id)
        settings.beginGroup("editor_plot")

        self.plot_color = settings.value("pen_color", defaultValue="dodgerblue")
        self.symbol_size = int(settings.value("symbol_size", defaultValue=25))
        self.plot_line_width = float(settings.value("pen_width", defaultValue=2))

        settings.endGroup()  # editor plot group

        settings.beginGroup("editor_interpolated_plot")

        self.interpolated_plot_color = settings.value("pen_color", defaultValue="orangered")
        self.interpolated_symbol_size = int(settings.value("symbol_size", defaultValue=25))
        self.interpolated_plot_line_width = float(settings.value("pen_width", defaultValue=2))

        settings.endGroup()  # editor interpolated plot group

        self.profile_scatter = ax.scatter([], [], c=self.plot_color, s=self.symbol_size)
        self.profile_plot: list[Line2D] = ax.plot([], [], c=self.plot_color)

        self.interpolated_profile_scatter = ax.scatter(
            [],
            [],
            c=self.interpolated_plot_color,
            s=self.interpolated_symbol_size
        )
        self.interpolated_profile_scatter.set_visible(False)
        self.interpolated_profile_plot: list[Line2D] = ax.plot([], [], c=self.interpolated_plot_color)
        self.interpolated_profile_plot[0].set_visible(False)

        # A gray overlay that will be active when the widget will be set to disabled
        self.locked_overlay = None

        # Dynamic scaling of the Y axis
        range_diff = self.upper_y_bound - self.lower_y_bound
        padding = range_diff * 0.1
        self.ax.set_ylim((self.lower_y_bound - padding, self.upper_y_bound + padding))

        self.ax.set_xlabel("Time [minutes] ")
        self.ax.set_ylabel(y_label)

        self.ax.grid(alpha=0.2)

        self.text_annotations = []  # Store text annotations for each point

        # Draw the horizontal line at LOWER_BOUND
        self.ax.axhline(self.lower_y_bound, color="r", linestyle="--")
        # Draw the horizontal line at UPPER_BOUND
        self.ax.axhline(self.upper_y_bound, color="r", linestyle="--")

        settings.endGroup()  # internal ID group

    @staticmethod
    def float_to_mm_ss(value: float):
        """
        Convert the time value in minutes to mm:ss format
        :param value:
        :return:
        """
        minutes = int(value)
        seconds = round((value - minutes) * 60)

        # Adjust if seconds is nearly 60 (e.g. 1.9999 minutes)
        if seconds == 60:
            minutes += 1
            seconds = 0

        if seconds == 0:
            return f"{minutes}m"

        return f"{minutes}m {seconds}s"

    def update_colors(self, profile_color: str, interpolated_profile_color: str):
        # Change color of profile scatter and plot
        self.profile_scatter.set_facecolor(profile_color)
        self.profile_plot[0].set_color(profile_color)
        self.plot_color = profile_color

        # Change color of interpolated profile scatter and plot
        self.interpolated_profile_scatter.set_facecolor(interpolated_profile_color)
        self.interpolated_profile_plot[0].set_color(interpolated_profile_color)
        self.interpolated_plot_color = interpolated_profile_color

    def update_text_annotations(self):
        plot_points = self.profile_scatter.get_offsets()
        for i, (x, y) in list(enumerate(zip(plot_points[:, 0], plot_points[:, 1]))):
            annotation = f"{self.float_to_mm_ss(x)} {y:.2f}  "
            if len(self.text_annotations) <= i:
                self.text_annotations.append(self.ax.text(x, y, annotation, ha="right", va="bottom"))
            else:
                self.text_annotations[i].set_position((x, y))
                self.text_annotations[i].set_text(annotation)

    def update_line_plot(self):
        """
        Create a line plot based on the scatter plot points

        :return: nothing
        """

        x = self.profile_scatter.get_offsets()[:, 0]
        y = self.profile_scatter.get_offsets()[:, 1]

        self.profile_plot[0].set_xdata(x)
        self.profile_plot[0].set_ydata(y)
        self.ax.relim()
        self.ax.autoscale_view()
        self.profile_plot[0].figure.canvas.draw()

    def lock_plot(self):
        """
        Lock the plot, hide the scatter plot, and add a gray overlay.
        """
        if isinstance(self.locked_overlay, patches.Rectangle):
            return

        # Hide the scatter plot
        self.profile_scatter.set_visible(False)

        # Add a gray overlay on the entire plot including axes
        x_lim = self.ax.get_xlim()
        y_lim = self.ax.get_ylim()

        self.locked_overlay = patches.Rectangle(
            (x_lim[0], y_lim[0]),
            x_lim[1] - x_lim[0],
            y_lim[1] - y_lim[0],
            color="gray",
            alpha=0.2, zorder=10
        )
        self.ax.add_patch(self.locked_overlay)

        self.profile_scatter.figure.canvas.draw()

    def unlock_plot(self):
        """
        Unlock the plot, show the scatter plot, and remove the gray overlay.
        """
        # Show the scatter plot
        self.profile_scatter.set_visible(True)

        # Remove the gray overlay
        if isinstance(self.locked_overlay, patches.Rectangle):
            self.locked_overlay.remove()
            self.locked_overlay = None

        self.profile_scatter.figure.canvas.draw()


class ProfileEditor(QWidget):
    def __init__(
            self,
            internal_id: str,
            lower_y_bound: float,
            upper_y_bound: float,
            plot_y_label: str,
            y_spinbox_suffix: str,
            parent=None
    ):
        super().__init__(parent)

        self.lower_y_bound: float = lower_y_bound
        self.upper_y_bound: float = upper_y_bound

        self.y_spinbox_suffix = y_spinbox_suffix

        self.interpolated_x_values: List[float] = []
        self.interpolated_y_values: List[float] = []

        self.figure, self.ax = plt.subplots()
        self.figure.set_facecolor("#f0f0f0")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(200)
        self.canvas.setMaximumHeight(500)
        self.add_point_button = QPushButton("+", self)
        self.add_point_button.setToolTip("Add new point")
        self.add_point_button.setFixedSize(40, 110)
        self.interpolate_checkbox = QCheckBox("Interpolate", self)

        self.interpolate_spinbox = QSpinBox(self)
        self.interpolate_spinbox.setMaximum(99999)
        self.interpolate_spinbox.setEnabled(self.interpolate_checkbox.isChecked())

        self.save_to_csv_button = QPushButton("Save to CSV", self)
        self.import_from_csv_button = QPushButton("Import from CSV", self)

        self.x_spin_boxes: List[QTimeEdit] = []
        self.y_inputs: List[QDoubleSpinBox] = []

        self.profile_plot = ProfilePlot(
            internal_id,
            self.ax,
            self.lower_y_bound,
            self.upper_y_bound,
            plot_y_label
        )

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        self.pairs_layout = QHBoxLayout()  # This layout will contain all pairs of spinboxes.

        # Add the stretch at the very beginning, and then we'll insert other layouts before it.
        self.pairs_layout.addStretch(1)

        # Sample data for initializing spinboxes
        x_data = [QTime(0, 1) for _ in range(5)]
        y_data = [10, 20, 15, 25, 30]

        # Add initial spin boxes with sample data
        for i in range(len(x_data)):
            self._add_input_pair(x_data[i], y_data[i])

        # Create the scroll area and a widget for it
        scroll = QScrollArea(self)
        # Allows the content to resize within the scroll area, otherwise the size would be constant when adding points
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(170)

        # Use a widget to put the pairs_layout inside, so we can set it in the scroll area
        scroll_widget = QWidget()
        scroll_widget.setLayout(QHBoxLayout())
        scroll_widget.layout().addWidget(self.add_point_button)
        scroll_widget.layout().addLayout(self.pairs_layout)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        inner_layout = QHBoxLayout()
        inner_layout.addWidget(self.interpolate_checkbox)
        inner_layout.addWidget(self.interpolate_spinbox)
        inner_layout.addStretch(1)

        layout.addLayout(inner_layout)

        inner_layout = QHBoxLayout()
        inner_layout.addWidget(self.save_to_csv_button)
        inner_layout.addWidget(self.import_from_csv_button)
        layout.addLayout(inner_layout)

        temp_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(self.style().standardIcon(QStyle.SP_MessageBoxInformation).pixmap(16, 16))
        info_label = QLabel("Editor assumes instantaneous changes, which should be accounted for by the operator")
        temp_layout.addWidget(icon_label)
        temp_layout.addWidget(info_label)
        temp_layout.addStretch(1)

        layout.addLayout(temp_layout)

        self.setLayout(layout)

        self.add_point_button.clicked.connect(lambda _: self._add_input_pair())

        self.interpolate_spinbox.valueChanged.connect(self._on_interpolation_value_changed)
        self.interpolate_checkbox.stateChanged.connect(self._on_interpolation_state_changed)

        self.import_from_csv_button.clicked.connect(self.import_from_csv)
        self.save_to_csv_button.clicked.connect(self.save_to_csv)

        # Plot the data on the canvas
        self._update_plot()
        self._update_interpolated_values()
        self._update_interpolated_plot()

    def sizeHint(self):
        # This will always return the size the widget had when it was last shown
        return self.size()

    def setEnabled(self, a0: bool) -> None:
        # Also paint a gray overlay over the plot, to indicate that editing is disabled
        super().setEnabled(a0)
        if a0:
            self.profile_plot.unlock_plot()
        else:
            self.profile_plot.lock_plot()

    def update_parameters(self, editor_params: Dict, interpolated_editor_params: Dict):
        """
        Wrapper that will update the plot parameters and will force a figure redraw

        :param editor_params: a Dict with pen_color: QColor, pen_width: float and symbol_size: float
        :param interpolated_editor_params: same as above, but applied to the interpolated plot

        :return: None
        """
        # Update colors
        self.profile_plot.update_colors(
            editor_params["pen_color"].name(),
            interpolated_editor_params["pen_color"].name()
        )

        # Update symbol sizes
        self.profile_plot.profile_scatter.set_sizes([editor_params["symbol_size"]])
        self.profile_plot.symbol_size = editor_params["symbol_size"]

        self.profile_plot.interpolated_profile_scatter.set_sizes([interpolated_editor_params["symbol_size"]])
        self.profile_plot.interpolated_symbol_size = interpolated_editor_params["symbol_size"]

        # Update line widths
        self.profile_plot.profile_plot[0].set_linewidth(editor_params["pen_width"])
        self.profile_plot.plot_line_width = editor_params["pen_width"]

        self.profile_plot.interpolated_profile_plot[0].set_linewidth(interpolated_editor_params["pen_width"])
        self.profile_plot.interpolated_plot_line_width = interpolated_editor_params["pen_width"]

        self.figure.canvas.draw()

    def _on_spinbox_value_changed(self):
        if self.interpolate_checkbox.isChecked():
            self._update_interpolated_values()
            self._update_interpolated_plot()
        self._update_plot()

    def _add_input_pair(
            self,
            default_x: Union[QTime, NoneType] = QTime(0, 1),
            default_y: Union[float, NoneType] = None
    ):
        index = len(self.x_spin_boxes) + 1

        pair_layout = QVBoxLayout()
        pair_layout.pair_index = index

        x_label = QLabel(f"X{index}:")
        y_label = QLabel(f"Y{index}:")
        x_label.setFixedWidth(25)
        y_label.setFixedWidth(25)

        x_spinbox = QTimeEdit(self)
        x_spinbox.setDisplayFormat("HH:mm:ss")
        x_spinbox.setMinimumTime(QTime(0, 0, 1))

        y_spinbox = QDoubleSpinBox(self)
        y_spinbox.setSuffix(self.y_spinbox_suffix)
        x_spinbox.setMinimumWidth(80)
        y_spinbox.setMinimumWidth(80)

        x_spinbox.setTime(default_x)

        # Get the default y value, which will be self.lower_y_bound for the first spinbox,
        # and the previous spinbox value for other cases
        if default_y is None:
            default_y = self.lower_y_bound if not self.y_inputs else self.y_inputs[-1].value()
        y_spinbox.setValue(default_y)

        # Setting the constraints for the y_spinbox
        y_spinbox.setRange(self.lower_y_bound, self.upper_y_bound)

        self.x_spin_boxes.append(x_spinbox)
        self.y_inputs.append(y_spinbox)

        # Add the remove button to each pair
        remove_button = QPushButton("-")
        remove_button.setFixedWidth(40)
        remove_button.setToolTip("Remove point")
        remove_button.clicked.connect(lambda: self._on_remove_button_clicked(pair_layout))

        pair_layout.addWidget(QLabel(f"X{index} (hh:mm:ss)"))
        pair_layout.addWidget(x_spinbox)
        pair_layout.addWidget(QLabel(f"Y{index}"))
        pair_layout.addWidget(y_spinbox)
        if index != 1:
            # We don't want the first point to be removable
            pair_layout.addWidget(remove_button)
        pair_layout.addStretch(1)

        # Insert the new QVBoxLayout just before the stretch
        self.pairs_layout.insertLayout(self.pairs_layout.count() - 1, pair_layout)

        x_spinbox.timeChanged.connect(self._on_spinbox_value_changed)
        y_spinbox.valueChanged.connect(self._on_spinbox_value_changed)

        # Set a new minimum for the interpolation spinbox
        self.interpolate_spinbox.setMinimum(len(self.y_inputs) + 1)
        self._update_interpolated_values()
        self._update_interpolated_plot()

        # Check if the plot has been created, then update it with the new data point
        if hasattr(self, "profile_plot"):
            self._update_plot()

    def _remove_all_spinbox_pairs(self):
        # Remove in reverse order to prevent issues with changing indices
        for i in reversed(range(len(self.pairs_layout))):
            item = self.pairs_layout.itemAt(i)
            if isinstance(item, QVBoxLayout) and hasattr(item, "pair_index"):
                self._on_remove_button_clicked(item)

    @staticmethod
    def _iter_layout(layout: QLayout):
        """
        Yield actual QLayouts from a given layout, skipping any QSpacerItems or other non-layout items.

        :param layout: QLayout to iterate over
        :return a generator that yields QLayouts within the given layout
        """
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if isinstance(item, QLayout):
                yield item

    def _on_interpolation_state_changed(self, new_state: Qt.CheckState):
        interpolation_enabled = new_state == Qt.Checked
        self.interpolate_spinbox.setEnabled(interpolation_enabled)
        self.profile_plot.interpolated_profile_scatter.set_visible(interpolation_enabled)
        self.profile_plot.interpolated_profile_plot[0].set_visible(interpolation_enabled)

        # Redraw the canvas, has to be done regardless of whether interpolation is on or off
        self.profile_plot.interpolated_profile_scatter.figure.canvas.draw()
        self.profile_plot.interpolated_profile_plot[0].figure.canvas.draw()

    def _on_interpolation_value_changed(self):
        self._update_interpolated_values()
        self._update_interpolated_plot()

    def _update_interpolated_values(self):
        if not self.x_spin_boxes or not self.y_inputs:
            return

        # Get the current data that needs to be interpolated
        x_data = [sb.time() for sb in self.x_spin_boxes]
        # Convert QTimes into milliseconds for QTimers
        x_data = [t.hour() * 60 + t.minute() + t.second() / 60 for t in x_data]
        y_data = [sb.value() for sb in self.y_inputs]

        absolute_x = [sum(x_data[:i]) for i in range(0, len(x_data))]

        self.interpolated_x_values = np.linspace(0, absolute_x[-1], self.interpolate_spinbox.value() + 1)
        self.interpolated_y_values = np.interp(self.interpolated_x_values, absolute_x, y_data)

    def save_to_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save profile to CSV", "./profile.csv",
                                                  "CSV Files (*.csv);;All Files (*)")
        if not filename:
            return

        # Flag to remove file after closing if writing failed
        remove_file_flag = False
        exception = None
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            try:
                writer = csv.writer(csvfile)
                writer.writerow(["X (hh:mm:ss)", f"Y ({self.y_spinbox_suffix})"])
                writer.writerows([(self.x_spin_boxes[i].time().toString(), self.y_inputs[i].value()) for i in
                                  range(len(self.x_spin_boxes))])
            except Exception as e:
                logging.error(f"Error while saving to CSV: {e}")
                remove_file_flag = True
                exception = e

        if remove_file_flag and exception:
            # Remove the file, and reraise the exception to inform the user of the error
            os.remove(filename)
            raise ValueError(f"Error while saving to CSV: {exception}")

    def import_from_csv(self):
        filePath, _ = QFileDialog.getOpenFileName(self, "Open profile CSV", "", "CSV Files (*.csv);;All Files (*)")

        if not filePath:
            return

        data = np.genfromtxt(filePath, delimiter=",", skip_header=1, encoding="utf-8", dtype=None)
        x_data = [row[0] for row in data]
        y_data = [row[1] for row in data]

        if len(x_data) != len(y_data) or len(x_data) == 0 or len(y_data) == 0:
            raise ValueError("Input profile is empty or amount of values does not match")

        # Cap off values out of bounds
        y_data = np.clip(y_data, self.lower_y_bound, self.upper_y_bound)

        # Remove any existing data points
        self._remove_all_spinbox_pairs()

        # Add the new data points from the CSV
        for x, y in zip(x_data, y_data):
            # Convert the string time into a QTime instance
            hh, mm, ss = (int(v) for v in x.split(sep=":"))
            x_qtime = QTime(hh, mm, ss)
            self._add_input_pair(x_qtime, y)

        # Redraw the plot
        self._update_plot()
        self._update_interpolated_values()
        self._update_interpolated_plot()

    def _update_plot(self):
        # Get the user input from spinboxes
        x_values = [spinbox.time() for spinbox in self.x_spin_boxes]
        y_values = [spinbox.value() for spinbox in self.y_inputs]

        # Every spinbox pair is represented by two points on the plot - the start and end
        absolute_x_values = []
        new_y_values = []

        for idx in range(2 * len(x_values)):
            if (idx % 2) == 0:
                # First point of the current setpoint/hold time
                absolute_x_values.append(0 if not absolute_x_values else absolute_x_values[-1])
                new_y_values.append(y_values[idx // 2])
            else:
                # Second point
                time = x_values[idx // 2]
                absolute_x_values.append(
                    absolute_x_values[-1] + time.hour() * 60 + time.minute() + time.second() / 60.0
                )
                new_y_values.append(new_y_values[-1])

        # Update the profile scatter plot data
        if absolute_x_values and new_y_values:
            self.profile_plot.profile_scatter.set_offsets(list(zip(absolute_x_values, new_y_values)))

        # Update the line plot and text annotations
        self.profile_plot.update_line_plot()
        self.profile_plot.update_text_annotations()

        # Redraw the canvas
        self.profile_plot.profile_scatter.figure.canvas.draw()

    def _update_interpolated_plot(self):
        # Get the user input from spinboxes
        x_values = self.interpolated_x_values
        y_values = self.interpolated_y_values

        # Every spinbox pair is represented by two points on the plot - the start and end
        absolute_x_values = []
        new_y_values = []

        for idx in range(2 * len(x_values)):
            if (idx % 2) == 0:
                # First point of the current setpoint/hold time
                absolute_x_values.append(0 if not absolute_x_values else absolute_x_values[-1])
                new_y_values.append(y_values[idx // 2])
            else:
                # Second point
                absolute_x_values.append(x_values[idx // 2])
                new_y_values.append(new_y_values[-1])

        # Update the profile scatter plot data
        self.profile_plot.interpolated_profile_scatter.set_offsets(list(zip(absolute_x_values, new_y_values)))

        # Redraw the canvas
        self.profile_plot.interpolated_profile_scatter.figure.canvas.draw()

        self.profile_plot.interpolated_profile_scatter.set_offsets(list(zip(absolute_x_values, new_y_values)))
        self.profile_plot.interpolated_profile_plot[0].set_xdata(absolute_x_values)
        self.profile_plot.interpolated_profile_plot[0].set_ydata(new_y_values)
        self.profile_plot.interpolated_profile_plot[0].figure.canvas.draw()

    def _on_remove_button_clicked(self, calling_layout: QVBoxLayout):
        while calling_layout.count():
            widget = calling_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        self.pairs_layout.removeItem(calling_layout)

        # Remove data from lists and update the plot
        self.x_spin_boxes.pop(calling_layout.pair_index - 1).deleteLater()
        self.y_inputs.pop(calling_layout.pair_index - 1).deleteLater()

        # Remove the text annotation for the deleted point
        self.profile_plot.text_annotations[calling_layout.pair_index - 1].set_visible(False)
        del self.profile_plot.text_annotations[calling_layout.pair_index - 1]

        # Renumbering the labels for the spinbox pairs after the removed one
        for idx, pair_layout in enumerate(self._iter_layout(self.pairs_layout)):
            if idx < calling_layout.pair_index - 1:  # Skip pairs before the removed one
                continue
            pair_layout.pair_index = idx + 1
            label_x = pair_layout.itemAt(0).widget()
            label_y = pair_layout.itemAt(2).widget()
            if label_x and label_y and isinstance(label_x, QLabel) and isinstance(label_y, QLabel):
                label_x.setText(f"X{idx + 1} (hh:mm:ss)")
                label_y.setText(f"Y{idx + 1}")

        self._update_plot()
        self._update_interpolated_values()
        self._update_interpolated_plot()

    @staticmethod
    def _qtimeedit_time_to_minutes(qt: QTime) -> float:
        return qt.hour() * 60 + qt.minute() + qt.second() / 60

    def get_profile_data(self) -> Tuple[List[float], List[float]]:
        if self.interpolate_checkbox.isChecked():
            # Interpolated X values are not relative to one another, we need to convert them
            relative_x_values = [0]
            relative_x_values.extend(self.interpolated_x_values)
            relative_x_values = [relative_x_values[i + 1] - relative_x_values[i] for i in
                                 range(len(relative_x_values) - 1)]

            return relative_x_values, self.interpolated_y_values
        else:
            return (
                [self._qtimeedit_time_to_minutes(sb.time()) for sb in self.x_spin_boxes],
                [sb.value() for sb in self.y_inputs]
            )

    def get_profile_data_on_plot(self) -> List[Tuple[float, float]]:
        if self.interpolate_checkbox.isChecked():
            return self.profile_plot.interpolated_profile_scatter.get_offsets()
        else:
            return self.profile_plot.profile_scatter.get_offsets()
