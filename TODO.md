# OmniCon — TODO

## Now
- [ ] First-run LibreOffice detection dialog
- [ ] Settings dialog (LO path override, default output dir)
- [ ] Batch mode + unoserver for high-volume Office conversions

## Later
- [ ] Table extraction engine (Camelot/pdfplumber -> XLSX)
- [ ] OCR support (Tesseract) for scanned PDFs
- [ ] Auto-update checker
- [ ] Nuitka build (reduce AV false positives)
- [ ] Code signing (Authenticode)

## Done
- [x] Project scaffold (CLAUDE.md, docs, pyproject.toml, source structure)
- [x] Initialize git repo
- [x] Set up virtual environment and install deps
- [x] Fix pyproject.toml build-backend (was invalid setuptools path)
- [x] Implement EngineRegistry (core/registry.py)
- [x] Implement ConversionDispatcher with fallback chain (core/dispatcher.py)
- [x] Implement PDFEngine — PDF -> text, DOCX, PNG/JPG, HTML (engines/pdf_engine.py)
- [x] Implement OfficeEngine — LibreOffice headless subprocess wrapper (engines/office_engine.py)
- [x] Implement ImageEngine — Pillow + img2pdf + CairoSVG (engines/image_engine.py)
- [x] Implement TextEngine — DOCX/PPTX/XLSX -> TXT, XLSX <-> CSV (engines/text_engine.py)
- [x] Implement HTMLEngine — HTML <-> PDF, DOCX -> HTML (engines/html_engine.py)
- [x] Implement PandocEngine — Markdown <-> DOCX/HTML/PDF/TXT (engines/pandoc_engine.py)
- [x] ConversionWorker — QRunnable thread pool worker (core/worker.py)
- [x] MainWindow GUI — drag-drop zone, format selector, queue panel (gui/main_window.py)
- [x] App bootstrap (app.py)
- [x] Fix worker GC race condition (setAutoDelete + strong references)
- [x] Fix Unicode logging crash on Windows (-> instead of arrow)
- [x] Fix LibreOffice PDF import filter (--infilter=writer_pdf_import)
- [x] Fix pdf2docx Converter cleanup (try/finally)
- [x] Fidelity improvements (300 DPI renders, JPEG quality=95, pdf2docx single-threaded)
- [x] PyInstaller build — OmniCon.exe (dist/OmniCon/)
- [x] NSIS installer — OmniConSetup.exe (260MB)
- [x] Tests: 73 passing across 9 test files
