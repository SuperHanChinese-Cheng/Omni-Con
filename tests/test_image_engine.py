"""Tests for ImageEngine conversions."""

from pathlib import Path

import pytest
from PIL import Image

from omnicon.core.job import ConversionJob
from omnicon.engines.image_engine import ImageEngine


@pytest.fixture
def engine() -> ImageEngine:
    return ImageEngine()


@pytest.fixture
def sample_png(tmp_path: Path) -> Path:
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    path = tmp_path / "sample.png"
    img.save(path)
    return path


@pytest.fixture
def sample_rgba_png(tmp_path: Path) -> Path:
    img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
    path = tmp_path / "rgba_sample.png"
    img.save(path)
    return path


@pytest.fixture
def sample_jpg(tmp_path: Path) -> Path:
    img = Image.new("RGB", (100, 100), color=(0, 255, 0))
    path = tmp_path / "sample.jpg"
    img.save(path, format="JPEG")
    return path


def make_job(input_path: Path, output_format: str, output_dir: Path) -> ConversionJob:
    return ConversionJob(
        input_path=input_path,
        output_format=output_format,
        output_dir=output_dir,
    )


def test_can_convert_image_to_image(engine: ImageEngine) -> None:
    assert engine.can_convert("png", "jpg") is True
    assert engine.can_convert("jpg", "webp") is True
    assert engine.can_convert("bmp", "png") is True
    assert engine.can_convert("png", "png") is False


def test_can_convert_image_to_pdf(engine: ImageEngine) -> None:
    assert engine.can_convert("png", "pdf") is True
    assert engine.can_convert("jpg", "pdf") is True


def test_can_convert_svg(engine: ImageEngine) -> None:
    assert engine.can_convert("svg", "png") is True
    assert engine.can_convert("svg", "pdf") is True


def test_can_convert_unsupported(engine: ImageEngine) -> None:
    assert engine.can_convert("pdf", "png") is False
    assert engine.can_convert("docx", "pdf") is False


def test_png_to_jpg(engine: ImageEngine, sample_png: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    job = make_job(sample_png, "jpg", out)
    result = engine.convert(job)

    assert result.exists()
    assert result.suffix == ".jpg"
    img = Image.open(result)
    assert img.format == "JPEG"


def test_jpg_to_png(engine: ImageEngine, sample_jpg: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    job = make_job(sample_jpg, "png", out)
    result = engine.convert(job)

    assert result.exists()
    assert result.suffix == ".png"


def test_png_to_webp(engine: ImageEngine, sample_png: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    job = make_job(sample_png, "webp", out)
    result = engine.convert(job)

    assert result.exists()
    assert result.suffix == ".webp"


def test_rgba_to_jpg_converts_to_rgb(engine: ImageEngine, sample_rgba_png: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    job = make_job(sample_rgba_png, "jpg", out)
    result = engine.convert(job)

    assert result.exists()
    img = Image.open(result)
    assert img.mode == "RGB"


def test_png_to_pdf(engine: ImageEngine, sample_png: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    job = make_job(sample_png, "pdf", out)
    result = engine.convert(job)

    assert result.exists()
    assert result.suffix == ".pdf"
    assert result.stat().st_size > 0


def test_jpg_to_pdf(engine: ImageEngine, sample_jpg: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    job = make_job(sample_jpg, "pdf", out)
    result = engine.convert(job)

    assert result.exists()
    assert result.suffix == ".pdf"


def test_priority(engine: ImageEngine) -> None:
    assert engine.priority == 10
