# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""Settings dialog — configure LibreOffice path, default output directory, etc."""

import logging
import platform
import shutil
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

_ORG_NAME = "OmniCon"
_APP_NAME = "OmniCon"

# QSettings keys
KEY_LO_PATH = "libreoffice/path"
KEY_OUTPUT_DIR = "general/default_output_dir"


def get_settings() -> QSettings:
    """Return a QSettings instance scoped to OmniCon."""
    return QSettings(_ORG_NAME, _APP_NAME)


def load_default_output_dir() -> Path:
    """Load the default output directory from QSettings.

    Falls back to ``~/Desktop`` if nothing has been saved yet.
    """
    settings = get_settings()
    raw = settings.value(KEY_OUTPUT_DIR, "")
    if raw:
        candidate = Path(str(raw))
        if candidate.is_dir():
            return candidate
    return Path.home() / "Desktop"


def load_libreoffice_path() -> Path | None:
    """Load a user-configured LibreOffice path from QSettings.

    Returns ``None`` when no custom path has been stored (or the stored
    path no longer exists on disk).
    """
    settings = get_settings()
    raw = settings.value(KEY_LO_PATH, "")
    if raw:
        candidate = Path(str(raw))
        if candidate.is_file():
            return candidate
    return None


def _detect_libreoffice() -> Path | None:
    """Auto-detect the LibreOffice ``soffice`` binary.

    Checks:
    * ``shutil.which`` for ``soffice`` / ``libreoffice``
    * Common Windows install locations
    """
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return Path(found)

    if platform.system() == "Windows":
        for prog_dir in (
            Path("C:/Program Files/LibreOffice/program"),
            Path("C:/Program Files (x86)/LibreOffice/program"),
        ):
            soffice = prog_dir / "soffice.exe"
            if soffice.exists():
                return soffice

    if platform.system() == "Darwin":
        mac_path = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
        if mac_path.exists():
            return mac_path

    return None


class SettingsDialog(QDialog):
    """Application-wide settings dialog.

    Provides controls for:
    * LibreOffice install path (browse + auto-detect)
    * Default output directory

    Persists values via ``QSettings`` with org *OmniCon* / app *OmniCon*.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)

        self._settings = get_settings()
        self._build_ui()
        self._load_settings()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Assemble all widgets inside the dialog."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(self._build_lo_group())
        layout.addWidget(self._build_output_group())
        layout.addStretch()

        # OK / Cancel / Apply
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        self._button_box.accepted.connect(self._on_ok)
        self._button_box.rejected.connect(self.reject)
        apply_btn = self._button_box.button(QDialogButtonBox.StandardButton.Apply)
        if apply_btn is not None:
            apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(self._button_box)

    def _build_lo_group(self) -> QGroupBox:
        """Build the LibreOffice path group box."""
        group = QGroupBox("LibreOffice")
        group_layout = QVBoxLayout(group)

        desc = QLabel(
            "OmniCon uses LibreOffice to convert Office documents.  "
            "Set the path to the <b>soffice</b> executable below, or "
            "click <i>Auto-detect</i>."
        )
        desc.setWordWrap(True)
        group_layout.addWidget(desc)

        row = QHBoxLayout()
        self._lo_edit = QLineEdit()
        self._lo_edit.setPlaceholderText("Path to soffice / soffice.exe")
        row.addWidget(self._lo_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_lo)
        row.addWidget(browse_btn)

        detect_btn = QPushButton("Auto-detect")
        detect_btn.clicked.connect(self._auto_detect_lo)
        row.addWidget(detect_btn)

        group_layout.addLayout(row)
        return group

    def _build_output_group(self) -> QGroupBox:
        """Build the default output directory group box."""
        group = QGroupBox("Default Output Directory")
        group_layout = QVBoxLayout(group)

        desc = QLabel(
            "Newly converted files will be placed here unless you choose "
            "a different folder in the main window."
        )
        desc.setWordWrap(True)
        group_layout.addWidget(desc)

        row = QHBoxLayout()
        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText("Default output folder")
        row.addWidget(self._output_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output)
        row.addWidget(browse_btn)

        group_layout.addLayout(row)
        return group

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _load_settings(self) -> None:
        """Populate fields from QSettings."""
        lo_path = self._settings.value(KEY_LO_PATH, "")
        self._lo_edit.setText(str(lo_path) if lo_path else "")

        output_dir = self._settings.value(KEY_OUTPUT_DIR, "")
        if not output_dir:
            output_dir = str(Path.home() / "Desktop")
        self._output_edit.setText(str(output_dir))

    def _save_settings(self) -> bool:
        """Validate and persist the current field values.

        Returns:
            ``True`` if all values are valid and saved, ``False`` otherwise.
        """
        # --- LibreOffice path ---
        lo_text = self._lo_edit.text().strip()
        if lo_text:
            lo_path = Path(lo_text)
            if not lo_path.is_file():
                QMessageBox.warning(
                    self,
                    "Invalid Path",
                    f"The LibreOffice path does not point to an existing file:\n{lo_path}",
                )
                return False
        self._settings.setValue(KEY_LO_PATH, lo_text)

        # --- Output directory ---
        output_text = self._output_edit.text().strip()
        if output_text:
            output_path = Path(output_text)
            if not output_path.is_dir():
                QMessageBox.warning(
                    self,
                    "Invalid Directory",
                    f"The output directory does not exist:\n{output_path}",
                )
                return False
        self._settings.setValue(KEY_OUTPUT_DIR, output_text)

        self._settings.sync()
        logger.info("Settings saved.")
        return True

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _browse_lo(self) -> None:
        """Open a file dialog to pick the soffice binary."""
        if platform.system() == "Windows":
            file_filter = "Executable (soffice.exe)"
        else:
            file_filter = "All files (*)"

        start_dir = self._lo_edit.text().strip()
        if not start_dir:
            start_dir = "C:/Program Files" if platform.system() == "Windows" else "/"

        path, _ = QFileDialog.getOpenFileName(
            self, "Select LibreOffice soffice executable", start_dir, file_filter
        )
        if path:
            self._lo_edit.setText(path)

    def _auto_detect_lo(self) -> None:
        """Try to auto-detect LibreOffice and fill the path field."""
        detected = _detect_libreoffice()
        if detected:
            self._lo_edit.setText(str(detected))
            QMessageBox.information(
                self,
                "LibreOffice Found",
                f"Detected LibreOffice at:\n{detected}",
            )
        else:
            QMessageBox.warning(
                self,
                "Not Found",
                "Could not auto-detect LibreOffice on this system.\n"
                "Please use the Browse button to locate soffice manually.",
            )

    def _browse_output(self) -> None:
        """Open a directory picker for the default output folder."""
        start_dir = self._output_edit.text().strip()
        if not start_dir:
            start_dir = str(Path.home() / "Desktop")

        path = QFileDialog.getExistingDirectory(
            self, "Select default output directory", start_dir
        )
        if path:
            self._output_edit.setText(path)

    def _on_ok(self) -> None:
        """Save and close the dialog."""
        if self._save_settings():
            self.accept()

    def _on_apply(self) -> None:
        """Save without closing."""
        self._save_settings()
