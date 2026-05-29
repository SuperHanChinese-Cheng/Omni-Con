"""Base engine interface for all conversion engines."""

from abc import ABC, abstractmethod
from pathlib import Path

from omnicon.core.job import ConversionJob


class BaseEngine(ABC):
    """Abstract base class for conversion engines.

    All engines must implement `can_convert` and `convert`.
    The `priority` attribute determines engine ordering in the fallback chain
    (lower value = tried first).
    """

    priority: int = 100  # Override in subclasses

    @abstractmethod
    def can_convert(self, src_fmt: str, dst_fmt: str) -> bool:
        """Check whether this engine supports the given conversion route.

        Args:
            src_fmt: Source format extension (e.g., "pdf", "docx").
            dst_fmt: Destination format extension (e.g., "docx", "pdf").

        Returns:
            True if this engine can handle the conversion.
        """
        ...

    @abstractmethod
    def convert(self, job: ConversionJob) -> Path:
        """Execute the conversion. Must be thread-safe.

        Args:
            job: The conversion job with input path, output format, and options.

        Returns:
            Path to the converted output file.

        Raises:
            EngineError: If conversion fails.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(priority={self.priority})"


class EngineError(Exception):
    """Raised when an engine fails to convert a file."""


class UnsupportedRouteError(EngineError):
    """Raised when an engine is asked to handle a route it doesn't support."""


class DependencyMissingError(EngineError):
    """Raised when a required system dependency (e.g., LibreOffice) is not found."""
