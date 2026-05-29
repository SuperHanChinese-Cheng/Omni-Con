"""Main application window with drag-drop zone and conversion queue."""

import logging
from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
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
from omnicon.engines.text_engine import TextEngine
from omnicon.gui.pdf_tools_dialog import PDFToolsDialog

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
        self.setWindowTitle("OmniCon — Universal File Converter")
        self.setMinimumSize(600, 500)
        self.resize(700, 550)

        self._registry = EngineRegistry()
        self._registry.register(PDFEngine())
        self._registry.register(ImageEngine())
        self._registry.register(TextEngine())
        self._registry.register(HTMLEngine())
        self._registry.register(PandocEngine())
        self._registry.register(OfficeEngine())
        self._dispatcher = ConversionDispatcher(self._registry)
        self._thread_pool = QThreadPool.globalInstance()

        self._pending_files: list[Path] = []
        self._job_widgets: list[JobWidget] = []
        self._active_workers: list[ConversionWorker] = []

        self._build_ui()

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

        self._output_dir = Path.home() / "Desktop"
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

    def _check_all_done(self) -> None:
        pending = any(
            w.job.status in (JobStatus.QUEUED, JobStatus.RUNNING)
            for w in self._job_widgets
        )
        if not pending:
            self._convert_btn.setEnabled(True)
