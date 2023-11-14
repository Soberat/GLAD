from PyQt5.QtCore import pyqtSignal, QSettings
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton


class LayoutSettingsWidget(QWidget):
    layoutListUpdated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())

        self.settings = QSettings("Mirosław Wiącek Code", "GLAD")

        self.settings.beginGroup("layouts")
        layout_list = {name.split(sep="/")[0] for name in self.settings.allKeys()}
        self.settings.endGroup()

        # Add informing label if there are no layouts defined
        if len(layout_list) == 0:
            self.layout().addWidget(
                QLabel("No layouts defined.\nYou can do so by going into View -> Layouts -> Save current layout.")
            )

        for name in layout_list:
            inner_layout = QHBoxLayout()
            inner_layout.addWidget(QLabel(name))

            inner_layout.addStretch(1)

            remove_button = QPushButton("Remove")
            # name=name captures the value for the iteration, rather than the loop variable reference
            remove_button.clicked.connect(
                lambda _, name=name, inner_layout=inner_layout: self.remove_layout(name, inner_layout)
            )

            inner_layout.addWidget(remove_button)

            self.layout().addLayout(inner_layout)

        self.layout().addStretch(1)

    def remove_layout(self, layout_name: str, inner_layout: QHBoxLayout):
        # Remove settings
        self.settings.beginGroup("layouts")
        self.settings.remove(layout_name)
        self.settings.endGroup()

        # Remove layout and its widgets
        while inner_layout.count():
            widget = inner_layout.itemAt(0).widget()
            if widget:
                widget.deleteLater()
            inner_layout.removeItem(inner_layout.itemAt(0))

        # Remove layout from parent layout
        self.layout().removeItem(inner_layout)
        inner_layout.deleteLater()

        # Notify about layout list changes
        self.layoutListUpdated.emit()
