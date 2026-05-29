# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""Main application window with drag-drop zone and conversion queue."""

import logging
from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from omnicon.core.dispatcher import ConversionDispatcher
from omnicon.core.job import ConversionJob, JobStatus
from omnicon.core.registry import EngineRegistry
from omnicon.core.worker import ConversionWorker
from omnicon.engines.html_engine import HTMLEngine
from omnicon.engines.image_engine import ImageEngine
from omnicon.engines.office_engine import OfficeEngine
from omnicon.engines.pandoc_engine import PandocEngine
from omnicon.engines.pdf_engine import PDFEngine
from omnicon.engines.table_engine import TableEngine
from omnicon.engines.text_engine import TextEngine
from omnicon.gui.pdf_tools_dialog import PDFToolsDialog
from omnicon.gui.settings_dialog import SettingsDialog, load_default_output_dir, load_libreoffice_path
from omnicon.utils.updater import UpdateWorker

logger = logging.getLogger(__name__)

_FORMAT_OPTIONS: dict[str, list[str]] = {
    "pdf": ["docx", "txt", "png", "jpg", "html", "pptx", "xlsx"],
    "docx": ["pdf", "txt", "html", "md"],
    "doc": ["pdf", "txt"],
    "pptx": ["pdf", "txt"],
    "ppt": ["pdf"],
    "xlsx": ["pdf", "csv", "txt"],
    "xls": ["pdf"],
    "odt": ["pdf"],
    "odp": ["pdf"],
    "ods": ["pdf"],
    "rtf": ["pdf"],
    "csv": ["xlsx"],
    "md": ["pdf", "docx", "html", "txt"],
    "html": ["pdf", "txt", "md"],
    "htm": ["pdf", "txt", "md"],
    "png": ["jpg", "webp", "bmp", "tiff", "pdf"],
    "jpg": ["png", "webp", "bmp", "tiff", "pdf"],
    "jpeg": ["png", "webp", "bmp", "tiff", "pdf"],
    "webp": ["png", "jpg", "bmp", "tiff", "pdf"],
    "bmp": ["png", "jpg", "webp", "tiff", "pdf"],
    "tiff": ["png", "jpg", "webp", "bmp", "pdf"],
    "tif": ["png", "jpg", "webp", "bmp", "pdf"],
    "gif": ["png", "jpg", "webp", "pdf"],
    "svg": ["png", "pdf"],
}


