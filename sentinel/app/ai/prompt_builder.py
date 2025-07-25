"""Prompt construction helpers for Sentinel.

Responsible for turning file metadata + extracted content into a formatted
prompt consumable by an LLM.  The actual template filling logic will be
implemented by a background agent.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "prompt_templates.json"

__all__ = ["build_prompt"]


# ---------------------------------------------------------------------------
# Public API – to be implemented by background agent
# ---------------------------------------------------------------------------

def build_prompt(metadata: Mapping[str, Any], content: str) -> str:
    """Return a prompt string ready for model inference.

    Expected steps (backend agent):
    1. Load *system_prompt* and any *few_shot_examples* from
       ``config/prompt_templates.json``.
    2. Interpolate *metadata* & *content* into the user prompt.
    3. Return a single string – *no* additional JSON serialization required.
    """
    import json
    import yaml
    import json
    try:
        import json
        import pathlib
        import json
        with CONFIG_PATH.open("r", encoding="utf-8") as fp:
            tpl = json.load(fp)
        system_prompt = tpl.get("system_prompt", "Organize files")
    except Exception:
        system_prompt = "Organize files"

    prompt_parts = [system_prompt, "\n", "### File Metadata", json.dumps(metadata, ensure_ascii=False, indent=2)]

    if content:
        snippet = content[:1000]
        prompt_parts.extend(["\n", "### Content Snippet (truncated)", snippet])

    prompt_parts.append("\n### Respond with JSON as specified earlier")

    return "\n".join(prompt_parts) 