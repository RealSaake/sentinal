"""File scanning utilities for Sentinel.

This module defines the public interface for traversing directories and
collecting metadata about each file.  The heavy-lifting implementation will be
added by a background agent – *do not* add application logic here.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional

__all__ = ["FileMetadata", "scan_directory"]


@dataclass(slots=True)
class FileMetadata:
    """Lightweight container for metadata discovered during a scan."""

    path: Path
    mime_type: Optional[str] = None
    size: Optional[int] = None  # Size in bytes
    creation_date: Optional[str] = None  # ISO-8601 timestamp as string
    checksum: Optional[str] = None  # Optional checksum populated later

    def as_dict(self) -> dict:
        """Return dict representation (useful for JSON encoding / DB storage)."""
        return {
            "path": str(self.path),
            "mime_type": self.mime_type,
            "size": self.size,
            "creation_date": self.creation_date,
            "checksum": self.checksum,
        }


# ---------------------------------------------------------------------------
# Public API – to be implemented by background agent
# ---------------------------------------------------------------------------

def scan_directory(directory: str | Path, *, follow_symlinks: bool = False) -> Iterator[FileMetadata]:
    """Recursively walk *directory* and yield :class:`FileMetadata` objects.

    Parameters
    ----------
    directory:
        Root directory to scan.
    follow_symlinks:
        Whether to traverse symbolic links while scanning.

    Yields
    ------
    FileMetadata
        Populated with *at minimum* ``path`` and ``size``.  MIME type and
        creation date should be detected when feasible, otherwise left ``None``.

    Notes
    -----
    • This function **must not block** the GUI thread.  It should either be run
      in a worker thread / process or designed as a generator that periodically
      yields control so the caller can update a progress bar.
    • Use :pypi:`filetype` for MIME detection.
    • Size and timestamps can be fetched from :pymod:`os.stat`.
    • Checksum calculation is *not* required at scan-time; leave ``checksum``
      ``None`` and let :pymod:`sentinel.app.core.integrity_checker` fill it on
      demand.
    """
    from os import scandir, stat
    from datetime import datetime
    from pathlib import Path as _P
    import filetype

    root = _P(directory).expanduser().resolve()

    def _walk(path: _P):
        try:
            with scandir(path) as it:
                for entry in it:
                    try:
                        entry_path = _P(entry.path)
                        if entry.is_dir(follow_symlinks=follow_symlinks):
                            yield from _walk(entry_path)
                        elif entry.is_file(follow_symlinks=follow_symlinks):
                            st = entry.stat()
                            size = st.st_size
                            ctime = datetime.fromtimestamp(st.st_ctime).isoformat()

                            # MIME detection
                            kind = filetype.guess(entry_path)
                            mime = kind.mime if kind else None

                            yield FileMetadata(
                                path=entry_path,
                                mime_type=mime,
                                size=size,
                                creation_date=ctime,
                            )
                    except PermissionError:
                        continue  # Skip inaccessible entries
        except PermissionError:
            pass

    yield from _walk(root) 