"""AI inference engine interface for Sentinel.

This module provides a thin wrapper around local or cloud-based LLM inference.
Only the public contracts live here – backend implementation will be supplied
later by an autonomous agent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from pathlib import Path

# Third-party
import json
import os
from pathlib import Path as _P

import requests

from sentinel.app.ai.prompt_builder import build_prompt
from sentinel.app.config_manager import CONFIG_PATH

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
        # Build prompt for LLM
        prompt = build_prompt(metadata, content)

        if self.backend_mode == "local":
            url = "http://127.0.0.1:8080/completion"
            payload = {
                "prompt": prompt,
                "max_tokens": 512,
                "temperature": 0.2,
                "stop": ["\n\n"],
                "stream": False,
            }
            try:
                resp = requests.post(url, json=payload, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                raw_text = data.get("choices", [{}])[0].get("text", "{}")
            except Exception as exc:  # noqa: BLE001
                return InferenceResult(
                    suggested_path=str(Path(metadata.get("path", "")).name),
                    confidence=0.0,
                    justification=f"Local inference error: {exc}",
                )
        else:  # cloud
            # Read endpoint / api key from config
            try:
                import yaml

                cfg = yaml.safe_load(CONFIG_PATH.read_text())
                endpoint = cfg.get("cloud_endpoint")
                api_key = cfg.get("cloud_api_key")
            except Exception:
                endpoint = None
                api_key = None

            if not endpoint:
                return InferenceResult(
                    suggested_path=str(Path(metadata.get("path", "")).name),
                    confidence=0.0,
                    justification="Cloud endpoint not configured",
                )

            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            payload = {"prompt": prompt, "max_tokens": 512}
            try:
                resp = requests.post(endpoint, json=payload, headers=headers, timeout=60)
                resp.raise_for_status()
                raw_text = resp.json().get("content", "{}")
            except Exception as exc:  # noqa: BLE001
                return InferenceResult(
                    suggested_path=str(Path(metadata.get("path", "")).name),
                    confidence=0.0,
                    justification=f"Cloud inference error: {exc}",
                )

        # Parse model JSON
        try:
            obj = json.loads(raw_text)
            return InferenceResult(
                suggested_path=obj["suggested_path"],
                confidence=float(obj.get("confidence_score", obj.get("confidence", 0.0))),
                justification=obj.get("justification", ""),
            )
        except Exception as exc:  # noqa: BLE001
            return InferenceResult(
                suggested_path=str(Path(metadata.get("path", "")).name),
                confidence=0.0,
                justification=f"Parse error: {exc}",
            ) 