# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""Office conversion engine — handles Office ↔ PDF via LibreOffice headless."""

import logging
import platform
import shutil
import subprocess
from pathlib import Path

from omnicon.core.job import ConversionJob
from omnicon.engines.base import BaseEngine, DependencyMissingError, EngineError, UnsupportedRouteError

logger = logging.getLogger(__name__)

_OFFICE_TO_PDF_FORMATS = {"docx", "doc", "pptx", "ppt", "xlsx", "xls", "odt", "odp", "ods", "rtf"}


class OfficeEngine(BaseEngine):
    """Converts Office documents to/from PDF using LibreOffice headless.

    Priority 50 — slower than native Python engines but handles the widest
    range of Office format conversions.
    """

    priority = 50

    SUPPORTED_ROUTES: set[tuple[str, str]] = {
        *((fmt, "pdf") for fmt in _OFFICE_TO_PDF_FORMATS),
        ("pdf", "docx"),
        ("pdf", "pptx"),
        ("pdf", "xlsx"),
    }

    def __init__(self, soffice_path: Path | None = None) -> None:
        self._soffice_path = soffice_path or self._detect_soffice()

    def can_convert(self, src_fmt: str, dst_fmt: str) -> bool:
        """Check if this engine supports the given conversion route."""
        return (src_fmt.lower(), dst_fmt.lower()) in self.SUPPORTED_ROUTES

    def convert(self, job: ConversionJob) -> Path:
        """Execute the conversion via LibreOffice headless subprocess."""
        if self._soffice_path is None:
            raise DependencyMissingError(
                "LibreOffice not found. Install from https://www.libreoffice.org/download/"
            )

        route = (job.src_format, job.output_format.lower())
        if route not in self.SUPPORTED_ROUTES:
            raise UnsupportedRouteError(
                f"Route {route} not supported by {self.__class__.__name__}"
            )

        return self._convert_via_soffice(job)

    def _convert_via_soffice(self, job: ConversionJob) -> Path:
        """Run LibreOffice headless to convert the file."""
        assert self._soffice_path is not None

        output_filter = self._get_output_filter(job.output_format.lower())

        # High-fidelity PDF export: embed fonts, max image quality, preserve layout
        if job.output_format.lower() == "pdf":
            if job.src_format in ("pptx", "ppt", "odp"):
                # Presentation → PDF: include notes, embed fonts, max quality
                output_filter = (
                    'pdf:impress_pdf_Export:{'
                    '"ExportNotesPages":{"type":"boolean","value":"true"},'
                    '"IsSkipEmptyPages":{"type":"boolean","value":"false"},'
                    '"MaxImageResolution":{"type":"long","value":"600"},'
                    '"Quality":{"type":"long","value":"100"},'
                    '"EmbedStandardFonts":{"type":"boolean","value":"true"}'
                    '}'
                )
            else:
                # Document → PDF: embed all fonts, max quality, preserve structure
                output_filter = (
                    'pdf:writer_pdf_Export:{'
                    '"IsSkipEmptyPages":{"type":"boolean","value":"false"},'
                    '"MaxImageResolution":{"type":"long","value":"600"},'
                    '"Quality":{"type":"long","value":"100"},'
                    '"EmbedStandardFonts":{"type":"boolean","value":"true"},'
                    '"UseTaggedPDF":{"type":"boolean","value":"true"}'
                    '}'
                )

        cmd = [
            str(self._soffice_path),
            "--headless",
        ]

        # PDF input requires an explicit import filter so LibreOffice opens
        # the file through Writer's PDF importer instead of guessing (which
        # fails silently and produces no output).
        if job.src_format == "pdf":
            cmd.append("--infilter=writer_pdf_import")

        cmd += [
            "--convert-to", output_filter,
            "--outdir", str(job.output_dir),
            str(job.input_path),
        ]

        logger.info(
            "Running LibreOffice: %s -> %s",
            job.input_path.name,
            job.output_format,
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            raise EngineError(
                f"LibreOffice timed out converting {job.input_path.name}"
            ) from exc
        except FileNotFoundError as exc:
            raise DependencyMissingError(
                f"LibreOffice binary not found at {self._soffice_path}"
            ) from exc

        if result.returncode != 0:
            raise EngineError(
                f"LibreOffice exited with code {result.returncode}: {result.stderr.strip()}"
            )

        output_path = job.expected_output_path
        if not output_path.exists():
            candidates = list(job.output_dir.glob(f"{job.input_path.stem}.*"))
            if candidates:
                actual = candidates[0]
                if actual != output_path:
                    actual.rename(output_path)
            else:
                stderr_hint = result.stderr.strip()
                msg = f"LibreOffice produced no output for {job.input_path.name}"
                if stderr_hint:
                    msg += f" (stderr: {stderr_hint})"
                raise EngineError(msg)

        job.progress = 100
        return output_path

    @staticmethod
    def _get_output_filter(dst_fmt: str) -> str:
        """Map output format to LibreOffice filter string.

        Uses explicit filter names for high-fidelity output where possible.
        """
        filters: dict[str, str] = {
            # Use explicit filter names for better fidelity
            "pdf": "pdf",
            "docx": 'docx:"Office Open XML Text"',
            "doc": "doc",
            "pptx": 'pptx:"Impress Office Open XML"',
            "xlsx": 'xlsx:"Calc Office Open XML"',
            "odt": "odt",
            "odp": "odp",
            "ods": "ods",
            "rtf": "rtf",
            "html": "html",
            "txt": "txt",
        }
        return filters.get(dst_fmt, dst_fmt)

    @staticmethod
    def _detect_soffice() -> Path | None:
        """Find the LibreOffice soffice binary on this system."""
        for name in ["soffice", "libreoffice"]:
            path = shutil.which(name)
            if path:
                logger.info("Found LibreOffice at %s", path)
                return Path(path)

        if platform.system() == "Windows":
            for prog_dir in [
                Path("C:/Program Files/LibreOffice/program"),
                Path("C:/Program Files (x86)/LibreOffice/program"),
            ]:
                soffice = prog_dir / "soffice.exe"
                if soffice.exists():
                    logger.info("Found LibreOffice at %s", soffice)
                    return soffice

        if platform.system() == "Darwin":
            mac_path = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
            if mac_path.exists():
                logger.info("Found LibreOffice at %s", mac_path)
                return mac_path

        logger.warning("LibreOffice not found on this system")
        return None

    @property
    def is_available(self) -> bool:
        """Whether LibreOffice was detected on this system."""
        return self._soffice_path is not None
