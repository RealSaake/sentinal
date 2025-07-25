"""Content extraction helpers for Sentinel.

This module exposes a single public function – :func:`extract_content` – that
returns a **plain-text** representation of a file's contents so it can be
embedded in an LLM prompt.

Implementation details are delegated to a background agent.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

__all__ = ["extract_content"]


class SupportsFilePath(Protocol):
    """Protocol for objects exposing a ``path`` attribute."""

    path: Path


# ---------------------------------------------------------------------------
# Public API – to be implemented by background agent
# ---------------------------------------------------------------------------

def extract_content(file: str | Path | SupportsFilePath, *, ocr_languages: str = "eng") -> str:
    """Extract a textual summary / full text from *file*.

    The return value **must** be UTF-8 text (no binary).  For binary or
    otherwise unreadable formats, return an empty string.

    Implementation guidelines (for backend agent):
    • Dispatch on MIME type to specialised extractors.
    • Use **PyMuPDF** for PDFs, **python-docx** for Word documents, and **pytesseract**
      for images.
    • Keep memory usage constrained – stream large files where possible.
    • Respect *ocr_languages* when performing OCR.
    """
    from pathlib import Path as _P
    import mimetypes
    import subprocess
    import io

    path = _P(file.path if hasattr(file, "path") else file).expanduser().resolve()

    # Quick size guard: skip >10MB
    if path.stat().st_size > 10 * 1024 * 1024:
        return ""

    mime, _ = mimetypes.guess_type(path)
    if mime and mime.startswith("text"):
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as fp:
                return fp.read()
        except Exception:
            return ""

    # PDF via PyMuPDF
    if path.suffix.lower() == ".pdf":
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(path)
            texts = [page.get_text() for page in doc[:5]]  # first 5 pages
            return "\n".join(texts)
        except Exception:
            return ""

    # DOCX via python-docx
    if path.suffix.lower() in {".docx"}:
        try:
            import docx

            doc = docx.Document(path)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return ""

    # Image OCR via pytesseract
    if mime and mime.startswith("image"):
        try:
            from PIL import Image
            import pytesseract

            img = Image.open(path)
            return pytesseract.image_to_string(img, lang=ocr_languages)
        except Exception:
            return ""

    return "" 