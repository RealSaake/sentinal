"""AI inference engine interface for Sentinel.

This module provides a thin wrapper around local or cloud-based LLM inference.
Only the public contracts live here – backend implementation will be supplied
later by an autonomous agent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional
from pathlib import Path
import time

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

    def __init__(self, *, backend_mode: str = "local", logger_manager=None, performance_monitor=None, **kwargs: Any):
        if backend_mode not in {"local", "cloud"}:
            raise ValueError("backend_mode must be 'local' or 'cloud'")
        self.backend_mode = backend_mode
        self.kwargs = kwargs  # e.g. model_path, api_key, etc.
        self.logger_manager = logger_manager
        self.performance_monitor = performance_monitor
        
        if self.logger_manager:
            self.logger = self.logger_manager.get_logger('inference_engine')
            self.logger.info(f"InferenceEngine initialized with backend_mode: {backend_mode}")

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
        file_path = metadata.get("path", "unknown")
        start_time = time.perf_counter()
        
        if self.logger_manager:
            self.logger.info(f"Starting AI inference for file: {file_path}")
            self.logger.debug(f"File metadata: {dict(metadata)}")
            self.logger.debug(f"Content length: {len(content)} characters")
        
        # Start performance monitoring
        operation_id = None
        if self.performance_monitor:
            operation_id = self.performance_monitor.start_operation(
                'ai_inference', 
                {'file_path': file_path, 'backend': self.backend_mode}
            )
        
        try:
            # Build prompt for LLM
            prompt = build_prompt(metadata, content)
            
            if self.logger_manager:
                self.logger.debug(f"Generated prompt length: {len(prompt)} characters")

            if self.backend_mode == "local":
                result = self._process_local_inference(prompt, file_path)
            else:  # cloud
                result = self._process_cloud_inference(prompt, file_path)
            
            # Calculate duration and log success
            duration = time.perf_counter() - start_time
            
            if self.logger_manager:
                self.logger.info(f"AI inference completed successfully in {duration:.3f}s - "
                               f"Suggested: {result.suggested_path}, Confidence: {result.confidence}")
            
            # Record performance metrics
            if self.performance_monitor:
                if operation_id:
                    self.performance_monitor.end_operation(operation_id, success=True)
                self.performance_monitor.log_ai_request(
                    duration=duration,
                    success=True,
                    model_name="llama3.2:3b" if self.backend_mode == "local" else "cloud"
                )
            
            return result
            
        except Exception as exc:
            # Calculate duration and log error
            duration = time.perf_counter() - start_time
            error_msg = str(exc)
            
            if self.logger_manager:
                self.logger.error(f"AI inference failed after {duration:.3f}s for file {file_path}: {error_msg}")
                self.logger.debug(f"Full exception details", exc_info=True)
            
            # Record performance metrics for failure
            if self.performance_monitor:
                if operation_id:
                    self.performance_monitor.end_operation(operation_id, success=False, error_message=error_msg)
                self.performance_monitor.log_ai_request(
                    duration=duration,
                    success=False,
                    model_name="llama3.2:3b" if self.backend_mode == "local" else "cloud",
                    error_message=error_msg
                )
            
            # Return fallback result
            return InferenceResult(
                suggested_path=str(Path(metadata.get("path", "")).name),
                confidence=0.0,
                justification=f"Inference error: {error_msg}",
            )
    
    def _process_local_inference(self, prompt: str, file_path: str) -> InferenceResult:
        """Process inference using local Ollama backend."""
        url = "http://127.0.0.1:11434/api/generate"
        payload = {
            "model": "llama3.2:3b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 512,
            }
        }
        
        if self.logger_manager:
            self.logger.debug(f"Sending request to local AI backend: {url}")
        
        try:
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data.get("response", "{}")
            
            if self.logger_manager:
                self.logger.debug(f"Received response from local AI backend, length: {len(raw_text)}")
            
        except requests.exceptions.ConnectionError as exc:
            error_msg = "Local AI server (Ollama) is not running or not accessible"
            if self.logger_manager:
                self.logger.error(f"Connection error to local AI backend: {error_msg}")
            raise Exception(error_msg) from exc
        except requests.exceptions.Timeout as exc:
            error_msg = "Local AI server request timed out after 60 seconds"
            if self.logger_manager:
                self.logger.error(f"Timeout error with local AI backend: {error_msg}")
            raise Exception(error_msg) from exc
        except Exception as exc:
            if self.logger_manager:
                self.logger.error(f"Unexpected error with local AI backend: {exc}")
            raise
        
        return self._parse_ai_response(raw_text, file_path)
    
    def _process_cloud_inference(self, prompt: str, file_path: str) -> InferenceResult:
        """Process inference using cloud backend."""
        # Read endpoint / api key from config
        try:
            import yaml
            cfg = yaml.safe_load(CONFIG_PATH.read_text())
            endpoint = cfg.get("cloud_endpoint")
            api_key = cfg.get("cloud_api_key")
        except Exception as exc:
            if self.logger_manager:
                self.logger.error(f"Failed to read cloud configuration: {exc}")
            endpoint = None
            api_key = None

        if not endpoint:
            error_msg = "Cloud endpoint not configured"
            if self.logger_manager:
                self.logger.error(error_msg)
            raise Exception(error_msg)

        if self.logger_manager:
            self.logger.debug(f"Sending request to cloud AI backend: {endpoint}")

        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        payload = {"prompt": prompt, "max_tokens": 512}
        
        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            raw_text = resp.json().get("content", "{}")
            
            if self.logger_manager:
                self.logger.debug(f"Received response from cloud AI backend, length: {len(raw_text)}")
                
        except Exception as exc:
            if self.logger_manager:
                self.logger.error(f"Cloud AI backend error: {exc}")
            raise
        
        return self._parse_ai_response(raw_text, file_path)
    
    def _parse_ai_response(self, raw_text: str, file_path: str) -> InferenceResult:
        """Parse the AI response into an InferenceResult."""
        try:
            obj = json.loads(raw_text)
            
            result = InferenceResult(
                suggested_path=obj["suggested_path"],
                confidence=float(obj.get("confidence_score", obj.get("confidence", 0.0))),
                justification=obj.get("justification", ""),
            )
            
            if self.logger_manager:
                self.logger.debug(f"Successfully parsed AI response for {file_path}")
            
            return result
            
        except json.JSONDecodeError as exc:
            error_msg = f"Failed to parse AI response as JSON: {exc}"
            if self.logger_manager:
                self.logger.error(f"{error_msg}. Raw response: {raw_text[:200]}...")
            raise Exception(error_msg) from exc
        except KeyError as exc:
            error_msg = f"Missing required field in AI response: {exc}"
            if self.logger_manager:
                self.logger.error(f"{error_msg}. Response: {raw_text[:200]}...")
            raise Exception(error_msg) from exc
        except Exception as exc:
            error_msg = f"Unexpected error parsing AI response: {exc}"
            if self.logger_manager:
                self.logger.error(error_msg)
            raise Exception(error_msg) from exc 