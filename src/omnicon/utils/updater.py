# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""Background update checker — queries GitHub Releases for newer versions."""

import json
import logging
import urllib.error
import urllib.request
from typing import NamedTuple

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

import omnicon

logger = logging.getLogger(__name__)

_RELEASES_URL = (
    "https://api.github.com/repos/SuperHanChinese-Cheng/Omni-Con/releases/latest"
)
_REQUEST_TIMEOUT_SECS = 10


class ReleaseInfo(NamedTuple):
    """Minimal metadata from a GitHub release."""

    tag: str
    version: tuple[int, ...]
    html_url: str


def parse_version(tag: str) -> tuple[int, ...]:
    """Parse a version tag like ``'v0.2.0'`` into a comparable tuple.

    Leading ``v`` / ``V`` is stripped. Non-numeric segments are ignored.

    Args:
        tag: Version string, e.g. ``'v0.2.0'`` or ``'0.2.0'``.

    Returns:
        Tuple of integers, e.g. ``(0, 2, 0)``.
    """
    cleaned = tag.lstrip("vV")
    parts: list[int] = []
    for segment in cleaned.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            break
    return tuple(parts) if parts else (0,)


def fetch_latest_release() -> ReleaseInfo | None:
    """Query the GitHub API for the latest release.

    Returns:
        A :class:`ReleaseInfo` on success, or ``None`` if the request
        fails or the response cannot be parsed.
    """
    req = urllib.request.Request(
        _RELEASES_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "OmniCon-UpdateChecker",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SECS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        logger.warning("Update check failed: %s", exc)
        return None
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("Could not parse release response: %s", exc)
        return None

    tag = data.get("tag_name", "")
    html_url = data.get("html_url", "")
    if not tag:
        logger.warning("Release response missing 'tag_name'.")
        return None

    return ReleaseInfo(tag=tag, version=parse_version(tag), html_url=html_url)


def is_newer(remote: tuple[int, ...], local: tuple[int, ...]) -> bool:
    """Return ``True`` if *remote* is strictly newer than *local*.

    Args:
        remote: Parsed remote version tuple.
        local: Parsed local version tuple.

    Returns:
        Whether *remote* > *local* using lexicographic comparison.
    """
    return remote > local


# ---------------------------------------------------------------------------
# Qt worker for non-blocking update check
# ---------------------------------------------------------------------------


class UpdateSignals(QObject):
    """Signals emitted by :class:`UpdateWorker`."""

    update_available = Signal(str, str)  # (tag, html_url)


class UpdateWorker(QRunnable):
    """Checks for a newer OmniCon release in a thread-pool thread.

    On success the :pyattr:`signals.update_available` signal is emitted with
    the new version tag and the download URL. If the current version is
    already up-to-date, or the network request fails, nothing is emitted.

    The caller must keep a strong reference to this worker until the signal
    fires or is no longer expected, to prevent premature garbage-collection
    of the :class:`UpdateSignals` QObject.
    """

    def __init__(self) -> None:
        super().__init__()
        self.signals = UpdateSignals()
        self.setAutoDelete(False)

    @Slot()
    def run(self) -> None:
        """Execute the update check (runs off the main thread)."""
        logger.debug("Checking for updates...")
        release = fetch_latest_release()
        if release is None:
            return

        local_version = parse_version(omnicon.__version__)
        if is_newer(release.version, local_version):
            logger.info(
                "New version available: %s (current: %s)",
                release.tag,
                omnicon.__version__,
            )
            self.signals.update_available.emit(release.tag, release.html_url)
        else:
            logger.debug(
                "OmniCon is up to date (%s).", omnicon.__version__
            )