class DropZone(QLabel):
    """Drag-and-drop area for file input."""

    def __init__(self, parent: "MainWindow") -> None:
        super().__init__(parent)
        self._main = parent
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumSize(400, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._set_idle_style()

    def _set_idle_style(self) -> None:
        self.setText("Drop files here\nor click Browse")
        self.setStyleSheet(
            "QLabel {"
            "  border: 2px dashed #888;"
            "  border-radius: 12px;"
            "  background: #f8f8f8;"
            "  color: #666;"
            "  font-size: 16px;"
            "  padding: 20px;"
            "}"
        )

    def _set_hover_style(self) -> None:
        self.setStyleSheet(
            "QLabel {"
            "  border: 2px dashed #0078d4;"
            "  border-radius: 12px;"
            "  background: #e8f0fe;"
            "  color: #0078d4;"
            "  font-size: 16px;"
            "  padding: 20px;"
            "}"
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_hover_style()

    def dragLeaveEvent(self, event: object) -> None:
        self._set_idle_style()

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_idle_style()
        files = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if files:
            self._main.add_files(files)

    def mousePressEvent(self, event: object) -> None:
        self._main.browse_files()


class JobWidget(QWidget):
    """Shows status for a single conversion job."""

    def __init__(self, job: ConversionJob, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.job = job
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self.name_label = QLabel(f"{job.input_path.name} → {job.output_format}")
        self.name_label.setMinimumWidth(200)

        self.status_label = QLabel("Queued")
        self.status_label.setMinimumWidth(80)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(120)

        layout.addWidget(self.name_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)

    def update_status(self) -> None:
        status_text = {
            JobStatus.QUEUED: "Queued",
            JobStatus.RUNNING: "Converting...",
            JobStatus.DONE: "Done",
            JobStatus.FAILED: "Failed",
            JobStatus.CANCELLED: "Cancelled",
        }
        self.status_label.setText(status_text.get(self.job.status, "Unknown"))
        self.progress_bar.setValue(self.job.progress)

        if self.job.status == JobStatus.DONE:
            self.status_label.setStyleSheet("color: #107c10;")
        elif self.job.status == JobStatus.FAILED:
            self.status_label.setStyleSheet("color: #d13438;")
            if self.job.error_message:
                self.status_label.setToolTip(self.job.error_message)


class MainWindow(QMainWindow):
    """Primary application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OmniCon — Universal File Converter | by Chenglin Qiu (SHC)")
        self.setMinimumSize(600, 500)
        self.resize(700, 550)

        # Feed the user-configured LibreOffice path (if any) into OfficeEngine
        # so it doesn't fall back to its own auto-detect when a path is saved.
        lo_path = load_libreoffice_path()

        self._registry = EngineRegistry()
        self._registry.register(PDFEngine())
        self._registry.register(ImageEngine())
        self._registry.register(TextEngine())
        self._registry.register(HTMLEngine())
        self._registry.register(PandocEngine())
        self._registry.register(TableEngine())
        self._registry.register(OfficeEngine(soffice_path=lo_path))
        self._dispatcher = ConversionDispatcher(self._registry)
        self._thread_pool = QThreadPool.globalInstance()

        self._pending_files: list[Path] = []
        self._job_widgets: list[JobWidget] = []
        self._active_workers: list[ConversionWorker] = []

        self._build_menu_bar()
        self._build_ui()
        self._check_for_updates()

    # ------------------------------------------------------------------
    # Auto-update check
    # ------------------------------------------------------------------

    def _check_for_updates(self) -> None:
        """Kick off a non-blocking update check against GitHub Releases.

        Runs once per session in a thread-pool thread. If a newer version
        is found, a dismissible info banner is shown at the top of the
        window. Network or API failures are silently logged.
        """
        self._update_worker = UpdateWorker()
        self._update_worker.signals.update_available.connect(
            self._show_update_banner
        )
        self._thread_pool.start(self._update_worker)

    def _show_update_banner(self, tag: str, html_url: str) -> None:
        """Display a non-intrusive info bar when a new version is available.

        Args:
            tag: The release tag, e.g. ``'v0.2.0'``.
            html_url: URL to the GitHub release page.
        """
        banner = QFrame(self.centralWidget())
        banner.setStyleSheet(
            "QFrame {"
            "  background: #e8f4fd;"
            "  border: 1px solid #b3d9f2;"
            "  border-radius: 6px;"
            "  padding: 6px 12px;"
            "}"
        )
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(8, 4, 8, 4)

        info_label = QLabel(
            f'A new version of OmniCon (<b>{tag}</b>) is available! '
            f'<a href="{html_url}">Download it here</a>.'
        )
        info_label.setOpenExternalLinks(True)
        info_label.setStyleSheet("color: #0b5394; font-size: 12px;")
        banner_layout.addWidget(info_label)

        banner_layout.addStretch()

        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.setFixedHeight(24)
        dismiss_btn.setStyleSheet(
            "QPushButton {"
            "  background: transparent;"
            "  color: #0b5394;"
            "  border: 1px solid #0b5394;"
            "  border-radius: 4px;"
            "  padding: 2px 10px;"
            "  font-size: 11px;"
            "}"
            "QPushButton:hover { background: #d0e8f7; }"
        )
        dismiss_btn.clicked.connect(banner.deleteLater)
        banner_layout.addWidget(dismiss_btn)

        # Insert at the top of the central widget's layout (index 0)
        central_layout = self.centralWidget().layout()
        central_layout.insertWidget(0, banner)
        logger.info("Update banner shown for %s", tag)

    def _build_menu_bar(self) -> None:
        """Create the application menu bar."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction("&Browse Files...", self.browse_files, "Ctrl+O")
        file_menu.addAction("&PDF Tools...", self._open_pdf_tools)
        file_menu.addSeparator()
        file_menu.addAction("&Settings...", self._open_settings, "Ctrl+,")
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close, "Ctrl+Q")

        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction("&About OmniCon", self._show_about)

    def _show_about(self) -> None:
        """Show the About dialog with author and version info."""
        QMessageBox.about(
            self,
            "About OmniCon",
            "<h2>OmniCon</h2>"
            "<p><b>Universal Desktop File Converter</b></p>"
            "<p>Version 0.1.0</p>"
            "<hr>"
            "<p>Created by <b>Chenglin Qiu (SHC - Super Han Chinese)</b></p>"
            "<p>Copyright &copy; 2026 Chenglin Qiu. All rights reserved.</p>"
            "<hr>"
            "<p>Convert anything to anything — PDF, Word, PowerPoint, "
            "Excel, images, HTML, Markdown, and more.</p>"
            '<p><a href="https://github.com/SuperHanChinese-Cheng/Omni-Con">'
            "github.com/SuperHanChinese-Cheng/Omni-Con</a></p>",
        )

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        self._drop_zone = DropZone(self)
        main_layout.addWidget(self._drop_zone)

        controls = QHBoxLayout()

        self._browse_btn = QPushButton("Browse...")
        self._browse_btn.clicked.connect(self.browse_files)
        controls.addWidget(self._browse_btn)

        self._pdf_tools_btn = QPushButton("PDF Tools")
        self._pdf_tools_btn.setToolTip("Split & Merge PDF files")
        self._pdf_tools_btn.setStyleSheet(
            "QPushButton { background: #e8e8e8; padding: 6px 14px;"
            " border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #d0d0d0; }"
        )
        self._pdf_tools_btn.clicked.connect(self._open_pdf_tools)
        controls.addWidget(self._pdf_tools_btn)

        controls.addWidget(QLabel("Convert to:"))
        self._format_combo = QComboBox()
        self._format_combo.setMinimumWidth(100)
        self._format_combo.setEnabled(False)
        controls.addWidget(self._format_combo)

        controls.addStretch()

        self._output_btn = QPushButton("Output folder...")
        self._output_btn.clicked.connect(self._pick_output_dir)
        controls.addWidget(self._output_btn)

        self._convert_btn = QPushButton("Convert")
        self._convert_btn.setEnabled(False)
        self._convert_btn.setStyleSheet(
            "QPushButton { background: #0078d4; color: white; padding: 6px 20px;"
            " border-radius: 4px; font-weight: bold; }"
            "QPushButton:disabled { background: #ccc; }"
        )
        self._convert_btn.clicked.connect(self._start_conversion)
        controls.addWidget(self._convert_btn)

        main_layout.addLayout(controls)

        # Load the default output directory from QSettings instead of
        # hardcoding ~/Desktop.
        self._output_dir = load_default_output_dir()
        self._output_label = QLabel(f"Output: {self._output_dir}")
        self._output_label.setStyleSheet("color: #666; font-size: 11px;")
        main_layout.addWidget(self._output_label)

        queue_label = QLabel("Conversion Queue")
        queue_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        main_layout.addWidget(queue_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._queue_container = QWidget()
        self._queue_layout = QVBoxLayout(self._queue_container)
        self._queue_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._queue_layout.setSpacing(2)
        scroll.setWidget(self._queue_container)
        main_layout.addWidget(scroll)

    def add_files(self, files: list[Path]) -> None:
        """Add files from drag-drop or browse dialog."""
        valid = [f for f in files if f.is_file()]
        if not valid:
            return

        self._pending_files = valid
        self._drop_zone.setText(
            f"{len(valid)} file(s) selected:\n"
            + "\n".join(f.name for f in valid[:5])
            + ("\n..." if len(valid) > 5 else "")
        )

        first_ext = valid[0].suffix.lstrip(".").lower()
        formats = _FORMAT_OPTIONS.get(first_ext, [])
        self._format_combo.clear()
        self._format_combo.addItems(formats)
        self._format_combo.setEnabled(bool(formats))
        self._convert_btn.setEnabled(bool(formats))

    def browse_files(self) -> None:
        """Open a file dialog to select input files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select files to convert",
            str(Path.home()),
            "All files (*.*)",
        )
        if files:
            self.add_files([Path(f) for f in files])

    def _pick_output_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select output folder", str(self._output_dir)
        )
        if dir_path:
            self._output_dir = Path(dir_path)
            self._output_label.setText(f"Output: {self._output_dir}")

    def _start_conversion(self) -> None:
        """Queue conversion jobs for all pending files."""
        if not self._pending_files:
            return

        output_format = self._format_combo.currentText()
        if not output_format:
            return

        self._convert_btn.setEnabled(False)

        for file_path in self._pending_files:
            job = ConversionJob(
                input_path=file_path,
                output_format=output_format,
                output_dir=self._output_dir,
            )
            widget = JobWidget(job)
            self._job_widgets.append(widget)
            self._queue_layout.addWidget(widget)

            worker = ConversionWorker(job, self._dispatcher)
            worker.signals.started.connect(self._on_job_started)
            worker.signals.finished.connect(self._on_job_finished)
            worker.signals.error.connect(self._on_job_error)
            self._active_workers.append(worker)
            self._thread_pool.start(worker)

        self._pending_files.clear()

    def _on_job_started(self, job: ConversionJob) -> None:
        for w in self._job_widgets:
            if w.job.job_id == job.job_id:
                w.update_status()
                break

    def _on_job_finished(self, job: ConversionJob) -> None:
        for w in self._job_widgets:
            if w.job.job_id == job.job_id:
                w.update_status()
                break
        self._release_worker(job)
        self._check_all_done()

    def _on_job_error(self, job: ConversionJob, error_msg: str) -> None:
        logger.error("Job %s failed: %s", job.input_path.name, error_msg)
        for w in self._job_widgets:
            if w.job.job_id == job.job_id:
                w.update_status()
                break
        self._release_worker(job)
        self._check_all_done()

    def _release_worker(self, job: ConversionJob) -> None:
        self._active_workers = [
            w for w in self._active_workers if w.job.job_id != job.job_id
        ]

    def _open_pdf_tools(self) -> None:
        """Open the PDF Split & Merge dialog."""
        dialog = PDFToolsDialog(self)
        dialog.exec()

    def _open_settings(self) -> None:
        """Open the Settings dialog and reload state on accept."""
        dialog = SettingsDialog(self)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            self._apply_settings()

    def _apply_settings(self) -> None:
        """Reload persisted settings into the running application.

        Called after the Settings dialog is accepted so that changes
        (output directory, LibreOffice path) take effect immediately.
        """
        # Refresh the default output directory
        self._output_dir = load_default_output_dir()
        self._output_label.setText(f"Output: {self._output_dir}")

        # Replace the existing OfficeEngine with one that uses the
        # (possibly changed) LibreOffice path.
        lo_path = load_libreoffice_path()
        self._registry._engines = [
            e for e in self._registry._engines if not isinstance(e, OfficeEngine)
        ]
        self._registry.register(OfficeEngine(soffice_path=lo_path))
        logger.info("Settings applied — output dir: %s, LO path: %s", self._output_dir, lo_path)

    def _check_all_done(self) -> None:
        pending = any(
            w.job.status in (JobStatus.QUEUED, JobStatus.RUNNING)
            for w in self._job_widgets
        )
        if not pending:
            self._convert_btn.setEnabled(True)
