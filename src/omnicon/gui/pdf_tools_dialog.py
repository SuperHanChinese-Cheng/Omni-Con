# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""PDF Tools dialog — split and merge PDF files."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
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


class _SplitTab(QWidget):
    """Tab for splitting a PDF by page ranges."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._input_path: Path | None = None
        self._output_dir: Path = Path.home() / "Desktop"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Source file ---
        src_group = QGroupBox("Source PDF")
        src_layout = QHBoxLayout(src_group)

        self._file_label = QLabel("No file selected")
        self._file_label.setStyleSheet("color: #666;")
        self._file_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        src_layout.addWidget(self._file_label)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_source)
        src_layout.addWidget(browse_btn)

        layout.addWidget(src_group)

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
        self._split_btn.setStyleSheet(
            "QPushButton { background: #0078d4; color: white; font-size: 14px;"
            " font-weight: bold; border-radius: 4px; padding: 6px 24px; }"
            "QPushButton:disabled { background: #ccc; }"
            "QPushButton:hover:!disabled { background: #106ebe; }"
        )
        self._split_btn.clicked.connect(self._do_split)
        layout.addWidget(self._split_btn)

        layout.addStretch()

    def _browse_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF to split",
            str(Path.home()),
            "PDF files (*.pdf)",
        )
        if path:
            self._input_path = Path(path)
            self._file_label.setText(self._input_path.name)
            self._file_label.setStyleSheet("color: #000;")
            try:
                count = get_pdf_page_count(self._input_path)
                self._page_info.setText(f"Pages: {count}")
                self._range_input.setPlaceholderText(f"e.g. 1-{count}")
            except PDFToolsError:
                self._page_info.setText("Could not read page count.")
            self._split_btn.setEnabled(True)

    def _pick_output_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select output folder", str(self._output_dir)
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
                self,
                "Split Complete",
                f"Created {len(results)} file(s):\n{names}",
            )
        except PDFToolsError as exc:
            QMessageBox.critical(self, "Split Failed", str(exc))
        except Exception as exc:
            logger.error("Unexpected split error: %s", exc, exc_info=True)
            QMessageBox.critical(self, "Error", f"Unexpected error: {exc}")


class _MergeTab(QWidget):
    """Tab for merging multiple PDFs into one."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._output_dir: Path = Path.home() / "Desktop"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- File list ---
        list_group = QGroupBox("PDF Files to Merge (top → bottom order)")
        list_layout = QVBoxLayout(list_group)

        self._file_list = QListWidget()
        self._file_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._file_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._file_list.setMinimumHeight(150)
        list_layout.addWidget(self._file_list)

        btn_row = QHBoxLayout()

        add_btn = QPushButton("Add Files...")
        add_btn.clicked.connect(self._add_files)
        btn_row.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(remove_btn)

        move_up_btn = QPushButton("Move Up")
        move_up_btn.clicked.connect(self._move_up)
        btn_row.addWidget(move_up_btn)

        move_down_btn = QPushButton("Move Down")
        move_down_btn.clicked.connect(self._move_down)
        btn_row.addWidget(move_down_btn)

        btn_row.addStretch()

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._file_list.clear)
        btn_row.addWidget(clear_btn)

        list_layout.addLayout(btn_row)
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
        self._merge_btn.setStyleSheet(
            "QPushButton { background: #0078d4; color: white; font-size: 14px;"
            " font-weight: bold; border-radius: 4px; padding: 6px 24px; }"
            "QPushButton:hover { background: #106ebe; }"
        )
        self._merge_btn.clicked.connect(self._do_merge)
        layout.addWidget(self._merge_btn)

        layout.addStretch()

    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PDF files to merge",
            str(Path.home()),
            "PDF files (*.pdf)",
        )
        for f in files:
            path = Path(f)
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            try:
                count = get_pdf_page_count(path)
                item.setText(f"{path.name}  ({count} pages)")
            except PDFToolsError:
                pass
            self._file_list.addItem(item)

    def _remove_selected(self) -> None:
        for item in self._file_list.selectedItems():
            row = self._file_list.row(item)
            self._file_list.takeItem(row)

    def _move_up(self) -> None:
        current = self._file_list.currentRow()
        if current > 0:
            item = self._file_list.takeItem(current)
            self._file_list.insertItem(current - 1, item)
            self._file_list.setCurrentRow(current - 1)

    def _move_down(self) -> None:
        current = self._file_list.currentRow()
        if current < self._file_list.count() - 1:
            item = self._file_list.takeItem(current)
            self._file_list.insertItem(current + 1, item)
            self._file_list.setCurrentRow(current + 1)

    def _pick_output_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select output folder", str(self._output_dir)
        )
        if dir_path:
            self._output_dir = Path(dir_path)
            self._out_label.setText(f"Output: {self._output_dir}")

    def _do_merge(self) -> None:
        count = self._file_list.count()
        if count < 2:
            QMessageBox.warning(
                self, "Not Enough Files", "Add at least 2 PDF files to merge."
            )
            return

        paths: list[Path] = []
        for i in range(count):
            item = self._file_list.item(i)
            raw = item.data(Qt.ItemDataRole.UserRole)
            if raw:
                paths.append(Path(raw))

        if len(paths) < 2:
            QMessageBox.warning(self, "Error", "Could not resolve file paths.")
            return

        filename = self._name_input.text().strip() or "merged.pdf"
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        output_path = self._output_dir / filename

        try:
            result = merge_pdfs(paths, output_path)
            QMessageBox.information(
                self,
                "Merge Complete",
                f"Merged {len(paths)} files into:\n{result.name}",
            )
        except PDFToolsError as exc:
            QMessageBox.critical(self, "Merge Failed", str(exc))
        except Exception as exc:
            logger.error("Unexpected merge error: %s", exc, exc_info=True)
            QMessageBox.critical(self, "Error", f"Unexpected error: {exc}")


class PDFToolsDialog(QDialog):
    """Dialog with tabs for PDF Split and Merge operations."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PDF Tools — Split & Merge")
        self.setMinimumSize(550, 480)
        self.resize(600, 520)

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(_SplitTab(), "Split PDF")
        tabs.addTab(_MergeTab(), "Merge PDFs")
        layout.addWidget(tabs)
