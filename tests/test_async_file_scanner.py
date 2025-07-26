#!/usr/bin/env python3
"""
Test suite for AsyncFileScanner
Following TDD approach - tests first, then implementation
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from helios.scanner.async_scanner import AsyncFileScanner, ScanMetrics
from helios.core.models import FileTask, FileMetadata
from helios.core.config import HeliosConfig


class TestAsyncFileScanner:
    """Test cases for AsyncFileScanner."""
    
    @pytest.fixture
    def temp_directory(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test file structure
            (temp_path / "images").mkdir()
            (temp_path / "images" / "photo1.jpg").write_text("fake image data")
            (temp_path / "images" / "photo2.png").write_text("fake image data")
            
            (temp_path / "videos").mkdir()
            (temp_path / "videos" / "movie.mp4").write_text("fake video data")
            
            (temp_path / "documents").mkdir()
            (temp_path / "documents" / "report.pdf").write_text("fake pdf data")
            (temp_path / "documents" / "notes.txt").write_text("fake text data")
            
            # Create nested structure
            (temp_path / "projects" / "myapp").mkdir(parents=True)
            (temp_path / "projects" / "myapp" / "main.py").write_text("print('hello')")
            (temp_path / "projects" / "myapp" / "package.json").write_text('{"name": "myapp"}')
            
            # Create system files (should be skipped)
            (temp_path / "thumbs.db").write_text("system file")
            (temp_path / ".hidden_file").write_text("hidden file")
            
            yield temp_path
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=HeliosConfig)
        config.organization.skip_system_files = True
        config.organization.skip_temp_files = True
        config.organization.min_size_bytes = 1
        config.organization.max_size_bytes = 1000000000
        config.performance.io_workers = 4
        config.should_skip_file.return_value = (False, "")
        return config
    
    @pytest.mark.asyncio
    async def test_scanner_initialization(self, mock_config):
        """Test AsyncFileScanner initialization."""
        scanner = AsyncFileScanner(
            base_directory="/test/path",
            config=mock_config,
            max_workers=4
        )
        
        assert scanner.base_directory == Path("/test/path")
        assert scanner.config == mock_config
        assert scanner.max_workers == 4
        assert isinstance(scanner.metrics, ScanMetrics)
        assert scanner.is_scanning == False
    
    @pytest.mark.asyncio
    async def test_directory_traversal(self, temp_directory, mock_config):
        """Test async directory traversal."""
        scanner = AsyncFileScanner(
            base_directory=str(temp_directory),
            config=mock_config
        )
        
        files_found = []
        async for file_task in scanner.scan_directory():
            files_found.append(file_task)
        
        # Should find all non-system files
        assert len(files_found) >= 6  # At least the files we created
        
        # Verify FileTask objects are created correctly
        for file_task in files_found:
            assert isinstance(file_task, FileTask)
            assert isinstance(file_task.metadata, FileMetadata)
            assert file_task.file_path.startswith(str(temp_directory))
    
    @pytest.mark.asyncio
    async def test_file_metadata_extraction(self, temp_directory, mock_config):
        """Test that file metadata is extracted correctly."""
        scanner = AsyncFileScanner(
            base_directory=str(temp_directory),
            config=mock_config
        )
        
        files_found = []
        async for file_task in scanner.scan_directory():
            if file_task.metadata.name == "photo1.jpg":
                files_found.append(file_task)
                break
        
        assert len(files_found) == 1
        file_task = files_found[0]
        
        # Verify metadata
        assert file_task.metadata.name == "photo1.jpg"
        assert file_task.metadata.extension == ".jpg"
        assert file_task.metadata.size_bytes > 0
        assert isinstance(file_task.metadata.created_time, datetime)
        assert isinstance(file_task.metadata.modified_time, datetime)
        assert file_task.metadata.mime_type is not None
    
    @pytest.mark.asyncio
    async def test_skip_rules_application(self, temp_directory, mock_config):
        """Test that skip rules are applied correctly."""
        # Configure mock to skip system files
        def mock_should_skip(file_path, file_size, file_age):
            if "thumbs.db" in file_path or file_path.startswith("."):
                return (True, "System file")
            return (False, "")
        
        mock_config.should_skip_file.side_effect = mock_should_skip
        
        scanner = AsyncFileScanner(
            base_directory=str(temp_directory),
            config=mock_config
        )
        
        files_found = []
        async for file_task in scanner.scan_directory():
            files_found.append(file_task)
        
        # Should not find system files
        file_names = [task.metadata.name for task in files_found]
        assert "thumbs.db" not in file_names
        assert ".hidden_file" not in file_names
    
    @pytest.mark.asyncio
    async def test_project_structure_detection(self, temp_directory, mock_config):
        """Test detection of project structures."""
        scanner = AsyncFileScanner(
            base_directory=str(temp_directory),
            config=mock_config
        )
        
        project_files = []
        async for file_task in scanner.scan_directory():
            if "myapp" in file_task.file_path:
                project_files.append(file_task)
        
        # Should find both main.py and package.json
        assert len(project_files) >= 2
        
        # Check that project indicators are detected
        for file_task in project_files:
            if file_task.metadata.name == "main.py":
                assert "package.json" in file_task.project_indicators
                assert file_task.is_part_of_project == True
    
    @pytest.mark.asyncio
    async def test_large_directory_performance(self, mock_config):
        """Test performance with large directory structures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create many files
            for i in range(100):
                (temp_path / f"file_{i:03d}.txt").write_text(f"content {i}")
            
            scanner = AsyncFileScanner(
                base_directory=str(temp_path),
                config=mock_config,
                max_workers=8
            )
            
            start_time = asyncio.get_event_loop().time()
            
            files_found = []
            async for file_task in scanner.scan_directory():
                files_found.append(file_task)
            
            end_time = asyncio.get_event_loop().time()
            scan_time = end_time - start_time
            
            assert len(files_found) == 100
            assert scan_time < 5.0  # Should complete within 5 seconds
            
            # Check performance metrics
            metrics = scanner.get_metrics()
            assert metrics.files_discovered == 100
            assert metrics.scan_time > 0
            assert metrics.files_per_second > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_permission_denied(self, mock_config):
        """Test handling of permission denied errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a file and make it inaccessible (on Unix systems)
            test_file = temp_path / "restricted.txt"
            test_file.write_text("restricted content")
            
            # Mock os.stat to raise PermissionError
            with patch('os.stat', side_effect=PermissionError("Access denied")):
                scanner = AsyncFileScanner(
                    base_directory=str(temp_path),
                    config=mock_config
                )
                
                files_found = []
                async for file_task in scanner.scan_directory():
                    files_found.append(file_task)
                
                # Should handle error gracefully and continue
                metrics = scanner.get_metrics()
                assert metrics.errors_count > 0
    
    @pytest.mark.asyncio
    async def test_scan_progress_tracking(self, temp_directory, mock_config):
        """Test scan progress tracking and metrics."""
        scanner = AsyncFileScanner(
            base_directory=str(temp_directory),
            config=mock_config
        )
        
        files_found = []
        async for file_task in scanner.scan_directory():
            files_found.append(file_task)
            
            # Check that metrics are updated during scan
            metrics = scanner.get_metrics()
            assert metrics.files_discovered >= len(files_found)
        
        # Final metrics check
        final_metrics = scanner.get_metrics()
        assert final_metrics.files_discovered == len(files_found)
        assert final_metrics.scan_time > 0
        assert final_metrics.files_per_second > 0
        assert final_metrics.directories_scanned > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_scanning(self, temp_directory, mock_config):
        """Test concurrent scanning with multiple workers."""
        scanner = AsyncFileScanner(
            base_directory=str(temp_directory),
            config=mock_config,
            max_workers=4
        )
        
        # Start scanning
        files_found = []
        async for file_task in scanner.scan_directory():
            files_found.append(file_task)
        
        assert len(files_found) > 0
        assert scanner.metrics.files_discovered == len(files_found)
    
    @pytest.mark.asyncio
    async def test_scan_cancellation(self, mock_config):
        """Test that scanning can be cancelled gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create many files
            for i in range(1000):
                (temp_path / f"file_{i:04d}.txt").write_text(f"content {i}")
            
            scanner = AsyncFileScanner(
                base_directory=str(temp_path),
                config=mock_config
            )
            
            files_found = []
            scan_task = None
            
            async def scan_with_cancellation():
                async for file_task in scanner.scan_directory():
                    files_found.append(file_task)
                    if len(files_found) >= 10:  # Cancel after 10 files
                        break
            
            # Run scan with early termination
            await scan_with_cancellation()
            
            assert len(files_found) == 10
            assert not scanner.is_scanning
    
    @pytest.mark.asyncio
    async def test_related_files_detection(self, temp_directory, mock_config):
        """Test detection of related files."""
        # Create related files
        related_dir = temp_directory / "related"
        related_dir.mkdir()
        
        (related_dir / "document.pdf").write_text("pdf content")
        (related_dir / "document.docx").write_text("docx content")
        (related_dir / "document.txt").write_text("txt content")
        
        scanner = AsyncFileScanner(
            base_directory=str(temp_directory),
            config=mock_config
        )
        
        related_files = []
        async for file_task in scanner.scan_directory():
            if file_task.metadata.name.startswith("document."):
                related_files.append(file_task)
        
        # Each file should detect the others as related
        for file_task in related_files:
            assert file_task.has_related_files == True
            assert len(file_task.related_files) >= 2
    
    @pytest.mark.asyncio
    async def test_memory_efficient_scanning(self, mock_config):
        """Test that scanning is memory efficient for large directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create many files
            for i in range(500):
                (temp_path / f"file_{i:04d}.txt").write_text(f"content {i}")
            
            scanner = AsyncFileScanner(
                base_directory=str(temp_path),
                config=mock_config
            )
            
            # Process files one by one (generator pattern)
            files_processed = 0
            async for file_task in scanner.scan_directory():
                files_processed += 1
                # Simulate processing
                await asyncio.sleep(0.001)
            
            assert files_processed == 500
            
            # Memory should not grow significantly during scan
            # (This is more of a conceptual test - actual memory testing would require more setup)
    
    def test_metrics_calculation(self):
        """Test scan metrics calculations."""
        metrics = ScanMetrics()
        
        # Test initial state
        assert metrics.files_discovered == 0
        assert metrics.directories_scanned == 0
        assert metrics.errors_count == 0
        assert metrics.files_per_second == 0.0
        
        # Simulate scan progress
        metrics.start_scan()
        metrics.record_file_discovered()
        metrics.record_file_discovered()
        metrics.record_directory_scanned()
        metrics.record_error("Test error")
        
        # Test calculations
        assert metrics.files_discovered == 2
        assert metrics.directories_scanned == 1
        assert metrics.errors_count == 1
        
        # End scan and check final metrics
        metrics.end_scan()
        assert metrics.scan_time > 0
        assert metrics.files_per_second > 0


# Integration tests
class TestAsyncFileScannerIntegration:
    """Integration tests for AsyncFileScanner with real file system."""
    
    @pytest.mark.asyncio
    async def test_real_directory_scan(self, mock_config):
        """Test scanning a real directory structure."""
        # Use current directory as test
        current_dir = Path(__file__).parent.parent
        
        scanner = AsyncFileScanner(
            base_directory=str(current_dir),
            config=mock_config
        )
        
        files_found = []
        count = 0
        async for file_task in scanner.scan_directory():
            files_found.append(file_task)
            count += 1
            if count >= 50:  # Limit to first 50 files for test speed
                break
        
        assert len(files_found) > 0
        
        # Verify all files exist
        for file_task in files_found:
            assert Path(file_task.file_path).exists()
    
    @pytest.mark.asyncio
    async def test_scan_with_real_config(self, temp_directory):
        """Test scanning with real configuration."""
        config = HeliosConfig("helios/config/helios_config.yaml")
        
        scanner = AsyncFileScanner(
            base_directory=str(temp_directory),
            config=config
        )
        
        files_found = []
        async for file_task in scanner.scan_directory():
            files_found.append(file_task)
        
        assert len(files_found) > 0
        
        # Check that configuration rules are applied
        metrics = scanner.get_metrics()
        assert metrics.files_discovered == len(files_found)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])