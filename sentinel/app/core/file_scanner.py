import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

import filetype

from .integrity_checker import calculate_sha256
from ..db import database_manager

logger = logging.getLogger(__name__)


def _gather_file_metadata(file_path: Path) -> Dict:
    """Collect file metadata suitable for inserting into the database."""
    stat = file_path.stat()
    kind = filetype.guess(str(file_path))
    mime_type = kind.mime if kind else "application/octet-stream"

    return {
        "original_path": str(file_path),
        "sha256_hash": calculate_sha256(file_path),
        "file_size": stat.st_size,
        "creation_date": datetime.fromtimestamp(stat.st_ctime),
        "modification_date": datetime.fromtimestamp(stat.st_mtime),
        "mime_type": mime_type,
        "ai_suggested_path": None,
        "ai_confidence_score": None,
        "ai_justification": None,
        "status": "pending_review",
    }


def scan_directory(path: str | Path, db_session) -> None:
    """Traverse *path* recursively and populate the database with file metadata."""
    path = Path(path).expanduser().resolve()

    if not path.exists():
        logger.error("Provided scan path %s does not exist.", path)
        return

    def _on_error(err):
        if isinstance(err, PermissionError):
            logger.warning("Permission denied while accessing %s. Skipping.", err.filename)
        else:
            logger.exception("Unexpected error while walking directory: %s", err)

    for root, _dirs, files in os.walk(path, onerror=_on_error):
        for filename in files:
            abs_path = Path(root) / filename
            try:
                if not abs_path.is_file():
                    continue
                file_data = _gather_file_metadata(abs_path)
                database_manager.add_file_record(db_session, file_data)
            except PermissionError:
                logger.warning("Permission denied for file %s, skipping.", abs_path)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to process file %s: %s", abs_path, exc) 