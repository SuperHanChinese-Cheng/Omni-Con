"""Tests for PDFEngine conversions."""

from pathlib import Path

import pytest

from omnicon.core.job import ConversionJob
from omnicon.engines.pdf_engine import PDFEngine


@pytest.fixture
def engine() -> PDFEngine:
    return PDFEngine()


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a minimal PDF with text content using PyMuPDF."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello OmniCon! This is a test PDF.", fontsize=14)
    page.insert_text((72, 120), "Second line of text for testing extraction.")
    path = tmp_path / "sample.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def multipage_pdf(tmp_path: Path) -> Path:
    """Create a multi-page PDF for image export tests."""
    import fitz

    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=18)
    path = tmp_path / "multipage.pdf"
    doc.save(str(path))
    doc.close()
    return path


def make_job(input_path: Path, output_format: str, output_dir: Path) -> ConversionJob:
    return ConversionJob(
        input_path=input_path,
        output_format=output_format,
        output_dir=output_dir,
    )


def test_can_convert_supported(engine: PDFEngine) -> None:
    assert engine.can_convert("pdf", "txt") is True
    assert engine.can_convert("pdf", "docx") is True
    assert engine.can_convert("pdf", "png") is True
    assert engine.can_convert("pdf", "jpg") is True
    assert engine.can_convert("pdf", "html") is True


def test_can_convert_unsupported(engine: PDFEngine) -> None:
    assert engine.can_convert("docx", "pdf") is False
    assert engine.can_convert("png", "jpg") is False
    assert engine.can_convert("pdf", "pptx") is False


def test_can_convert_case_insensitive(engine: PDFEngine) -> None:
    assert engine.can_convert("PDF", "TXT") is True
    assert engine.can_convert("Pdf", "Docx") is True


def test_pdf_to_text(engine: PDFEngine, sample_pdf: Path, tmp_path: Path) -> None:
    job = make_job(sample_pdf, "txt", tmp_path)
    result = engine.convert(job)

    assert result.exists()
    assert result.suffix == ".txt"
    content = result.read_text(encoding="utf-8")
    assert "Hello OmniCon" in content
    assert "Second line" in content
    assert job.progress == 100


def test_pdf_to_docx(engine: PDFEngine, sample_pdf: Path, tmp_path: Path) -> None:
    job = make_job(sample_pdf, "docx", tmp_path)
    result = engine.convert(job)

    assert result.exists()
    assert result.suffix == ".docx"
    assert result.stat().st_size > 0
    assert job.progress == 100


def test_pdf_to_png_single_page(engine: PDFEngine, sample_pdf: Path, tmp_path: Path) -> None:
    job = make_job(sample_pdf, "png", tmp_path)
    result = engine.convert(job)

    assert result.exists()
    assert result.suffix == ".png"
    assert result.stat().st_size > 0
    assert job.progress == 100


def test_pdf_to_png_multipage(engine: PDFEngine, multipage_pdf: Path, tmp_path: Path) -> None:
    job = make_job(multipage_pdf, "png", tmp_path)
    result = engine.convert(job)

    assert result.exists()
    assert "_page_001" in result.stem
    page2 = tmp_path / f"{multipage_pdf.stem}_page_002.png"
    page3 = tmp_path / f"{multipage_pdf.stem}_page_003.png"
    assert page2.exists()
    assert page3.exists()


def test_pdf_to_jpg(engine: PDFEngine, sample_pdf: Path, tmp_path: Path) -> None:
    job = make_job(sample_pdf, "jpg", tmp_path)
    result = engine.convert(job)

    assert result.exists()
    assert result.suffix == ".jpg"
    assert result.stat().st_size > 0


def test_pdf_to_html(engine: PDFEngine, sample_pdf: Path, tmp_path: Path) -> None:
    job = make_job(sample_pdf, "html", tmp_path)
    result = engine.convert(job)

    assert result.exists()
    assert result.suffix == ".html"
    content = result.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "page-1" in content
    assert job.progress == 100


def test_priority(engine: PDFEngine) -> None:
    assert engine.priority == 10
