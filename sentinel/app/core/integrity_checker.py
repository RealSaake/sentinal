import hashlib
from pathlib import Path
from typing import Union

_BUFFER_SIZE = 1024 * 1024  # 1 MiB


def calculate_sha256(file_path: Union[str, Path]) -> str:
    """Compute SHA-256 hash for *file_path* in an efficient streaming manner."""
    file_path = Path(file_path)
    sha = hashlib.sha256()
    with file_path.open("rb") as fh:
        while chunk := fh.read(_BUFFER_SIZE):
            sha.update(chunk)
    return sha.hexdigest() 