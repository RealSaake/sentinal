#!/usr/bin/env python3
"""
Test the GPU Worker system
"""

import multiprocessing as mp
import sys
import time
from pathlib import Path

# Add helios to path
sys.path.insert(0, str(Path(__file__).parent))

from helios.workers.gpu_worker import GPUWorker, WorkerPool, WorkerMetrics

def test_single_gpu_worker():
    """Test a single GPU worker."""
    print("🧪 Testing single GPU worker...")
    
    # Create queues
    input_queue = mp.Queue(maxsize=50)
    output_queue = mp.Queue(maxsize=50)
    metrics_queue = mp.Queue(maxsize=50)
    
    # Mock config
    class MockConfig:
        def __init__(self):
            self.inference = type('obj', (object,), {
                'onnx_model_path': 'helios/models/sentinel_v1.onnx',
                'cuda_enabled': True,
                'confidence_threshold': 0.7
            })()
            self.performance = type('obj', (object,), {
                'batch_size': 5
            })()
    
    config = MockConfig()
    
    # Create test tasks
    test_tasks = []
    for i in range(10):
        task = {
            'path': f'/test/file_{i:02d}.jpg',
            'name': f'file_{i:02d}.jpg',
            'extension': '.jpg',
            'size_bytes': 1024000 + i * 1000,
            'modified_time': time.time()
        }
        test_tasks.append(task)
        input_queue.put(task)
    
    print(f"📤 Queued {len(test_tasks)} test tasks")
    
    # Create and start worker
    worker = GPUWorker(
        worker_id=1,
        input_queue=input_queue,
        output_queue=output_queue,
        metrics_queue=metrics_queue,
        config=config,
        heartbeat_interval=2.0  # Fast heartbeat for testing
    )
    
    print(f"🚀 Starting worker...")
    process = worker.start()
    
    # Wait for processing
    time.sleep(5)
    
    # Stop worker
    print(f"🛑 Stopping worker...")
    worker.stop()
    
    # Collect results
    results = []
    while not output_queue.empty():
        results.append(output_queue.get())
    
    print(f"📊 Results:")
    print(f"   Tasks processed: {len(results)}")
    
    if results:
        sample_result = results[0]
        print(f"   Sample result keys: {list(sample_result.keys())}")
        print(f"   Sample categorized_path: {sample_result.get('categorized_path', 'N/A')}")
        print(f"   Sample confidence: {sample_result.get('confidence', 'N/A')}")
        print(f"   Sample tags: {sample_result.get('tags', 'N/A')}")
    
    # Collect metrics
    metrics_reports = []
    heartbeats = []
    while not metrics_queue.empty():
        msg = metrics_queue.get()
        if msg.get('type') == 'heartbeat':
            heartbeats.append(msg)
        elif msg.get('type') == 'metrics':
            metrics_reports.append(msg)
    
    print(f"   Heartbeats received: {len(heartbeats)}")
    print(f"   Metrics reports: {len(metrics_reports)}")
    
    if metrics_reports:
        final_metrics = metrics_reports[-1]
        print(f"   Files processed: {final_metrics.get('files_processed', 0)}")
        print(f"   Files/sec: {final_metrics.get('files_per_second', 0):.1f}")
        print(f"   Errors: {final_metrics.get('errors_count', 0)}")
    
    # Verify worker stopped
    if not process.is_alive():
        print("   ✅ Worker stopped cleanly")
    else:
        print("   ⚠️  Worker still running")
    
    return len(results) >= 5  # Should process at least half the tasks

def test_worker_pool():
    """Test worker pool with multiple workers."""
    print("\n🧪 Testing worker pool...")
    
    # Create queues
    input_queue = mp.Queue(maxsize=100)
    output_queue = mp.Queue(maxsize=100)
    metrics_queue = mp.Queue(maxsize=100)
    
    # Mock config
    class MockConfig:
        def __init__(self):
            self.inference = type('obj', (object,), {
                'onnx_model_path': 'helios/models/sentinel_v1.onnx',
                'cuda_enabled': True,
                'confidence_threshold': 0.7
            })()
            self.performance = type('obj', (object,), {
                'batch_size': 3
            })()
    
    config = MockConfig()
    
    # Create many test tasks
    num_tasks = 20
    for i in range(num_tasks):
        task = {
            'path': f'/test/batch_file_{i:02d}.txt',
            'name': f'batch_file_{i:02d}.txt',
            'extension': '.txt',
            'size_bytes': 5000 + i * 100,
            'modified_time': time.time()
        }
        input_queue.put(task)
    
    print(f"📤 Queued {num_tasks} test tasks")
    
    # Create worker pool
    num_workers = 3
    pool = WorkerPool(
        num_workers=num_workers,
        input_queue=input_queue,
        output_queue=output_queue,
        metrics_queue=metrics_queue,
        config=config
    )
    
    print(f"🚀 Starting pool with {num_workers} workers...")
    pool.start()
    
    # Check worker status
    status = pool.get_worker_status()
    print(f"   Workers started: {len([s for s in status if s['is_alive']])}/{num_workers}")
    
    # Wait for processing
    time.sleep(8)
    
    # Stop pool
    print(f"🛑 Stopping worker pool...")
    pool.stop()
    
    # Collect results
    results = []
    while not output_queue.empty():
        results.append(output_queue.get())
    
    print(f"📊 Pool Results:")
    print(f"   Tasks processed: {len(results)}")
    
    # Check which workers contributed
    worker_ids = set(result.get('worker_id') for result in results)
    print(f"   Workers that processed tasks: {sorted(worker_ids)}")
    
    # Collect metrics
    worker_metrics = {}
    while not metrics_queue.empty():
        msg = metrics_queue.get()
        if msg.get('type') == 'metrics':
            worker_id = msg.get('worker_id')
            if worker_id is not None:
                worker_metrics[worker_id] = msg
    
    print(f"   Workers with metrics: {len(worker_metrics)}")
    for worker_id, metrics in worker_metrics.items():
        print(f"     Worker {worker_id}: {metrics.get('files_processed', 0)} files, "
              f"{metrics.get('files_per_second', 0):.1f} files/sec")
    
    return len(results) >= num_tasks * 0.7  # Should process at least 70% of tasks

