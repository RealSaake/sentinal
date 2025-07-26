#!/usr/bin/env python3
"""
Sentinel 2.0 - Directory Scout Module
High-speed, low-overhead directory analysis for pre-flight checks
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict, Counter
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class ScoutMetrics:
    """Metrics collected by the directory scout."""
    total_files: int = 0
    total_directories: int = 0
    total_size_bytes: int = 0
    extension_histogram: Dict[str, int] = None
    large_files: List[Tuple[str, int]] = None  # (path, size) for files > threshold
    problematic_files: List[str] = None  # Files with no extension or other issues
    scan_duration_seconds: float = 0.0
    deepest_path_level: int = 0
    average_files_per_directory: float = 0.0
    
    def __post_init__(self):
        if self.extension_histogram is None:
            self.extension_histogram = {}
        if self.large_files is None:
            self.large_files = []
        if self.problematic_files is None:
            self.problematic_files = []


class DirectoryScout:
    """
    High-speed directory scanner that collects metadata without reading file contents.
    Designed for pre-flight analysis to give users accurate expectations.
    """
    
    def __init__(self, 
                 large_file_threshold_mb: int = 100,
                 max_workers: int = 4,
                 skip_hidden: bool = True,
                 skip_system_dirs: bool = True):
        """
        Initialize the directory scout.
        
        Args:
            large_file_threshold_mb: Files larger than this are flagged as "large"
            max_workers: Number of threads for parallel scanning
            skip_hidden: Skip hidden files and directories
            skip_system_dirs: Skip common system directories
        """
        self.large_file_threshold_bytes = large_file_threshold_mb * 1024 * 1024
        self.max_workers = max_workers
        self.skip_hidden = skip_hidden
        self.skip_system_dirs = skip_system_dirs
        
        # System directories to skip (Windows and Unix)
        self.system_dirs = {
            'System Volume Information', '$Recycle.Bin', 'Windows', 'Program Files',
            'Program Files (x86)', 'ProgramData', 'AppData', '.git', '.svn', 
            'node_modules', '__pycache__', '.vscode', '.idea', 'venv', '.env'
        }
        
        # Thread-safe counters
        self._lock = threading.Lock()
        self._metrics = ScoutMetrics()
        self._cancelled = False
    
    def cancel(self):
        """Cancel the current scan operation."""
        self._cancelled = True
    
    def _should_skip_directory(self, dir_path: Path) -> bool:
        """Determine if a directory should be skipped."""
        dir_name = dir_path.name
        
        # Skip hidden directories
        if self.skip_hidden and dir_name.startswith('.'):
            return True
        
        # Skip system directories
        if self.skip_system_dirs and dir_name in self.system_dirs:
            return True
        
        return False
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if a file should be skipped."""
        file_name = file_path.name
        
        # Skip hidden files
        if self.skip_hidden and file_name.startswith('.'):
            return True
        
        return False
    
    def _scan_directory_chunk(self, directory_paths: List[Path]) -> ScoutMetrics:
        """Scan a chunk of directories (used for parallel processing)."""
        chunk_metrics = ScoutMetrics()
        extension_counter = Counter()
        large_files = []
        problematic_files = []
        max_depth = 0
        
        for dir_path in directory_paths:
            if self._cancelled:
                break
                
            try:
                for root, dirs, files in os.walk(dir_path):
                    if self._cancelled:
                        break
                    
                    root_path = Path(root)
                    current_depth = len(root_path.parts)
                    max_depth = max(max_depth, current_depth)
                    
                    # Filter directories to skip
                    dirs[:] = [d for d in dirs if not self._should_skip_directory(root_path / d)]
                    
                    chunk_metrics.total_directories += 1
                    
                    for file_name in files:
                        if self._cancelled:
                            break
                        
                        file_path = root_path / file_name
                        
                        if self._should_skip_file(file_path):
                            continue
                        
                        try:
                            stat_info = file_path.stat()
                            file_size = stat_info.st_size
                            
                            chunk_metrics.total_files += 1
                            chunk_metrics.total_size_bytes += file_size
                            
                            # Track extension
                            extension = file_path.suffix.lower()
                            if not extension:
                                problematic_files.append(str(file_path))
                                extension = '<no_extension>'
                            
                            extension_counter[extension] += 1
                            
                            # Track large files
                            if file_size > self.large_file_threshold_bytes:
                                large_files.append((str(file_path), file_size))
                            
                        except (OSError, PermissionError) as e:
                            logger.debug(f"Cannot access file {file_path}: {e}")
                            problematic_files.append(str(file_path))
                            
            except (OSError, PermissionError) as e:
                logger.warning(f"Cannot access directory {dir_path}: {e}")
                problematic_files.append(str(dir_path))
        
        chunk_metrics.extension_histogram = dict(extension_counter)
        chunk_metrics.large_files = large_files
        chunk_metrics.problematic_files = problematic_files
        chunk_metrics.deepest_path_level = max_depth
        
        return chunk_metrics
    
    def _merge_metrics(self, metrics_list: List[ScoutMetrics]) -> ScoutMetrics:
        """Merge metrics from multiple chunks."""
        merged = ScoutMetrics()
        extension_counter = Counter()
        
        for metrics in metrics_list:
            merged.total_files += metrics.total_files
            merged.total_directories += metrics.total_directories
            merged.total_size_bytes += metrics.total_size_bytes
            merged.large_files.extend(metrics.large_files)
            merged.problematic_files.extend(metrics.problematic_files)
            merged.deepest_path_level = max(merged.deepest_path_level, metrics.deepest_path_level)
            
            for ext, count in metrics.extension_histogram.items():
                extension_counter[ext] += count
        
        merged.extension_histogram = dict(extension_counter)
        
        # Sort large files by size (descending)
        merged.large_files.sort(key=lambda x: x[1], reverse=True)
        
        # Calculate average files per directory
        if merged.total_directories > 0:
            merged.average_files_per_directory = merged.total_files / merged.total_directories
        
        return merged
    
    def scout_directory(self, target_path: str) -> ScoutMetrics:
        """
        Perform high-speed directory scouting.
        
        Args:
            target_path: Path to the directory to scout
            
        Returns:
            ScoutMetrics with collected information
        """
        start_time = time.time()
        target = Path(target_path)
        
        if not target.exists():
            raise FileNotFoundError(f"Target directory does not exist: {target_path}")
        
        if not target.is_dir():
            raise NotADirectoryError(f"Target is not a directory: {target_path}")
        
        logger.info(f"🔍 Starting directory scout for: {target_path}")
        
        # Reset state
        self._cancelled = False
        
        # For parallel processing, we'll collect top-level directories
        # and distribute them across workers
        try:
            top_level_items = list(target.iterdir())
            directories_to_scan = [item for item in top_level_items if item.is_dir() and not self._should_skip_directory(item)]
            
            # If no subdirectories, scan the target directory itself
            if not directories_to_scan:
                directories_to_scan = [target]
            
            # Distribute directories across workers
            chunk_size = max(1, len(directories_to_scan) // self.max_workers)
            directory_chunks = [
                directories_to_scan[i:i + chunk_size] 
                for i in range(0, len(directories_to_scan), chunk_size)
            ]
            
            # Process chunks in parallel
            metrics_list = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_chunk = {
                    executor.submit(self._scan_directory_chunk, chunk): chunk 
                    for chunk in directory_chunks
                }
                
                for future in as_completed(future_to_chunk):
                    if self._cancelled:
                        break
                    
                    try:
                        chunk_metrics = future.result()
                        metrics_list.append(chunk_metrics)
                    except Exception as e:
                        logger.error(f"Error processing directory chunk: {e}")
            
            # Merge results
            final_metrics = self._merge_metrics(metrics_list)
            final_metrics.scan_duration_seconds = time.time() - start_time
            
            logger.info(f"✅ Scout completed in {final_metrics.scan_duration_seconds:.2f}s")
            logger.info(f"   Found {final_metrics.total_files:,} files in {final_metrics.total_directories:,} directories")
            logger.info(f"   Total size: {final_metrics.total_size_bytes / (1024**3):.2f} GB")
            
            return final_metrics
            
        except Exception as e:
            logger.error(f"❌ Scout failed: {e}")
            raise
    
    def get_summary_report(self, metrics: ScoutMetrics) -> str:
        """Generate a human-readable summary report."""
        report_lines = [
            "📊 Directory Scout Report",
            "=" * 50,
            f"Total Files: {metrics.total_files:,}",
            f"Total Directories: {metrics.total_directories:,}",
            f"Total Size: {metrics.total_size_bytes / (1024**3):.2f} GB",
            f"Scan Duration: {metrics.scan_duration_seconds:.2f} seconds",
            f"Deepest Path Level: {metrics.deepest_path_level}",
            f"Avg Files/Directory: {metrics.average_files_per_directory:.1f}",
            "",
            "📁 File Extensions (Top 10):",
        ]
        
        # Top extensions
        sorted_extensions = sorted(
            metrics.extension_histogram.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        for ext, count in sorted_extensions:
            percentage = (count / metrics.total_files) * 100 if metrics.total_files > 0 else 0
            report_lines.append(f"  {ext:<15} {count:>8,} ({percentage:>5.1f}%)")
        
        # Large files
        if metrics.large_files:
            report_lines.extend([
                "",
                f"🔍 Large Files (>{self.large_file_threshold_bytes / (1024**2):.0f}MB):"
            ])
            
            for file_path, size in metrics.large_files[:5]:  # Top 5
                size_mb = size / (1024**2)
                report_lines.append(f"  {size_mb:>8.1f}MB  {file_path}")
        
        # Problematic files
        if metrics.problematic_files:
            report_lines.extend([
                "",
                f"⚠️  Problematic Files: {len(metrics.problematic_files)}"
            ])
        
        return "\n".join(report_lines)


# Convenience function for quick scouting
def quick_scout(directory_path: str, **kwargs) -> ScoutMetrics:
    """Perform a quick directory scout with default settings."""
    scout = DirectoryScout(**kwargs)
    return scout.scout_directory(directory_path)