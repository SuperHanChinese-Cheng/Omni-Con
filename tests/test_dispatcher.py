"""Tests for ConversionDispatcher."""

from pathlib import Path

import pytest

from omnicon.core.dispatcher import ConversionDispatcher, ConversionError
from omnicon.core.job import ConversionJob, JobStatus
from omnicon.core.registry import EngineRegistry
from omnicon.engines.base import BaseEngine, EngineError


class SuccessEngine(BaseEngine):
    priority = 10
    def can_convert(self, src_fmt: str, dst_fmt: str) -> bool:
        return (src_fmt, dst_fmt) == ("pdf", "txt")
    def convert(self, job: ConversionJob) -> Path:
        out = job.expected_output_path
        out.write_text("converted content")
        return out


class FailEngine(BaseEngine):
    priority = 5
    def can_convert(self, src_fmt: str, dst_fmt: str) -> bool:
        return (src_fmt, dst_fmt) == ("pdf", "txt")
    def convert(self, job: ConversionJob) -> Path:
        raise EngineError("intentional failure")


class FallbackEngine(BaseEngine):
    priority = 20
    def can_convert(self, src_fmt: str, dst_fmt: str) -> bool:
        return (src_fmt, dst_fmt) == ("pdf", "txt")
    def convert(self, job: ConversionJob) -> Path:
        out = job.expected_output_path
        out.write_text("fallback content")
        return out


@pytest.fixture
def dummy_pdf(tmp_path: Path) -> Path:
    f = tmp_path / "test.pdf"
    f.write_bytes(b"%PDF-1.4 dummy")
    return f


def make_job(input_path: Path, output_format: str, output_dir: Path) -> ConversionJob:
    return ConversionJob(
        input_path=input_path,
        output_format=output_format,
        output_dir=output_dir,
    )


def test_successful_conversion(dummy_pdf: Path, tmp_path: Path) -> None:
    reg = EngineRegistry()
    reg.register(SuccessEngine())
    dispatcher = ConversionDispatcher(reg)

    job = make_job(dummy_pdf, "txt", tmp_path)
    result = dispatcher.convert(job)

    assert result.exists()
    assert result.suffix == ".txt"
    assert job.status == JobStatus.DONE
    assert job.progress == 100
    assert job.engine_name == "SuccessEngine"


def test_fallback_on_failure(dummy_pdf: Path, tmp_path: Path) -> None:
    reg = EngineRegistry()
    reg.register(FailEngine())       # priority 5 — tried first, will fail
    reg.register(FallbackEngine())   # priority 20 — fallback
    dispatcher = ConversionDispatcher(reg)

    job = make_job(dummy_pdf, "txt", tmp_path)
    result = dispatcher.convert(job)

    assert result.exists()
    assert job.status == JobStatus.DONE
    assert job.engine_name == "FallbackEngine"


def test_all_engines_fail(dummy_pdf: Path, tmp_path: Path) -> None:
    reg = EngineRegistry()
    reg.register(FailEngine())
    dispatcher = ConversionDispatcher(reg)

    job = make_job(dummy_pdf, "txt", tmp_path)
    with pytest.raises(ConversionError) as exc_info:
        dispatcher.convert(job)

    assert job.status == JobStatus.FAILED
    assert len(exc_info.value.attempts) == 1
    assert "intentional failure" in exc_info.value.attempts[0][1]


def test_no_engines_for_route(dummy_pdf: Path, tmp_path: Path) -> None:
    reg = EngineRegistry()
    reg.register(SuccessEngine())  # only handles pdf→txt
    dispatcher = ConversionDispatcher(reg)

    job = make_job(dummy_pdf, "xlsx", tmp_path)
    with pytest.raises(ConversionError):
        dispatcher.convert(job)

    assert job.status == JobStatus.FAILED


def test_can_convert(dummy_pdf: Path) -> None:
    reg = EngineRegistry()
    reg.register(SuccessEngine())
    dispatcher = ConversionDispatcher(reg)

    assert dispatcher.can_convert("pdf", "txt") is True
    assert dispatcher.can_convert("pdf", "xlsx") is False
