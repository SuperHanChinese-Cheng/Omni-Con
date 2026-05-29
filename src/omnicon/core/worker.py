"""QThreadPool worker for async conversion — keeps the GUI thread responsive."""

import logging
import traceback

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from omnicon.core.dispatcher import ConversionDispatcher, ConversionError
from omnicon.core.job import ConversionJob, JobStatus

logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    """Signals emitted by ConversionWorker."""

    started = Signal(object)
    progress = Signal(object, int)
    finished = Signal(object)
    error = Signal(object, str)


class ConversionWorker(QRunnable):
    """Runs a single ConversionJob in a thread pool.

    Caller must hold a strong reference to this worker until the finished/error
    signal fires, otherwise the WorkerSignals QObject may be garbage-collected
    before the queued cross-thread signal is delivered.
    """

    def __init__(self, job: ConversionJob, dispatcher: ConversionDispatcher) -> None:
        super().__init__()
        self.job = job
        self.dispatcher = dispatcher
        self.signals = WorkerSignals()
        self.setAutoDelete(False)

    @Slot()
    def run(self) -> None:
        """Execute the conversion job."""
        self.job.status = JobStatus.RUNNING
        self.signals.started.emit(self.job)
        try:
            self.dispatcher.convert(self.job)
            self.signals.finished.emit(self.job)
        except ConversionError as exc:
            logger.error("Conversion failed: %s", exc)
            self.signals.error.emit(self.job, str(exc))
        except Exception as exc:
            logger.error("Unexpected error: %s\n%s", exc, traceback.format_exc())
            self.job.status = JobStatus.FAILED
            self.job.error_message = str(exc)
            self.signals.error.emit(self.job, f"Unexpected error: {exc}")
