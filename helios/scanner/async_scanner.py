#!/usr/bin/env python3
"""
AsyncFileScanner - High-performance async file system scanner
Non-blocking file discovery with intelligent filtering and context analysis
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

from helios.core.models import FileTask, FileMetadata
from helios.core.config import HeliosConfig

logger = logging.getLogger(__name__)


@dataclass
class ScanMetrics:
    """Metrics for file scanning performance."""
    files_discovered: int = 0
    directories_scanned: int = 0
    errors_count: int = 0
    skipped_count: int = 0
    scan_time: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    errors: List[str] = field(default_factory=list)
    
    def start_scan(self) -> None:
        """Start scan timing."""
        self.start_time = time.time()
    
    def end_scan(self) -> None:
        """End scan timing."""
        self.end_time = time.time()
        if self.start_time:
            self.scan_time = self.end_time - self.start_time
    
    def record_file_discovered(self) -> None:
        """Record a file discovery."""
        self.files_discovered += 1
    
    def record_directory_scanned(self) -> None:
        """Record a directory scan."""
        self.directories_scanned += 1
    
    def record_error(self, error_msg: str) -> None:
        """Record an error."""
        self.errors_count += 1
        self.errors.append(error_msg)
        if len(self.errors) > 100:  # Keep only recent errors
            self.errors = self.errors[-100:]
    
    def record_skipped(self) -> None:
        """Record a skipped file."""
        self.skipped_count += 1
    
    @property
    def files_per_second(self) -> float:
        """Calculate files per second."""
        if self.scan_time > 0:
            return self.files_discovered / self.scan_time
        return 0.0
    
    @property
    def total_items_processed(self) -> int:
        """Total items processed (files + directories)."""
        return self.files_discovered + self.directories_scanned
    
    def to_dict(self) -> Dict[str, any]:
        """Convert metrics to dictionary."""
        return {
            'files_discovered': self.files_discovered,
            'directories_scanned': self.directories_scanned,
            'errors_count': self.errors_count,
            'skipped_count': self.skipped_count,
            'scan_time': self.scan_time,
            'files_per_second': self.files_per_second,
            'total_items_processed': self.total_items_processed,
            'recent_errors': self.errors[-10:] if self.errors else []
        }


class AsyncFileScanner:
    """High-performance async file scanner with intelligent filtering."""
    
    def __init__(
        self,
        base_directory: str,
        config: HeliosConfig,
        max_workers: int = 4,
        chunk_size: int = 100
    ):
        """Initialize async file scanner."""
        self.base_directory = Path(base_directory).resolve()
        self.config = config
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        
        # State tracking
        self.is_scanning = False
        self.metrics = ScanMetrics()
        self._scan_cancelled = False
        
        # Thread pool for I/O operations
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Caching for performance
        self._stat_cache: Dict[str, os.stat_result] = {}
        self._skip_cache: Dict[str, bool] = {}
        
        logger.info(f"🔍 AsyncFileScanner initialized")
        logger.info(f"   Base directory: {self.base_directory}")
        logger.info(f"   Max workers: {self.max_workers}")
        logger.info(f"   Chunk size: {self.chunk_size}")
    
    async def scan_directory(self) -> AsyncGenerator[FileTask, None]:
        """
        Async generator that yields FileTask objects for discovered files.
        Uses non-blocking I/O for maximum performance.
        """
        if not self.base_directory.exists():
            raise FileNotFoundError(f"Directory not found: {self.base_directory}")
        
        if not self.base_directory.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {self.base_directory}")
        
        logger.info(f"🚀 Starting async directory scan: {self.base_directory}")
        
        self.is_scanning = True
        self._scan_cancelled = False
        self.metrics.start_scan()
        
        try:
            # Use asyncio to scan directories concurrently
            async for file_task in self._scan_directory_recursive(self.base_directory):
                if self._scan_cancelled:
                    logger.info("📛 Scan cancelled by user")
                    break
                
                yield file_task
                
        except Exception as e:
            logger.error(f"❌ Scan failed: {e}")
            self.metrics.record_error(str(e))
            raise
        
        finally:
            self.is_scanning = False
            self.metrics.end_scan()
            logger.info(f"✅ Scan completed: {self.metrics.files_discovered} files in {self.metrics.scan_time:.2f}s")
    
    async def _scan_directory_recursive(self, directory: Path) -> AsyncGenerator[FileTask, None]:
        """Recursively scan directory structure using async I/O."""
        try:
            # Get directory contents asynchronously
            entries = await self._get_directory_entries(directory)
            self.metrics.record_directory_scanned()
            
            # Process entries in chunks for better performance
            for chunk in self._chunk_list(entries, self.chunk_size):
                # Process chunk concurrently
                tasks = [self._process_entry(entry) for entry in chunk]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        self.metrics.record_error(str(result))
                        continue
                    
                    if result is None:
                        continue
                    
                    if isinstance(result, FileTask):
                        # It's a file
                        self.metrics.record_file_discovered()
                        yield result
                    elif isinstance(result, Path):
                        # It's a directory - recurse
                        async for file_task in self._scan_directory_recursive(result):
                            yield file_task
                
        except PermissionError as e:
            logger.warning(f"⚠️  Permission denied: {directory}")
            self.metrics.record_error(f"Permission denied: {directory}")
        except Exception as e:
            logger.error(f"❌ Error scanning {directory}: {e}")
            self.metrics.record_error(f"Error scanning {directory}: {e}")
    
    async def _get_directory_entries(self, directory: Path) -> List[Path]:
        """Get directory entries asynchronously."""
        loop = asyncio.get_event_loop()
        
        def _list_directory():
            try:
                return [directory / entry for entry in os.listdir(directory)]
            except (OSError, PermissionError) as e:
                logger.warning(f"⚠️  Cannot list directory {directory}: {e}")
                return []
        
        return await loop.run_in_executor(self._executor, _list_directory)
    
    async def _process_entry(self, entry_path: Path) -> Optional[any]:
        """Process a single directory entry (file or directory)."""
        try:
            # Get file stats asynchronously
            stat_result = await self._get_file_stats(entry_path)
            if not stat_result:
                return None
            
            if entry_path.is_dir():
                # Return directory for recursive processing
                return entry_path
            
            elif entry_path.is_file():
                # Check if file should be skipped
                should_skip, skip_reason = await self._should_skip_file(entry_path, stat_result)
                if should_skip:
                    self.metrics.record_skipped()
                    logger.debug(f"⏭️  Skipping {entry_path}: {skip_reason}")
                    return None
                
                # Create FileTask
                file_task = await self._create_file_task(entry_path, stat_result)
                return file_task
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️  Error processing {entry_path}: {e}")
            self.metrics.record_error(f"Error processing {entry_path}: {e}")
            return None
    
    async def _get_file_stats(self, file_path: Path) -> Optional[os.stat_result]:
        """Get file statistics asynchronously with caching."""
        file_str = str(file_path)
        
        # Check cache first
        if file_str in self._stat_cache:
            return self._stat_cache[file_str]
        
        loop = asyncio.get_event_loop()
        
        def _get_stats():
            try:
                return os.stat(file_path)
            except (OSError, PermissionError):
                return None
        
        stat_result = await loop.run_in_executor(self._executor, _get_stats)
        
        # Cache result
        if stat_result:
            self._stat_cache[file_str] = stat_result
            
            # Limit cache size
            if len(self._stat_cache) > 10000:
                # Remove oldest entries
                keys_to_remove = list(self._stat_cache.keys())[:1000]
                for key in keys_to_remove:
                    del self._stat_cache[key]
        
        return stat_result
    
    async def _should_skip_file(self, file_path: Path, stat_result: os.stat_result) -> tuple[bool, str]:
        """Check if file should be skipped based on configuration rules."""
        file_str = str(file_path)
        
        # Check cache first
        if file_str in self._skip_cache:
            return self._skip_cache[file_str], "Cached skip decision"
        
        # Calculate file age
        file_age_days = (time.time() - stat_result.st_mtime) / (24 * 3600)
        
        # Use configuration skip rules
        should_skip, reason = self.config.should_skip_file(
            file_str, 
            stat_result.st_size, 
            int(file_age_days)
        )
        
        # Cache decision
        self._skip_cache[file_str] = should_skip
        
        # Limit cache size
        if len(self._skip_cache) > 5000:
            # Remove oldest entries
            keys_to_remove = list(self._skip_cache.keys())[:500]
            for key in keys_to_remove:
                del self._skip_cache[key]
        
        return should_skip, reason
    
    async def _create_file_task(self, file_path: Path, stat_result: os.stat_result) -> FileTask:
        """Create FileTask with full metadata and context analysis."""
        loop = asyncio.get_event_loop()
        
        def _build_file_task():
            # Create metadata
            metadata = FileMetadata(
                path=str(file_path),
                name=file_path.name,
                extension=file_path.suffix.lower(),
                size_bytes=stat_result.st_size,
                created_time=datetime.fromtimestamp(stat_result.st_ctime),
                modified_time=datetime.fromtimestamp(stat_result.st_mtime),
                accessed_time=datetime.fromtimestamp(stat_result.st_atime)
            )
            
            # Create base task
            task = FileTask(
                file_path=str(file_path),
                metadata=metadata,
                priority=self._calculate_priority(file_path, stat_result)
            )
            
            # Add context analysis
            self._analyze_file_context(task, file_path)
            
            return task
        
        return await loop.run_in_executor(self._executor, _build_file_task)
    
    def _calculate_priority(self, file_path: Path, stat_result: os.stat_result) -> int:
        """Calculate processing priority for file (1-10)."""
        priority = 5  # Default
        
        # Higher priority for larger files
        size_mb = stat_result.st_size / (1024 * 1024)
        if size_mb > 100:  # > 100MB
            priority += 2
        elif size_mb > 10:  # > 10MB
            priority += 1
        
        # Higher priority for media files
        media_extensions = {'.jpg', '.jpeg', '.png', '.mp4', '.avi', '.mp3', '.wav'}
        if file_path.suffix.lower() in media_extensions:
            priority += 1
        
        # Lower priority for system files
        if file_path.name.startswith('.') or 'system' in file_path.name.lower():
            priority -= 2
        
        return max(1, min(10, priority))
    
    def _analyze_file_context(self, task: FileTask, file_path: Path) -> None:
        """Analyze file context and relationships."""
        try:
            parent_dir = file_path.parent
            
            # Get sibling files
            try:
                siblings = [f for f in parent_dir.iterdir() if f.is_file() and f != file_path]
                task.related_files = [
                    str(f) for f in siblings 
                    if f.stem == file_path.stem  # Same name, different extension
                ]
            except (OSError, PermissionError):
                task.related_files = []
            
            # Detect project indicators
            project_indicators = [
                'package.json', 'requirements.txt', 'pom.xml', 'Cargo.toml',
                '.git', 'makefile', 'Makefile', '.gitignore', 'README.md'
            ]
            
            try:
                parent_items = list(parent_dir.iterdir())
                parent_files = [f.name for f in parent_items if f.is_file()]
                parent_dirs = [d.name for d in parent_items if d.is_dir()]
                all_names = parent_files + parent_dirs
                
                task.project_indicators = [
                    indicator for indicator in project_indicators
                    if indicator in all_names or indicator.lower() in [name.lower() for name in all_names]
                ]
            except (OSError, PermissionError):
                task.project_indicators = []
            
            # Set parent directory
            task.parent_directory = str(parent_dir)
            
        except Exception as e:
            logger.debug(f"Context analysis failed for {file_path}: {e}")
            task.related_files = []
            task.project_indicators = []
    
    def _chunk_list(self, items: List[any], chunk_size: int) -> List[List[any]]:
        """Split list into chunks for batch processing."""
        for i in range(0, len(items), chunk_size):
            yield items[i:i + chunk_size]
    
    def cancel_scan(self) -> None:
        """Cancel ongoing scan."""
        self._scan_cancelled = True
        logger.info("📛 Scan cancellation requested")
    
    def get_metrics(self) -> ScanMetrics:
        """Get current scan metrics."""
        return self.metrics
    
    def reset_metrics(self) -> None:
        """Reset scan metrics."""
        self.metrics = ScanMetrics()
        logger.info("📊 Scan metrics reset")
    
    def clear_caches(self) -> None:
        """Clear internal caches."""
        self._stat_cache.clear()
        self._skip_cache.clear()
        logger.info("🧹 Scanner caches cleared")
    
    async def get_directory_summary(self, directory: Optional[Path] = None) -> Dict[str, any]:
        """Get summary of directory contents without full scan."""
        target_dir = directory or self.base_directory
        
        if not target_dir.exists():
            return {'error': 'Directory not found'}
        
        summary = {
            'path': str(target_dir),
            'total_items': 0,
            'files': 0,
            'directories': 0,
            'total_size_bytes': 0,
            'file_types': {},
            'largest_files': [],
            'errors': []
        }
        
        try:
            entries = await self._get_directory_entries(target_dir)
            
            for entry in entries[:1000]:  # Limit for performance
                try:
                    if entry.is_file():
                        summary['files'] += 1
                        stat_result = await self._get_file_stats(entry)
                        if stat_result:
                            summary['total_size_bytes'] += stat_result.st_size
                            
                            # Track file types
                            ext = entry.suffix.lower()
                            summary['file_types'][ext] = summary['file_types'].get(ext, 0) + 1
                            
                            # Track largest files
                            if len(summary['largest_files']) < 10:
                                summary['largest_files'].append({
                                    'name': entry.name,
                                    'size_bytes': stat_result.st_size,
                                    'size_mb': stat_result.st_size / (1024 * 1024)
                                })
                            else:
                                # Replace smallest if this is larger
                                smallest_idx = min(range(len(summary['largest_files'])), 
                                                 key=lambda i: summary['largest_files'][i]['size_bytes'])
                                if stat_result.st_size > summary['largest_files'][smallest_idx]['size_bytes']:
                                    summary['largest_files'][smallest_idx] = {
                                        'name': entry.name,
                                        'size_bytes': stat_result.st_size,
                                        'size_mb': stat_result.st_size / (1024 * 1024)
                                    }
                    
                    elif entry.is_dir():
                        summary['directories'] += 1
                    
                    summary['total_items'] += 1
                    
                except Exception as e:
                    summary['errors'].append(f"Error processing {entry}: {e}")
            
            # Sort largest files
            summary['largest_files'].sort(key=lambda x: x['size_bytes'], reverse=True)
            
        except Exception as e:
            summary['errors'].append(f"Error scanning directory: {e}")
        
        return summary
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.cancel_scan()
        self._executor.shutdown(wait=True)
        self.clear_caches()
    
    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)