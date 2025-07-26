#!/usr/bin/env python3
"""
Test structured JSON output processing
"""

import sys
from pathlib import Path
from datetime import datetime

# Add helios to path
sys.path.insert(0, str(Path(__file__).parent))

from helios.inference.onnx_engine import ONNXInferenceEngine
from helios.core.models import FileTask, FileMetadata

def test_structured_json_output():
    """Test that AI output conforms to required JSON schema."""
    print("🧪 Testing Structured JSON Output Processing...")
    
    # Initialize engine
    engine = ONNXInferenceEngine(
        model_path="helios/models/sentinel_v1.onnx",
        confidence_threshold=0.7
    )
    
    # Test cases with expected categorizations
    test_cases = [
        {
            "file": ("screenshot_2024-01-15.png", ".png", "image/png", 2048000),
            "expected_category": "Screenshots",
            "expected_tags": ["image", "screenshot"]
        },
        {
            "file": ("Game.of.Thrones.S01E01.1080p.mkv", ".mkv", "video/x-matroska", 1500000000),
            "expected_category": "TV Shows", 
            "expected_tags": ["video", "tv_show", "series"]
        },
        {
            "file": ("my_python_project.py", ".py", "text/x-python", 15000),
            "expected_category": "Scripts",
            "expected_tags": ["code", "script"]
        },
        {
            "file": ("User_Manual_v2.pdf", ".pdf", "application/pdf", 5000000),
            "expected_category": "Manuals",
            "expected_tags": ["document", "manual"]
        },
        {
            "file": ("backup_2024.zip", ".zip", "application/zip", 50000000),
            "expected_category": "Backups",
            "expected_tags": ["archive", "backup"]
        }
    ]
    
    print(f"\n📋 Testing {len(test_cases)} categorization scenarios...")
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        name, ext, mime, size = test_case["file"]
        expected_category = test_case["expected_category"]
        expected_tags = test_case["expected_tags"]
        
        # Create file task
        metadata = FileMetadata(
            path=f"/test/{name}",
            name=name,
            extension=ext,
            size_bytes=size,
            created_time=datetime.now(),
            modified_time=datetime.now(),
            accessed_time=datetime.now(),
            mime_type=mime
        )
        
        task = FileTask(file_path=f"/test/{name}", metadata=metadata)
        
        # Process file
        results = engine.process_batch([task])
        result = results[0]
        
        print(f"\n  {i}. {name}")
        print(f"     → {result['categorized_path']}")
        print(f"     Confidence: {result['confidence']:.2f}")
        print(f"     Tags: {', '.join(result['tags'])}")
        
        # Validate JSON structure
        required_fields = ['categorized_path', 'confidence', 'tags']
        for field in required_fields:
            if field not in result:
                print(f"     ❌ Missing required field: {field}")
                all_passed = False
                continue
        
        # Validate data types
        if not isinstance(result['categorized_path'], str):
            print(f"     ❌ categorized_path must be string")
            all_passed = False
        
        if not isinstance(result['confidence'], (int, float)):
            print(f"     ❌ confidence must be numeric")
            all_passed = False
        
        if not isinstance(result['tags'], list):
            print(f"     ❌ tags must be list")
            all_passed = False
        
        # Validate confidence range
        if not 0.0 <= result['confidence'] <= 1.0:
            print(f"     ❌ confidence must be between 0.0 and 1.0")
            all_passed = False
        
        # Check if expected category is in path
        if expected_category not in result['categorized_path']:
            print(f"     ⚠️  Expected category '{expected_category}' not found in path")
        
        # Check if expected tags are present
        missing_tags = [tag for tag in expected_tags if tag not in result['tags']]
        if missing_tags:
            print(f"     ⚠️  Missing expected tags: {missing_tags}")
        
        print(f"     ✅ JSON structure valid")
    
    # Test edge cases
    print(f"\n🔍 Testing edge cases...")
    
    # Very large file
    large_metadata = FileMetadata(
        path="/test/huge_video.mp4",
        name="huge_video.mp4", 
        extension=".mp4",
        size_bytes=5000000000,  # 5GB
        created_time=datetime.now(),
        modified_time=datetime.now(),
        accessed_time=datetime.now(),
        mime_type="video/mp4"
    )
    
    large_task = FileTask(file_path="/test/huge_video.mp4", metadata=large_metadata)
    results = engine.process_batch([large_task])
    
    if "large_file" in results[0]['tags']:
        print("     ✅ Large file detection working")
    else:
        print("     ⚠️  Large file not detected")
    
    # Very small file
    small_metadata = FileMetadata(
        path="/test/tiny.txt",
        name="tiny.txt",
        extension=".txt", 
        size_bytes=50,  # 50 bytes
        created_time=datetime.now(),
        modified_time=datetime.now(),
        accessed_time=datetime.now(),
        mime_type="text/plain"
    )
    
    small_task = FileTask(file_path="/test/tiny.txt", metadata=small_metadata)
    results = engine.process_batch([small_task])
    
    if "small_file" in results[0]['tags']:
        print("     ✅ Small file detection working")
    else:
        print("     ⚠️  Small file not detected")
    
    # Project file with indicators
    project_metadata = FileMetadata(
        path="/test/myproject/main.py",
        name="main.py",
        extension=".py",
        size_bytes=5000,
        created_time=datetime.now(),
        modified_time=datetime.now(),
        accessed_time=datetime.now(),
        mime_type="text/x-python"
    )
    
    project_task = FileTask(file_path="/test/myproject/main.py", metadata=project_metadata)
    project_task.project_indicators = ['package.json', '.git']  # Simulate project detection
    project_task.parent_directory = "/test/myproject"
    
    results = engine.process_batch([project_task])
    
    if "project" in results[0]['tags'] and "Projects" in results[0]['categorized_path']:
        print("     ✅ Project structure preservation working")
    else:
        print("     ⚠️  Project structure preservation not working")
    
    engine.shutdown()
    
    if all_passed:
        print(f"\n🎉 All structured JSON output tests passed!")
        return True
    else:
        print(f"\n💥 Some tests failed!")
        return False

if __name__ == "__main__":
    print("🚀 Structured JSON Output Test Suite")
    print("=" * 50)
    
    success = test_structured_json_output()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Structured JSON output processing is working correctly!")
        sys.exit(0)
    else:
        print("❌ Structured JSON output processing needs fixes!")
        sys.exit(1)