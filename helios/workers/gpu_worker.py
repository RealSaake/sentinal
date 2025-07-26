#!/usr/bin/env python3
"""
GPUWorker - Independent multiprocessing worker for AI inference
True parallel processing that bypasses Python's GIL
"""

import logging
import multiprocessing as mp
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
import os
import signal

from helios.inference.onnx_engine import ONNXInferenceEngine
from helios.core.config import HeliosConfig

logger = logging.getLogger(__name__)


@dataclass
class WorkerMetrics:
    """Metrics for individual worker performance."""
    worker_id: int
    files_processed: int = 0
    total_processing_time: float = 0.0
    errors_count: int = 0
    start_time: Optional[float] = None
    processing_times: List[float] = field(default_factory=list)
    recent_errors: List[str] = field(default_factory=list)
    
    def record_processing(self, processing_time: float, batch_size: int) -> None:
        """Record batch processing metrics."""
        self.files_processed += batch_size
        self.total_processing_time += processing_time
        self.processing_times.append(processing_time)
        
        # Keep only recent processing times for memory efficiency
        if len(self.processing_times) > 100:
            self.processing_times = self.processing_times[-100:]
    
    def record_error(self, error_msg: str) -> None:
        """Record an error."""
        self.errors_count += 1
        self.recent_errors.append(error_msg)
        
        # Keep only recent errors
        if len(self.recent_errors) > 20:
            self.recent_errors = self.recent_errors[-20:]
    
    @property
    def avg_processing_time(self) -> float:
        """Average processing time per batch."""
        return (self.total_processing_time / len(self.processing_times) 
                if self.processing_times else 0.0)
    
    @property
    def files_per_second(self) -> float:
        """Files processed per second."""
        return (self.files_processed / self.total_processing_time 
                if self.total_processing_time > 0 else 0.0)
    
    @property
    def uptime_seconds(self) -> float:
        """Worker uptime in seconds."""
        return time.time() - self.start_time if self.start_time else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for IPC."""
        return {
            'worker_id': self.worker_id,
            'files_processed': self.files_processed,
            'total_processing_time': self.total_processing_time,
            'avg_processing_time': self.avg_processing_time,
            'files_per_second': self.files_per_second,
            'errors_count': self.errors_count,
            'uptime_seconds': self.uptime_seconds,
            'recent_errors': self.recent_errors[-5:],  # Last 5 errors
            'timestamp': datetime.now().isoformat()
        }


class GPUWorker:
    """
    Independent GPU worker process for AI inference.
    Each worker runs in its own process with its own ONNX inference engine.
    """
    
    def __init__(
        self,
        worker_id: int,
        input_queue: mp.Queue,
        output_queue: mp.Queue,
        metrics_queue: mp.Queue,
        config: HeliosConfig,
        heartbeat_interval: float = 30.0,
        batch_timeout: float = 1.0
    ):
        """Initialize GPU worker."""
        self.worker_id = worker_id
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.metrics_queue = metrics_queue
        self.config = config
        self.heartbeat_interval = heartbeat_interval
        self.batch_timeout = batch_timeout
        
        # Process management
        self.process: Optional[mp.Process] = None
        self.is_running = False
        self._stop_event = mp.Event()
        
        # Metrics
        self.metrics = WorkerMetrics(worker_id=worker_id)
        
        logger.info(f"🤖 GPUWorker {worker_id} initialized")
    
    def start(self) -> mp.Process:
        """Start the worker process."""
        if self.process and self.process.is_alive():
            logger.warning(f"Worker {self.worker_id} is already running")
            return self.process
        
        self._stop_event.clear()
        self.process = mp.Process(
            target=self._worker_main,
            name=f"GPUWorker-{self.worker_id}"
        )
        self.process.start()
        self.is_running = True
        
        logger.info(f"🚀 GPUWorker {self.worker_id} started (PID: {self.process.pid})")
        return self.process
    
    def stop(self, timeout: float = 10.0) -> None:
        """Stop the worker process gracefully."""
        if not self.process or not self.process.is_alive():
            return
        
        logger.info(f"🛑 Stopping GPUWorker {self.worker_id}...")
        
        # Signal stop
        self._stop_event.set()
        
        # Wait for graceful shutdown
        self.process.join(timeout=timeout)
        
        # Force terminate if needed
        if self.process.is_alive():
            logger.warning(f"Force terminating GPUWorker {self.worker_id}")
            self.process.terminate()
            self.process.join(timeout=2)
        
        self.is_running = False
        logger.info(f"✅ GPUWorker {self.worker_id} stopped")
    
    def _worker_main(self) -> None:
        """Main worker process function."""
        # Set up logging for this process
        logging.basicConfig(
            level=logging.INFO,
            format=f'%(asctime)s - Worker{self.worker_id} - %(levelname)s - %(message)s'
        )
        
        logger.info(f"🤖 GPUWorker {self.worker_id} starting main loop")
        
        # Initialize metrics
        self.metrics.start_time = time.time()
        
        # Initialize inference engine
        inference_engine = None
        try:
            inference_engine = ONNXInferenceEngine(
                model_path=self.config.inference.onnx_model_path,
                use_cuda=self.config.inference.cuda_enabled,
                confidence_threshold=self.config.inference.confidence_threshold,
                initial_batch_size=self.config.performance.batch_size
            )
            logger.info(f"✅ Inference engine initialized for worker {self.worker_id}")
            
        except Exception as e:
            error_msg = f"Failed to initialize inference engine: {e}"
            logger.error(error_msg)
            self.metrics.record_error(error_msg)
            self._send_metrics()
            return
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Worker {self.worker_id} received signal {signum}")
            self._stop_event.set()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Main processing loop
        last_heartbeat = time.time()
        current_batch = []
        last_batch_time = time.time()
        
        try:
            while not self._stop_event.is_set():
                try:
                    # Check for heartbeat
                    if time.time() - last_heartbeat >= self.heartbeat_interval:
                        self._send_heartbeat()
                        last_heartbeat = time.time()
                    
                    # Try to get task from queue
                    try:
                        task = self.input_queue.get(timeout=0.1)
                        
                        # Check for stop signal
                        if task is None:
                            logger.info(f"Worker {self.worker_id} received stop signal")
                            break
                        
                        # Add to current batch
                        current_batch.append(task)
                        
                    except Exception:
                        # No task available - check if we should process current batch
                        pass
                    
                    # Process batch if ready
                    should_process = (
                        len(current_batch) >= self.config.performance.batch_size or
                        (current_batch and time.time() - last_batch_time >= self.batch_timeout)
                    )
                    
                    if should_process and current_batch:
                        self._process_batch(current_batch, inference_engine)
                        current_batch = []
                        last_batch_time = time.time()
                
                except Exception as e:
                    error_msg = f"Error in worker main loop: {e}"
                    logger.error(error_msg)
                    self.metrics.record_error(error_msg)
            
            # Process remaining batch
            if current_batch:
                self._process_batch(current_batch, inference_engine)
            
        except Exception as e:
            error_msg = f"Fatal error in worker {self.worker_id}: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.metrics.record_error(error_msg)
        
        finally:
            # Send final metrics
            self._send_metrics()
            
            # Cleanup
            if inference_engine:
                inference_engine.shutdown()
            
            logger.info(f"🏁 GPUWorker {self.worker_id} main loop ended")
    
    def _process_batch(self, batch: List[Dict[str, Any]], inference_engine: ONNXInferenceEngine) -> None:
        """Process a batch of file tasks."""
        if not batch:
            return
        
        logger.debug(f"🔄 Worker {self.worker_id} processing batch of {len(batch)} files")
        
        batch_start_time = time.time()
        
        try:
            # Convert dict data back to FileTask objects for processing
            # For MVP, we'll work directly with the dict data
            file_tasks = []
            for task_data in batch:
                # Create a simple task object
                file_task = type('FileTask', (), {
                    'metadata': type('Metadata', (), {
                        'name': task_data.get('name', 'unknown'),
                        'extension': task_data.get('extension', ''),
                        'size_bytes': task_data.get('size_bytes', 0),
                        'size_mb': task_data.get('size_bytes', 0) / (1024 * 1024)
                    })(),
                    'file_path': task_data.get('path', ''),
                    'project_indicators': task_data.get('project_indicators', []),
                    'related_files': task_data.get('related_files', []),
                    'parent_directory': task_data.get('parent_directory', '')
                })()
                file_tasks.append(file_task)
            
            # Process batch with inference engine
            results = inference_engine.process_batch(file_tasks)
            
            # Send results to output queue
            for i, result in enumerate(results):
                original_task = batch[i]
                
                # Enhance result with worker info
                enhanced_result = {
                    'original_path': original_task.get('path', ''),
                    'categorized_path': result.get('categorized_path', ''),
                    'confidence': result.get('confidence', 0.0),
                    'tags': result.get('tags', []),
                    'worker_id': self.worker_id,
                    'processing_time': time.time() - batch_start_time,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Add any error information
                if 'error' in result:
                    enhanced_result['error'] = result['error']
                
                self.output_queue.put(enhanced_result)
            
            # Record metrics
            processing_time = time.time() - batch_start_time
            self.metrics.record_processing(processing_time, len(batch))
            
            logger.debug(f"✅ Worker {self.worker_id} completed batch in {processing_time:.3f}s")
            
        except Exception as e:
            error_msg = f"Batch processing failed: {e}"
            logger.error(error_msg)
            self.metrics.record_error(error_msg)
            
            # Send error results
            for task_data in batch:
                error_result = {
                    'original_path': task_data.get('path', ''),
                    'categorized_path': f"Errors/{task_data.get('name', 'unknown')}",
                    'confidence': 0.0,
                    'tags': ['error'],
                    'error': error_msg,
                    'worker_id': self.worker_id,
                    'timestamp': datetime.now().isoformat()
                }
                self.output_queue.put(error_result)
    
    def _send_heartbeat(self) -> None:
        """Send heartbeat message."""
        try:
            heartbeat = {
                'type': 'heartbeat',
                'worker_id': self.worker_id,
                'status': 'alive',
                'timestamp': datetime.now().isoformat(),
                'pid': os.getpid()
            }
            self.metrics_queue.put(heartbeat)
            
        except Exception as e:
            logger.warning(f"Failed to send heartbeat: {e}")
    
    def _send_metrics(self) -> None:
        """Send current metrics."""
        try:
            metrics_data = self.metrics.to_dict()
            metrics_data['type'] = 'metrics'
            self.metrics_queue.put(metrics_data)
            
        except Exception as e:
            logger.warning(f"Failed to send metrics: {e}")
    
    def is_alive(self) -> bool:
        """Check if worker process is alive."""
        return self.process is not None and self.process.is_alive()
    
    def get_pid(self) -> Optional[int]:
        """Get worker process PID."""
        return self.process.pid if self.process else None


class WorkerPool:
    """Manages a pool of GPU workers."""
    
    def __init__(
        self,
        num_workers: int,
        input_queue: mp.Queue,
        output_queue: mp.Queue,
        metrics_queue: mp.Queue,
        config: HeliosConfig
    ):
        """Initialize worker pool."""
        self.num_workers = num_workers
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.metrics_queue = metrics_queue
        self.config = config
        
        self.workers: List[GPUWorker] = []
        self.is_running = False
        
        logger.info(f"🏭 WorkerPool initialized with {num_workers} workers")
    
    def start(self) -> None:
        """Start all workers."""
        if self.is_running:
            logger.warning("Worker pool is already running")
            return
        
        logger.info(f"🚀 Starting {self.num_workers} GPU workers...")
        
        for worker_id in range(self.num_workers):
            worker = GPUWorker(
                worker_id=worker_id,
                input_queue=self.input_queue,
                output_queue=self.output_queue,
                metrics_queue=self.metrics_queue,
                config=self.config
            )
            
            worker.start()
            self.workers.append(worker)
        
        self.is_running = True
        logger.info(f"✅ All {self.num_workers} workers started")
    
    def stop(self, timeout: float = 10.0) -> None:
        """Stop all workers."""
        if not self.is_running:
            return
        
        logger.info(f"🛑 Stopping {len(self.workers)} workers...")
        
        # Send stop signals
        for _ in self.workers:
            self.input_queue.put(None)
        
        # Stop all workers
        for worker in self.workers:
            worker.stop(timeout=timeout)
        
        self.workers.clear()
        self.is_running = False
        
        logger.info("✅ All workers stopped")
    
    def get_worker_status(self) -> List[Dict[str, Any]]:
        """Get status of all workers."""
        status = []
        for worker in self.workers:
            status.append({
                'worker_id': worker.worker_id,
                'is_alive': worker.is_alive(),
                'pid': worker.get_pid(),
                'is_running': worker.is_running
            })
        return status
    
    def restart_failed_workers(self) -> int:
        """Restart any failed workers. Returns number of workers restarted."""
        restarted = 0
        
        for i, worker in enumerate(self.workers):
            if not worker.is_alive():
                logger.warning(f"Restarting failed worker {worker.worker_id}")
                
                # Stop the old worker
                worker.stop(timeout=2)
                
                # Create new worker
                new_worker = GPUWorker(
                    worker_id=worker.worker_id,
                    input_queue=self.input_queue,
                    output_queue=self.output_queue,
                    metrics_queue=self.metrics_queue,
                    config=self.config
                )
                
                new_worker.start()
                self.workers[i] = new_worker
                restarted += 1
        
        return restarted