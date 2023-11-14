from PyQt5.QtGui import QPixmap, QIcon, QColor
from PyQt5.QtWidgets import QGroupBox, QFormLayout, QColorDialog, QPushButton, QDoubleSpinBox


class PlotConfigurationGroupBox(QGroupBox):
    def __init__(
            self,
            initial_color_picker_color: QColor,
            initial_line_width: float,
            initial_symbol_size: float,
            group_title: str = "Plot settings"
    ):
        super().__init__(group_title)
        layout = QFormLayout()

        self.chosen_color = initial_color_picker_color
        color_picker_dialog = QColorDialog(parent=self)
        color_picker_dialog.setCurrentColor(QColor(255, 0, 255))
        color_picker_launch_button = QPushButton(QIcon(QPixmap()), "Pick color")
        color_pixmap = QPixmap(10, 10)
        color_pixmap.fill(initial_color_picker_color)
        color_icon = QIcon(color_pixmap)
        color_picker_launch_button.setIcon(color_icon)

        def pick_color():
            chosen_color = color_picker_dialog.getColor(initial=initial_color_picker_color)
            if chosen_color.isValid():
                # Setting an icon with the chosen color as its pixmap
                color_pixmap = QPixmap(10, 10)
                color_pixmap.fill(chosen_color)
                color_icon = QIcon(color_pixmap)
                color_picker_launch_button.setIcon(color_icon)
                self.chosen_color = chosen_color

        color_picker_launch_button.clicked.connect(pick_color)
        layout.addRow("Line color", color_picker_launch_button)

        self.line_width_spinbox = QDoubleSpinBox()
        self.line_width_spinbox.setMinimum(1.0)
        self.line_width_spinbox.setMaximum(50.0)
        self.line_width_spinbox.setSingleStep(0.5)
        self.line_width_spinbox.setValue(initial_line_width)
        layout.addRow("Line width", self.line_width_spinbox)

        self.symbol_size_spinbox = QDoubleSpinBox()
        self.symbol_size_spinbox.setMinimum(1.0)
        self.symbol_size_spinbox.setMaximum(50.0)
        self.symbol_size_spinbox.setSingleStep(0.5)
        self.symbol_size_spinbox.setValue(float(initial_symbol_size))
        layout.addRow("Symbol size", self.symbol_size_spinbox)

        self.setLayout(layout)

    def get_parameters_as_dict(self):
        return {
            "pen_color": self.chosen_color,
            "pen_width": self.line_width_spinbox.value(),
            "symbol_size": self.symbol_size_spinbox.value()
        }
