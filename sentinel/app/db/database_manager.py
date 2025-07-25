from __future__ import annotations

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# --------------------------------------------------------------------------- #
# Configuration helpers
# --------------------------------------------------------------------------- #
_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "config.yaml"


def _load_config() -> Dict[str, Any]:
    """Load YAML configuration if available."""
    if _CONFIG_PATH.exists():
        with _CONFIG_PATH.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    return {}


def _get_database_url() -> str:
    cfg = _load_config()
    db_path = cfg.get("database_path", "sentinel.db")
    db_path = os.path.expanduser(db_path)
    return f"sqlite:///{db_path}"


# --------------------------------------------------------------------------- #
# ORM setup
# --------------------------------------------------------------------------- #
Base = declarative_base()


class FileRecord(Base):
    """SQLAlchemy ORM model representing a scanned file."""

    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_path = Column(Text, index=True, nullable=False)
    sha256_hash = Column(Text, index=True, nullable=False)
    file_size = Column(Integer, nullable=False)
    creation_date = Column(DateTime, nullable=False)
    modification_date = Column(DateTime, nullable=False)
    mime_type = Column(Text, nullable=False)
    ai_suggested_path = Column(Text, nullable=True)
    ai_confidence_score = Column(Float, nullable=True)
    ai_justification = Column(Text, nullable=True)
    status = Column(String, default="pending_review", nullable=False)

    __table_args__ = (
        Index("ix_files_sha256_hash", "sha256_hash"),
        Index("ix_files_original_path", "original_path"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-python dict representation of this record."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# --------------------------------------------------------------------------- #
# Engine / Session management
# --------------------------------------------------------------------------- #
_ENGINE = create_engine(
    _get_database_url(),
    connect_args={"check_same_thread": False},
    echo=False,
    future=True,
)
SessionLocal = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create tables if they don't already exist."""
    Base.metadata.create_all(_ENGINE)


# --------------------------------------------------------------------------- #
# CRUD helpers
# --------------------------------------------------------------------------- #

def add_file_record(session: Session, file_data: Dict[str, Any]) -> FileRecord:
    """Insert a new file record and commit the transaction."""
    record = FileRecord(**file_data)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get_pending_files(session: Session) -> List[FileRecord]:
    """Return all files with status ``pending_review``."""
    return session.query(FileRecord).filter(FileRecord.status == "pending_review").all()


def update_file_suggestion(session: Session, file_id: int, suggestion_data: Dict[str, Any]) -> Optional[FileRecord]:
    """Update AI suggestion fields for the specified file id."""
    record: Optional[FileRecord] = session.get(FileRecord, file_id)
    if not record:
        logging.warning("File id %s not found during suggestion update.", file_id)
        return None

    for key, value in suggestion_data.items():
        if hasattr(record, key):
            setattr(record, key, value)

    session.commit()
    session.refresh(record)
    return record 