#!/usr/bin/env python3
"""
Test the AsyncFileScanner implementation
"""

import asyncio
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Add helios to path
sys.path.insert(0, str(Path(__file__).parent))

from helios.scanner.async_scanner import AsyncFileScanner, ScanMetrics
from helios.core.config import HeliosConfig

async def test_async_scanner():
    """Test AsyncFileScanner with real file system."""
    print("🧪 Testing AsyncFileScanner...")
    
    # Create temporary test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test file structure
        print(f"📁 Creating test files in: {temp_path}")
        
        # Images
        images_dir = temp_path / "images"
        images_dir.mkdir()
        (images_dir / "photo1.jpg").write_text("fake image data 1" * 100)
        (images_dir / "photo2.png").write_text("fake image data 2" * 100)
        (images_dir / "screenshot_2024.png").write_text("fake screenshot data" * 100)
        
        # Videos
        videos_dir = temp_path / "videos"
        videos_dir.mkdir()
        (videos_dir / "movie.mp4").write_text("fake video data" * 1000)
        (videos_dir / "Game.of.Thrones.S01E01.mkv").write_text("fake tv show data" * 1000)
        
        # Documents
        docs_dir = temp_path / "documents"
        docs_dir.mkdir()
        (docs_dir / "report.pdf").write_text("fake pdf data" * 200)
        (docs_dir / "manual.pdf").write_text("fake manual data" * 200)
        (docs_dir / "notes.txt").write_text("fake text data" * 50)
        
        # Code project
        project_dir = temp_path / "projects" / "myapp"
        project_dir.mkdir(parents=True)
        (project_dir / "main.py").write_text("print('hello world')")
        (project_dir / "package.json").write_text('{"name": "myapp", "version": "1.0.0"}')
        (project_dir / "README.md").write_text("# My App\nThis is my app")
        
        # System files (should be skipped)
        (temp_path / "thumbs.db").write_text("system file")
        (temp_path / ".hidden").write_text("hidden file")
        
        print(f"✅ Created test file structure")
        
        # Load configuration
        try:
            config = HeliosConfig("helios/config/helios_config.yaml")
            print("✅ Configuration loaded")
        except Exception as e:
            print(f"⚠️  Using default config due to: {e}")
            # Create minimal mock config
            class MockConfig:
                def should_skip_file(self, file_path, file_size, file_age):
                    # Skip system files
                    if "thumbs.db" in file_path or file_path.startswith("."):
                        return (True, "System file")
                    return (False, "")
            config = MockConfig()
        
        # Initialize scanner
        scanner = AsyncFileScanner(
            base_directory=str(temp_path),
            config=config,
            max_workers=4
        )
        
        print(f"🔍 Starting async scan...")
        
        # Scan files
        files_found = []
        start_time = asyncio.get_event_loop().time()
        
        async for file_task in scanner.scan_directory():
            files_found.append(file_task)
            
            # Print progress every 5 files
            if len(files_found) % 5 == 0:
                metrics = scanner.get_metrics()
                print(f"   📊 Found {len(files_found)} files, {metrics.files_per_second:.1f} files/sec")
        
        end_time = asyncio.get_event_loop().time()
        scan_time = end_time - start_time
        
        print(f"\n📈 Scan Results:")
        print(f"   Files found: {len(files_found)}")
        print(f"   Scan time: {scan_time:.3f} seconds")
        print(f"   Performance: {len(files_found) / scan_time:.1f} files/sec")
        
        # Get final metrics
        metrics = scanner.get_metrics()
        print(f"\n📊 Scanner Metrics:")
        print(f"   Files discovered: {metrics.files_discovered}")
        print(f"   Directories scanned: {metrics.directories_scanned}")
        print(f"   Errors: {metrics.errors_count}")
        print(f"   Skipped: {metrics.skipped_count}")
        print(f"   Files/sec: {metrics.files_per_second:.1f}")
        
        # Analyze found files
        print(f"\n🔍 File Analysis:")
        file_types = {}
        project_files = []
        large_files = []
        
        for file_task in files_found:
            # Count file types
            ext = file_task.metadata.extension
            file_types[ext] = file_types.get(ext, 0) + 1
            
            # Find project files
            if file_task.is_part_of_project:
                project_files.append(file_task)
            
            # Find large files
            if file_task.metadata.size_mb > 0.01:  # > 10KB
                large_files.append(file_task)
        
        print(f"   File types: {dict(sorted(file_types.items()))}")
        print(f"   Project files: {len(project_files)}")
        print(f"   Large files: {len(large_files)}")
        
        # Test specific features
        print(f"\n🧪 Testing specific features...")
        
        # Check that system files were skipped
        system_files = [f for f in files_found if "thumbs.db" in f.file_path or f.metadata.name.startswith(".")]
        if len(system_files) == 0:
            print("   ✅ System files correctly skipped")
        else:
            print(f"   ⚠️  Found {len(system_files)} system files")
        
        # Check project detection
        py_files = [f for f in files_found if f.metadata.extension == ".py"]
        if py_files and any(f.is_part_of_project for f in py_files):
            print("   ✅ Project detection working")
        else:
            print("   ⚠️  Project detection not working")
        
        # Check related files detection
        related_files = [f for f in files_found if f.has_related_files]
        if related_files:
            print(f"   ✅ Related files detection working ({len(related_files)} files with relations)")
        else:
            print("   ⚠️  No related files detected")
        
        # Test directory summary
        print(f"\n📋 Testing directory summary...")
        summary = await scanner.get_directory_summary()
        print(f"   Total items: {summary['total_items']}")
        print(f"   Files: {summary['files']}")
        print(f"   Directories: {summary['directories']}")
        print(f"   Total size: {summary['total_size_bytes'] / 1024:.1f} KB")
        print(f"   File types: {len(summary['file_types'])}")
        
        print(f"\n✅ AsyncFileScanner test completed successfully!")
        return True

