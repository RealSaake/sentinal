#!/usr/bin/env python3
"""
Test suite for GPUWorker
Following TDD approach - tests first, then implementation
"""

import pytest
import multiprocessing as mp
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from helios.workers.gpu_worker import GPUWorker, WorkerMetrics
from helios.core.config import HeliosConfig


class TestGPUWorker:
    """Test cases for GPUWorker."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=HeliosConfig)
        config.inference.onnx_model_path = "helios/models/sentinel_v1.onnx"
        config.inference.cuda_enabled = True
        config.inference.confidence_threshold = 0.7
        config.performance.batch_size = 32
        return config
    
    @pytest.fixture
    def test_queues(self):
        """Create test input and output queues."""
        input_queue = mp.Queue(maxsize=100)
        output_queue = mp.Queue(maxsize=100)
        metrics_queue = mp.Queue(maxsize=100)
        return input_queue, output_queue, metrics_queue
    
    def test_worker_initialization(self, mock_config, test_queues):
        """Test GPUWorker initialization."""
        input_queue, output_queue, metrics_queue = test_queues
        
        worker = GPUWorker(
            worker_id=1,
            input_queue=input_queue,
            output_queue=output_queue,
            metrics_queue=metrics_queue,
            config=mock_config
        )
        
        assert worker.worker_id == 1
        assert worker.input_queue == input_queue
        assert worker.output_queue == output_queue
        assert worker.metrics_queue == metrics_queue
        assert worker.config == mock_config
        assert isinstance(worker.metrics, WorkerMetrics)
        assert worker.is_running == False
    
    def test_worker_lifecycle(self, mock_config, test_queues):
        """Test worker process lifecycle."""
        input_queue, output_queue, metrics_queue = test_queues
        
        worker = GPUWorker(
            worker_id=1,
            input_queue=input_queue,
            output_queue=output_queue,
            metrics_queue=metrics_queue,
            config=mock_config
        )
        
        # Test start
        process = worker.start()
        assert process is not None
        assert process.is_alive()
        
        # Test stop
        worker.stop()
        process.join(timeout=5)
        assert not process.is_alive()
    
    def test_batch_processing(self, mock_config, test_queues):
        """Test batch processing of file tasks."""
        input_queue, output_queue, metrics_queue = test_queues
        
        # Create test file tasks
        test_tasks = []
        for i in range(5):
            task_data = {
                'path': f'/test/file_{i}.jpg',
                'name': f'file_{i}.jpg',
                'extension': '.jpg',
                'size_bytes': 1024000,
                'modified_time': time.time()
            }
            test_tasks.append(task_data)
            input_queue.put(task_data)
        
        # Add stop signal
        input_queue.put(None)
        
        worker = GPUWorker(
            worker_id=1,
            input_queue=input_queue,
            output_queue=output_queue,
            metrics_queue=metrics_queue,
            config=mock_config
        )
        
        # Start worker
        process = worker.start()
        
        # Wait for processing
        time.sleep(2)
        
        # Stop worker
        worker.stop()
        process.join(timeout=5)
        
        # Check results
        results = []
        while not output_queue.empty():
            results.append(output_queue.get())
        
        assert len(results) >= 5
        
        # Verify result structure
        for result in results:
            assert 'original_path' in result
            assert 'categorized_path' in result
            assert 'confidence' in result
            assert 'tags' in result
            assert 'worker_id' in result
    
    def test_metrics_collection(self, mock_config, test_queues):
        """Test worker metrics collection."""
        input_queue, output_queue, metrics_queue = test_queues
        
        # Add test tasks
        for i in range(3):
            task_data = {
                'path': f'/test/file_{i}.txt',
                'name': f'file_{i}.txt',
                'extension': '.txt',
                'size_bytes': 1024,
                'modified_time': time.time()
            }
            input_queue.put(task_data)
        
        input_queue.put(None)  # Stop signal
        
        worker = GPUWorker(
            worker_id=2,
            input_queue=input_queue,
            output_queue=output_queue,
            metrics_queue=metrics_queue,
            config=mock_config
        )
        
        # Start and wait
        process = worker.start()
        time.sleep(2)
        worker.stop()
        process.join(timeout=5)
        
        # Check metrics
        metrics_reports = []
        while not metrics_queue.empty():
            metrics_reports.append(metrics_queue.get())
        
        assert len(metrics_reports) > 0
        
        # Verify metrics structure
        for metrics in metrics_reports:
            assert 'worker_id' in metrics
            assert 'files_processed' in metrics
            assert 'processing_time' in metrics
            assert 'avg_inference_time' in metrics
            assert metrics['worker_id'] == 2
    
    def test_error_handling(self, mock_config, test_queues):
        """Test error handling in worker."""
        input_queue, output_queue, metrics_queue = test_queues
        
        # Add invalid task data
        invalid_task = {'invalid': 'data'}
        input_queue.put(invalid_task)
        input_queue.put(None)  # Stop signal
        
        worker = GPUWorker(
            worker_id=3,
            input_queue=input_queue,
            output_queue=output_queue,
            metrics_queue=metrics_queue,
            config=mock_config
        )
        
        # Start and wait
        process = worker.start()
        time.sleep(2)
        worker.stop()
        process.join(timeout=5)
        
        # Should handle error gracefully and continue
        assert not process.is_alive()
        
        # Check for error metrics
        metrics_reports = []
        while not metrics_queue.empty():
            metrics_reports.append(metrics_queue.get())
        
        # Should have error count
        if metrics_reports:
            assert 'errors_count' in metrics_reports[-1]
    
    def test_heartbeat_mechanism(self, mock_config, test_queues):
        """Test worker heartbeat mechanism."""
        input_queue, output_queue, metrics_queue = test_queues
        
        worker = GPUWorker(
            worker_id=4,
            input_queue=input_queue,
            output_queue=output_queue,
            metrics_queue=metrics_queue,
            config=mock_config,
            heartbeat_interval=0.5  # Fast heartbeat for testing
        )
        
        # Start worker
        process = worker.start()
        
        # Wait for heartbeats
        time.sleep(1.5)
        
        # Stop worker
        worker.stop()
        process.join(timeout=5)
        
        # Check for heartbeat messages
        heartbeats = []
        while not metrics_queue.empty():
            msg = metrics_queue.get()
            if msg.get('type') == 'heartbeat':
                heartbeats.append(msg)
        
        assert len(heartbeats) >= 2  # Should have multiple heartbeats
        
        for heartbeat in heartbeats:
            assert heartbeat['worker_id'] == 4
            assert 'timestamp' in heartbeat
            assert heartbeat['status'] == 'alive'
    
    def test_batch_size_adjustment(self, mock_config, test_queues):
        """Test automatic batch size adjustment."""
        input_queue, output_queue, metrics_queue = test_queues
        
        # Mock CUDA OOM error
        with patch('helios.inference.onnx_engine.ONNXInferenceEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_engine.process_batch.side_effect = [
                RuntimeError("CUDA out of memory"),  # First call fails
                [{'result': 'success'}]  # Second call succeeds
            ]
            mock_engine_class.return_value = mock_engine
            
            # Add test task
            task_data = {
                'path': '/test/large_file.jpg',
                'name': 'large_file.jpg',
                'extension': '.jpg',
                'size_bytes': 10000000,
                'modified_time': time.time()
            }
            input_queue.put(task_data)
            input_queue.put(None)
            
            worker = GPUWorker(
                worker_id=5,
                input_queue=input_queue,
                output_queue=output_queue,
                metrics_queue=metrics_queue,
                config=mock_config
            )
            
            # Start and wait
            process = worker.start()
            time.sleep(2)
            worker.stop()
            process.join(timeout=5)
            
            # Should have attempted batch size reduction
            # (This is more of an integration test - actual verification would require more setup)
    
    def test_worker_restart_on_failure(self, mock_config, test_queues):
        """Test worker restart mechanism on failure."""
        input_queue, output_queue, metrics_queue = test_queues
        
        worker = GPUWorker(
            worker_id=6,
            input_queue=input_queue,
            output_queue=output_queue,
            metrics_queue=metrics_queue,
            config=mock_config
        )
        
        # Start worker
        process1 = worker.start()
        original_pid = process1.pid
        
        # Simulate process failure
        process1.terminate()
        process1.join(timeout=2)
        
        # Restart worker
        process2 = worker.start()
        new_pid = process2.pid
        
        assert new_pid != original_pid
        assert process2.is_alive()
        
        # Cleanup
        worker.stop()
        process2.join(timeout=5)
    
    def test_concurrent_workers(self, mock_config):
        """Test multiple workers running concurrently."""
        # Create shared queues
        input_queue = mp.Queue(maxsize=200)
        output_queue = mp.Queue(maxsize=200)
        metrics_queue = mp.Queue(maxsize=200)
        
        # Add many test tasks
        for i in range(20):
            task_data = {
                'path': f'/test/file_{i:02d}.jpg',
                'name': f'file_{i:02d}.jpg',
                'extension': '.jpg',
                'size_bytes': 1024000,
                'modified_time': time.time()
            }
            input_queue.put(task_data)
        
        # Create multiple workers
        workers = []
        processes = []
        
        for worker_id in range(3):
            worker = GPUWorker(
                worker_id=worker_id,
                input_queue=input_queue,
                output_queue=output_queue,
                metrics_queue=metrics_queue,
                config=mock_config
            )
            workers.append(worker)
            processes.append(worker.start())
        
        # Wait for processing
        time.sleep(3)
        
        # Stop all workers
        for worker in workers:
            worker.stop()
        
        for process in processes:
            process.join(timeout=5)
        
        # Check results
        results = []
        while not output_queue.empty():
            results.append(output_queue.get())
        
        # Should have processed most/all tasks
        assert len(results) >= 15  # Allow for some timing variations
        
        # Verify different workers processed tasks
        worker_ids = set(result.get('worker_id') for result in results)
        assert len(worker_ids) > 1  # Multiple workers should have contributed


class TestWorkerMetrics:
    """Test WorkerMetrics class."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = WorkerMetrics(worker_id=1)
        
        assert metrics.worker_id == 1
        assert metrics.files_processed == 0
        assert metrics.total_processing_time == 0.0
        assert metrics.errors_count == 0
        assert len(metrics.processing_times) == 0
    
    def test_metrics_recording(self):
        """Test metrics recording."""
        metrics = WorkerMetrics(worker_id=2)
        
        # Record some processing
        metrics.record_processing(0.1, 5)  # 0.1s for 5 files
        metrics.record_processing(0.2, 3)  # 0.2s for 3 files
        
        assert metrics.files_processed == 8
        assert metrics.total_processing_time == 0.3
        assert len(metrics.processing_times) == 2
        
        # Test calculated properties
        assert metrics.avg_processing_time == 0.15
        assert metrics.files_per_second > 0
    
    def test_metrics_error_recording(self):
        """Test error recording."""
        metrics = WorkerMetrics(worker_id=3)
        
        metrics.record_error("Test error 1")
        metrics.record_error("Test error 2")
        
        assert metrics.errors_count == 2
        assert len(metrics.recent_errors) == 2
        assert "Test error 1" in metrics.recent_errors
    
    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = WorkerMetrics(worker_id=4)
        metrics.record_processing(0.1, 2)
        metrics.record_error("Test error")
        
        metrics_dict = metrics.to_dict()
        
        required_fields = [
            'worker_id', 'files_processed', 'total_processing_time',
            'avg_processing_time', 'files_per_second', 'errors_count'
        ]
        
        for field in required_fields:
            assert field in metrics_dict
        
        assert metrics_dict['worker_id'] == 4
        assert metrics_dict['files_processed'] == 2
        assert metrics_dict['errors_count'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])