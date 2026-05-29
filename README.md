# OmniCon — Universal Desktop File Converter

Convert anything to anything. PDF ↔ Word, PowerPoint, Excel, images, HTML, Markdown, and more.

## Features

- **PDF as hub**: PDF → DOCX, PPTX, XLSX, PNG/JPG, HTML, text — and back
- **Office cross-format**: DOCX ↔ HTML, PPTX → DOCX, XLSX ↔ CSV
- **Markdown**: MD → PDF, DOCX, HTML via Pandoc
- **Images**: PNG, JPG, WEBP, BMP, TIFF, SVG conversions
- **Batch mode**: drag multiple files, convert in parallel
- **Modern UI**: PySide6 + Fluent design, drag-and-drop, progress tracking
- **Cross-platform**: Windows, macOS, Linux

## Requirements

- Python 3.11+
- LibreOffice 7.6+ (for Office ↔ PDF conversions)
- Ghostscript (optional, for PDF table extraction)

## Quick Start

```bash
git clone https://github.com/yourname/omnicon.git
cd omnicon
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
python -m omnicon
```

## Development

```bash
pytest tests/ -v          # run tests
ruff check src/ tests/    # lint
ruff format src/ tests/   # format
mypy src/                 # type check
```

## License

MIT
