# OmniCon — Architecture

## High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│                    PySide6 GUI Layer                     │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ MainWindow│  │ QueuePanel   │  │ SettingsDialog   │   │
│  │ (drag-drop│  │ (job list +  │  │ (LO path, output │   │
│  │  + format │  │  progress)   │  │  dir, prefs)     │   │
│  │  selector)│  │              │  │                  │   │
│  └─────┬─────┘  └──────┬───────┘  └──────────────────┘   │
│        │               │                                 │
│        └───────┬───────┘                                 │
│                ▼                                         │
│        ┌───────────────┐                                 │
│        │ QThreadPool   │  ← GUI never blocks             │
│        │ Worker        │                                 │
│        └───────┬───────┘                                 │
└────────────────┼─────────────────────────────────────────┘
                 │ emits: progress(int), finished(Path), error(str)
                 ▼
┌─────────────────────────────────────────────────────────┐
│                    Core Layer                            │
│  ┌────────────────────────────────────────────────────┐  │
│  │ ConversionDispatcher                               │  │
│  │  - detect(input_mime, output_format) → Engine      │  │
│  │  - convert(job) → tries engines in priority order  │  │
│  │  - fallback chain: Engine A → B → C → error        │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │                                │
│  ┌──────────────────────▼─────────────────────────────┐  │
│  │ EngineRegistry                                     │  │
│  │  - register(engine: BaseEngine)                    │  │
│  │  - get_engines(src_fmt, dst_fmt) → list[BaseEngine]│  │
│  │  - engines sorted by priority (lower = preferred)  │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌────────────────────────────────┐   │
│  │ ConversionJob│  │ Worker (QRunnable)              │   │
│  │  - input_path│  │  - wraps dispatcher.convert()   │   │
│  │  - output_fmt│  │  - emits signals to GUI thread  │   │
│  │  - output_dir│  │  - handles cancellation         │   │
│  │  - status    │  │                                 │   │
│  │  - progress  │  │                                 │   │
│  └──────────────┘  └────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│                    Engine Layer                          │
│                                                          │
│  All engines implement BaseEngine ABC:                   │
│    can_convert(src: str, dst: str) -> bool               │
│    convert(job: ConversionJob) -> Path                   │
│    priority: int  (lower = tried first)                  │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ PDFEngine   │  │ OfficeEngine │  │ ImageEngine  │   │
│  │ priority: 10│  │ priority: 50 │  │ priority: 10 │   │
│  │             │  │              │  │              │   │
│  │ PyMuPDF     │  │ LibreOffice  │  │ Pillow       │   │
│  │ pdf2docx    │  │ headless     │  │ img2pdf      │   │
│  │ pdfminer    │  │ docx2pdf     │  │ CairoSVG     │   │
│  │             │  │ unoserver    │  │ pdf2image    │   │
│  └─────────────┘  └──────────────┘  └──────────────┘   │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ PandocEngine│  │ HTMLEngine   │  │ TableEngine  │   │
│  │ priority: 30│  │ priority: 20 │  │ priority: 15 │   │
│  │             │  │              │  │              │   │
│  │ pypandoc    │  │ WeasyPrint   │  │ Camelot      │   │
│  │ (bundled    │  │ mammoth      │  │ pdfplumber   │   │
│  │  binary)    │  │              │  │ → pandas     │   │
│  └─────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Dependency Direction (strict)

```
gui → core → engines → third-party libs
 ↓
 NEVER: engines → gui
 NEVER: core → gui
```

GUI imports core. Core imports engines. Engines import only third-party libs and utils.
No engine should ever import from `gui/`. No core module should import from `gui/`.

## Engine Priority System

Each engine has a `priority: int` attribute. Lower numbers are tried first.
The dispatcher collects all engines that `can_convert(src, dst)` and sorts by priority.

Typical priority assignments:
- 10: Native Python specialist (PyMuPDF, Pillow, img2pdf) — fastest, no external deps
- 15: Table extraction (Camelot) — specialized, needs Ghostscript
- 20: HTML specialist (WeasyPrint, mammoth) — pure Python, no external deps
- 30: Pandoc (needs bundled binary, but fast)
- 50: LibreOffice headless (slowest, but most versatile fallback)
- 60: COM automation / docx2pdf (Windows-only, needs MS Office)

## ConversionJob Lifecycle

```
QUEUED → RUNNING → DONE
                 → FAILED (with error message)
                 → CANCELLED (user cancelled)
```

Jobs are immutable after creation except for status, progress, and output_path fields.
Workers update these via Qt signals, never by direct mutation from the GUI thread.

## System Dependency Detection

At first launch, `deps.py` checks for:

| Dependency       | Detection method                           | Required? |
|------------------|--------------------------------------------|-----------|
| LibreOffice      | `which soffice` / registry scan (Windows)  | Yes (for Office↔PDF) |
| Poppler          | `which pdftoppm`                           | No (PyMuPDF is primary) |
| Ghostscript      | `which gs` / `gswin64c.exe`               | No (only for Camelot) |
| Tesseract        | `which tesseract`                          | No (Phase 3 OCR) |
| MS Office (Win)  | COM registration check                    | No (enhances quality) |

Missing required deps trigger a setup dialog. Missing optional deps disable specific routes
and show a tooltip explaining why.

## Batch Conversion Strategy

Single file: spawn `soffice --headless` per conversion (simple, isolated).
Batch (>5 files): start a `unoserver` listener, route all Office conversions through it.
Kill the listener when batch completes or app closes.

```python
# Pseudocode for batch strategy
if batch_size > UNOSERVER_THRESHOLD:
    start_unoserver()
    for job in batch:
        convert_via_unoserver(job)
    stop_unoserver()
else:
    for job in batch:
        convert_via_subprocess(job)
```

## Error Handling Strategy

1. Engine raises specific exception (e.g., `LibreOfficeNotFoundError`, `PDFParseError`)
2. Dispatcher catches it, logs it, tries next engine in fallback chain
3. If all engines fail, dispatcher raises `ConversionError` with details of all attempts
4. Worker catches `ConversionError`, emits `error` signal with user-friendly message
5. GUI shows error in queue panel with "Details" expandable section

Never swallow exceptions silently. Never show raw tracebacks to users.
