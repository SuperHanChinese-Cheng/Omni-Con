"""Application bootstrap — creates and configures the QApplication."""

import sys

from PySide6.QtWidgets import QApplication

from omnicon.gui.main_window import MainWindow


def create_app(argv: list[str] | None = None) -> QApplication:
    """Create the OmniCon QApplication and main window.

    Args:
        argv: Command-line arguments (defaults to sys.argv).

    Returns:
        The configured QApplication instance, ready for .exec().
    """
    if argv is None:
        argv = sys.argv

    app = QApplication(argv)
    app.setApplicationName("OmniCon")
    app.setOrganizationName("OmniCon")

    window = MainWindow()
    window.show()

    app._main_window = window  # type: ignore[attr-defined]

    return app
