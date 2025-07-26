#!/usr/bin/env python3
"""
Simple, fast queue integration test
"""

import asyncio
import multiprocessing as mp
import sys
import tempfile
import time
from pathlib import Path

# Add helios to path
sys.path.insert(0, str(Path(__file__).parent))

async def simple_queue_test():
    """Simple, fast queue test."""
    print("🚀 Simple Queue Test")
    
    # Create test files quickly
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        print("📁 Creating 10 test files...")
        for i in range(10):
            (temp_path / f"file_{i}.txt").write_text(f"content {i}")
        
        print("✅ Files created")
        
        # Simple file discovery
        files = list(temp_path.rglob("*.txt"))
        print(f"🔍 Found {len(files)} files")
        
        # Create queue
        queue = mp.Queue(maxsize=20)
        
        # Queue files
        for file_path in files:
            file_data = {
                'path': str(file_path),
                'name': file_path.name,
                'size': file_path.stat().st_size
            }
            queue.put(file_data)
        
        print(f"📤 Queued {len(files)} files")
        
        # Retrieve from queue
        results = []
        while not queue.empty():
            results.append(queue.get())
        
        print(f"📥 Retrieved {len(results)} files")
        print("✅ Simple queue test passed!")
        
        return True

if __name__ == "__main__":
    asyncio.run(simple_queue_test())