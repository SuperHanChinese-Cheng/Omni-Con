"""Image conversion engine — handles image format swaps and image ↔ PDF."""

import logging
from pathlib import Path

from PIL import Image

from omnicon.core.job import ConversionJob
from omnicon.engines.base import BaseEngine, EngineError, UnsupportedRouteError

logger = logging.getLogger(__name__)

_IMAGE_FORMATS = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif", "gif", "ico"}
_PIL_FORMAT_MAP: dict[str, str] = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "bmp": "BMP",
    "tiff": "TIFF",
    "tif": "TIFF",
    "gif": "GIF",
    "ico": "ICO",
}


class ImageEngine(BaseEngine):
    """Handles image format conversions (Pillow) and image ↔ PDF (img2pdf, PyMuPDF)."""

    priority = 10

    SUPPORTED_ROUTES: set[tuple[str, str]] = {
        *((src, dst) for src in _IMAGE_FORMATS for dst in _IMAGE_FORMATS if src != dst),
        *((fmt, "pdf") for fmt in _IMAGE_FORMATS),
        ("svg", "png"),
        ("svg", "pdf"),
    }

    def can_convert(self, src_fmt: str, dst_fmt: str) -> bool:
        """Check if this engine supports the given conversion route."""
        src = src_fmt.lower()
        dst = dst_fmt.lower()
        if src == "jpeg":
            src = "jpg"
        if dst == "jpeg":
            dst = "jpg"
        return (src, dst) in self.SUPPORTED_ROUTES

    def convert(self, job: ConversionJob) -> Path:
        """Execute the conversion."""
        src = job.src_format
        dst = job.output_format.lower()

        if src == "svg":
            return self._svg_convert(job)
        if dst == "pdf":
            return self._image_to_pdf(job)
        if src in _IMAGE_FORMATS and dst in _IMAGE_FORMATS:
            return self._image_to_image(job)

        raise UnsupportedRouteError(
            f"Route ({src}, {dst}) not supported by {self.__class__.__name__}"
        )

    def _image_to_image(self, job: ConversionJob) -> Path:
        """Convert between image formats using Pillow."""
        output_path = job.expected_output_path
        dst_fmt = job.output_format.lower()
        pil_format = _PIL_FORMAT_MAP.get(dst_fmt)
        if not pil_format:
            raise EngineError(f"Unknown image format: {dst_fmt}")

        logger.info("Converting %s -> %s via Pillow", job.input_path.name, dst_fmt.upper())

        try:
            img = Image.open(job.input_path)
            if img.mode == "RGBA" and pil_format in ("JPEG", "BMP", "ICO"):
                img = img.convert("RGB")
            save_kwargs: dict[str, int] = {}
            if pil_format in ("JPEG", "WEBP"):
                save_kwargs["quality"] = 95
            img.save(output_path, format=pil_format, **save_kwargs)
        except Exception as exc:
            raise EngineError(f"Pillow conversion failed: {exc}") from exc

        job.progress = 100
        return output_path

    def _image_to_pdf(self, job: ConversionJob) -> Path:
        """Convert image(s) to PDF using img2pdf (lossless for JPEG) or Pillow fallback."""
        output_path = job.expected_output_path
        logger.info("Converting %s -> PDF", job.input_path.name)

        src_fmt = job.src_format
        if src_fmt in ("jpg", "jpeg", "png", "tiff", "tif", "gif"):
            try:
                import img2pdf

                with open(job.input_path, "rb") as img_f, open(output_path, "wb") as pdf_f:
                    pdf_f.write(img2pdf.convert(img_f))
                job.progress = 100
                return output_path
            except Exception as exc:
                logger.warning("img2pdf failed, falling back to Pillow: %s", exc)

        try:
            img = Image.open(job.input_path)
            if img.mode == "RGBA":
                img = img.convert("RGB")
            img.save(output_path, format="PDF")
        except Exception as exc:
            raise EngineError(f"Image to PDF conversion failed: {exc}") from exc

        job.progress = 100
        return output_path

    def _svg_convert(self, job: ConversionJob) -> Path:
        """Convert SVG to PNG or PDF using CairoSVG."""
        output_path = job.expected_output_path
        dst = job.output_format.lower()
        logger.info("Converting %s -> %s via CairoSVG", job.input_path.name, dst.upper())

        try:
            import cairosvg
        except ImportError as exc:
            raise EngineError("CairoSVG is not installed") from exc

        try:
            if dst == "png":
                cairosvg.svg2png(url=str(job.input_path), write_to=str(output_path))
            elif dst == "pdf":
                cairosvg.svg2pdf(url=str(job.input_path), write_to=str(output_path))
            else:
                raise UnsupportedRouteError(f"SVG -> {dst} not supported")
        except UnsupportedRouteError:
            raise
        except Exception as exc:
            raise EngineError(f"CairoSVG conversion failed: {exc}") from exc

        job.progress = 100
        return output_path
