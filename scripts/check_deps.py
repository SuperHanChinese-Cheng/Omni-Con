"""Check system dependencies required by OmniCon.

Run this script to verify your environment is ready:
    python scripts/check_deps.py
"""

import platform
import shutil
import subprocess
import sys
from pathlib import Path


def check_binary(name: str, test_args: list[str] | None = None) -> str | None:
    """Check if a binary exists on PATH and return its path, or None."""
    path = shutil.which(name)
    if path and test_args:
        try:
            subprocess.run(
                [path, *test_args],
                capture_output=True,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None
    return path


def check_python_version() -> bool:
    """Check Python version is 3.11+."""
    major, minor = sys.version_info[:2]
    ok = major == 3 and minor >= 11
    status = "✅" if ok else "❌"
    print(f"  {status} Python {major}.{minor} (need 3.11+)")
    return ok


def check_libreoffice() -> bool:
    """Check LibreOffice is installed."""
    # Try common binary names
    for name in ["soffice", "libreoffice"]:
        path = check_binary(name, ["--version"])
        if path:
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                version = result.stdout.strip()
                print(f"  ✅ LibreOffice: {version} ({path})")
                return True
            except (subprocess.TimeoutExpired, OSError):
                pass

    # Windows: check common install paths
    if platform.system() == "Windows":
        for prog_dir in ["C:/Program Files/LibreOffice", "C:/Program Files (x86)/LibreOffice"]:
            soffice = Path(prog_dir) / "program" / "soffice.exe"
            if soffice.exists():
                print(f"  ✅ LibreOffice found at {soffice}")
                return True

    print("  ❌ LibreOffice not found — install from https://www.libreoffice.org/download/")
    return False


def check_ghostscript() -> bool:
    """Check Ghostscript is installed (needed for Camelot table extraction)."""
    names = ["gs", "gswin64c", "gswin32c"] if platform.system() == "Windows" else ["gs"]
    for name in names:
        path = check_binary(name, ["--version"])
        if path:
            print(f"  ✅ Ghostscript: {path}")
            return True
    print("  ⚠️  Ghostscript not found — needed for PDF table extraction (optional)")
    return False


def check_poppler() -> bool:
    """Check Poppler utils are installed (optional, PyMuPDF is primary)."""
    path = check_binary("pdftoppm")
    if path:
        print(f"  ✅ Poppler: {path}")
        return True
    print("  ⚠️  Poppler not found — optional (PyMuPDF is used as primary PDF renderer)")
    return False


def check_tesseract() -> bool:
    """Check Tesseract OCR is installed (Phase 3)."""
    path = check_binary("tesseract", ["--version"])
    if path:
        print(f"  ✅ Tesseract: {path}")
        return True
    print("  ⚠️  Tesseract not found — needed for OCR on scanned PDFs (optional, Phase 3)")
    return False


def main() -> None:
    """Run all dependency checks and print a summary."""
    print("OmniCon — System Dependency Check")
    print("=" * 50)

    print("\n🐍 Python:")
    py_ok = check_python_version()

    print("\n📦 Required:")
    lo_ok = check_libreoffice()

    print("\n📦 Optional:")
    check_ghostscript()
    check_poppler()
    check_tesseract()

    print("\n" + "=" * 50)
    if py_ok and lo_ok:
        print("✅ All required dependencies found. You're good to go!")
    else:
        print("❌ Some required dependencies are missing. See above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
