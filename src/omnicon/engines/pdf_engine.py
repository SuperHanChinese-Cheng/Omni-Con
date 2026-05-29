# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""PDF conversion engine — handles PDF-centric routes via PyMuPDF and pdf2docx."""

import logging
from pathlib import Path

import fitz  # PyMuPDF

from omnicon.core.job import ConversionJob
from omnicon.engines.base import BaseEngine, EngineError, UnsupportedRouteError

logger = logging.getLogger(__name__)


class PDFEngine(BaseEngine):
    """Handles PDF-centric conversions using PyMuPDF and pdf2docx."""

    priority = 10

    SUPPORTED_ROUTES: set[tuple[str, str]] = {
        ("pdf", "txt"),
        ("pdf", "docx"),
        ("pdf", "png"),
        ("pdf", "jpg"),
        ("pdf", "html"),
    }

    def can_convert(self, src_fmt: str, dst_fmt: str) -> bool:
        """Check if this engine supports the given conversion route."""
        return (src_fmt.lower(), dst_fmt.lower()) in self.SUPPORTED_ROUTES

    def convert(self, job: ConversionJob) -> Path:
        """Execute the conversion. Must be thread-safe."""
        route = (job.src_format, job.output_format.lower())
        match route:
            case ("pdf", "txt"):
                return self._pdf_to_text(job)
            case ("pdf", "docx"):
                return self._pdf_to_docx(job)
            case ("pdf", "png") | ("pdf", "jpg"):
                return self._pdf_to_image(job)
            case ("pdf", "html"):
                return self._pdf_to_html(job)
            case _:
                raise UnsupportedRouteError(
                    f"Route {route} not supported by {self.__class__.__name__}"
                )

    def _pdf_to_text(self, job: ConversionJob) -> Path:
        """Extract text from all pages of a PDF."""
        output_path = job.expected_output_path
        logger.info("Extracting text from %s", job.input_path.name)

        try:
            doc = fitz.open(job.input_path)
        except Exception as exc:
            raise EngineError(f"Failed to open PDF: {exc}") from exc

        try:
            pages = len(doc)
            text_parts: list[str] = []
            for i, page in enumerate(doc):
                text_parts.append(page.get_text())
                job.progress = int((i + 1) / pages * 100)
            output_path.write_text("\n\n".join(text_parts), encoding="utf-8")
        finally:
            doc.close()

        return output_path

    def _pdf_to_docx(self, job: ConversionJob) -> Path:
        """Convert PDF to DOCX using pdf2docx."""
        output_path = job.expected_output_path
        logger.info("Converting %s to DOCX via pdf2docx", job.input_path.name)

        try:
            from pdf2docx import Converter
        except ImportError as exc:
            raise EngineError("pdf2docx is not installed") from exc

        cv = Converter(str(job.input_path))
        try:
            cv.convert(str(output_path), multi_processing=False)
        except Exception as exc:
            raise EngineError(f"pdf2docx conversion failed: {exc}") from exc
        finally:
            cv.close()

        job.progress = 100
        return output_path

    def _pdf_to_image(self, job: ConversionJob) -> Path:
        """Render PDF pages as images using PyMuPDF.

        For multi-page PDFs, creates numbered output files (page_001.png, etc.)
        and returns the path to the first image. For single-page PDFs, returns
        the direct output path.
        """
        fmt = job.output_format.lower()
        logger.info("Rendering %s to %s", job.input_path.name, fmt.upper())

        try:
            doc = fitz.open(job.input_path)
        except Exception as exc:
            raise EngineError(f"Failed to open PDF: {exc}") from exc

        try:
            pages = len(doc)
            dpi = 300
            matrix = fitz.Matrix(dpi / 72, dpi / 72)

            if pages == 1:
                output_path = job.expected_output_path
                pix = doc[0].get_pixmap(matrix=matrix)
                pix.save(str(output_path))
                job.progress = 100
                return output_path

            first_path: Path | None = None
            for i, page in enumerate(doc):
                page_path = job.output_dir / f"{job.input_path.stem}_page_{i + 1:03d}.{fmt}"
                pix = page.get_pixmap(matrix=matrix)
                pix.save(str(page_path))
                if first_path is None:
                    first_path = page_path
                job.progress = int((i + 1) / pages * 100)

            assert first_path is not None
            return first_path
        finally:
            doc.close()

    def _pdf_to_html(self, job: ConversionJob) -> Path:
        """Extract HTML representation of PDF pages using PyMuPDF."""
        output_path = job.expected_output_path
        logger.info("Converting %s to HTML", job.input_path.name)

        try:
            doc = fitz.open(job.input_path)
        except Exception as exc:
            raise EngineError(f"Failed to open PDF: {exc}") from exc

        try:
            pages = len(doc)
            html_parts = [
                "<!DOCTYPE html>",
                '<html lang="en">',
                "<head><meta charset=\"utf-8\"><title>"
                + job.input_path.stem
                + "</title></head>",
                "<body>",
            ]
            for i, page in enumerate(doc):
                html_parts.append(f'<div class="page" id="page-{i + 1}">')
                html_parts.append(page.get_text("html"))
                html_parts.append("</div>")
                job.progress = int((i + 1) / pages * 100)
            html_parts.append("</body></html>")
            output_path.write_text("\n".join(html_parts), encoding="utf-8")
        finally:
            doc.close()

        return output_path
