#!/usr/bin/env python3
"""
Simple test for GPU workers
"""

import multiprocessing as mp
import sys
import time
from pathlib import Path

# Add helios to path
sys.path.insert(0, str(Path(__file__).parent))

# Global mock config for multiprocessing
class GlobalMockConfig:
    def __init__(self):
        self.inference = type('obj', (object,), {
            'onnx_model_path': 'helios/models/sentinel_v1.onnx',
            'cuda_enabled': True,
            'confidence_threshold': 0.7
        })()
        self.performance = type('obj', (object,), {
            'batch_size': 3
        })()

def test_simple_worker():
    """Simple worker test."""
    print("🧪 Testing simple GPU worker...")
    
    from helios.workers.gpu_worker import GPUWorker
    
    # Create queues
    input_queue = mp.Queue(maxsize=20)
    output_queue = mp.Queue(maxsize=20)
    metrics_queue = mp.Queue(maxsize=20)
    
    # Create test tasks
    for i in range(5):
        task = {
            'path': f'/test/simple_{i}.jpg',
            'name': f'simple_{i}.jpg',
            'extension': '.jpg',
            'size_bytes': 1024000,
            'modified_time': time.time()
        }
        input_queue.put(task)
    
    print(f"📤 Queued 5 test tasks")
    
    # Create worker with global config
    config = GlobalMockConfig()
    worker = GPUWorker(
        worker_id=1,
        input_queue=input_queue,
        output_queue=output_queue,
        metrics_queue=metrics_queue,
        config=config
    )
    
    print(f"🚀 Starting worker...")
    process = worker.start()
    
    # Wait for processing
    time.sleep(3)
    
    # Stop worker
    print(f"🛑 Stopping worker...")
    worker.stop()
    
    # Check results
    results = []
    while not output_queue.empty():
        results.append(output_queue.get())
    
    print(f"📊 Results: {len(results)} tasks processed")
    
    if results:
        sample = results[0]
        print(f"   Sample: {sample.get('categorized_path', 'N/A')}")
        print(f"   Confidence: {sample.get('confidence', 'N/A')}")
    
    # Check metrics
    metrics_count = 0
    while not metrics_queue.empty():
        msg = metrics_queue.get()
        if msg.get('type') == 'metrics':
            metrics_count += 1
            print(f"   Files processed: {msg.get('files_processed', 0)}")
    
    print(f"   Metrics reports: {metrics_count}")
    
    if len(results) >= 3:
        print("✅ Simple worker test passed!")
        return True
    else:
        print("❌ Not enough results")
        return False

if __name__ == "__main__":
    try:
        success = test_simple_worker()
        exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)