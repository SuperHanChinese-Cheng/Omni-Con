# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""Conversion job model — the unit of work flowing through the system."""

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from uuid import UUID, uuid4


class JobStatus(Enum):
    """Lifecycle states for a conversion job."""

    QUEUED = auto()
    RUNNING = auto()
    DONE = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class ConversionJob:
    """A single file conversion request.

    Attributes:
        input_path: Path to the source file.
        output_format: Target format extension (e.g., "docx", "pdf", "png").
        output_dir: Directory where the converted file will be written.
        job_id: Unique identifier for this job.
        status: Current lifecycle status.
        progress: Conversion progress as a percentage (0–100).
        output_path: Path to the output file (set after conversion completes).
        error_message: Human-readable error message (set on failure).
        engine_name: Name of the engine that handled/is handling this job.
    """

    input_path: Path
    output_format: str
    output_dir: Path
    job_id: UUID = field(default_factory=uuid4)
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    output_path: Path | None = None
    error_message: str | None = None
    engine_name: str | None = None

    @property
    def src_format(self) -> str:
        """Source file format derived from the input file extension."""
        return self.input_path.suffix.lstrip(".").lower()

    @property
    def output_filename(self) -> str:
        """Generated output filename: original stem + new extension."""
        return f"{self.input_path.stem}.{self.output_format}"

    @property
    def expected_output_path(self) -> Path:
        """Full expected output path."""
        return self.output_dir / self.output_filename
