"""Database access layer for Sentinel.

Defines the public :class:`DatabaseManager` responsible for persisting scan
results, inference outputs, and user feedback.  Detailed ORM mappings will be
implemented by a background agent.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

# pyright: reportGeneralTypeIssues=false
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

__all__ = ["DatabaseManager"]


class DatabaseManager:
    """Lightweight wrapper around SQLAlchemy engine & session factory."""

    def __init__(self, db_path: str | Path = "sentinel.db") -> None:
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False, future=True)
        self.SessionFactory = sessionmaker(bind=self.engine, future=True)

        # Declare ORM base and models lazily to avoid circular imports.
        Base = declarative_base()

        class File(Base):
            __tablename__ = "files"

            id = Column(Integer, primary_key=True, autoincrement=True)
            path = Column(String, unique=True, nullable=False)
            mime_type = Column(String, nullable=True)
            size = Column(Integer, nullable=True)
            creation_date = Column(String, nullable=True)
            checksum = Column(String, nullable=True)

            inference = relationship("Inference", back_populates="file", uselist=False)

        class Inference(Base):
            __tablename__ = "inferences"

            id = Column(Integer, primary_key=True, autoincrement=True)
            file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"))
            suggested_path = Column(String, nullable=False)
            confidence = Column(Float, nullable=False)
            justification = Column(String, nullable=False)
            approved = Column(Boolean, nullable=True)  # None = pending
            revised_path = Column(String, nullable=True)

            file = relationship("File", back_populates="inference")

        # Store on instance for later type reference
        self._Base = Base
        self.File = File
        self.Inference = Inference

    # ------------------------------------------------------------------
    # Public API – to be implemented by background agent
    # ------------------------------------------------------------------

    def init_schema(self) -> None:
        """Create database tables if they don't exist."""
        self._Base.metadata.create_all(self.engine)

    def save_scan_result(self, metadata: dict[str, Any]) -> int:
        """Persist file metadata and return its ID, or existing ID if duplicate."""
        path = metadata.get("path")
        if not path:
            raise ValueError("'path' key is required in metadata")

        with self.SessionFactory() as session:
            file_obj = session.query(self.File).filter_by(path=path).one_or_none()
            if file_obj is None:
                file_obj = self.File(
                    path=path,
                    mime_type=metadata.get("mime_type"),
                    size=metadata.get("size"),
                    creation_date=metadata.get("creation_date"),
                    checksum=metadata.get("checksum"),
                )
                session.add(file_obj)
                session.commit()
            return file_obj.id

    def save_inference(self, file_id: int, inference: dict[str, Any]) -> None:
        """Persist inference result for a file."""
        with self.SessionFactory() as session:
            # Upsert pattern
            inf_obj = session.query(self.Inference).filter_by(file_id=file_id).one_or_none()
            if inf_obj is None:
                inf_obj = self.Inference(file_id=file_id)
                session.add(inf_obj)

            inf_obj.suggested_path = inference.get("suggested_path")
            inf_obj.confidence = inference.get("confidence")
            inf_obj.justification = inference.get("justification")
            inf_obj.approved = inference.get("approved")
            inf_obj.revised_path = inference.get("revised_path")
            session.commit()

    def save_feedback(self, file_id: int, approved: bool, revised_path: str | None) -> None:
        with self.SessionFactory() as session:
            inf_obj = session.query(self.Inference).filter_by(file_id=file_id).one_or_none()
            if inf_obj is None:
                raise ValueError("Inference row not found for file_id")
            inf_obj.approved = approved
            inf_obj.revised_path = revised_path
            session.commit() 