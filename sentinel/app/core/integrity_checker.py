"""File integrity utilities for Sentinel.

Provides checksum computation and verification helpers.  The implementation will
be supplied by a background agent; only signatures and documentation live here.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

Algo = Literal["md5", "sha1", "sha256", "sha512"]

__all__ = ["compute_checksum", "verify_integrity"]


# ---------------------------------------------------------------------------
# Public API – to be implemented by background agent
# ---------------------------------------------------------------------------

def compute_checksum(file_path: str | Path, algorithm: Algo = "sha256", /) -> str:
    """Return the hexadecimal *algorithm* digest for *file_path*.

    Implementation hints (backend agent):
    • Stream file in 1-8 MiB chunks to keep memory usage stable.
    • Use :pymod:`hashlib` algorithms mapped by *algorithm*.
    """
    h = hashlib.new(algorithm)
    path = Path(file_path)
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):  # 1 MiB chunks
            h.update(chunk)
    return h.hexdigest()


def verify_integrity(file_path: str | Path, checksum: str, algorithm: Algo = "sha256", /) -> bool:
    """Compare *checksum* against freshly computed digest of *file_path*."""
    return compute_checksum(file_path, algorithm) == checksum 