import csv
import logging
import time
from itertools import cycle

import xlsxwriter as xlsxwriter
from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, \
    QDialogButtonBox, QFileDialog, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QDateTimeEdit, QLabel, \
    QRadioButton
from pyqtgraph import PlotWidget, DateAxisItem, LinearRegionItem
from datetime import datetime

from typing import List

from src.widgets.DeviceWidgetBase import DeviceWidgetBase


class ExportDialog(QDialog):
    def __init__(self, widgets: List[DeviceWidgetBase], min_time, max_time, checked_combinations=None, parent=None):
        super().__init__(parent)

        logging.debug("Creating export dialog")

        # Disable "What's this" button
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)
        self.setWindowTitle("Configure export options")

        self.setLayout(QHBoxLayout())

        # File format choice using radio buttons
        format_layout = QVBoxLayout()
        self.radio_excel = QRadioButton("Export as Excel")
        self.radio_csv = QRadioButton("Export as CSV")
        self.radio_csv.setChecked(True)  # Default to CSV
        format_layout.addWidget(self.radio_excel)
        format_layout.addWidget(self.radio_csv)

        # Time range selection
        time_layout = QVBoxLayout()
        self.start_time = QDateTimeEdit(QDateTime.fromSecsSinceEpoch(min_time), self)
        self.end_time = QDateTimeEdit(QDateTime.fromSecsSinceEpoch(max_time), self)
        time_layout.addWidget(QLabel("Start time"))
        time_layout.addWidget(self.start_time)
        time_layout.addWidget(QLabel("End time"))
        time_layout.addWidget(self.end_time)

        # Widgets selection using QTreeWidget
        self.device_selection_tree = QTreeWidget()
        self.device_selection_tree.setHeaderLabel("Data to export")

        for widget in widgets:
            measurements = widget.get_measured_values()
            # Skip devices with no measurements
            if not measurements:
                continue

            widget_item = QTreeWidgetItem(self.device_selection_tree)
            widget_item.setText(0, str(widget))
            widget_item.setCheckState(0, Qt.Checked if checked_combinations and any(
                (str(widget), measurement) in checked_combinations for measurement in
                measurements.keys()) else Qt.Unchecked)
            widget_item.setFlags(widget_item.flags() | Qt.ItemIsAutoTristate)

            for measurement in measurements.keys():
                measurement_item = QTreeWidgetItem(widget_item)
                measurement_item.setText(0, measurement)
                measurement_item.setCheckState(0, Qt.Checked if checked_combinations and (
                    str(widget), measurement) in checked_combinations else Qt.Unchecked)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        temp_layout = QVBoxLayout()
        temp_layout.addLayout(format_layout)
        temp_layout.addLayout(time_layout)
        temp_layout.addStretch(1)
        self.layout().addLayout(temp_layout)

        temp_layout = QVBoxLayout()
        temp_layout.addWidget(self.device_selection_tree)
        temp_layout.addWidget(button_box)

        self.layout().addLayout(temp_layout)

        logging.debug("Dialog created")

    def get_export_options(self):
        file_format = "excel" if self.radio_excel.isChecked() else "csv"
        start = self.start_time.dateTime().toSecsSinceEpoch()
        end = self.end_time.dateTime().toSecsSinceEpoch()

        widgets = []
        for widget in range(self.device_selection_tree.topLevelItemCount()):
            widget_item = self.device_selection_tree.topLevelItem(widget)
            for measurement in range(widget_item.childCount()):
                measurement_item = widget_item.child(measurement)
                if measurement_item.checkState(0) == Qt.Checked:
                    widgets.append((widget_item.text(0), measurement_item.text(0)))

        return file_format, start, end, widgets


class FilterDialog(QDialog):
    def __init__(self, unique_combinations, checked_combinations=None, parent=None):
        super().__init__(parent)

        logging.debug("Creating combination filter dialog")

        # Disable "What's this" button
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)
        self.setWindowTitle("Filter measurements")

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Widgets and measurements"])
        layout.addWidget(self.tree)

        self.checkboxes = {}
        self.widget_nodes = {}

        # Group the measurements by widgets
        widgets = {}
        for widget, measurement in unique_combinations:
            if widget not in widgets:
                widgets[widget] = []
            widgets[widget].append(measurement)

        for widget, measurements in widgets.items():
            if not measurements:  # Skip devices with no measurements
                continue

            widget_item = QTreeWidgetItem(self.tree)
            widget_item.setText(0, widget)
            widget_item.setCheckState(0, Qt.Checked if checked_combinations and any(
                (widget, measurement) in checked_combinations for measurement in measurements) else Qt.Unchecked)
            widget_item.setFlags(widget_item.flags() | Qt.ItemIsAutoTristate)
            self.widget_nodes[widget] = widget_item

            for measurement in measurements:
                measurement_item = QTreeWidgetItem(widget_item)
                measurement_item.setText(0, measurement)
                measurement_item.setCheckState(0, Qt.Checked if checked_combinations and (
                    widget, measurement) in checked_combinations else Qt.Unchecked)
                self.checkboxes[(widget, measurement)] = measurement_item

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Expand the whole tree
        self.tree.expandAll()

        # Set size to show all items
        self.setMinimumSize(375, 400)

        logging.debug("Dialog created")

    def get_checked_combinations(self):
        return [combo for combo, item in self.checkboxes.items() if item.checkState(0) == Qt.Checked]


