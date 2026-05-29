"""HTML conversion engine — handles HTML-centric routes via WeasyPrint and mammoth."""

import logging
import re
from pathlib import Path

from omnicon.core.job import ConversionJob
from omnicon.engines.base import BaseEngine, EngineError, UnsupportedRouteError

logger = logging.getLogger(__name__)


class HTMLEngine(BaseEngine):
    """Handles HTML-centric conversions using WeasyPrint and mammoth."""

    priority = 20

    SUPPORTED_ROUTES: set[tuple[str, str]] = {
        ("html", "pdf"),
        ("docx", "html"),
        ("html", "txt"),
    }

    def can_convert(self, src_fmt: str, dst_fmt: str) -> bool:
        """Check if this engine supports the given conversion route."""
        return (src_fmt.lower(), dst_fmt.lower()) in self.SUPPORTED_ROUTES

    def convert(self, job: ConversionJob) -> Path:
        """Execute the conversion. Must be thread-safe.

        Args:
            job: The conversion job with input path, output format, and options.

        Returns:
            Path to the converted output file.

        Raises:
            EngineError: If conversion fails.
            UnsupportedRouteError: If the route is not supported by this engine.
        """
        route = (job.src_format, job.output_format.lower())
        match route:
            case ("html", "pdf"):
                return self._html_to_pdf(job)
            case ("docx", "html"):
                return self._docx_to_html(job)
            case ("html", "txt"):
                return self._html_to_text(job)
            case _:
                raise UnsupportedRouteError(
                    f"Route {route} not supported by {self.__class__.__name__}"
                )

    def _html_to_pdf(self, job: ConversionJob) -> Path:
        """Convert HTML to PDF using WeasyPrint.

        Args:
            job: The conversion job containing input HTML path.

        Returns:
            Path to the generated PDF file.
        """
        output_path = job.expected_output_path
        logger.info("Converting %s -> PDF via WeasyPrint", job.input_path.name)

        try:
            from weasyprint import HTML
        except ImportError as exc:
            raise EngineError("weasyprint is not installed") from exc

        try:
            HTML(filename=str(job.input_path)).write_pdf(str(output_path))
        except Exception as exc:
            raise EngineError(f"HTML to PDF conversion failed: {exc}") from exc

        job.progress = 100
        return output_path

    def _docx_to_html(self, job: ConversionJob) -> Path:
        """Convert DOCX to semantic HTML using mammoth.

        Args:
            job: The conversion job containing input DOCX path.

        Returns:
            Path to the generated HTML file.
        """
        output_path = job.expected_output_path
        logger.info("Converting %s -> HTML via mammoth", job.input_path.name)

        try:
            import mammoth
        except ImportError as exc:
            raise EngineError("mammoth is not installed") from exc

        try:
            with open(job.input_path, "rb") as f:
                result = mammoth.convert_to_html(f)
            html_content = (
                "<!DOCTYPE html>"
                "<html><head><meta charset='utf-8'></head>"
                f"<body>{result.value}</body></html>"
            )
            output_path.write_text(html_content, encoding="utf-8")
        except Exception as exc:
            raise EngineError(f"DOCX to HTML conversion failed: {exc}") from exc

        job.progress = 100
        return output_path

    def _html_to_text(self, job: ConversionJob) -> Path:
        """Convert HTML to plain text by stripping tags.

        Args:
            job: The conversion job containing input HTML path.

        Returns:
            Path to the generated text file.
        """
        output_path = job.expected_output_path
        logger.info("Extracting text from %s", job.input_path.name)

        try:
            html_content = job.input_path.read_text(encoding="utf-8")
            text = re.sub(r"<[^>]+>", "", html_content)
            text = re.sub(r"\s+", " ", text).strip()
            output_path.write_text(text, encoding="utf-8")
        except Exception as exc:
            raise EngineError(f"HTML to text conversion failed: {exc}") from exc

        job.progress = 100
        return output_path
