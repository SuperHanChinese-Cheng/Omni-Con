# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""Conversion dispatcher — routes jobs through the engine fallback chain."""

import logging
from pathlib import Path

from omnicon.core.job import ConversionJob, JobStatus
from omnicon.core.registry import EngineRegistry
from omnicon.engines.base import EngineError

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Raised when all engines fail to convert a file."""

    def __init__(self, job: ConversionJob, attempts: list[tuple[str, str]]) -> None:
        self.job = job
        self.attempts = attempts
        details = "; ".join(f"{name}: {err}" for name, err in attempts)
        super().__init__(
            f"All engines failed for {job.input_path.name} "
            f"({job.src_format} -> {job.output_format}): {details}"
        )


class ConversionDispatcher:
    """Routes conversion jobs through the engine registry with fallback.

    The dispatcher queries the registry for engines that can handle
    the requested route, then tries each in priority order. If an engine
    fails, the next one is attempted. If all fail, a ConversionError is raised.
    """

    def __init__(self, registry: EngineRegistry) -> None:
        self._registry = registry

    def convert(self, job: ConversionJob) -> Path:
        """Execute a conversion job, trying engines in priority order.

        Args:
            job: The conversion job to execute.

        Returns:
            Path to the converted output file.

        Raises:
            ConversionError: If no engine can handle the route or all engines fail.
        """
        engines = self._registry.get_engines(job.src_format, job.output_format)

        if not engines:
            job.status = JobStatus.FAILED
            job.error_message = (
                f"No engine supports {job.src_format} -> {job.output_format}"
            )
            raise ConversionError(job, [("registry", "no engines found for this route")])

        job.status = JobStatus.RUNNING
        attempts: list[tuple[str, str]] = []

        for engine in engines:
            engine_name = engine.__class__.__name__
            logger.info(
                "Trying %s for %s -> %s",
                engine_name,
                job.input_path.name,
                job.output_format,
            )
            try:
                job.engine_name = engine_name
                result = engine.convert(job)
                job.status = JobStatus.DONE
                job.output_path = result
                job.progress = 100
                logger.info(
                    "Success: %s converted %s -> %s",
                    engine_name,
                    job.input_path.name,
                    result.name,
                )
                return result
            except EngineError as exc:
                msg = str(exc)
                attempts.append((engine_name, msg))
                logger.warning(
                    "Engine %s failed for %s: %s — trying next",
                    engine_name,
                    job.input_path.name,
                    msg,
                )

        job.status = JobStatus.FAILED
        job.error_message = f"All {len(attempts)} engine(s) failed"
        raise ConversionError(job, attempts)

    def can_convert(self, src_fmt: str, dst_fmt: str) -> bool:
        """Check if any registered engine can handle this route.

        Args:
            src_fmt: Source format extension.
            dst_fmt: Destination format extension.

        Returns:
            True if at least one engine supports this route.
        """
        return len(self._registry.get_engines(src_fmt, dst_fmt)) > 0
