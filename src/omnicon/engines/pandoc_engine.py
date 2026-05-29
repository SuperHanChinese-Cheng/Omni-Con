# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""Pandoc conversion engine — handles Markdown-centric routes via pypandoc."""

import logging
from pathlib import Path

from omnicon.core.job import ConversionJob
from omnicon.engines.base import BaseEngine, EngineError, UnsupportedRouteError

logger = logging.getLogger(__name__)

_PANDOC_FORMATS: dict[str, str] = {
    "md": "markdown",
    "docx": "docx",
    "html": "html",
    "pdf": "pdf",
    "txt": "plain",
}


class PandocEngine(BaseEngine):
    """Handles Markdown-centric conversions using pypandoc."""

    priority = 30

    SUPPORTED_ROUTES: set[tuple[str, str]] = {
        ("md", "pdf"),
        ("md", "docx"),
        ("md", "html"),
        ("docx", "md"),
        ("html", "md"),
        ("md", "txt"),
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
            case ("md", "pdf"):
                return self._pandoc_convert(job)
            case ("md", "docx"):
                return self._pandoc_convert(job)
            case ("md", "html"):
                return self._pandoc_convert(job)
            case ("docx", "md"):
                return self._pandoc_convert(job)
            case ("html", "md"):
                return self._pandoc_convert(job)
            case ("md", "txt"):
                return self._pandoc_convert(job)
            case _:
                raise UnsupportedRouteError(
                    f"Route {route} not supported by {self.__class__.__name__}"
                )

    def _pandoc_convert(self, job: ConversionJob) -> Path:
        """Convert a file using pypandoc.

        Args:
            job: The conversion job containing input path and output format.

        Returns:
            Path to the converted output file.
        """
        output_path = job.expected_output_path
        src_fmt = _PANDOC_FORMATS.get(job.src_format, job.src_format)
        dst_fmt = _PANDOC_FORMATS.get(job.output_format.lower(), job.output_format.lower())

        logger.info(
            "Converting %s -> %s via pypandoc",
            job.input_path.name,
            job.output_format.upper(),
        )

        try:
            import pypandoc
        except ImportError as exc:
            raise EngineError("pypandoc is not installed") from exc

        extra_args: list[str] = []
        if job.output_format.lower() == "pdf":
            extra_args = ["--pdf-engine=weasyprint"]

        try:
            pypandoc.convert_file(
                str(job.input_path),
                dst_fmt,
                format=src_fmt,
                outputfile=str(output_path),
                extra_args=extra_args,
            )
        except Exception as exc:
            raise EngineError(f"Pandoc conversion failed: {exc}") from exc

        job.progress = 100
        return output_path
