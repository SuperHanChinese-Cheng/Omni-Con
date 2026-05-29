"""Tests for EngineRegistry."""

from pathlib import Path

from omnicon.core.job import ConversionJob
from omnicon.core.registry import EngineRegistry
from omnicon.engines.base import BaseEngine


class FakeEngineA(BaseEngine):
    priority = 10
    def can_convert(self, src_fmt: str, dst_fmt: str) -> bool:
        return (src_fmt, dst_fmt) == ("pdf", "txt")
    def convert(self, job: ConversionJob) -> Path:
        return job.expected_output_path


class FakeEngineB(BaseEngine):
    priority = 50
    def can_convert(self, src_fmt: str, dst_fmt: str) -> bool:
        return (src_fmt, dst_fmt) in {("pdf", "txt"), ("docx", "pdf")}
    def convert(self, job: ConversionJob) -> Path:
        return job.expected_output_path


class FakeEngineC(BaseEngine):
    priority = 30
    def can_convert(self, src_fmt: str, dst_fmt: str) -> bool:
        return (src_fmt, dst_fmt) == ("png", "jpg")
    def convert(self, job: ConversionJob) -> Path:
        return job.expected_output_path


def test_register_and_list() -> None:
    reg = EngineRegistry()
    a = FakeEngineA()
    b = FakeEngineB()
    reg.register(a)
    reg.register(b)
    assert reg.all_engines == [a, b]


def test_priority_ordering() -> None:
    reg = EngineRegistry()
    b = FakeEngineB()  # priority 50
    a = FakeEngineA()  # priority 10
    reg.register(b)
    reg.register(a)
    assert reg.all_engines == [a, b]


def test_get_engines_returns_matching() -> None:
    reg = EngineRegistry()
    a = FakeEngineA()
    b = FakeEngineB()
    c = FakeEngineC()
    reg.register(a)
    reg.register(b)
    reg.register(c)

    pdf_txt = reg.get_engines("pdf", "txt")
    assert pdf_txt == [a, b]

    docx_pdf = reg.get_engines("docx", "pdf")
    assert docx_pdf == [b]

    png_jpg = reg.get_engines("png", "jpg")
    assert png_jpg == [c]


def test_get_engines_empty_for_unsupported() -> None:
    reg = EngineRegistry()
    reg.register(FakeEngineA())
    assert reg.get_engines("xlsx", "csv") == []
