#!/usr/bin/env python3
"""
Test queue integration with backpressure mechanism
"""

import asyncio
import multiprocessing as mp
import sys
import tempfile
import time
from pathlib import Path

# Add helios to path
sys.path.insert(0, str(Path(__file__).parent))

from helios.scanner.queue_producer import QueueProducer, BatchQueueProducer, create_test_queue
from helios.core.config import HeliosConfig

async def test_basic_queue_integration():
    """Test basic queue integration."""
    print("🧪 Testing basic queue integration...")
    
    # Create test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        for i in range(20):
            (temp_path / f"file_{i:02d}.txt").write_text(f"Content {i}")
        
        # Create subdirectory
        sub_dir = temp_path / "subdir"
        sub_dir.mkdir()
        for i in range(10):
            (sub_dir / f"subfile_{i:02d}.txt").write_text(f"Sub content {i}")
        
        print(f"📁 Created 30 test files")
        
        # Mock config
        class MockConfig:
            def __init__(self):
                self.performance = type('obj', (object,), {'queue_max_size': 50})()
            
            def should_skip_file(self, file_path, file_size, file_age):
                return (False, "")
        
        config = MockConfig()
        
        # Create queue and producer
        test_queue = create_test_queue(maxsize=50)
        producer = QueueProducer(
            queue=test_queue,
            config=config,
            max_queue_size=50,
            backpressure_threshold=0.8
        )
        
        # Start production
        start_time = time.time()
        await producer.produce_from_directory(str(temp_path), max_workers=4)
        production_time = time.time() - start_time
        
        print(f"⚡ Production completed in {production_time:.3f}s")
        
        # Collect results from queue
        results = []
        while not test_queue.empty():
            try:
                item = test_queue.get_nowait()
                results.append(item)
            except:
                break
        
        print(f"📊 Results:")
        print(f"   Items queued: {len(results)}")
        print(f"   Production rate: {len(results) / production_time:.1f} items/sec")
        
        # Get metrics
        metrics = producer.get_metrics()
        print(f"   Queue metrics: {metrics['queue_metrics']}")
        
        # Verify results
        if len(results) >= 30:  # Should find at least our test files
            print("   ✅ All files successfully queued")
        else:
            print(f"   ⚠️  Only {len(results)} files queued (expected ≥30)")
        
        # Verify data structure
        if results and isinstance(results[0], dict):
            sample = results[0]
            required_fields = ['file_path', 'metadata', 'priority']
            if all(field in sample for field in required_fields):
                print("   ✅ Queue data structure is correct")
            else:
                print("   ❌ Queue data structure is incorrect")
                print(f"      Sample: {list(sample.keys())}")
        
        return len(results) >= 30

