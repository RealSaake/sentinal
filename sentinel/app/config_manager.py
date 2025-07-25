"""Lightweight loader / writer for *config/config.yaml*.

Keeps GUI code independent of YAML parsing details.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.yaml"


@dataclass(slots=True)
class AppConfig:
    database_path: str = "sentinel.db"
    default_scan_directory: str = "~/"
    ai_backend_mode: str = "local"  # "local" or "cloud"

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AppConfig":
        return cls(
            database_path=data.get("database_path", cls.database_path),
            default_scan_directory=data.get("default_scan_directory", cls.default_scan_directory),
            ai_backend_mode=data.get("ai_backend_mode", cls.ai_backend_mode),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "database_path": self.database_path,
            "default_scan_directory": self.default_scan_directory,
            "ai_backend_mode": self.ai_backend_mode,
        }


class ConfigManager:
    """Handles reading and persisting application configuration."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else CONFIG_PATH
        self.config = self._load()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def save(self) -> None:
        with self.path.open("w", encoding="utf-8") as fp:
            yaml.safe_dump(self.config.to_mapping(), fp)

    def _load(self) -> AppConfig:
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as fp:
                data = yaml.safe_load(fp) or {}
        else:
            data = {}
        return AppConfig.from_mapping(data)

    # Convenience wrappers ------------------------------------------------

    def set_backend_mode(self, mode: str) -> None:
        if mode not in {"local", "cloud"}:
            raise ValueError("Backend mode must be 'local' or 'cloud'.")
        self.config.ai_backend_mode = mode
        self.save()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ConfigManager path={self.path} backend={self.config.ai_backend_mode}>" 