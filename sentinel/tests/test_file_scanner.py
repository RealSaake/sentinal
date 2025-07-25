import hashlib
from pathlib import Path
import os

from sentinel.app.core.file_scanner import scan_directory
from sentinel.app.db import database_manager


def test_scan_directory_inserts_records(tmp_path: Path):
    # Create a sample file
    sample_file = tmp_path / "sample.txt"
    data = b"sample data"
    sample_file.write_bytes(data)

    # Recreate a fresh database for the test
    db_file = Path(os.path.expanduser("sentinel.db"))
    if db_file.exists():
        db_file.unlink()

    database_manager.init_db()
    session = database_manager.SessionLocal()

    try:
        scan_directory(tmp_path, session)
        records = session.query(database_manager.FileRecord).all()
        assert len(records) == 1
        record = records[0]
        assert record.original_path == str(sample_file)
        assert record.sha256_hash == hashlib.sha256(data).hexdigest()
        assert record.status == "pending_review"
    finally:
        session.close()