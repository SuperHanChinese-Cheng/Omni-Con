# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""PDF Tools dialog — split and merge PDF files with drag-and-drop support."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from omnicon.core.pdf_tools import (
    PDFToolsError,
    get_pdf_page_count,
    merge_pdfs,
    split_pdf,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared styles
# ---------------------------------------------------------------------------
_BTN_PRIMARY = (
    "QPushButton { background: #0078d4; color: white; font-size: 14px;"
    " font-weight: bold; border-radius: 4px; padding: 6px 24px; }"
    "QPushButton:disabled { background: #ccc; }"
    "QPushButton:hover:!disabled { background: #106ebe; }"
)

_DROP_IDLE = (
    "QLabel {"
    "  border: 2px dashed #888; border-radius: 8px;"
    "  background: #f8f8f8; color: #888; font-size: 13px; padding: 16px;"
    "}"
)

_DROP_HOVER = (
    "QLabel {"
    "  border: 2px dashed #0078d4; border-radius: 8px;"
    "  background: #e8f0fe; color: #0078d4; font-size: 13px; padding: 16px;"
    "}"
)


# ===================================================================
# Split Tab
# ===================================================================
class _SplitTab(QWidget):
    """Tab for splitting a PDF by page ranges. Supports drag-and-drop."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._input_path: Path | None = None
        self._output_dir: Path = Path.home() / "Desktop"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Drop zone / source file ---
        self._drop_label = QLabel("Drop a PDF here or click Browse")
        self._drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_label.setMinimumHeight(70)
        self._drop_label.setStyleSheet(_DROP_IDLE)
        layout.addWidget(self._drop_label)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_source)
        layout.addWidget(browse_btn)

        # --- Page info ---
        self._page_info = QLabel("")
        self._page_info.setStyleSheet("color: #0078d4; font-size: 12px;")
        layout.addWidget(self._page_info)

        # --- Page range input ---
        range_group = QGroupBox("Page Ranges")
        range_layout = QVBoxLayout(range_group)

        range_help = QLabel(
            "Enter page ranges separated by commas.\n"
            "Examples:  1-3, 5, 7-10  |  1-5  |  3  |  1,3,5-8\n"
            "Each range creates a separate PDF file."
        )
        range_help.setStyleSheet("color: #888; font-size: 11px;")
        range_layout.addWidget(range_help)

        self._range_input = QLineEdit()
        self._range_input.setPlaceholderText("e.g. 1-3, 5, 7-10")
        self._range_input.setMinimumHeight(32)
        self._range_input.setStyleSheet("font-size: 14px; padding: 4px 8px;")
        range_layout.addWidget(self._range_input)

        layout.addWidget(range_group)

        # --- Output directory ---
        out_row = QHBoxLayout()
        self._out_label = QLabel(f"Output: {self._output_dir}")
        self._out_label.setStyleSheet("color: #666; font-size: 11px;")
        out_row.addWidget(self._out_label)

        out_btn = QPushButton("Output folder...")
        out_btn.clicked.connect(self._pick_output_dir)
        out_row.addWidget(out_btn)
        layout.addLayout(out_row)

        # --- Split button ---
        self._split_btn = QPushButton("Split PDF")
        self._split_btn.setEnabled(False)
        self._split_btn.setMinimumHeight(38)
        self._split_btn.setStyleSheet(_BTN_PRIMARY)
        self._split_btn.clicked.connect(self._do_split)
        layout.addWidget(self._split_btn)

        layout.addStretch()

    # -- Drag-and-drop -------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    self._drop_label.setStyleSheet(_DROP_HOVER)
                    return

    def dragLeaveEvent(self, event: object) -> None:
        self._drop_label.setStyleSheet(_DROP_IDLE)

    def dropEvent(self, event: QDropEvent) -> None:
        self._drop_label.setStyleSheet(_DROP_IDLE)
        for url in event.mimeData().urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
                self._set_source(Path(url.toLocalFile()))
                return

    # -- Helpers -------------------------------------------------------------

    def _set_source(self, path: Path) -> None:
        """Load a PDF as the split source."""
        self._input_path = path
        self._drop_label.setText(f"Selected: {path.name}")
        self._drop_label.setStyleSheet(
            "QLabel { border: 2px solid #107c10; border-radius: 8px;"
            " background: #f0fff0; color: #107c10; font-size: 13px; padding: 16px; }"
        )
        try:
            count = get_pdf_page_count(path)
            self._page_info.setText(f"Pages: {count}")
            self._range_input.setPlaceholderText(f"e.g. 1-{count}")
        except PDFToolsError:
            self._page_info.setText("Could not read page count.")
        self._split_btn.setEnabled(True)

    def _browse_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF to split", str(Path.home()), "PDF files (*.pdf)",
        )
        if path:
            self._set_source(Path(path))

    def _pick_output_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select output folder", str(self._output_dir),
        )
        if dir_path:
            self._output_dir = Path(dir_path)
            self._out_label.setText(f"Output: {self._output_dir}")

    def _do_split(self) -> None:
        if not self._input_path:
            return
        range_str = self._range_input.text().strip()
        if not range_str:
            QMessageBox.warning(self, "No Range", "Please enter a page range to split.")
            return
        try:
            results = split_pdf(self._input_path, range_str, self._output_dir)
            names = "\n".join(f"  - {p.name}" for p in results)
            QMessageBox.information(
                self, "Split Complete", f"Created {len(results)} file(s):\n{names}",
            )
        except PDFToolsError as exc:
            QMessageBox.critical(self, "Split Failed", str(exc))
        except Exception as exc:
            logger.error("Unexpected split error: %s", exc, exc_info=True)
            QMessageBox.critical(self, "Error", f"Unexpected error: {exc}")


# ===================================================================
# Merge file entry widget (one row per PDF)
# ===================================================================
class _MergeFileRow(QWidget):
    """A single row in the merge list: filename, page count, page range input."""

    def __init__(
        self, pdf_path: Path, page_count: int, parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.page_count = page_count

        row = QHBoxLayout(self)
        row.setContentsMargins(4, 2, 4, 2)

        # File name + page count
        self._name_label = QLabel(f"{pdf_path.name}  ({page_count} pages)")
        self._name_label.setMinimumWidth(200)
        self._name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(self._name_label)

        # Page range input
        row.addWidget(QLabel("Pages:"))
        self._range_input = QLineEdit()
        self._range_input.setPlaceholderText(f"All (1-{page_count})")
        self._range_input.setFixedWidth(130)
        self._range_input.setToolTip(
            f"Leave empty for all pages, or enter ranges like 1-3, 5, 7-{page_count}"
        )
        row.addWidget(self._range_input)

        # Remove button
        remove_btn = QPushButton("X")
        remove_btn.setFixedSize(28, 28)
        remove_btn.setStyleSheet(
            "QPushButton { background: #d13438; color: white; font-weight: bold;"
            " border-radius: 4px; } QPushButton:hover { background: #a4262c; }"
        )
        remove_btn.clicked.connect(self._remove_self)
        row.addWidget(remove_btn)

    @property
    def page_range(self) -> str | None:
        """Return the user-entered page range, or None for all pages."""
        text = self._range_input.text().strip()
        return text if text else None

    def _remove_self(self) -> None:
        """Remove this row from its parent layout."""
        self.setParent(None)
        self.deleteLater()


# ===================================================================
# Merge Tab
# ===================================================================
class _MergeTab(QWidget):
    """Tab for merging multiple PDFs with per-file page selection. Supports drag-and-drop."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._output_dir: Path = Path.home() / "Desktop"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Drop zone ---
        self._drop_label = QLabel("Drop PDF files here or click Add Files")
        self._drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_label.setMinimumHeight(60)
        self._drop_label.setStyleSheet(_DROP_IDLE)
        layout.addWidget(self._drop_label)

        # --- File list (scrollable) ---
        list_group = QGroupBox("PDFs to Merge (top → bottom order)")
        list_outer = QVBoxLayout(list_group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(160)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(2)
        scroll.setWidget(self._list_container)
        list_outer.addWidget(scroll)

        # Buttons
        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Files...")
        add_btn.clicked.connect(self._browse_files)
        btn_row.addWidget(add_btn)

        btn_row.addStretch()

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_all)
        btn_row.addWidget(clear_btn)

        list_outer.addLayout(btn_row)
        layout.addWidget(list_group)

        # --- Output ---
        out_row = QHBoxLayout()
        self._out_label = QLabel(f"Output: {self._output_dir}")
        self._out_label.setStyleSheet("color: #666; font-size: 11px;")
        out_row.addWidget(self._out_label)

        out_btn = QPushButton("Output folder...")
        out_btn.clicked.connect(self._pick_output_dir)
        out_row.addWidget(out_btn)
        layout.addLayout(out_row)

        # --- Output filename ---
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Output filename:"))
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("merged.pdf")
        self._name_input.setText("merged.pdf")
        name_row.addWidget(self._name_input)
        layout.addLayout(name_row)

        # --- Merge button ---
        self._merge_btn = QPushButton("Merge PDFs")
        self._merge_btn.setMinimumHeight(38)
        self._merge_btn.setStyleSheet(_BTN_PRIMARY)
        self._merge_btn.clicked.connect(self._do_merge)
        layout.addWidget(self._merge_btn)

        layout.addStretch()

    # -- Drag-and-drop -------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    self._drop_label.setStyleSheet(_DROP_HOVER)
                    return

    def dragLeaveEvent(self, event: object) -> None:
        self._drop_label.setStyleSheet(_DROP_IDLE)

    def dropEvent(self, event: QDropEvent) -> None:
        self._drop_label.setStyleSheet(_DROP_IDLE)
        for url in event.mimeData().urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
                self._add_pdf(Path(url.toLocalFile()))

    # -- Helpers -------------------------------------------------------------

    def _add_pdf(self, path: Path) -> None:
        """Add a PDF file row to the merge list."""
        try:
            count = get_pdf_page_count(path)
        except PDFToolsError:
            count = 0
        row = _MergeFileRow(path, count)
        self._list_layout.addWidget(row)

    def _get_rows(self) -> list[_MergeFileRow]:
        """Return all current merge file rows in order."""
        rows: list[_MergeFileRow] = []
        for i in range(self._list_layout.count()):
            widget = self._list_layout.itemAt(i).widget()
            if isinstance(widget, _MergeFileRow):
                rows.append(widget)
        return rows

    def _browse_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PDF files to merge", str(Path.home()), "PDF files (*.pdf)",
        )
        for f in files:
            self._add_pdf(Path(f))

    def _clear_all(self) -> None:
        for row in self._get_rows():
            row.setParent(None)
            row.deleteLater()

    def _pick_output_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select output folder", str(self._output_dir),
        )
        if dir_path:
            self._output_dir = Path(dir_path)
            self._out_label.setText(f"Output: {self._output_dir}")

    def _do_merge(self) -> None:
        rows = self._get_rows()
        if len(rows) < 2:
            QMessageBox.warning(
                self, "Not Enough Files", "Add at least 2 PDF files to merge.",
            )
            return

        entries: list[tuple[Path, str | None]] = [
            (row.pdf_path, row.page_range) for row in rows
        ]

        filename = self._name_input.text().strip() or "merged.pdf"
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        output_path = self._output_dir / filename

        try:
            result = merge_pdfs(entries, output_path)
            QMessageBox.information(
                self, "Merge Complete",
                f"Merged {len(entries)} files into:\n{result.name}",
            )
        except PDFToolsError as exc:
            QMessageBox.critical(self, "Merge Failed", str(exc))
        except Exception as exc:
            logger.error("Unexpected merge error: %s", exc, exc_info=True)
            QMessageBox.critical(self, "Error", f"Unexpected error: {exc}")


# ===================================================================
# Main Dialog
# ===================================================================
class PDFToolsDialog(QDialog):
    """Dialog with tabs for PDF Split and Merge operations."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PDF Tools — Split & Merge")
        self.setMinimumSize(600, 520)
        self.resize(680, 580)

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(_SplitTab(), "Split PDF")
        tabs.addTab(_MergeTab(), "Merge PDFs")
        layout.addWidget(tabs)
