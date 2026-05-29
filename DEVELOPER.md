# OmniCon — Universal Desktop File Converter

## Project overview
OmniCon is a cross-platform (Windows/macOS/Linux) desktop file converter built with Python + PySide6. It converts anything-to-anything: PDF ↔ Word/PPTX/XLSX/images/HTML/text, Office cross-format, Markdown, and image format swaps. The architecture uses a three-tier engine dispatcher (native Python libs → LibreOffice headless → Pandoc) with specialist libraries per conversion route.

## Tech stack
- **Language**: Python 3.11+
- **GUI**: PySide6 (Qt 6, LGPL) + QFluentWidgets for modern Fluent/WinUI3 look
- **PDF core**: PyMuPDF (fitz), pdf2docx, pdf2image, img2pdf, pdfminer.six
- **Office**: python-docx, python-pptx, openpyxl, pandas
- **Conversion engines**: LibreOffice headless (subprocess/unoserver), pypandoc, WeasyPrint
- **Images**: Pillow, CairoSVG
- **Packaging**: PyInstaller (v1), Nuitka (v2)
- **Testing**: pytest + pytest-qt

## Bash commands
```bash
# Dev environment
python -m venv .venv && source .venv/bin/activate  # Linux/macOS
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -e ".[dev]"

# Run the app
python -m omnicon

# Run tests
pytest tests/ -v
pytest tests/test_engines.py -v -k "test_pdf_to_docx"  # single test

# Type checking
mypy src/ --ignore-missing-imports

# Linting
ruff check src/ tests/
ruff format src/ tests/

# Build
pyinstaller omnicon.spec --noconfirm
```

## Project structure
```
omnicon/
├── DEVELOPER.md           # Developer guide
├── pyproject.toml         # Project config + dependencies
├── requirements.txt       # Pinned deps for reproducibility
├── omnicon.spec           # PyInstaller spec (generated later)
├── src/
│   ├── __init__.py
│   ├── __main__.py        # Entry point: python -m omnicon
│   ├── app.py             # QApplication bootstrap
│   ├── core/
│   │   ├── __init__.py
│   │   ├── dispatcher.py  # ConversionDispatcher — routes input→engine
│   │   ├── registry.py    # EngineRegistry — registers all engines
│   │   ├── job.py         # ConversionJob dataclass + status enum
│   │   └── worker.py      # QThreadPool worker for async conversion
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── base.py        # BaseEngine ABC
│   │   ├── pdf_engine.py  # PyMuPDF, pdf2docx, pdfminer routes
│   │   ├── office_engine.py  # LibreOffice headless + docx2pdf fallback
│   │   ├── image_engine.py   # Pillow, img2pdf, CairoSVG, pdf2image
│   │   ├── pandoc_engine.py  # pypandoc wrapper
│   │   ├── html_engine.py    # WeasyPrint, mammoth
│   │   └── table_engine.py   # Camelot, pdfplumber → XLSX extraction
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py # Main window with drag-drop zone + queue
│   │   ├── queue_panel.py # Conversion queue with per-job progress
│   │   ├── settings_dialog.py  # LibreOffice path, default output dir
│   │   └── widgets/       # Reusable custom widgets
│   └── utils/
│       ├── __init__.py
│       ├── mime.py         # MIME detection (python-magic or mimetypes)
│       ├── deps.py         # System dependency checker (LibreOffice, Poppler, etc.)
│       └── paths.py        # Platform-aware path resolution
├── tests/
│   ├── conftest.py         # Shared fixtures, sample files
│   ├── test_dispatcher.py
│   ├── test_engines.py
│   ├── test_gui.py
│   └── fixtures/           # Sample PDF/DOCX/PPTX/images for testing
├── docs/
│   ├── ROADMAP.md
│   ├── ARCHITECTURE.md
│   └── CONVENTIONS.md
└── scripts/
    └── check_deps.py      # CLI script to verify system deps
```

## Code style
- Python 3.11+ — use modern syntax: `match/case`, `type` aliases, `Self`, `|` union types
- Format with **ruff** (line length 100, double quotes)
- Type hints on all function signatures — no `Any` unless unavoidable
- Docstrings: Google style, required on all public classes/methods
- Imports: group as stdlib → third-party → local, one blank line between groups
- Use `pathlib.Path` everywhere — never raw string paths
- Use `logging` module, never `print()` for status/debug output
- Prefer composition over inheritance for engines
- All engine methods must be thread-safe (no shared mutable state)

## Architecture rules
- **Every conversion route** must go through ConversionDispatcher — never call engines directly from GUI code
- **Engines implement BaseEngine ABC** with `can_convert(src_fmt, dst_fmt) -> bool` and `convert(job: ConversionJob) -> Path`
- **Fallback chains**: dispatcher tries engines in priority order; if engine A raises, try B, then C. Log each attempt.
- **GUI thread never blocks**: all conversion work runs in QThreadPool workers. Workers emit signals for progress/completion/error.
- **No engine should import GUI code** — clean dependency direction: gui → core → engines
- **LibreOffice calls go through a single subprocess wrapper** in office_engine.py — never scatter `subprocess.run(["soffice", ...])` calls

## Testing rules
- Every new engine method needs a corresponding test
- Use pytest fixtures for sample files (keep small: <100KB per fixture)
- Mock subprocess calls for LibreOffice/Pandoc in unit tests
- Integration tests (marked `@pytest.mark.integration`) can use real LibreOffice
- Run `pytest tests/ -v` and confirm green before committing

## Git workflow
- Branch per feature: `feat/pdf-to-docx`, `fix/libreoffice-detection`, `refactor/engine-registry`
- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- Never commit directly to `main` — always branch + PR
- Keep commits atomic — one logical change per commit

## Key decisions & constraints
- **LibreOffice is an external dependency** — not bundled. App detects it at first launch and prompts user to install if missing. Store user-configured path in QSettings.
- **PyMuPDF (AGPL)** — if we go closed-source later, budget for Artifex commercial license
- **pdf2docx** is the primary PDF→DOCX engine; LibreOffice is fallback
- **PDF→PPTX is image-based** (page renders as slide backgrounds via python-pptx) — no editable text. Show clear warning in UI.
- **PDF→XLSX** is table extraction (Camelot/pdfplumber), not full document conversion. Frame as "Extract tables to Excel" in UI.
- **Batch mode** uses unoserver (persistent LibreOffice process) for performance — spawning `soffice` per file is too slow for 50+ files

## What NOT to do
- Don't use Tkinter or CustomTkinter — we chose PySide6 + QFluentWidgets
- Don't use wkhtmltopdf — it's archived/EOL. Use WeasyPrint for HTML→PDF
- Don't use PyPDF2 — use pypdf or PyMuPDF instead
- Don't hardcode paths — use pathlib + platform detection
- Don't catch bare `Exception` — catch specific exceptions, let unexpected ones bubble
- Don't add ML/AI engines (Docling, Marker) in Phase 1 — they're Phase 3
- Don't try to bundle LibreOffice inside the installer — it's 400MB+ and creates update nightmares

## Reference docs
- @docs/ROADMAP.md — phased implementation plan
- @docs/ARCHITECTURE.md — engine dispatcher design, conversion matrix
- @docs/CONVENTIONS.md — detailed code conventions and patterns
