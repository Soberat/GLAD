from datetime import datetime
from typing import Dict

import numpy as np
import pyqtgraph
from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame
from pyqtgraph import PlotWidget, InfiniteLine, DateAxisItem

from src.widgets.settings.PlotConfigurationGroupBox import PlotConfigurationGroupBox


class PlotWidgetWithCrosshair(PlotWidget):
    def __init__(self, internal_id: str, has_profile: bool = False, *args, **kwargs):
        super(PlotWidgetWithCrosshair, self).__init__(axisItems={"bottom": DateAxisItem()}, *args, **kwargs)
        self.internal_id = internal_id

        # Provide settings as a convenience
        self.settings: QSettings = QSettings("Mirosław Wiącek Code", "GLAD")

        # Set up the initial look by adding a legend, grid and title
        self.getPlotItem().addLegend()
        self.getPlotItem().showGrid(x=True, y=True, alpha=0.5)
        self.setTitle(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, measured: none")

        # Get plot configuration from settings
        self.settings.beginGroup(internal_id)

        self.settings.beginGroup("measured_plot")
        self.measured_plot_pen = pyqtgraph.mkPen(
            color=QColor(self.settings.value("pen_color", defaultValue="#2ec41e")),
            width=float(self.settings.value("pen_width", defaultValue=2.25))
        )
        self.measured_plot_symbol_size = float(self.settings.value("symbol_size", defaultValue=6))
        self.settings.endGroup()  # measured_plot group

        self.settings.beginGroup("profile_plot")
        self.profile_plot_pen = pyqtgraph.mkPen(
            color=QColor(self.settings.value("pen_color", defaultValue="#1e90ff")),
            width=float(self.settings.value("pen_width", defaultValue=2.25))
        )
        self.profile_plot_symbol_size = float(self.settings.value("symbol_size", defaultValue=6))
        self.settings.endGroup()  # profile_plot group

        self.settings.endGroup()

        self.measured_values_plot = self.plot(
            [],
            pen=self.measured_plot_pen,
            symbolBrush=self.measured_plot_pen.color(),
            symbolPen=self.measured_plot_pen,
            symbol="o",
            symbolSize=self.measured_plot_symbol_size,
            name="Measured"
        )

        # Whether the plot also displays a profile of wanted Y values
        self.has_profile = has_profile
        if self.has_profile:
            self.profile_values_plot = self.plot(
                [],
                pen=self.profile_plot_pen,
                symbolBrush=self.profile_plot_pen.color(),
                symbolPen=self.profile_plot_pen,
                symbol="o",
                symbolSize=self.profile_plot_symbol_size,
                name="Profile"
            )

        # Draw the measured data over the profile data
        self.measured_values_plot.setZValue(1)

        # Create lines for the crosshair
        self.crosshair_v_line = InfiniteLine(angle=90, movable=False)
        self.crosshair_h_line = InfiniteLine(angle=0, movable=False)

        self.addItem(self.crosshair_v_line, ignoreBounds=True)
        self.addItem(self.crosshair_h_line, ignoreBounds=True)

        # Connect mouse move event
        self.scene().sigMouseMoved.connect(self.mouse_moved)

    def mouse_moved(self, evt):
        if not self.sceneBoundingRect().contains(evt):
            return

        # Convert the mouse position to the coordinate system of the plot
        mousePoint = self.getPlotItem().vb.mapSceneToView(evt)

        # Test if X is valid
        if mousePoint.x() <= 0:
            return

        self.crosshair_v_line.setPos(mousePoint.x())
        self.crosshair_h_line.setPos(mousePoint.y())

        measured_x_values, measured_y_values = self.measured_values_plot.getData()

        if measured_x_values is None:
            return

        # Find the index of the nearest x-value
        idx_measured = np.searchsorted(measured_x_values, mousePoint.x(), side="right")

        # Create the first part of the label text, since it will always exist
        label_text = f"Time: {datetime.fromtimestamp(mousePoint.x()).strftime('%Y-%m-%d %H:%M:%S')}"

        # Check if index is within bounds and show corresponding y value
        if 0 <= idx_measured < len(measured_y_values):
            # Get y values for both plots
            measured_y = measured_y_values[idx_measured]
            label_text += f", measured: {measured_y :.2f}"
        else:
            label_text += f", measured: none"

        if self.has_profile:
            profile_plot_x_data, profile_plot_y_data = self.profile_values_plot.getData()

            if profile_plot_x_data is not None:
                idx_profile = np.searchsorted(profile_plot_x_data, mousePoint.x(), side="right")

                # If the index is not out of the profile X bounds
                if idx_profile < len(profile_plot_y_data):
                    profile_y = profile_plot_y_data[idx_profile]
                    label_text += f", profile: {profile_y: .2f}"
                else:
                    label_text += f", profile: none"

        self.setTitle(label_text)

    def get_settings_widget(self) -> QWidget:
        widget = QFrame()
        widget.setLayout(QVBoxLayout())

        widget.plot_configuration_group_box = PlotConfigurationGroupBox(
            initial_color_picker_color=self.measured_plot_pen.color(),
            initial_line_width=self.measured_plot_pen.width(),
            initial_symbol_size=self.measured_plot_symbol_size
        )
        widget.layout().addWidget(widget.plot_configuration_group_box)

        if self.has_profile:
            widget.profile_plot_configuration_group_box = PlotConfigurationGroupBox(
                initial_color_picker_color=self.profile_plot_pen.color(),
                initial_line_width=self.profile_plot_pen.width(),
                initial_symbol_size=self.profile_plot_symbol_size,
                group_title="Profile plot settings"
            )
            widget.layout().addWidget(widget.profile_plot_configuration_group_box)

        return widget

    def apply_values_from_config(self, measured_plot_parameters: Dict, profile_plot_parameters: Dict = {}):
        # Update plot parameters
        self.measured_plot_pen = pyqtgraph.mkPen(
            color=measured_plot_parameters["pen_color"],
            width=measured_plot_parameters["pen_width"]
        )
        self.measured_plot_symbol_size = measured_plot_parameters["symbol_size"]

        measured_x_values, measured_y_values = self.measured_values_plot.getData()
        self.measured_values_plot.setData(
            x=measured_x_values,
            y=measured_y_values,
            pen=self.measured_plot_pen,
            symbolBrush=self.measured_plot_pen.color(),
            symbolPen=self.measured_plot_pen,
            symbolSize=self.measured_plot_symbol_size
        )

        # Update profile plot parameters
        if self.has_profile:
            profile_x_values, profile_y_values = self.profile_values_plot.getData()
            self.profile_plot_pen = pyqtgraph.mkPen(
                color=profile_plot_parameters["pen_color"],
                width=profile_plot_parameters["pen_width"]
            )
            self.profile_plot_symbol_size = profile_plot_parameters["symbol_size"]

            self.profile_values_plot.setData(
                x=profile_x_values,
                y=profile_y_values,
                pen=self.profile_plot_pen,
                symbolBrush=self.profile_plot_pen.color(),
                symbolPen=self.profile_plot_pen,
                symbolSize=self.profile_plot_symbol_size
            )

    def update_settings(self):
        # Update the values in the appropriate group
        self.settings.beginGroup(self.internal_id)

        # Plot settings
        self.settings.beginGroup("measured_plot")
        self.settings.setValue("pen_color", self.measured_plot_pen.color().name())
        self.settings.setValue("pen_width", self.measured_plot_pen.width())
        self.settings.setValue("symbol_size", self.measured_plot_symbol_size)
        self.settings.endGroup()  # plot group

        # Profile plot settings
        if self.has_profile:
            self.settings.beginGroup("profile_plot")
            self.settings.setValue("pen_color", self.profile_plot_pen.color().name())
            self.settings.setValue("pen_width", self.profile_plot_pen.width())
            self.settings.setValue("symbol_size", self.profile_plot_symbol_size)
            self.settings.endGroup()  # profile plot group

        self.settings.endGroup()  # internal_id group
