import argparse
import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler

import requests
from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QErrorMessage

from src.widgets.GLADMainWindow import GLADMainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("GLAD")
    app.setApplicationDisplayName("GLAD")
    app.setWindowIcon(QIcon("glad_icon.png"))

    # Check the arguments, and if --wipe-settings is defined, wipe the settings and quit
    parser = argparse.ArgumentParser(description="GLAD")
    parser.add_argument("--wipe-settings", action="store_true",
                        help="Erase stored settings, do not launch the application")
    args = parser.parse_args()

    settings = QSettings("Mirosław Wiącek Code", "GLAD")

    if args.wipe_settings:
        settings.clear()
        sys.exit(0)

    # Fusion style fixed incorrect rendering of QMdiSubWindow titlebar when maximized
    app.setStyle("fusion")

    # Set up the logger
    logger = logging.getLogger()

    error_message = QErrorMessage()
    error_message.setMinimumSize(600, 600)


    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Do not log interruptions caused by KeyboardInterrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

        formatted_exception = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        html_exception = formatted_exception.replace("\n", "<br>")

        error_message.showMessage(html_exception)

        if settings.value("api_logging_enabled", defaultValue="false") == "true":
            # Send the exception to an API that registers errors
            API_ENDPOINT = settings.value(
                "api_logging_endpoint",
                defaultValue="http://localhost:8080/api/glad/exceptions"
            )

            try:
                response = requests.post(API_ENDPOINT, json={"exception": formatted_exception}, timeout=5)
                # Raise a HTTPError if the HTTP request returned an unsuccessful status code
                response.raise_for_status()

                if response.status_code != 200:
                    logging.error(f"Failed to send exception to API. Status code {response.status_code}")
                else:
                    logging.info(f"Uncaught exception logged and stored")
            except Exception as e:
                logging.error(f"Error occurred while sending exception to API: {e}")

    sys.excepthook = handle_exception

    logger.setLevel(logging.DEBUG)  # Set the desired logging level

    # Ensure that the "logs" directory exists
    log_directory = "logs"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # Create a rotating file handler to write log messages to a file with size limit
    log_file = os.path.join(log_directory, "app.log")
    log_file_size = int(3 * 1024 * 1024)  # 3 MB
    file_handler = RotatingFileHandler(log_file, maxBytes=log_file_size, backupCount=50)
    file_handler.setLevel(logging.DEBUG)  # Set the desired logging level for file

    # Create a console handler to print log messages to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # Set the desired logging level for console

    # Create a formatter and set it for all handlers
    formatter = logging.Formatter("%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    mainWin = GLADMainWindow()

    mainWin.show()
    sys.exit(app.exec())
