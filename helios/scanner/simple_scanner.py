#!/usr/bin/env python3
"""
Simple, fast file scanner for MVP
Focuses on speed over complexity
"""

import asyncio
import multiprocessing as mp
import time
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List
from dataclasses import dataclass


@dataclass
class SimpleScanMetrics:
    """Simple metrics for scanning."""
    files_found: int = 0
    scan_time: float = 0.0
    
    @property
    def files_per_second(self) -> float:
        return self.files_found / self.scan_time if self.scan_time > 0 else 0.0


class SimpleFileScanner:
    """Simple, fast file scanner."""
    
    def __init__(self, base_directory: str, config: Any = None):
        self.base_directory = Path(base_directory)
        self.config = config
        self.metrics = SimpleScanMetrics()
    
    async def scan_and_queue(self, queue: mp.Queue) -> None:
        """Scan directory and put files directly in queue."""
        print(f"🔍 Scanning: {self.base_directory}")
        
        start_time = time.time()
        files_queued = 0
        
        # Simple recursive scan
        for file_path in self.base_directory.rglob("*"):
            if file_path.is_file():
                # Quick skip check
                if self._should_skip_quick(file_path):
                    continue
                
                # Create simple file data
                try:
                    stat = file_path.stat()
                    file_data = {
                        'path': str(file_path),
                        'name': file_path.name,
                        'extension': file_path.suffix.lower(),
                        'size_bytes': stat.st_size,
                        'modified_time': stat.st_mtime
                    }
                    
                    # Queue it
                    queue.put(file_data)
                    files_queued += 1
                    
                    # Yield control occasionally
                    if files_queued % 100 == 0:
                        await asyncio.sleep(0.001)
                        print(f"   📊 Queued {files_queued} files...")
                
                except (OSError, PermissionError):
                    continue
        
        self.metrics.scan_time = time.time() - start_time
        self.metrics.files_found = files_queued
        
        print(f"✅ Scan complete: {files_queued} files in {self.metrics.scan_time:.2f}s")
        print(f"   Rate: {self.metrics.files_per_second:.1f} files/sec")
    
    def _should_skip_quick(self, file_path: Path) -> bool:
        """Quick skip check for common unwanted files."""
        name = file_path.name.lower()
        
        # Skip system files
        if name.startswith('.') or name in ['thumbs.db', 'desktop.ini']:
            return True
        
        # Skip temp files
        if name.endswith(('.tmp', '.temp', '.cache')):
            return True
        
        # Skip very small files
        try:
            if file_path.stat().st_size < 10:  # < 10 bytes
                return True
        except:
            return True
        
        return False


class SimpleQueueProducer:
    """Simple queue producer for MVP."""
    
    def __init__(self, queue: mp.Queue, config: Any = None):
        self.queue = queue
        self.config = config
        self.scanner = None
    
    async def produce_from_directory(self, directory: str) -> Dict[str, Any]:
        """Produce files from directory into queue."""
        self.scanner = SimpleFileScanner(directory, self.config)
        await self.scanner.scan_and_queue(self.queue)
        
        return {
            'files_found': self.scanner.metrics.files_found,
            'scan_time': self.scanner.metrics.scan_time,
            'files_per_second': self.scanner.metrics.files_per_second
        }


# Quick test function
async def test_simple_scanner():
    """Test the simple scanner."""
    print("🧪 Testing SimpleFileScanner...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        print("📁 Creating test files...")
        for i in range(50):
            (temp_path / f"file_{i:02d}.txt").write_text(f"content {i}")
        
        # Create subdirectory
        sub_dir = temp_path / "subdir"
        sub_dir.mkdir()
        for i in range(25):
            (sub_dir / f"sub_{i:02d}.txt").write_text(f"sub content {i}")
        
        print("✅ Created 75 test files")
        
        # Mock config
        class MockConfig:
            pass
        
        # Test scanner
        queue = mp.Queue(maxsize=200)
        producer = SimpleQueueProducer(queue, MockConfig())
        
        start_time = time.time()
        metrics = await producer.produce_from_directory(str(temp_path))
        total_time = time.time() - start_time
        
        print(f"📊 Results:")
        print(f"   Files found: {metrics['files_found']}")
        print(f"   Total time: {total_time:.3f}s")
        print(f"   Rate: {metrics['files_per_second']:.1f} files/sec")
        
        # Check queue
        queued_items = []
        while not queue.empty():
            queued_items.append(queue.get())
        
        print(f"   Items in queue: {len(queued_items)}")
        
        if len(queued_items) >= 75:
            print("✅ Simple scanner test passed!")
            return True
        else:
            print("❌ Not all files were queued")
            return False


if __name__ == "__main__":
    import tempfile
    asyncio.run(test_simple_scanner())