def test_worker_metrics():
    """Test worker metrics functionality."""
    print("\n🧪 Testing worker metrics...")
    
    # Test WorkerMetrics class
    metrics = WorkerMetrics(worker_id=99)
    
    # Record some processing
    metrics.record_processing(0.1, 5)  # 0.1s for 5 files
    metrics.record_processing(0.2, 3)  # 0.2s for 3 files
    metrics.record_error("Test error")
    
    print(f"📊 Metrics Test:")
    print(f"   Files processed: {metrics.files_processed}")
    print(f"   Total time: {metrics.total_processing_time}")
    print(f"   Avg time: {metrics.avg_processing_time}")
    print(f"   Files/sec: {metrics.files_per_second:.1f}")
    print(f"   Errors: {metrics.errors_count}")
    
    # Test serialization
    metrics_dict = metrics.to_dict()
    required_fields = ['worker_id', 'files_processed', 'files_per_second', 'errors_count']
    
    missing_fields = [field for field in required_fields if field not in metrics_dict]
    if not missing_fields:
        print("   ✅ Metrics serialization working")
        return True
    else:
        print(f"   ❌ Missing fields: {missing_fields}")
        return False

def test_error_handling():
    """Test error handling in workers."""
    print("\n🧪 Testing error handling...")
    
    # Create queues
    input_queue = mp.Queue(maxsize=10)
    output_queue = mp.Queue(maxsize=10)
    metrics_queue = mp.Queue(maxsize=10)
    
    # Mock config
    class MockConfig:
        def __init__(self):
            self.inference = type('obj', (object,), {
                'onnx_model_path': 'helios/models/sentinel_v1.onnx',
                'cuda_enabled': True,
                'confidence_threshold': 0.7
            })()
            self.performance = type('obj', (object,), {
                'batch_size': 2
            })()
    
    config = MockConfig()
    
    # Add some invalid tasks
    invalid_tasks = [
        {'invalid': 'data'},
        {'path': '/test/valid.txt', 'name': 'valid.txt', 'extension': '.txt', 'size_bytes': 1000},
        {'another': 'invalid', 'task': 'data'}
    ]
    
    for task in invalid_tasks:
        input_queue.put(task)
    
    print(f"📤 Queued {len(invalid_tasks)} tasks (some invalid)")
    
    # Create worker
    worker = GPUWorker(
        worker_id=88,
        input_queue=input_queue,
        output_queue=output_queue,
        metrics_queue=metrics_queue,
        config=config
    )
    
    # Start and wait
    process = worker.start()
    time.sleep(3)
    worker.stop()
    
    # Check that worker handled errors gracefully
    if not process.is_alive():
        print("   ✅ Worker handled errors and stopped cleanly")
        
        # Check for error metrics
        error_count = 0
        while not metrics_queue.empty():
            msg = metrics_queue.get()
            if msg.get('type') == 'metrics':
                error_count = msg.get('errors_count', 0)
        
        if error_count > 0:
            print(f"   ✅ Errors properly recorded: {error_count}")
        else:
            print("   ⚠️  No errors recorded (may be expected)")
        
        return True
    else:
        print("   ❌ Worker did not stop cleanly")
        return False

def main():
    """Run all tests."""
    print("🚀 GPU Worker Test Suite")
    print("=" * 50)
    
    try:
        # Run tests
        test1 = test_single_gpu_worker()
        test2 = test_worker_pool()
        test3 = test_worker_metrics()
        test4 = test_error_handling()
        
        print("\n" + "=" * 50)
        if all([test1, test2, test3, test4]):
            print("🎉 All tests passed! GPU Workers are ready!")
            return 0
        else:
            print("💥 Some tests failed!")
            return 1
            
    except Exception as e:
        print(f"💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())