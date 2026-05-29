# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""PDF split and merge operations using PyMuPDF."""

import logging
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFToolsError(Exception):
    """Raised when a PDF split or merge operation fails."""


def parse_page_ranges(range_str: str, total_pages: int) -> list[tuple[int, int]]:
    """Parse a human-friendly page range string into (start, end) tuples (0-indexed).

    Supports formats like: "1-3, 5, 7-10", "1-3", "5", "1,3,5-8".
    Page numbers are 1-based in the input and converted to 0-based internally.

    Args:
        range_str: Comma-separated page ranges (e.g., "1-3, 5, 7-10").
        total_pages: Total number of pages in the PDF (for validation).

    Returns:
        List of (start, end) tuples, 0-indexed, inclusive on both ends.

    Raises:
        PDFToolsError: If the range string is invalid or out of bounds.
    """
    if not range_str.strip():
        raise PDFToolsError("Page range cannot be empty.")

    ranges: list[tuple[int, int]] = []

    for part in range_str.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            pieces = part.split("-", maxsplit=1)
            try:
                start = int(pieces[0].strip())
                end = int(pieces[1].strip())
            except ValueError as exc:
                raise PDFToolsError(f"Invalid page range: '{part}'") from exc

            if start < 1 or end < 1:
                raise PDFToolsError(f"Page numbers must be >= 1, got: '{part}'")
            if start > total_pages or end > total_pages:
                raise PDFToolsError(
                    f"Page range '{part}' exceeds document length ({total_pages} pages)."
                )
            if start > end:
                raise PDFToolsError(f"Invalid range: start ({start}) > end ({end}).")

            # Convert to 0-indexed
            ranges.append((start - 1, end - 1))
        else:
            try:
                page = int(part)
            except ValueError as exc:
                raise PDFToolsError(f"Invalid page number: '{part}'") from exc

            if page < 1 or page > total_pages:
                raise PDFToolsError(
                    f"Page {page} out of range (document has {total_pages} pages)."
                )
            ranges.append((page - 1, page - 1))

    if not ranges:
        raise PDFToolsError("No valid page ranges found.")

    return ranges


def get_pdf_page_count(pdf_path: Path) -> int:
    """Return the number of pages in a PDF file.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Number of pages.

    Raises:
        PDFToolsError: If the file cannot be opened.
    """
    try:
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count
    except Exception as exc:
        raise PDFToolsError(f"Cannot open PDF: {exc}") from exc


def split_pdf(
    input_path: Path,
    range_str: str,
    output_dir: Path,
) -> list[Path]:
    """Split a PDF into one or more files based on page ranges.

    Each comma-separated range produces a separate output file.
    For example, "1-3, 5, 7-10" creates three files:
      - pages 1-3
      - page 5
      - pages 7-10

    Args:
        input_path: Path to the source PDF.
        range_str: Comma-separated page ranges (1-based, e.g., "1-3, 5, 7-10").
        output_dir: Directory where split files will be saved.

    Returns:
        List of paths to the created PDF files.

    Raises:
        PDFToolsError: If the operation fails.
    """
    try:
        doc = fitz.open(input_path)
    except Exception as exc:
        raise PDFToolsError(f"Cannot open PDF: {exc}") from exc

    try:
        total_pages = len(doc)
        ranges = parse_page_ranges(range_str, total_pages)
        output_paths: list[Path] = []

        for idx, (start, end) in enumerate(ranges, start=1):
            out_doc = fitz.open()  # New empty PDF
            try:
                out_doc.insert_pdf(doc, from_page=start, to_page=end)

                # Build filename
                if start == end:
                    label = f"page_{start + 1}"
                else:
                    label = f"pages_{start + 1}-{end + 1}"

                out_name = f"{input_path.stem}_{label}.pdf"
                out_path = output_dir / out_name

                # Avoid overwriting: add a suffix if file exists
                counter = 1
                while out_path.exists():
                    out_name = f"{input_path.stem}_{label}_{counter}.pdf"
                    out_path = output_dir / out_name
                    counter += 1

                out_doc.save(str(out_path))
                output_paths.append(out_path)
                logger.info(
                    "Split %s: pages %d-%d → %s",
                    input_path.name,
                    start + 1,
                    end + 1,
                    out_path.name,
                )
            finally:
                out_doc.close()

        return output_paths
    finally:
        doc.close()


def merge_pdfs(input_paths: list[Path], output_path: Path) -> Path:
    """Merge multiple PDF files into a single PDF.

    Args:
        input_paths: Ordered list of PDF files to merge.
        output_path: Path for the merged output PDF.

    Returns:
        Path to the merged PDF file.

    Raises:
        PDFToolsError: If the operation fails.
    """
    if len(input_paths) < 2:
        raise PDFToolsError("Need at least 2 PDF files to merge.")

    merged = fitz.open()  # New empty PDF
    try:
        for pdf_path in input_paths:
            if not pdf_path.exists():
                raise PDFToolsError(f"File not found: {pdf_path}")
            if not pdf_path.suffix.lower() == ".pdf":
                raise PDFToolsError(f"Not a PDF file: {pdf_path.name}")

            try:
                src = fitz.open(pdf_path)
            except Exception as exc:
                raise PDFToolsError(f"Cannot open {pdf_path.name}: {exc}") from exc

            try:
                merged.insert_pdf(src)
                logger.info("Merged: %s (%d pages)", pdf_path.name, len(src))
            finally:
                src.close()

        # Avoid overwriting
        final_path = output_path
        counter = 1
        while final_path.exists():
            final_path = output_path.parent / f"{output_path.stem}_{counter}.pdf"
            counter += 1

        merged.save(str(final_path))
        logger.info(
            "Merge complete: %d files → %s (%d pages)",
            len(input_paths),
            final_path.name,
            len(merged),
        )
        return final_path
    finally:
        merged.close()
