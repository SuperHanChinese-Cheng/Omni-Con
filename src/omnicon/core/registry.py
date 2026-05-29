# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""Engine registry — collects and queries available conversion engines."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnicon.engines.base import BaseEngine

logger = logging.getLogger(__name__)


class EngineRegistry:
    """Central registry of all conversion engines.

    Engines are registered at startup and queried by the dispatcher
    to find capable engines for a given conversion route.
    """

    def __init__(self) -> None:
        self._engines: list[BaseEngine] = []

    def register(self, engine: "BaseEngine") -> None:
        """Register an engine instance.

        Args:
            engine: An engine implementing the BaseEngine interface.
        """
        self._engines.append(engine)
        self._engines.sort(key=lambda e: e.priority)
        logger.info("Registered %r", engine)

    def get_engines(self, src_fmt: str, dst_fmt: str) -> list["BaseEngine"]:
        """Return all engines capable of converting src_fmt → dst_fmt, sorted by priority.

        Args:
            src_fmt: Source format extension (e.g., "pdf").
            dst_fmt: Destination format extension (e.g., "docx").

        Returns:
            List of engines that support this route, lowest priority number first.
        """
        return [e for e in self._engines if e.can_convert(src_fmt, dst_fmt)]

    @property
    def all_engines(self) -> list["BaseEngine"]:
        """All registered engines, sorted by priority."""
        return list(self._engines)

    def supported_routes(self) -> set[tuple[str, str]]:
        """Return the set of all (src_fmt, dst_fmt) pairs any registered engine can handle."""
        routes: set[tuple[str, str]] = set()
        for engine in self._engines:
            if hasattr(engine, "SUPPORTED_ROUTES"):
                routes.update(engine.SUPPORTED_ROUTES)
        return routes