class MeasurementDialog(QDialog):
    def __init__(self, widgets: List[DeviceWidgetBase], parent=None):
        super().__init__(parent)

        logging.debug("Creating measurement viewer dialog")

        # Disable "What's this" button
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)

        self.setWindowTitle("Measurements")

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create a secondary plot for time control
        self.time_control_plot = PlotWidget(axisItems={"bottom": DateAxisItem()})
        self.time_control_plot.setFixedHeight(100)
        self.time_control_plot.setMouseEnabled(x=False, y=False)

        # Linear region for selecting time range
        self.time_region = LinearRegionItem()
        self.time_region.setZValue(-10)
        self.time_control_plot.addItem(self.time_region)

        # Set the initial region value around the current time
        current_time = time.time()
        # Set the region to be +/- 30 minutes around the current time
        self.time_region.setRegion([current_time - 1800, current_time + 1800])

        layout.addWidget(self.time_control_plot)

        # Connect the region change to the update function
        self.time_region.sigRegionChanged.connect(self.update_time_range)

        self.plot_widget = PlotWidget(axisItems={"bottom": DateAxisItem()}, parent=self)
        self.plot_widget.getPlotItem().showGrid(x=True, y=True, alpha=0.5)
        layout.addWidget(self.plot_widget)

        # Create a table widget
        self.table_widget = QTableWidget()
        # Disable editing
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["Device", "Measurement", "Timestamp", "Value"])
        layout.addWidget(self.table_widget)

        # Make table sortable
        self.table_widget.setSortingEnabled(True)

        # Create a button layout
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        # Add a filter button
        self.filter_button = QPushButton("Filter")
        self.filter_button.clicked.connect(self.filter_data)
        button_layout.addWidget(self.filter_button)

        # Add an export button
        self.export_button = QPushButton("Export data")
        self.export_button.clicked.connect(self.export_data)
        button_layout.addWidget(self.export_button)

        # Save the widget references
        self.widgets: List[DeviceWidgetBase] = widgets

        # Initially display no measurements, force the user to use the filter dialog
        self.checked_combinations = set()

        self.populate_data()

        # Sort by third column (timestamp) in descending order
        self.table_widget.sortItems(2, Qt.DescendingOrder)

        self.resize(550, 800)

        logging.debug("Dialog created")

    def populate_data(self):
        logging.debug("Populating data")

        # Clear existing data first
        self.plot_widget.clear()
        self.table_widget.setRowCount(0)

        # Disable sorting while populating
        self.table_widget.setSortingEnabled(False)

        # Create a legend
        self.plot_widget.addLegend()

        # Create a color cycle iterator
        colors = cycle([
            "DodgerBlue", "DarkOrange", "MediumPurple", "ForestGreen", "HotPink",
            "SaddleBrown", "Aqua", "DarkRed", "Goldenrod", "DarkSlateGray",
            "Orchid", "MediumSeaGreen", "DeepSkyBlue", "FireBrick", "DarkViolet",
            "Teal", "Sienna", "Lime", "SteelBlue", "Tomato",
            "Olive", "DarkKhaki", "MediumVioletRed", "RoyalBlue", "RosyBrown",
            "DarkSalmon", "CadetBlue", "SandyBrown", "Peru", "DarkOliveGreen"
        ])

        row = 0
        # Plot the same data on the control plot, but just as background
        for widget in self.widgets:
            class_name = str(widget)
            data = widget.get_measured_values()

            if len(data) == 0:
                continue

            for key, values in data.items():
                self.time_control_plot.plot(
                    [p[0] for p in values],
                    [p[1] for p in values],
                    pen=0.2  # Lighter color to keep it as background
                )

            for key, values in data.items():
                if self.checked_combinations is not None and (class_name, key) not in self.checked_combinations:
                    continue

                color = next(colors)  # Get the next color from the cycle
                self.plot_widget.plot(
                    [x[0] for x in values],
                    [x[1] for x in values],
                    pen={"color": color, "width": 2},
                    symbol="o",
                    symbolSize=5,
                    symbolPen={"color": color},
                    symbolBrush=color,
                    name=f"{class_name} - {key}"
                )

                # Populate table
                for x, y in values:
                    self.table_widget.insertRow(row)
                    self.table_widget.setItem(row, 0, QTableWidgetItem(class_name))
                    self.table_widget.setItem(row, 1, QTableWidgetItem(key))
                    self.table_widget.setItem(row, 2,
                                              QTableWidgetItem(datetime.fromtimestamp(x).strftime("%Y-%m-%d %H:%M:%S")))
                    self.table_widget.setItem(row, 3, QTableWidgetItem(str(y)))
                    row += 1

        self.table_widget.setSortingEnabled(True)
        self.table_widget.sortItems(2, Qt.DescendingOrder)

        # After populating data, adjust the time_region to fit within the data time range
        timestamps = [x[0] for widget in self.widgets for _, values in widget.get_measured_values().items() for x in
                      values]
        if timestamps:  # Check if we have any timestamps
            min_time = min(timestamps)
            max_time = max(timestamps)
            # Get current region
            start, end = self.time_region.getRegion()
            # Adjust region to fit within data time range
            self.time_region.setRegion([max(min_time, start), min(max_time, end)])
            # After populating data, adjust the time_control_plot Y-axis to fit the data
            self.time_control_plot.autoRange()

        logging.debug("Finished populating data")

    def filter_data(self):
        unique_combinations = set()
        for widget in self.widgets:
            for key in widget.get_measured_values():
                unique_combinations.add((str(widget), key))

        dialog = FilterDialog(unique_combinations, self.checked_combinations)
        result = dialog.exec()

        if result == QDialog.Accepted:
            self.checked_combinations = dialog.get_checked_combinations()
            self.populate_data()

    def update_time_range(self):
        start, end = self.time_region.getRegion()
        logging.debug(f"Updating time range to {start}-{end}")
        self.plot_widget.setXRange(start, end, padding=0)

    def export_data(self):
        # Calculate the min and max time from the data
        timestamps = [
            x[0] for widget in self.widgets for _, values in widget.get_measured_values().items() for x in values
        ]
        min_time = int(min(timestamps)) if timestamps else time.time() - 1800  # default to 30 minutes ago
        max_time = int(max(timestamps)) if timestamps else time.time() + 1800  # default to 30 minutes in future

        dialog = ExportDialog(self.widgets, min_time, max_time, self.checked_combinations, self)
        result = dialog.exec()
        if result == QDialog.Accepted:
            file_format, start, end, selected_widgets = dialog.get_export_options()

            options = QFileDialog.Options()
            ext = ".xlsx" if file_format == "excel" else ".csv"
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save File",
                "",
                f"{file_format.capitalize()} Files (*{ext});;All Files (*)",
                options=options
            )

            if path:
                if not path.endswith(ext):
                    path += ext

                logging.debug(f"Exporting to {file_format} at {path}, {start}-{end} from {selected_widgets}")
                if file_format == "excel":
                    rows_written = self.export_to_excel(path, start, end, selected_widgets)
                else:
                    rows_written = self.export_to_csv(path, start, end, selected_widgets)
                logging.debug(f"Export done, written {rows_written} rows")

    def export_to_csv(self, path: str, start_timestamp: int, end_timestamp: int, selected_widgets: List[str]) -> int:
        rows = self.table_widget.rowCount()
        cols = self.table_widget.columnCount()

        with open(path, "w", newline="") as file:
            writer = csv.writer(file)

            # Write headers
            logging.debug("Writing CSV headers")
            headers = [self.table_widget.horizontalHeaderItem(col).text() for col in range(cols)]
            writer.writerow(headers)

            # Write content
            logging.debug("Writing CSV content")
            written = 0
            for row in range(rows):
                timestamp = datetime.strptime(self.table_widget.item(row, 2).text(), "%Y-%m-%d %H:%M:%S").timestamp()
                if self.table_widget.item(row, 0).text() in selected_widgets and \
                        start_timestamp <= timestamp <= end_timestamp:
                    writer.writerow([self.table_widget.item(row, col).text() for col in range(cols)])
                    written += 1

            return written

    def export_to_excel(self, path: str, start_timestamp: int, end_timestamp: int, selected_widgets: List[str]) -> int:
        workbook = xlsxwriter.Workbook(path)
        worksheet = workbook.add_worksheet()
        rows = self.table_widget.rowCount()
        cols = self.table_widget.columnCount()

        # Write headers
        for col in range(cols):
            worksheet.write(0, col, self.table_widget.horizontalHeaderItem(col).text())

        # Write content
        row_num = 1
        for row in range(rows):
            timestamp = datetime.strptime(self.table_widget.item(row, 2).text(), "%Y-%m-%d %H:%M:%S").timestamp()
            if self.table_widget.item(row, 0).text() in selected_widgets and \
                    start_timestamp <= timestamp <= end_timestamp:
                for col in range(cols):
                    worksheet.write(row_num, col, self.table_widget.item(row, col).text())
                row_num += 1

        workbook.close()

        return row_num - 1
