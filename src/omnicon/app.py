# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""Application bootstrap — creates and configures the QApplication."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

from omnicon.gui.main_window import MainWindow


def _is_windows_dark_mode() -> bool:
    """Detect if Windows is using dark mode via the registry."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0
    except Exception:
        return False


def _apply_dark_palette(app: QApplication) -> None:
    """Apply a dark color palette to the application."""
    palette = QPalette()

    # Base colors
    dark = QColor(30, 30, 30)
    mid_dark = QColor(45, 45, 45)
    mid = QColor(60, 60, 60)
    light_text = QColor(220, 220, 220)
    accent = QColor(0, 120, 212)
    disabled_text = QColor(128, 128, 128)

    palette.setColor(QPalette.ColorRole.Window, mid_dark)
    palette.setColor(QPalette.ColorRole.WindowText, light_text)
    palette.setColor(QPalette.ColorRole.Base, dark)
    palette.setColor(QPalette.ColorRole.AlternateBase, mid_dark)
    palette.setColor(QPalette.ColorRole.ToolTipBase, mid)
    palette.setColor(QPalette.ColorRole.ToolTipText, light_text)
    palette.setColor(QPalette.ColorRole.Text, light_text)
    palette.setColor(QPalette.ColorRole.Button, mid_dark)
    palette.setColor(QPalette.ColorRole.ButtonText, light_text)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Link, accent)
    palette.setColor(QPalette.ColorRole.Highlight, accent)
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)

    # Disabled state
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled_text,
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_text,
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled_text,
    )

    app.setPalette(palette)


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

    # Use Fusion style for consistent cross-platform look
    app.setStyle(QStyleFactory.create("Fusion"))

    # Detect system dark mode and apply matching palette
    if _is_windows_dark_mode():
        _apply_dark_palette(app)
        app.setProperty("_omnicon_dark", True)
    else:
        app.setProperty("_omnicon_dark", False)

    window = MainWindow()
    window.show()

    app._main_window = window  # type: ignore[attr-defined]

    return app
