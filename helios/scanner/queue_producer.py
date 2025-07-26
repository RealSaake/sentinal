#!/usr/bin/env python3
"""
Queue Producer for AsyncFileScanner
Integrates async file scanning with multiprocessing queues
"""

import asyncio
import logging
import multiprocessing as mp
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from .async_scanner import AsyncFileScanner, ScanMetrics
from helios.core.models import FileTask
from helios.core.config import HeliosConfig

logger = logging.getLogger(__name__)


@dataclass
class QueueMetrics:
    """Metrics for queue operations."""
    items_queued: int = 0
    queue_full_events: int = 0
    backpressure_events: int = 0
    total_wait_time: float = 0.0
    avg_queue_size: float = 0.0
    max_queue_size: int = 0
    queue_size_samples: list = field(default_factory=list)
    
    def record_item_queued(self, queue_size: int) -> None:
        """Record an item being queued."""
        self.items_queued += 1
        self.queue_size_samples.append(queue_size)
        self.max_queue_size = max(self.max_queue_size, queue_size)
        
        # Keep only recent samples for memory efficiency
        if len(self.queue_size_samples) > 1000:
            self.queue_size_samples = self.queue_size_samples[-1000:]
        
        # Update average
        if self.queue_size_samples:
            self.avg_queue_size = sum(self.queue_size_samples) / len(self.queue_size_samples)
    
    def record_queue_full(self) -> None:
        """Record a queue full event."""
        self.queue_full_events += 1
    
    def record_backpressure(self, wait_time: float) -> None:
        """Record a backpressure event."""
        self.backpressure_events += 1
        self.total_wait_time += wait_time
    
    @property
    def avg_wait_time(self) -> float:
        """Average wait time per backpressure event."""
        return self.total_wait_time / self.backpressure_events if self.backpressure_events > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'items_queued': self.items_queued,
            'queue_full_events': self.queue_full_events,
            'backpressure_events': self.backpressure_events,
            'total_wait_time': self.total_wait_time,
            'avg_wait_time': self.avg_wait_time,
            'avg_queue_size': self.avg_queue_size,
            'max_queue_size': self.max_queue_size
        }


