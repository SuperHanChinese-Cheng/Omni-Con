# OmniCon — Development Roadmap

## Phase 1: MVP (Weeks 1–4)
> Goal: working app that handles the core PDF + Office + image conversions

### Week 1: Scaffold + Core
- [ ] Initialize project: pyproject.toml, src/ structure, .venv, ruff config
- [ ] Implement BaseEngine ABC and EngineRegistry
- [ ] Implement ConversionJob dataclass with status enum (QUEUED, RUNNING, DONE, FAILED)
- [ ] Implement ConversionDispatcher with fallback chain logic
- [ ] Write deps.py — detect LibreOffice, Poppler, Ghostscript on all 3 platforms
- [ ] Write mime.py — reliable MIME detection using python-magic with mimetypes fallback
- [ ] Write initial tests: test_dispatcher.py, test_registry.py

### Week 2: PDF + Image Engines
- [ ] Implement pdf_engine.py:
  - PDF → text (PyMuPDF page.get_text())
  - PDF → DOCX (pdf2docx with multiprocessing)
  - PDF → PNG/JPG (PyMuPDF page.get_pixmap())
  - PDF → HTML (PyMuPDF page.get_text("html"))
- [ ] Implement image_engine.py:
  - Images → PDF (img2pdf, lossless)
  - Image format conversions (Pillow: PNG/JPG/WEBP/BMP/TIFF)
  - SVG → PNG/PDF (CairoSVG)
- [ ] Implement office_engine.py:
  - DOCX/PPTX/XLSX → PDF (LibreOffice headless subprocess)
  - Auto-detect MS Office on Windows → prefer docx2pdf COM path
- [ ] Write test_engines.py with sample fixture files

### Week 3: GUI Shell
- [ ] PySide6 + QFluentWidgets app bootstrap (app.py, __main__.py)
- [ ] MainWindow with:
  - Drag-and-drop zone (accept files)
  - Format selector dropdown (output format based on input MIME)
  - "Convert" button
  - Output directory picker
- [ ] QueuePanel:
  - List of ConversionJobs with per-job progress bar
  - Status indicators (queued/running/done/failed)
  - Cancel button per job
- [ ] QThreadPool worker integration — GUI stays responsive during conversion
- [ ] First-run dialog: detect LibreOffice, prompt to install if missing
- [ ] SettingsDialog: LibreOffice path override, default output dir

### Week 4: Polish + Package
- [ ] Error handling: user-friendly error messages for common failures
- [ ] Batch mode: drag multiple files, queue all conversions
- [ ] Basic logging: file-based log + status bar messages
- [ ] PyInstaller spec file — build --onedir for Windows/macOS/Linux
- [ ] Code-sign on Windows (Authenticode) and macOS (Developer ID) if certs available
- [ ] Smoke test on all 3 platforms
- [ ] Tag v0.1.0

## Phase 2: Cross-Format + Quality (Weeks 5–8)

### Week 5: Pandoc + Markdown Engine
- [ ] Implement pandoc_engine.py:
  - Markdown → PDF (via WeasyPrint pdf engine)
  - Markdown → DOCX
  - Markdown → HTML
  - DOCX → Markdown
- [ ] Bundle Pandoc via pypandoc_binary — no user install needed
- [ ] Tests for all Pandoc routes

### Week 6: Table Extraction + HTML Engine
- [ ] Implement table_engine.py:
  - PDF → XLSX via Camelot (lattice + stream modes)
  - Fallback: pdfplumber for borderless tables
  - Output via pandas ExcelWriter + openpyxl
- [ ] Implement html_engine.py:
  - HTML → PDF (WeasyPrint)
  - DOCX → HTML (mammoth for semantic HTML)
- [ ] Ship Ghostscript in Windows installer for Camelot
- [ ] XLSX ↔ CSV (pandas, trivial)

### Week 7: Remaining Cross-Format Routes
- [ ] PDF → PPTX (image-based: PyMuPDF render → python-pptx slide backgrounds)
  - Add clear "non-editable slides" warning in UI
- [ ] PPTX → DOCX (text extraction via python-pptx → python-docx)
  - Add "content-only, no layout" notice
- [ ] DOCX → PPTX (DOCX → PDF → image PPTX pipeline)
- [ ] Wire unoserver for batch Office conversions (persistent LO process)

### Week 8: Batch Mode + UX
- [ ] Batch mode toggle in UI — parallel conversion with unoserver pool
- [ ] Progress reporting: per-file + overall batch progress
- [ ] Conversion history panel (recent conversions, re-convert, open output)
- [ ] Keyboard shortcuts (Ctrl+O open, Ctrl+Q quit, etc.)
- [ ] System tray integration (optional, minimize to tray)
- [ ] Tag v0.2.0

## Phase 3: Differentiators (Weeks 9–12+)

### AI Mode Plugin (Optional)
- [ ] Add Docling (MIT, CPU-friendly) as optional "AI mode" for high-quality PDF → Markdown/JSON
- [ ] Add PyMuPDF4LLM for fast PDF → Markdown (no GPU required)
- [ ] Toggle in settings: "Use AI-enhanced conversion" (off by default)
- [ ] Defer Marker until GPU build is justified

### OCR Support
- [ ] Tesseract OCR integration for scanned PDFs
- [ ] Auto-detect image-only PDFs and offer OCR before conversion
- [ ] OCR language selection in settings

### Polish + Distribution
- [ ] Nuitka build alongside PyInstaller (reduce AV false positives)
- [ ] Auto-update checker (check GitHub releases)
- [ ] Installer: NSIS on Windows, DMG on macOS, AppImage on Linux
- [ ] User documentation / help pages
- [ ] Tag v1.0.0

## Conversion Support Matrix (Target)

| From \ To    | PDF | DOCX | PPTX | XLSX | PNG/JPG | HTML | Markdown | Text | CSV |
|-------------|-----|------|------|------|---------|------|----------|------|-----|
| **PDF**     | —   | ✅   | ⚠️   | ⚠️   | ✅      | ✅   | ✅       | ✅   | —   |
| **DOCX**    | ✅  | —    | ⚠️   | —    | —       | ✅   | ✅       | ✅   | —   |
| **PPTX**    | ✅  | ⚠️   | —    | —    | —       | —    | —        | ✅   | —   |
| **XLSX**    | ✅  | —    | —    | —    | —       | —    | —        | —    | ✅  |
| **PNG/JPG** | ✅  | —    | —    | —    | ✅      | —    | —        | —    | —   |
| **HTML**    | ✅  | —    | —    | —    | —       | —    | ✅       | ✅   | —   |
| **Markdown**| ✅  | ✅   | —    | —    | —       | ✅   | —        | ✅   | —   |
| **CSV**     | —   | —    | —    | ✅   | —       | —    | —        | —    | —   |
| **SVG**     | ✅  | —    | —    | —    | ✅      | —    | —        | —    | —   |

✅ = full fidelity  ⚠️ = lossy / best-effort (documented in UI)
