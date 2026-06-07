# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""PDF Tools dialog — Split, Merge, and Split & Merge with drag-and-drop."""

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
from omnicon.gui import theme

logger = logging.getLogger(__name__)


def _accept_pdf_drop(event: QDragEnterEvent) -> bool:
    """Check if a drag event contains at least one PDF file."""
    if event.mimeData().hasUrls():
        for url in event.mimeData().urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
                return True
    return False


def _get_pdf_paths_from_drop(event: QDropEvent) -> list[Path]:
    """Extract PDF file paths from a drop event."""
    paths: list[Path] = []
    for url in event.mimeData().urls():
        if url.isLocalFile() and url.toLocalFile().lower().endswith(".pdf"):
            paths.append(Path(url.toLocalFile()))
    return paths


# ===================================================================
# Tab 1: Split
# ===================================================================
class _SplitTab(QWidget):
    """Split a single PDF into multiple files by page ranges."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._input_path: Path | None = None
        self._output_dir: Path = Path.home() / "Desktop"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Drop zone ---
        self._drop_label = QLabel("Drop a PDF here or click Browse")
        self._drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_label.setMinimumHeight(70)
        self._drop_label.setStyleSheet(theme.drop_zone_idle())
        layout.addWidget(self._drop_label)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_source)
        layout.addWidget(browse_btn)

        self._page_info = QLabel("")
        self._page_info.setStyleSheet(theme.label_accent())
        layout.addWidget(self._page_info)

        # --- Page range ---
        range_group = QGroupBox("Page Ranges")
        range_layout = QVBoxLayout(range_group)
        range_help = QLabel(
            "Enter page ranges separated by commas.\n"
            "Examples:  1-3, 5, 7-10  |  1-5  |  3  |  1,3,5-8\n"
            "Each range creates a separate PDF file."
        )
        range_help.setStyleSheet(theme.label_hint())
        range_layout.addWidget(range_help)

        self._range_input = QLineEdit()
        self._range_input.setPlaceholderText("e.g. 1-3, 5, 7-10")
        self._range_input.setMinimumHeight(32)
        self._range_input.setStyleSheet("font-size: 14px; padding: 4px 8px;")
        range_layout.addWidget(self._range_input)
        layout.addWidget(range_group)

        # --- Output ---
        out_row = QHBoxLayout()
        self._out_label = QLabel(f"Output: {self._output_dir}")
        self._out_label.setStyleSheet(theme.label_muted())
        out_row.addWidget(self._out_label)
        out_btn = QPushButton("Output folder...")
        out_btn.clicked.connect(self._pick_output_dir)
        out_row.addWidget(out_btn)
        layout.addLayout(out_row)

        self._split_btn = QPushButton("Split PDF")
        self._split_btn.setEnabled(False)
        self._split_btn.setMinimumHeight(38)
        self._split_btn.setStyleSheet(theme.btn_primary())
        self._split_btn.clicked.connect(self._do_split)
        layout.addWidget(self._split_btn)
        layout.addStretch()

    # -- Drag-and-drop --
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if _accept_pdf_drop(event):
            event.acceptProposedAction()
            self._drop_label.setStyleSheet(theme.drop_zone_hover())

    def dragLeaveEvent(self, event: object) -> None:
        if self._input_path:
            self._drop_label.setStyleSheet(theme.drop_zone_loaded())
        else:
            self._drop_label.setStyleSheet(theme.drop_zone_idle())

    def dropEvent(self, event: QDropEvent) -> None:
        paths = _get_pdf_paths_from_drop(event)
        if paths:
            self._set_source(paths[0])

    # -- Logic --
    def _set_source(self, path: Path) -> None:
        self._input_path = path
        self._drop_label.setText(f"Selected: {path.name}")
        self._drop_label.setStyleSheet(theme.drop_zone_loaded())
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
        d = QFileDialog.getExistingDirectory(self, "Select output folder", str(self._output_dir))
        if d:
            self._output_dir = Path(d)
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
# Tab 2: Merge (simple — all pages, just combine)
# ===================================================================
class _MergeTab(QWidget):
    """Quick merge — combine entire PDFs together in order."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._pdf_paths: list[Path] = []
        self._output_dir: Path = Path.home() / "Desktop"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Drop zone ---
        self._drop_label = QLabel("Drop PDF files here or click Add Files\nAll pages will be merged in order")
        self._drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_label.setMinimumHeight(70)
        self._drop_label.setStyleSheet(theme.drop_zone_idle())
        layout.addWidget(self._drop_label)

        # --- File list (simple text list) ---
        list_group = QGroupBox("PDFs to Merge (top → bottom)")
        list_outer = QVBoxLayout(list_group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(120)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(2)
        scroll.setWidget(self._list_container)
        list_outer.addWidget(scroll)

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
        self._out_label.setStyleSheet(theme.label_muted())
        out_row.addWidget(self._out_label)
        out_btn = QPushButton("Output folder...")
        out_btn.clicked.connect(self._pick_output_dir)
        out_row.addWidget(out_btn)
        layout.addLayout(out_row)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Output filename:"))
        self._name_input = QLineEdit("merged.pdf")
        self._name_input.setPlaceholderText("merged.pdf")
        name_row.addWidget(self._name_input)
        layout.addLayout(name_row)

        self._merge_btn = QPushButton("Merge All")
        self._merge_btn.setMinimumHeight(38)
        self._merge_btn.setStyleSheet(theme.btn_primary())
        self._merge_btn.clicked.connect(self._do_merge)
        layout.addWidget(self._merge_btn)
        layout.addStretch()

    # -- Drag-and-drop --
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if _accept_pdf_drop(event):
            event.acceptProposedAction()
            self._drop_label.setStyleSheet(theme.drop_zone_hover())

    def dragLeaveEvent(self, event: object) -> None:
        self._drop_label.setStyleSheet(theme.drop_zone_idle())

    def dropEvent(self, event: QDropEvent) -> None:
        self._drop_label.setStyleSheet(theme.drop_zone_idle())
        for path in _get_pdf_paths_from_drop(event):
            self._add_pdf(path)

    # -- Logic --
    def _add_pdf(self, path: Path) -> None:
        self._pdf_paths.append(path)
        try:
            count = get_pdf_page_count(path)
            label_text = f"{path.name}  ({count} pages)"
        except PDFToolsError:
            label_text = path.name

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(4, 2, 4, 2)
        row_layout.addWidget(QLabel(label_text))
        row_layout.addStretch()

        remove_btn = QPushButton("X")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setStyleSheet(theme.btn_remove())
        idx = len(self._pdf_paths) - 1
        remove_btn.clicked.connect(lambda checked, r=row, i=idx: self._remove(r, i))
        row_layout.addWidget(remove_btn)

        self._list_layout.addWidget(row)

    def _remove(self, row: QWidget, idx: int) -> None:
        if 0 <= idx < len(self._pdf_paths):
            self._pdf_paths[idx] = None  # type: ignore[assignment]
        row.setParent(None)
        row.deleteLater()

    def _browse_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PDF files", str(Path.home()), "PDF files (*.pdf)",
        )
        for f in files:
            self._add_pdf(Path(f))

    def _clear_all(self) -> None:
        self._pdf_paths.clear()
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _pick_output_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select output folder", str(self._output_dir))
        if d:
            self._output_dir = Path(d)
            self._out_label.setText(f"Output: {self._output_dir}")

    def _do_merge(self) -> None:
        valid = [p for p in self._pdf_paths if p is not None]
        if len(valid) < 2:
            QMessageBox.warning(self, "Not Enough Files", "Add at least 2 PDF files to merge.")
            return

        filename = self._name_input.text().strip() or "merged.pdf"
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        entries: list[tuple[Path, str | None]] = [(p, None) for p in valid]

        try:
            result = merge_pdfs(entries, self._output_dir / filename)
            QMessageBox.information(
                self, "Merge Complete", f"Merged {len(valid)} files into:\n{result.name}",
            )
        except PDFToolsError as exc:
            QMessageBox.critical(self, "Merge Failed", str(exc))
        except Exception as exc:
            logger.error("Unexpected merge error: %s", exc, exc_info=True)
            QMessageBox.critical(self, "Error", f"Unexpected error: {exc}")