class QueueProducer:
    """
    Async producer that feeds FileTask objects into multiprocessing queue.
    Implements backpressure mechanism to prevent memory exhaustion.
    """
    
    def __init__(
        self,
        queue: mp.Queue,
        config: HeliosConfig,
        max_queue_size: Optional[int] = None,
        backpressure_threshold: float = 0.8,
        backpressure_wait: float = 0.1
    ):
        """Initialize queue producer."""
        self.queue = queue
        self.config = config
        self.max_queue_size = max_queue_size or config.performance.queue_max_size
        self.backpressure_threshold = backpressure_threshold
        self.backpressure_wait = backpressure_wait
        
        # State tracking
        self.is_producing = False
        self.production_cancelled = False
        
        # Metrics
        self.queue_metrics = QueueMetrics()
        self.scanner_metrics: Optional[ScanMetrics] = None
        
        logger.info(f"🏭 QueueProducer initialized")
        logger.info(f"   Max queue size: {self.max_queue_size}")
        logger.info(f"   Backpressure threshold: {self.backpressure_threshold}")
        logger.info(f"   Backpressure wait: {self.backpressure_wait}s")
    
    async def produce_from_directory(
        self,
        directory: str,
        max_workers: int = 4
    ) -> None:
        """
        Scan directory and feed files into queue with backpressure control.
        """
        if self.is_producing:
            raise RuntimeError("Producer is already running")
        
        directory_path = Path(directory)
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        logger.info(f"🚀 Starting queue production from: {directory}")
        
        self.is_producing = True
        self.production_cancelled = False
        
        try:
            # Initialize scanner
            async with AsyncFileScanner(
                base_directory=directory,
                config=self.config,
                max_workers=max_workers
            ) as scanner:
                
                # Scan and queue files
                async for file_task in scanner.scan_directory():
                    if self.production_cancelled:
                        logger.info("📛 Production cancelled")
                        break
                    
                    # Apply backpressure if queue is getting full
                    await self._handle_backpressure()
                    
                    # Queue the file task
                    await self._queue_file_task(file_task)
                
                # Store scanner metrics
                self.scanner_metrics = scanner.get_metrics()
                
        except Exception as e:
            logger.error(f"❌ Production failed: {e}")
            raise
        
        finally:
            self.is_producing = False
            logger.info(f"✅ Production completed: {self.queue_metrics.items_queued} items queued")
    
    async def _handle_backpressure(self) -> None:
        """Handle backpressure when queue is getting full."""
        try:
            # Get approximate queue size (this is not exact due to multiprocessing)
            current_size = self._get_approximate_queue_size()
            
            # Check if we need to apply backpressure
            if current_size >= self.max_queue_size * self.backpressure_threshold:
                logger.debug(f"🔄 Applying backpressure: queue size ~{current_size}")
                
                wait_start = time.time()
                
                # Wait for queue to drain
                while current_size >= self.max_queue_size * self.backpressure_threshold:
                    if self.production_cancelled:
                        break
                    
                    await asyncio.sleep(self.backpressure_wait)
                    current_size = self._get_approximate_queue_size()
                
                wait_time = time.time() - wait_start
                self.queue_metrics.record_backpressure(wait_time)
                
                logger.debug(f"✅ Backpressure released after {wait_time:.3f}s")
        
        except Exception as e:
            logger.warning(f"⚠️  Backpressure handling error: {e}")
    
    def _get_approximate_queue_size(self) -> int:
        """
        Get approximate queue size.
        Note: multiprocessing.Queue doesn't provide exact size,
        so this is an approximation based on our tracking.
        """
        try:
            # This is a rough approximation
            # In practice, you might need a more sophisticated approach
            return min(self.queue_metrics.items_queued, self.max_queue_size)
        except:
            return 0
    
    async def _queue_file_task(self, file_task: FileTask) -> None:
        """Queue a file task with error handling."""
        try:
            # Convert FileTask to dictionary for multiprocessing
            task_dict = file_task.to_dict()
            
            # Try to put item in queue (non-blocking)
            try:
                self.queue.put_nowait(task_dict)
                current_size = self._get_approximate_queue_size()
                self.queue_metrics.record_item_queued(current_size)
                
                logger.debug(f"📤 Queued: {file_task.metadata.name}")
                
            except Exception as e:
                # Queue is full - record event and wait
                self.queue_metrics.record_queue_full()
                logger.debug(f"🔄 Queue full, waiting...")
                
                # Wait and retry
                await asyncio.sleep(self.backpressure_wait)
                
                # Retry with blocking put (in executor to avoid blocking event loop)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.queue.put, task_dict)
                
                current_size = self._get_approximate_queue_size()
                self.queue_metrics.record_item_queued(current_size)
        
        except Exception as e:
            logger.error(f"❌ Failed to queue file task: {e}")
            raise
    
    def cancel_production(self) -> None:
        """Cancel ongoing production."""
        self.production_cancelled = True
        logger.info("📛 Production cancellation requested")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics."""
        metrics = {
            'queue_metrics': self.queue_metrics.to_dict(),
            'is_producing': self.is_producing,
            'production_cancelled': self.production_cancelled
        }
        
        if self.scanner_metrics:
            metrics['scanner_metrics'] = self.scanner_metrics.to_dict()
        
        return metrics
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.queue_metrics = QueueMetrics()
        self.scanner_metrics = None
        logger.info("📊 Producer metrics reset")


class BatchQueueProducer(QueueProducer):
    """
    Enhanced producer that batches files before queuing for better performance.
    """
    
    def __init__(
        self,
        queue: mp.Queue,
        config: HeliosConfig,
        batch_size: int = 10,
        batch_timeout: float = 1.0,
        **kwargs
    ):
        """Initialize batch queue producer."""
        super().__init__(queue, config, **kwargs)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.current_batch = []
        self.last_batch_time = time.time()
        
        logger.info(f"📦 BatchQueueProducer initialized")
        logger.info(f"   Batch size: {self.batch_size}")
        logger.info(f"   Batch timeout: {self.batch_timeout}s")
    
    async def produce_from_directory(
        self,
        directory: str,
        max_workers: int = 4
    ) -> None:
        """Scan directory and feed batched files into queue."""
        if self.is_producing:
            raise RuntimeError("Producer is already running")
        
        directory_path = Path(directory)
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        logger.info(f"🚀 Starting batched queue production from: {directory}")
        
        self.is_producing = True
        self.production_cancelled = False
        self.current_batch = []
        self.last_batch_time = time.time()
        
        try:
            # Initialize scanner
            async with AsyncFileScanner(
                base_directory=directory,
                config=self.config,
                max_workers=max_workers
            ) as scanner:
                
                # Scan and batch files
                async for file_task in scanner.scan_directory():
                    if self.production_cancelled:
                        logger.info("📛 Production cancelled")
                        break
                    
                    # Add to current batch
                    self.current_batch.append(file_task)
                    
                    # Check if batch is ready
                    if await self._should_flush_batch():
                        await self._flush_batch()
                
                # Flush remaining batch
                if self.current_batch:
                    await self._flush_batch()
                
                # Store scanner metrics
                self.scanner_metrics = scanner.get_metrics()
                
        except Exception as e:
            logger.error(f"❌ Batched production failed: {e}")
            raise
        
        finally:
            self.is_producing = False
            logger.info(f"✅ Batched production completed: {self.queue_metrics.items_queued} items queued")
    
    async def _should_flush_batch(self) -> bool:
        """Check if batch should be flushed."""
        # Flush if batch is full
        if len(self.current_batch) >= self.batch_size:
            return True
        
        # Flush if timeout reached
        if time.time() - self.last_batch_time >= self.batch_timeout:
            return True
        
        return False
    
    async def _flush_batch(self) -> None:
        """Flush current batch to queue."""
        if not self.current_batch:
            return
        
        logger.debug(f"📦 Flushing batch of {len(self.current_batch)} items")
        
        # Apply backpressure
        await self._handle_backpressure()
        
        # Convert batch to dictionary format
        batch_dict = {
            'type': 'file_batch',
            'items': [task.to_dict() for task in self.current_batch],
            'batch_size': len(self.current_batch),
            'timestamp': time.time()
        }
        
        # Queue the batch
        try:
            self.queue.put_nowait(batch_dict)
            
            # Update metrics
            for _ in self.current_batch:
                current_size = self._get_approximate_queue_size()
                self.queue_metrics.record_item_queued(current_size)
            
        except Exception as e:
            # Queue full - wait and retry
            self.queue_metrics.record_queue_full()
            await asyncio.sleep(self.backpressure_wait)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.queue.put, batch_dict)
            
            # Update metrics
            for _ in self.current_batch:
                current_size = self._get_approximate_queue_size()
                self.queue_metrics.record_item_queued(current_size)
        
        # Clear batch
        self.current_batch = []
        self.last_batch_time = time.time()


# Utility functions for testing
def create_test_queue(maxsize: int = 1000) -> mp.Queue:
    """Create a test multiprocessing queue."""
    return mp.Queue(maxsize=maxsize)


async def test_queue_integration(directory: str, config: HeliosConfig) -> Dict[str, Any]:
    """Test queue integration with a directory."""
    # Create test queue
    test_queue = create_test_queue(maxsize=100)
    
    # Create producer
    producer = QueueProducer(
        queue=test_queue,
        config=config,
        max_queue_size=100,
        backpressure_threshold=0.8
    )
    
    # Start production
    await producer.produce_from_directory(directory, max_workers=4)
    
    # Collect results
    results = []
    while not test_queue.empty():
        try:
            item = test_queue.get_nowait()
            results.append(item)
        except:
            break
    
    # Get metrics
    metrics = producer.get_metrics()
    metrics['items_retrieved'] = len(results)
    
    return metrics