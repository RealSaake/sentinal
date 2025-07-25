import hashlib
from pathlib import Path

import pytest

from sentinel.app.core.integrity_checker import calculate_sha256


def test_sha256_non_empty_file(tmp_path: Path):
    data = b"hello world"
    file_path = tmp_path / "file.txt"
    file_path.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert calculate_sha256(file_path) == expected


def test_sha256_empty_file(tmp_path: Path):
    file_path = tmp_path / "empty.txt"
    file_path.touch()
    expected = hashlib.sha256(b"").hexdigest()
    assert calculate_sha256(file_path) == expected