# OmniCon — Code Conventions

## Python version & syntax
- Target Python 3.11+
- Use `match/case` for format routing in dispatcher
- Use `type` aliases: `type FilePath = Path`
- Use `X | Y` union syntax, not `Union[X, Y]`
- Use `Self` return type where applicable

## Formatting & linting
- **ruff** for both linting and formatting
- Line length: 100
- Quote style: double quotes
- Trailing commas: always in multi-line structures
- Import sorting: isort-compatible (stdlib → third-party → local)

## Naming
- Classes: `PascalCase` — `PDFEngine`, `ConversionJob`, `MainWindow`
- Functions/methods: `snake_case` — `can_convert()`, `get_engines()`
- Constants: `UPPER_SNAKE` — `MAX_BATCH_SIZE`, `UNOSERVER_THRESHOLD`
- Private: single underscore prefix — `_detect_libreoffice()`
- Module-level loggers: `logger = logging.getLogger(__name__)`

## Type hints
- All function signatures must have type hints
- Return types are mandatory — use `-> None` explicitly
- Avoid `Any` — if truly needed, add a `# type: ignore[<code>]` comment explaining why
- Use `pathlib.Path` for all file paths, never `str`

## Docstrings (Google style)
```python
def convert(self, job: ConversionJob) -> Path:
    """Convert a file using this engine.

    Args:
        job: The conversion job containing input path, output format, and options.

    Returns:
        Path to the converted output file.

    Raises:
        ConversionError: If conversion fails after all attempts.
        LibreOfficeNotFoundError: If LibreOffice is required but not installed.
    """
```

## Error handling patterns
```python
# DO: catch specific exceptions
try:
    result = pdf2docx_convert(input_path, output_path)
except pdf2docx.ConversionError as e:
    logger.warning("pdf2docx failed for %s: %s", input_path.name, e)
    raise EngineError(f"PDF to DOCX conversion failed: {e}") from e

# DON'T: bare except or catch Exception
try:
    result = convert(path)
except Exception:  # BAD — too broad
    pass           # BAD — swallows the error
```

## Logging
- Use `logging` module, never `print()`
- Log levels: DEBUG for internals, INFO for user-visible actions, WARNING for fallbacks, ERROR for failures
- Format: include the engine name and file being processed
```python
logger.info("Converting %s → %s via %s", input_path.name, output_fmt, self.__class__.__name__)
logger.warning("Engine %s failed, falling back to %s", engine_a, engine_b)
```

## Threading rules
- GUI thread: only GUI operations (widget updates, signal handling)
- Worker threads: all conversion work via QRunnable + QThreadPool
- Communication: Qt signals only — never share mutable state between threads
- Progress updates: worker emits `progress(int)` signal, GUI connects to update bar

## File path handling
```python
# DO: use pathlib
output_path = job.output_dir / f"{job.input_path.stem}.{job.output_format}"

# DON'T: string concatenation
output_path = job.output_dir + "/" + job.input_path.stem + "." + job.output_format
```

## Engine implementation pattern
```python
from omnicon.core.base import BaseEngine
from omnicon.core.job import ConversionJob

class PDFEngine(BaseEngine):
    """Handles PDF-centric conversions using PyMuPDF and pdf2docx."""

    priority = 10

    def can_convert(self, src_fmt: str, dst_fmt: str) -> bool:
        """Check if this engine supports the given conversion route."""
        return (src_fmt, dst_fmt) in self._SUPPORTED_ROUTES

    def convert(self, job: ConversionJob) -> Path:
        """Execute the conversion. Must be thread-safe."""
        route = (job.src_format, job.dst_format)
        match route:
            case ("pdf", "docx"):
                return self._pdf_to_docx(job)
            case ("pdf", "png") | ("pdf", "jpg"):
                return self._pdf_to_image(job)
            case _:
                raise UnsupportedRouteError(f"Route {route} not supported by {self}")
```

## Testing patterns
```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a minimal test PDF."""
    # Use a small fixture file from tests/fixtures/
    src = Path(__file__).parent / "fixtures" / "sample.pdf"
    dst = tmp_path / "sample.pdf"
    shutil.copy(src, dst)
    return dst

def test_pdf_to_docx(sample_pdf: Path, tmp_path: Path) -> None:
    """PDF to DOCX conversion produces a valid .docx file."""
    engine = PDFEngine()
    job = ConversionJob(input_path=sample_pdf, output_format="docx", output_dir=tmp_path)
    result = engine.convert(job)
    assert result.exists()
    assert result.suffix == ".docx"
    assert result.stat().st_size > 0
```

## Import ordering
```python
# 1. Standard library
import logging
import shutil
from pathlib import Path

# 2. Third-party
from PySide6.QtCore import QThreadPool, Signal
from PySide6.QtWidgets import QMainWindow
import fitz  # PyMuPDF

# 3. Local
from omnicon.core.dispatcher import ConversionDispatcher
from omnicon.core.job import ConversionJob
```
