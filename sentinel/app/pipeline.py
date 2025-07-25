"""Analysis pipeline orchestrator.

This layer glues core scanning/content extraction, AI inference, and database
persistence together.  It intentionally handles *only* control-flow and error
management – heavyweight tasks remain delegated to their respective modules.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from sentinel.app.core import FileMetadata, scan_directory, extract_content
from sentinel.app.ai import InferenceEngine, InferenceResult, build_prompt
from sentinel.app.db import DatabaseManager
from sentinel.app.config_manager import AppConfig


def run_analysis(directory: str | Path, *, db: DatabaseManager, config: AppConfig) -> List[dict]:
    """Run full analysis over *directory*.

    Returns a list of dictionaries suitable for consumption by ReviewDialog.
    Each dict has keys: ``original_path``, ``suggested_path``, ``confidence``,
    and ``justification``.

    This default implementation is *highly* defensive – if any stage raises
    ``NotImplementedError`` or other exceptions, it falls back to stub behavior
    so that the UI remains responsive during early development phases.
    """
    results: list[dict] = []

    try:
        db.init_schema()

        # Prepare engine according to backend mode
        engine = InferenceEngine(backend_mode=config.ai_backend_mode)

        for meta in scan_directory(directory):  # type: ignore[arg-type]
            # Persist metadata first
            file_id = db.save_scan_result(meta.as_dict())

            try:
                content = extract_content(meta.path)
                prompt = build_prompt(meta.as_dict(), content)
                inference: InferenceResult = engine.analyze(meta.as_dict(), content)  # type: ignore[arg-type]
            except NotImplementedError:
                # Placeholder inference – suggest same path
                inference = InferenceResult(
                    suggested_path=str(meta.path),
                    confidence=0.5,
                    justification="Backend not implemented",
                )
            db.save_inference(file_id, inference.as_dict())

            results.append(
                {
                    "file_id": file_id,
                    "original_path": str(meta.path),
                    "suggested_path": inference.suggested_path,
                    "confidence": inference.confidence,
                    "justification": inference.justification,
                }
            )
    except NotImplementedError:
        # If the very first call fails, fallback to stub scan
        from pathlib import Path as _P

        for path in list(_P(directory).rglob("*"))[:100]:
            results.append(
                {
                    "file_id": -1,
                    "original_path": str(path),
                    "suggested_path": str(path),
                    "confidence": 0.1,
                    "justification": "Stub – full pipeline not ready",
                }
            )
    return results 