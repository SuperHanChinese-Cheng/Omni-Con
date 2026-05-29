"""Tests for OfficeEngine (unit tests — mock subprocess)."""

from pathlib import Path
from unittest.mock import MagicMock, patch  # noqa: F401 — patch used in decorators too

import pytest

from omnicon.core.job import ConversionJob
from omnicon.engines.office_engine import OfficeEngine


@pytest.fixture
def mock_soffice(tmp_path: Path) -> Path:
    soffice = tmp_path / "soffice.exe"
    soffice.write_text("fake")
    return soffice


@pytest.fixture
def engine(mock_soffice: Path) -> OfficeEngine:
    return OfficeEngine(soffice_path=mock_soffice)


@pytest.fixture
def sample_docx(tmp_path: Path) -> Path:
    from docx import Document

    doc = Document()
    doc.add_paragraph("Hello from OmniCon test.")
    path = tmp_path / "sample.docx"
    doc.save(str(path))
    return path


def make_job(input_path: Path, output_format: str, output_dir: Path) -> ConversionJob:
    return ConversionJob(
        input_path=input_path,
        output_format=output_format,
        output_dir=output_dir,
    )


def test_can_convert_office_to_pdf(engine: OfficeEngine) -> None:
    assert engine.can_convert("docx", "pdf") is True
    assert engine.can_convert("pptx", "pdf") is True
    assert engine.can_convert("xlsx", "pdf") is True
    assert engine.can_convert("odt", "pdf") is True
    assert engine.can_convert("rtf", "pdf") is True


def test_can_convert_pdf_to_office(engine: OfficeEngine) -> None:
    assert engine.can_convert("pdf", "docx") is True
    assert engine.can_convert("pdf", "pptx") is True
    assert engine.can_convert("pdf", "xlsx") is True


def test_can_convert_unsupported(engine: OfficeEngine) -> None:
    assert engine.can_convert("png", "pdf") is False
    assert engine.can_convert("docx", "png") is False


def test_convert_calls_subprocess(
    engine: OfficeEngine, sample_docx: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    out.mkdir()
    job = make_job(sample_docx, "pdf", out)

    expected_output = out / "sample.pdf"
    expected_output.write_bytes(b"%PDF-1.4 fake output")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        result = engine.convert(job)

    assert result == expected_output
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "--headless" in args
    assert "--convert-to" in args


def test_no_soffice_raises() -> None:
    with patch.object(OfficeEngine, "_detect_soffice", return_value=None):
        engine = OfficeEngine(soffice_path=None)
    from omnicon.engines.base import DependencyMissingError

    job = make_job(Path("dummy.docx"), "pdf", Path("/tmp"))
    with pytest.raises(DependencyMissingError):
        engine.convert(job)


def test_is_available(engine: OfficeEngine) -> None:
    assert engine.is_available is True

    with patch.object(OfficeEngine, "_detect_soffice", return_value=None):
        no_lo = OfficeEngine(soffice_path=None)
    assert no_lo.is_available is False


def test_priority(engine: OfficeEngine) -> None:
    assert engine.priority == 50
