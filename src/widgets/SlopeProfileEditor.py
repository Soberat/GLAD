from types import NoneType
from typing import Union, Tuple, List

import numpy as np
from PyQt5.QtCore import QTime, Qt
from PyQt5.QtWidgets import QLabel, QTimeEdit, QDoubleSpinBox, QPushButton, QVBoxLayout,  QFileDialog

from src.widgets.ProfileEditor import ProfileEditor


class SlopeProfileEditor(ProfileEditor):
    """
    Version of ProfileEditor that operates on slopes rather than absolute Y values.
    Removes/disables interpolation, as all implementations rely on on-device ramping.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interpolation_disabled = True

        self.interpolate_spinbox.deleteLater()
        self.interpolate_checkbox.deleteLater()

        self._update_plot()

    def _on_spinbox_value_changed(self):
        self._update_plot()

    def _add_spinbox_pair(
            self,
            default_x: Union[QTime, NoneType] = QTime(0, 1),
            default_y: Union[float, NoneType] = None
    ):
        index = len(self.x_spin_boxes) + 1
        
        pair_layout = QVBoxLayout()
        pair_layout.pair_index = index

        x_label = QLabel(f"X{index}:")
        y_label = QLabel(f"dy/dx{index}:")
        x_label.setFixedWidth(25)
        y_label.setFixedWidth(25)

        x_spinbox = QTimeEdit(self)
        x_spinbox.setDisplayFormat("HH:mm:ss")
        x_spinbox.setMinimumTime(QTime(0, 0, 1))

        y_spinbox = QDoubleSpinBox(self)
        y_spinbox.setRange(-10000, 10000)
        y_spinbox.setSuffix(f" {self.y_spinbox_suffix}/m")
        x_spinbox.setMinimumWidth(80)
        y_spinbox.setMinimumWidth(80)

        x_spinbox.setTime(default_x)

        # Get the default y value, which will be self.LOWER_BOUND for the first spinbox,
        # and the previous spinbox value for other cases
        if default_y is None:
            default_y = self.lower_y_bound if not self.y_spin_boxes else self.y_spin_boxes[-1].value()
        y_spinbox.setValue(default_y)

        self.x_spin_boxes.append(x_spinbox)
        self.y_spin_boxes.append(y_spinbox)

        # Add the remove button to each pair
        remove_button = QPushButton("-")
        remove_button.setFixedWidth(40)
        remove_button.setToolTip("Remove point")
        remove_button.clicked.connect(lambda: self._on_remove_button_clicked(pair_layout))

        pair_layout.addWidget(QLabel(f"X{index} (hh:mm:ss)"))
        pair_layout.addWidget(x_spinbox)
        pair_layout.addWidget(QLabel(f"dY/dX{index}"))
        pair_layout.addWidget(y_spinbox)
        if index != 1:
            # We don't want the first point to be removable
            pair_layout.addWidget(remove_button)
        pair_layout.addStretch(1)

        # Insert the new QVBoxLayout just before the stretch
        self.pairs_layout.insertLayout(self.pairs_layout.count() - 1, pair_layout)

        x_spinbox.timeChanged.connect(self._on_spinbox_value_changed)
        y_spinbox.valueChanged.connect(self._on_spinbox_value_changed)

        # Check if the plot has been created, then update it with the new data point
        if hasattr(self, "profile_plot"):
            self._update_plot()

    def _on_interpolation_state_changed(self, new_state: Qt.CheckState):
        pass

    def _on_interpolation_value_changed(self):
        pass

    def _update_interpolated_values(self):
        if not self.x_spin_boxes or not self.y_spin_boxes:
            return

        # Get the current data that needs to be interpolated
        x_data = [sb.time() for sb in self.x_spin_boxes]
        # Convert QTimes into milliseconds for QTimers
        x_data = [t.hour() * 60 + t.minute() + t.second() / 60 for t in x_data]
        y_data = [sb.value() for sb in self.y_spin_boxes]

        absolute_x = [sum(x_data[:i]) for i in range(0, len(x_data))]

        self.interpolated_x_values = np.linspace(0, absolute_x[-1], self.interpolate_spinbox.value() + 1)
        self.interpolated_y_values = np.interp(self.interpolated_x_values, absolute_x, y_data)

    def import_from_csv(self):
        # Open a file dialog
        filePath, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv);;All Files (*)")

        if not filePath:
            return

        # Read the CSV file
        data = np.genfromtxt(filePath, delimiter=",", skip_header=1, encoding="utf-8", dtype=None)
        x_data = [row[0] for row in data]
        y_data = [row[1] for row in data]

        # Cap off values out of bounds
        y_data = np.clip(y_data, self.lower_y_bound, self.upper_y_bound)

        # Remove any existing data points
        self._remove_all_spinbox_pairs()

        # Add the new data points from the CSV
        for x, y in zip(x_data, y_data):
            # Convert the string time into a QTime instance
            hh, mm, ss = (int(v) for v in x.split(sep=":"))
            x_qtime = QTime(hh, mm, ss)
            self._add_spinbox_pair(x_qtime, y)

        # Redraw the plot
        self._update_plot()

    def _update_plot(self):
        # Get the user input from spinboxes
        x_values = [spinbox.time() for spinbox in self.x_spin_boxes]
        slopes = [spinbox.value() for spinbox in self.y_spin_boxes]

        absolute_x_values = [0]
        y_values = [0]

        for i in range(len(x_values)):
            # Current slope for this segment
            current_slope = slopes[i]

            # Calculate the ending x-value for this segment based on the time
            time = x_values[i]
            delta_x = time.hour() * 60 + time.minute() + time.second() / 60.0
            end_x = absolute_x_values[-1] + delta_x

            # Append ending point of the segment
            delta_y = current_slope * delta_x
            new_y = y_values[-1] + delta_y
            absolute_x_values.append(end_x)
            y_values.append(np.clip(new_y, a_min=self.lower_y_bound, a_max=self.upper_y_bound))

        # Update the profile scatter plot data
        if absolute_x_values and y_values:
            self.profile_plot.profile_scatter.set_offsets(list(zip(absolute_x_values, y_values)))

        # Update the line plot and text annotations
        self.profile_plot.update_line_plot()
        self.profile_plot.update_text_annotations()

        # Redraw the canvas
        self.profile_plot.profile_scatter.figure.canvas.draw()
        
    def _on_remove_button_clicked(self, calling_layout: QVBoxLayout):
        while calling_layout.count():
            widget = calling_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        self.pairs_layout.removeItem(calling_layout)

        # Remove data from lists and update the plot
        self.x_spin_boxes.pop(calling_layout.pair_index - 1).deleteLater()
        self.y_spin_boxes.pop(calling_layout.pair_index - 1).deleteLater()

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
            if label_x and label_y:
                label_x.setText(f"X{idx + 1} (hh:mm:ss)")
                label_y.setText(f"Y{idx + 1}")

        self._update_plot()

    def get_profile_data(self) -> Tuple[List[float], List[float]]:
        return (
            [self._qtimeedit_time_to_minutes(sb.time()) for sb in self.x_spin_boxes],
            [sb.value() for sb in self.y_spin_boxes]
        )

    def get_profile_data_on_plot(self) -> List[Tuple[float, float]]:
        return self.profile_plot.profile_scatter.get_offsets()