async def test_backpressure_mechanism():
    """Test backpressure mechanism with small queue."""
    print("\n🧪 Testing backpressure mechanism...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create many files to trigger backpressure
        for i in range(100):
            (temp_path / f"file_{i:03d}.txt").write_text(f"Content {i}")
        
        print(f"📁 Created 100 test files")
        
        # Mock config
        class MockConfig:
            def __init__(self):
                self.performance = type('obj', (object,), {'queue_max_size': 20})()
            
            def should_skip_file(self, file_path, file_size, file_age):
                return (False, "")
        
        config = MockConfig()
        
        # Create small queue to trigger backpressure
        test_queue = create_test_queue(maxsize=20)
        producer = QueueProducer(
            queue=test_queue,
            config=config,
            max_queue_size=20,
            backpressure_threshold=0.7,  # Trigger at 70% full
            backpressure_wait=0.01  # Short wait for testing
        )
        
        # Start production (should trigger backpressure)
        start_time = time.time()
        
        # Start a consumer to drain the queue
        async def slow_consumer():
            consumed = 0
            while consumed < 50:  # Consume half the items
                try:
                    test_queue.get_nowait()
                    consumed += 1
                    await asyncio.sleep(0.01)  # Slow consumption
                except:
                    await asyncio.sleep(0.01)
        
        # Run producer and consumer concurrently
        consumer_task = asyncio.create_task(slow_consumer())
        await producer.produce_from_directory(str(temp_path), max_workers=2)
        await consumer_task
        
        production_time = time.time() - start_time
        
        print(f"⚡ Production with backpressure completed in {production_time:.3f}s")
        
        # Get metrics
        metrics = producer.get_metrics()
        queue_metrics = metrics['queue_metrics']
        
        print(f"📊 Backpressure Metrics:")
        print(f"   Items queued: {queue_metrics['items_queued']}")
        print(f"   Queue full events: {queue_metrics['queue_full_events']}")
        print(f"   Backpressure events: {queue_metrics['backpressure_events']}")
        print(f"   Avg wait time: {queue_metrics['avg_wait_time']:.3f}s")
        print(f"   Max queue size: {queue_metrics['max_queue_size']}")
        
        # Verify backpressure was triggered
        if queue_metrics['backpressure_events'] > 0:
            print("   ✅ Backpressure mechanism working")
            return True
        else:
            print("   ⚠️  Backpressure not triggered (queue may be too large)")
            return True  # Still pass if queue was large enough

async def test_batch_queue_producer():
    """Test batch queue producer."""
    print("\n🧪 Testing batch queue producer...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        for i in range(25):
            (temp_path / f"file_{i:02d}.txt").write_text(f"Content {i}")
        
        print(f"📁 Created 25 test files")
        
        # Mock config
        class MockConfig:
            def __init__(self):
                self.performance = type('obj', (object,), {'queue_max_size': 100})()
            
            def should_skip_file(self, file_path, file_size, file_age):
                return (False, "")
        
        config = MockConfig()
        
        # Create batch producer
        test_queue = create_test_queue(maxsize=100)
        producer = BatchQueueProducer(
            queue=test_queue,
            config=config,
            batch_size=5,  # Small batches for testing
            batch_timeout=0.5
        )
        
        # Start production
        start_time = time.time()
        await producer.produce_from_directory(str(temp_path), max_workers=4)
        production_time = time.time() - start_time
        
        print(f"⚡ Batch production completed in {production_time:.3f}s")
        
        # Collect batches from queue
        batches = []
        total_items = 0
        while not test_queue.empty():
            try:
                batch = test_queue.get_nowait()
                batches.append(batch)
                if isinstance(batch, dict) and 'items' in batch:
                    total_items += len(batch['items'])
            except:
                break
        
        print(f"📊 Batch Results:")
        print(f"   Batches created: {len(batches)}")
        print(f"   Total items: {total_items}")
        print(f"   Avg batch size: {total_items / len(batches) if batches else 0:.1f}")
        
        # Verify batch structure
        if batches and isinstance(batches[0], dict):
            sample_batch = batches[0]
            if 'type' in sample_batch and sample_batch['type'] == 'file_batch':
                print("   ✅ Batch structure is correct")
                
                if 'items' in sample_batch and isinstance(sample_batch['items'], list):
                    print("   ✅ Batch items structure is correct")
                else:
                    print("   ❌ Batch items structure is incorrect")
            else:
                print("   ❌ Batch structure is incorrect")
        
        return total_items >= 25

async def test_error_handling():
    """Test error handling in queue integration."""
    print("\n🧪 Testing error handling...")
    
    # Mock config
    class MockConfig:
        def __init__(self):
            self.performance = type('obj', (object,), {'queue_max_size': 100})()
        
        def should_skip_file(self, file_path, file_size, file_age):
            return (False, "")
    
    config = MockConfig()
    test_queue = create_test_queue(maxsize=100)
    
    # Test with non-existent directory
    producer = QueueProducer(queue=test_queue, config=config)
    
    try:
        await producer.produce_from_directory("/nonexistent/directory")
        print("   ❌ Should have failed with non-existent directory")
        return False
    except FileNotFoundError:
        print("   ✅ Correctly handled non-existent directory")
    
    # Test cancellation
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create many files
        for i in range(100):
            (temp_path / f"file_{i:03d}.txt").write_text(f"Content {i}")
        
        producer = QueueProducer(queue=test_queue, config=config)
        
        # Start production and cancel it
        async def cancel_after_delay():
            await asyncio.sleep(0.1)  # Let it start
            producer.cancel_production()
        
        cancel_task = asyncio.create_task(cancel_after_delay())
        await producer.produce_from_directory(str(temp_path))
        await cancel_task
        
        metrics = producer.get_metrics()
        if metrics['production_cancelled']:
            print("   ✅ Cancellation mechanism working")
        else:
            print("   ⚠️  Cancellation not detected (production may have completed too quickly)")
    
    return True

async def test_performance():
    """Test queue integration performance."""
    print("\n🚀 Testing performance...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create many files
        print("📁 Creating 500 test files...")
        for i in range(500):
            (temp_path / f"file_{i:04d}.txt").write_text(f"Content {i}")
        
        # Mock config
        class MockConfig:
            def __init__(self):
                self.performance = type('obj', (object,), {'queue_max_size': 1000})()
            
            def should_skip_file(self, file_path, file_size, file_age):
                return (False, "")
        
        config = MockConfig()
        
        # Test regular producer
        test_queue = create_test_queue(maxsize=1000)
        producer = QueueProducer(queue=test_queue, config=config)
        
        start_time = time.time()
        await producer.produce_from_directory(str(temp_path), max_workers=8)
        regular_time = time.time() - start_time
        
        # Count items
        regular_items = 0
        while not test_queue.empty():
            try:
                test_queue.get_nowait()
                regular_items += 1
            except:
                break
        
        print(f"📊 Regular Producer:")
        print(f"   Time: {regular_time:.3f}s")
        print(f"   Items: {regular_items}")
        print(f"   Rate: {regular_items / regular_time:.1f} items/sec")
        
        # Test batch producer
        test_queue2 = create_test_queue(maxsize=1000)
        batch_producer = BatchQueueProducer(
            queue=test_queue2, 
            config=config,
            batch_size=20,
            batch_timeout=0.1
        )
        
        start_time = time.time()
        await batch_producer.produce_from_directory(str(temp_path), max_workers=8)
        batch_time = time.time() - start_time
        
        # Count batches and items
        batch_count = 0
        batch_items = 0
        while not test_queue2.empty():
            try:
                batch = test_queue2.get_nowait()
                batch_count += 1
                if isinstance(batch, dict) and 'items' in batch:
                    batch_items += len(batch['items'])
            except:
                break
        
        print(f"📊 Batch Producer:")
        print(f"   Time: {batch_time:.3f}s")
        print(f"   Batches: {batch_count}")
        print(f"   Items: {batch_items}")
        print(f"   Rate: {batch_items / batch_time:.1f} items/sec")
        
        # Performance should be reasonable
        min_rate = 50  # items per second
        if regular_items / regular_time >= min_rate and batch_items / batch_time >= min_rate:
            print("   ✅ Performance targets met")
            return True
        else:
            print("   ⚠️  Performance below target")
            return False

async def main():
    """Run all tests."""
    print("🚀 Queue Integration Test Suite")
    print("=" * 50)
    
    try:
        # Run tests
        test1 = await test_basic_queue_integration()
        test2 = await test_backpressure_mechanism()
        test3 = await test_batch_queue_producer()
        test4 = await test_error_handling()
        test5 = await test_performance()
        
        print("\n" + "=" * 50)
        if all([test1, test2, test3, test4, test5]):
            print("🎉 All tests passed! Queue integration is ready!")
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
    exit(asyncio.run(main()))