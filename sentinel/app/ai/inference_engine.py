from __future__ import annotations

import abc
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import yaml

logger = logging.getLogger(__name__)


def _load_config() -> Dict[str, Any]:
    cfg_path = Path(__file__).resolve().parent.parent.parent / "config" / "config.yaml"
    if cfg_path.exists():
        with cfg_path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    return {}


def _safe_parse_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    logger.warning("Unable to parse JSON from LLM output: %s", text)
    return None


class InferenceEngine(abc.ABC):
    @abc.abstractmethod
    def get_organization_suggestion(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Return the LLM's suggestion parsed as a dict or None on failure."""


class LocalInferenceEngine(InferenceEngine):
    def __init__(self, server_url: str = "http://127.0.0.1:8080/completion"):
        self.server_url = server_url

    def get_organization_suggestion(self, prompt: str) -> Optional[Dict[str, Any]]:
        payload = {
            "prompt": prompt,
            "temperature": 0.2,
            "max_tokens": 512,
            "stop": ["</s>"],
        }
        try:
            resp = requests.post(self.server_url, json=payload, timeout=120)
            resp.raise_for_status()
            if resp.headers.get("content-type", "").startswith("application/json"):
                data = resp.json()
                llm_output = data.get("content") or data.get("text") or json.dumps(data)
            else:
                llm_output = resp.text
            return _safe_parse_json(llm_output)
        except (requests.RequestException, json.JSONDecodeError) as exc:
            logger.error("Local LLM request failed: %s", exc)
            return None


class CloudInferenceEngine(InferenceEngine):
    def __init__(self):
        cfg = _load_config()
        self.endpoint = cfg.get("cloud_api_endpoint")
        self.api_key = cfg.get("cloud_api_key")
        if not self.endpoint:
            raise ValueError("cloud_api_endpoint missing in config.yaml")
        if not self.api_key:
            logger.warning("cloud_api_key is empty; requests may fail.")

    def get_organization_suggestion(self, prompt: str) -> Optional[Dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "Content-Type": "application/json",
        }
        payload = {"prompt": prompt}
        try:
            resp = requests.post(self.endpoint, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            if resp.headers.get("content-type", "").startswith("application/json"):
                data = resp.json()
                llm_output = (
                    data.get("choices", [{}])[0].get("message", {}).get("content")
                    if "choices" in data
                    else data.get("content") or json.dumps(data)
                )
            else:
                llm_output = resp.text
            return _safe_parse_json(llm_output)
        except (requests.RequestException, json.JSONDecodeError) as exc:
            logger.error("Cloud LLM request failed: %s", exc)
            return None 