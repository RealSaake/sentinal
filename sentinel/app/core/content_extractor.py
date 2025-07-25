from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import filetype
from PIL import Image
import pytesseract
import fitz  # PyMuPDF
from docx import Document
from psd_tools import PSDImage

logger = logging.getLogger(__name__)


def _extract_from_image(pth: Path) -> Dict[str, Any]:
    with Image.open(pth) as img:
        img.verify()
    with Image.open(pth) as img:
        ocr_text = ""
        try:
            ocr_text = pytesseract.image_to_string(img)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Tesseract OCR failed for %s: %s", pth, exc)
        return {"image_object": img, "ocr_text": ocr_text.strip()}


def _extract_from_pdf(pth: Path) -> str:
    text_chunks: list[str] = []
    try:
        doc = fitz.open(pth)
        for page in doc:
            text_chunks.append(page.get_text())
    finally:
        if "doc" in locals():
            doc.close()
    return "\n".join(text_chunks).strip()


def _extract_from_docx(pth: Path) -> str:
    doc = Document(pth)
    return "\n".join(p.text for p in doc.paragraphs).strip()


def _extract_from_psd(pth: Path) -> str:
    psd = PSDImage.open(pth)
    text_layers = []
    for layer in psd.descendants():
        if layer.is_text_layer():
            try:
                text_layers.append(layer.text_data.text)
            except Exception:
                continue
    return "\n".join(text_layers).strip()


def extract_content(file_path: str | Path) -> Optional[Any]:
    """Extract text/content from a file depending on its MIME type."""
    pth = Path(file_path)
    kind = filetype.guess(str(pth))
    mime = kind.mime if kind else None

    try:
        if mime and mime.startswith("image/"):
            return _extract_from_image(pth)
        if mime == "application/pdf":
            return _extract_from_pdf(pth)
        if mime in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ):
            return _extract_from_docx(pth)
        if mime == "image/vnd.adobe.photoshop" or pth.suffix.lower() == ".psd":
            return _extract_from_psd(pth)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to extract content from %s: %s", file_path, exc)
    return None 