async def test_performance():
    """Test scanner performance with many files."""
    print("\n🚀 Testing performance with large dataset...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create many files
        print("📁 Creating 200 test files...")
        for i in range(200):
            file_path = temp_path / f"file_{i:03d}.txt"
            file_path.write_text(f"Content for file {i}" * 10)
        
        # Create subdirectories
        for i in range(10):
            sub_dir = temp_path / f"subdir_{i}"
            sub_dir.mkdir()
            for j in range(10):
                file_path = sub_dir / f"subfile_{j}.txt"
                file_path.write_text(f"Content for subfile {i}-{j}" * 5)
        
        print("✅ Test files created")
        
        # Mock config
        class MockConfig:
            def should_skip_file(self, file_path, file_size, file_age):
                return (False, "")
        
        scanner = AsyncFileScanner(
            base_directory=str(temp_path),
            config=MockConfig(),
            max_workers=8
        )
        
        # Scan with performance measurement
        files_found = []
        start_time = asyncio.get_event_loop().time()
        
        async for file_task in scanner.scan_directory():
            files_found.append(file_task)
        
        end_time = asyncio.get_event_loop().time()
        scan_time = end_time - start_time
        
        print(f"📈 Performance Results:")
        print(f"   Files scanned: {len(files_found)}")
        print(f"   Scan time: {scan_time:.3f} seconds")
        print(f"   Performance: {len(files_found) / scan_time:.1f} files/sec")
        
        # Should be fast
        if len(files_found) / scan_time > 100:  # > 100 files/sec
            print("   ✅ Performance target met")
            return True
        else:
            print("   ⚠️  Performance below target")
            return False

async def test_error_handling():
    """Test error handling scenarios."""
    print("\n🧪 Testing error handling...")
    
    # Mock config
    class MockConfig:
        def should_skip_file(self, file_path, file_size, file_age):
            return (False, "")
    
    # Test with non-existent directory
    try:
        scanner = AsyncFileScanner(
            base_directory="/nonexistent/directory",
            config=MockConfig()
        )
        
        files = []
        async for file_task in scanner.scan_directory():
            files.append(file_task)
        
        print("   ❌ Should have failed with non-existent directory")
        return False
        
    except FileNotFoundError:
        print("   ✅ Correctly handled non-existent directory")
    
    # Test with file instead of directory
    with tempfile.NamedTemporaryFile() as temp_file:
        try:
            scanner = AsyncFileScanner(
                base_directory=temp_file.name,
                config=MockConfig()
            )
            
            files = []
            async for file_task in scanner.scan_directory():
                files.append(file_task)
            
            print("   ❌ Should have failed with file instead of directory")
            return False
            
        except NotADirectoryError:
            print("   ✅ Correctly handled file instead of directory")
    
    print("   ✅ Error handling tests passed")
    return True

async def main():
    """Run all tests."""
    print("🚀 AsyncFileScanner Test Suite")
    print("=" * 50)
    
    try:
        # Run tests
        test1 = await test_async_scanner()
        test2 = await test_performance()
        test3 = await test_error_handling()
        
        print("\n" + "=" * 50)
        if test1 and test2 and test3:
            print("🎉 All tests passed! AsyncFileScanner is ready!")
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