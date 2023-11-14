
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel, QLineEdit


class GeneralSettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())

        self.settings = QSettings("Mirosław Wiącek Code", "GLAD")

        # API logging configuration
        self.api_logging_configuration_group_box = QGroupBox("API logging configuration")
        self.api_logging_configuration_group_box.setCheckable(True)
        self.api_logging_configuration_group_box.setChecked(
            self.settings.value("api_logging_enabled", defaultValue="false") == "true"
        )
        self.api_logging_configuration_group_box.toggled.connect(self._on_api_logging_toggled)

        self.api_logging_endpoint_lineedit = QLineEdit()
        self.api_logging_endpoint_lineedit.setText(
            self.settings.value("api_logging_endpoint", defaultValue="http://localhost:8080/api/glad/exceptions")
        )
        self.api_logging_endpoint_lineedit.editingFinished.connect(self._on_api_logging_endpoint_changed)

        api_logging_configuration_group_box_layout = QFormLayout()

        # Add an informative label
        api_logging_configuration_group_box_layout.addWidget(QLabel(
            "Errors in the application can be sent to a special\nwebsite setup by the developer "
            "to enable remote diagnostics"
        ))
        api_logging_configuration_group_box_layout.addRow("Endpoint", self.api_logging_endpoint_lineedit)

        self.api_logging_configuration_group_box.setLayout(api_logging_configuration_group_box_layout)

        self.layout().addWidget(self.api_logging_configuration_group_box)
        self.layout().addStretch(1)

    def _on_api_logging_toggled(self, is_checked: bool):
        self.settings.setValue("api_logging_enabled", "true" if is_checked else "false")

    def _on_api_logging_endpoint_changed(self):
        new_text = self.api_logging_endpoint_lineedit.text()
        self.settings.setValue("api_logging_endpoint", new_text)