# ===================================================================
# Tab 3: Split & Merge (cherry-pick pages from multiple PDFs)
# ===================================================================
class _SplitMergeFileRow(QWidget):
    """One PDF entry in the Split & Merge list with page selection."""

    def __init__(self, pdf_path: Path, page_count: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.page_count = page_count

        row = QHBoxLayout(self)
        row.setContentsMargins(6, 4, 6, 4)

        # File info
        info = QLabel(f"<b>{pdf_path.name}</b> — {page_count} pages")
        info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(info)

        # Page range input
        row.addWidget(QLabel("Pages:"))
        self._range_input = QLineEdit()
        self._range_input.setPlaceholderText(f"All (1-{page_count})")
        self._range_input.setFixedWidth(140)
        self._range_input.setToolTip(
            f"Leave empty for all {page_count} pages.\n"
            f"Or enter ranges: 1-3, 5, 7-{page_count}"
        )
        row.addWidget(self._range_input)

        # Remove
        remove_btn = QPushButton("X")
        remove_btn.setFixedSize(28, 28)
        remove_btn.setStyleSheet(theme.btn_remove())
        remove_btn.clicked.connect(self._remove_self)
        row.addWidget(remove_btn)

        self.setStyleSheet(theme.file_row())

    @property
    def page_range(self) -> str | None:
        text = self._range_input.text().strip()
        return text if text else None

    def _remove_self(self) -> None:
        self.setParent(None)
        self.deleteLater()


class _SplitMergeTab(QWidget):
    """Cherry-pick pages from multiple PDFs and merge them into one."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._output_dir: Path = Path.home() / "Desktop"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Instructions ---
        hint = QLabel(
            "Drop multiple PDFs below, then choose which pages from each.\n"
            "Selected pages are combined into one output PDF."
        )
        hint.setStyleSheet(theme.label_hint())
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # --- Drop zone ---
        self._drop_label = QLabel("Drop PDFs here or click Add Files")
        self._drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_label.setMinimumHeight(55)
        self._drop_label.setStyleSheet(theme.drop_zone_idle())
        layout.addWidget(self._drop_label)

        # --- File rows (scrollable) ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(180)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(4)
        scroll.setWidget(self._list_container)
        layout.addWidget(scroll)

        # --- Buttons ---
        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Files...")
        add_btn.clicked.connect(self._browse_files)
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_all)
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

        # --- Output ---
        out_row = QHBoxLayout()
        self._out_label = QLabel(f"Output: {self._output_dir}")
        self._out_label.setStyleSheet(theme.label_muted())
        out_row.addWidget(self._out_label)
        out_btn = QPushButton("Output folder...")
        out_btn.clicked.connect(self._pick_output_dir)
        out_row.addWidget(out_btn)
        layout.addLayout(out_row)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Output filename:"))
        self._name_input = QLineEdit("combined.pdf")
        self._name_input.setPlaceholderText("combined.pdf")
        name_row.addWidget(self._name_input)
        layout.addLayout(name_row)

        # --- Build button ---
        self._build_btn = QPushButton("Build PDF")
        self._build_btn.setMinimumHeight(40)
        self._build_btn.setStyleSheet(theme.btn_build())
        self._build_btn.clicked.connect(self._do_build)
        layout.addWidget(self._build_btn)

    # -- Drag-and-drop --
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if _accept_pdf_drop(event):
            event.acceptProposedAction()
            self._drop_label.setStyleSheet(theme.drop_zone_hover())

    def dragLeaveEvent(self, event: object) -> None:
        self._drop_label.setStyleSheet(theme.drop_zone_idle())

    def dropEvent(self, event: QDropEvent) -> None:
        self._drop_label.setStyleSheet(theme.drop_zone_idle())
        for path in _get_pdf_paths_from_drop(event):
            self._add_pdf(path)

    # -- Logic --
    def _add_pdf(self, path: Path) -> None:
        try:
            count = get_pdf_page_count(path)
        except PDFToolsError:
            count = 0
        row = _SplitMergeFileRow(path, count)
        self._list_layout.addWidget(row)

    def _get_rows(self) -> list[_SplitMergeFileRow]:
        rows: list[_SplitMergeFileRow] = []
        for i in range(self._list_layout.count()):
            w = self._list_layout.itemAt(i).widget()
            if isinstance(w, _SplitMergeFileRow):
                rows.append(w)
        return rows

    def _browse_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select PDF files", str(Path.home()), "PDF files (*.pdf)",
        )
        for f in files:
            self._add_pdf(Path(f))

    def _clear_all(self) -> None:
        for row in self._get_rows():
            row.setParent(None)
            row.deleteLater()

    def _pick_output_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select output folder", str(self._output_dir))
        if d:
            self._output_dir = Path(d)
            self._out_label.setText(f"Output: {self._output_dir}")

    def _do_build(self) -> None:
        rows = self._get_rows()
        if not rows:
            QMessageBox.warning(self, "No Files", "Add at least one PDF file.")
            return

        entries: list[tuple[Path, str | None]] = [
            (row.pdf_path, row.page_range) for row in rows
        ]

        # Allow single file with page selection (extract specific pages)
        if len(entries) == 1 and entries[0][1] is None:
            QMessageBox.warning(
                self, "Nothing to do",
                "You added one PDF with all pages selected.\n"
                "Either add more PDFs, or specify a page range.",
            )
            return

        filename = self._name_input.text().strip() or "combined.pdf"
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        # For single-file extraction, we still use merge_pdfs but need at
        # least 2 entries — use split_pdf instead for single files.
        if len(entries) == 1:
            path, range_str = entries[0]
            try:
                results = split_pdf(path, range_str or "", self._output_dir)
                QMessageBox.information(
                    self, "Done",
                    f"Extracted pages into:\n{results[0].name}",
                )
            except PDFToolsError as exc:
                QMessageBox.critical(self, "Failed", str(exc))
            return

        try:
            result = merge_pdfs(entries, self._output_dir / filename)
            # Summarize what was included
            summary_parts: list[str] = []
            for row in rows:
                pages = row.page_range or "all pages"
                summary_parts.append(f"  {row.pdf_path.name}: {pages}")
            summary = "\n".join(summary_parts)

            QMessageBox.information(
                self, "Build Complete",
                f"Created {result.name}\n\nSources:\n{summary}",
            )
        except PDFToolsError as exc:
            QMessageBox.critical(self, "Build Failed", str(exc))
        except Exception as exc:
            logger.error("Unexpected build error: %s", exc, exc_info=True)
            QMessageBox.critical(self, "Error", f"Unexpected error: {exc}")


# ===================================================================
# Main Dialog
# ===================================================================
class PDFToolsDialog(QDialog):
    """Dialog with tabs for Split, Merge, and Split & Merge."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PDF Tools — Split, Merge & Combine")
        self.setMinimumSize(650, 560)
        self.resize(720, 620)

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(_SplitTab(), "Split")
        tabs.addTab(_MergeTab(), "Merge")
        tabs.addTab(_SplitMergeTab(), "Split && Merge")
        layout.addWidget(tabs)
