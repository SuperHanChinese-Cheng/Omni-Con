"""Shared pytest fixtures for OmniCon tests."""

import shutil
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    """Provide a clean temporary output directory."""
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Copy sample.pdf to a temp directory and return its path."""
    src = FIXTURES_DIR / "sample.pdf"
    if not src.exists():
        pytest.skip("sample.pdf fixture not found — add a small PDF to tests/fixtures/")
    dst = tmp_path / "sample.pdf"
    shutil.copy(src, dst)
    return dst


@pytest.fixture
def sample_docx(tmp_path: Path) -> Path:
    """Copy sample.docx to a temp directory and return its path."""
    src = FIXTURES_DIR / "sample.docx"
    if not src.exists():
        pytest.skip("sample.docx fixture not found — add a small DOCX to tests/fixtures/")
    dst = tmp_path / "sample.docx"
    shutil.copy(src, dst)
    return dst


@pytest.fixture
def sample_png(tmp_path: Path) -> Path:
    """Create a minimal test PNG image."""
    from PIL import Image

    dst = tmp_path / "sample.png"
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    img.save(dst)
    return dst
