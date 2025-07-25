"""AI inference engine interface for Sentinel.

This module provides a thin wrapper around local or cloud-based LLM inference.
Only the public contracts live here – backend implementation will be supplied
later by an autonomous agent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from pathlib import Path

__all__ = ["InferenceResult", "InferenceEngine"]


@dataclass(slots=True)
class InferenceResult:
    """Container for model output."""

    suggested_path: str
    confidence: float
    justification: str

    def as_dict(self) -> dict:
        return {
            "suggested_path": self.suggested_path,
            "confidence": self.confidence,
            "justification": self.justification,
        }


class InferenceEngine:
    """Dispatches prompts to the chosen backend and returns :class:`InferenceResult`."""

    def __init__(self, *, backend_mode: str = "local", **kwargs: Any):
        if backend_mode not in {"local", "cloud"}:
            raise ValueError("backend_mode must be 'local' or 'cloud'")
        self.backend_mode = backend_mode
        self.kwargs = kwargs  # e.g. model_path, api_key, etc.

    # ---------------------------------------------------------------------
    # Public API – to be implemented by background agent
    # ---------------------------------------------------------------------
    def analyze(self, metadata: Mapping[str, Any], content: str) -> InferenceResult:
        """Run inference on a single file.

        Parameters
        ----------
        metadata:
            Dictionary conforming to :class:`sentinel.app.core.file_scanner.FileMetadata`.
        content:
            Extracted textual content of the file.

        Returns
        -------
        InferenceResult
            Suggested destination path with confidence & justification.
        """
        path: str = metadata.get("path", "")
        ext = Path(path).suffix.lower()

        # Simple heuristic categorization
        if ext in {".jpg", ".jpeg", ".png", ".gif", ".heic"}:
            suggested = f"Photos/{Path(path).name}"
            confidence = 0.6
        elif ext in {".pdf", ".doc", ".docx", ".txt"}:
            if "invoice" in Path(path).stem.lower():
                suggested = f"Documents/Invoices/{Path(path).name}"
                confidence = 0.75
            else:
                suggested = f"Documents/{Path(path).name}"
                confidence = 0.6
        elif ext in {".py", ".js", ".ts", ".java"}:
            suggested = f"Code/{ext[1:].upper()}/{Path(path).name}"
            confidence = 0.5
        else:
            suggested = f"Other/{Path(path).name}"
            confidence = 0.3

        return InferenceResult(
            suggested_path=suggested,
            confidence=confidence,
            justification="Heuristic placeholder categorization",
        ) 