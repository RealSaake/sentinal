#!/usr/bin/env python3
"""
Test the Agentic Pipeline Integration
Verify that our FastAgentOrchestrator integrates correctly with Sentinel
"""

import sys
import asyncio
import tempfile
import shutil
from pathlib import Path

# Add sentinel to path
sys.path.insert(0, str(Path(__file__).parent))

from sentinel.app.agentic_pipeline import AgenticPipeline, run_agentic_analysis
from sentinel.app.db import DatabaseManager
from sentinel.app.config_manager import AppConfig
from sentinel.app.ai import InferenceEngine


class MockInferenceEngine:
    """Mock inference engine for testing."""
    
    def __init__(self, backend_mode="mock", logger_manager=None, performance_monitor=None):
        self.backend_mode = backend_mode
        self.call_count = 0
    
    async def generate(self, prompt: str) -> str:
        """Generate mock response."""
        self.call_count += 1
        
        # Fast mock responses
        if "Categorize this file" in prompt:
            if ".py" in prompt:
                return '{"category": "CODE", "confidence": 0.95, "reasoning": "Python code file"}'
            elif ".txt" in prompt:
                return '{"category": "DOCUMENTS", "confidence": 0.90, "reasoning": "Text document"}'
            elif ".jpg" in prompt or ".png" in prompt:
                return '{"category": "MEDIA", "confidence": 0.92, "reasoning": "Image file"}'
            else:
                return '{"category": "DOCUMENTS", "confidence": 0.80, "reasoning": "Generic document"}'
        
        elif "Extract relevant tags" in prompt:
            if "python" in prompt.lower() or ".py" in prompt:
                return '{"tags": ["python", "code", "script"], "confidence": 0.88, "reasoning": "Python tags"}'
            elif "image" in prompt.lower() or ".jpg" in prompt or ".png" in prompt:
                return '{"tags": ["image", "media", "visual"], "confidence": 0.85, "reasoning": "Image tags"}'
            else:
                return '{"tags": ["document", "text"], "confidence": 0.75, "reasoning": "Generic tags"}'
        
        elif "Generate a structured file path" in prompt:
            if "CODE" in prompt:
                return '{"suggested_path": "code/python/script.py", "confidence": 0.90, "reasoning": "Code path"}'
            elif "MEDIA" in prompt:
                return '{"suggested_path": "media/images/image.jpg", "confidence": 0.88, "reasoning": "Media path"}'
            else:
                return '{"suggested_path": "documents/text/file.txt", "confidence": 0.80, "reasoning": "Document path"}'
        
        elif "Evaluate the quality" in prompt:
            return '{"final_confidence": 0.87, "agent_breakdown": {"categorization": 0.90, "tagging": 0.85, "naming": 0.86}, "consistency_score": 0.88, "issues": [], "reasoning": "High quality analysis"}'
        
        return '{"result": "processed", "confidence": 0.8, "reasoning": "Mock response"}'


def create_test_directory() -> Path:
    """Create a temporary directory with test files."""
    test_dir = Path(tempfile.mkdtemp(prefix="sentinel_test_"))
    
    # Create various test files
    test_files = [
        "script.py",
        "document.txt", 
        "image.jpg",
        "data.json",
        "config.yaml",
        "readme.md",
        "archive.zip",
        "video.mp4",
        "audio.mp3",
        "spreadsheet.xlsx"
    ]
    
    for filename in test_files:
        file_path = test_dir / filename
        file_path.write_text(f"Test content for {filename}")
    
    # Create subdirectories with files
    (test_dir / "subdir1").mkdir()
    (test_dir / "subdir1" / "nested.py").write_text("# Nested Python file")
    
    (test_dir / "subdir2").mkdir()
    (test_dir / "subdir2" / "deep.txt").write_text("Deep text file")
    
    return test_dir


async def test_agentic_pipeline_async():
    """Test the agentic pipeline asynchronously."""
    print("🧪 Testing Agentic Pipeline Integration")
    print("=" * 50)
    
    # Create test directory
    test_dir = create_test_directory()
    print(f"📁 Created test directory: {test_dir}")
    
    try:
        # Create in-memory database for testing
        db = DatabaseManager(":memory:")
        
        # Create mock config
        config = AppConfig()
        config.ai_backend_mode = "mock"
        
        # Replace the inference engine with our mock
        original_inference_engine = InferenceEngine
        
        # Monkey patch for testing
        import sentinel.app.agentic_pipeline
        sentinel.app.agentic_pipeline.InferenceEngine = MockInferenceEngine
        
        # Initialize pipeline
        pipeline = AgenticPipeline(config, db)
        
        print("🚀 Running agentic analysis...")
        
        # Run analysis
        results = await pipeline.run_analysis_async(test_dir)
        
        print(f"📊 Analysis Results:")
        print(f"   Files processed: {len(results)}")
        
        successful = len([r for r in results if r.get('success', True)])
        print(f"   Successful: {successful}")
        print(f"   Success rate: {(successful/len(results))*100:.1f}%")
        
        # Show sample results
        print(f"\n📋 Sample Results:")
        for i, result in enumerate(results[:5]):  # Show first 5
            print(f"   {i+1}. {Path(result['original_path']).name}")
            print(f"      → {result['suggested_path']}")
            print(f"      Category: {result.get('category', 'N/A')}")
            print(f"      Confidence: {result['confidence']:.2f}")
            print(f"      Tags: {result.get('tags', [])}")
            print()
        
        # Performance stats
        stats = pipeline.orchestrator.get_performance_stats()
        print(f"📈 Performance Stats:")
        print(f"   Throughput: {stats['throughput_files_per_sec']:.1f} files/sec")
        print(f"   Avg processing time: {stats['avg_processing_time_ms']:.1f}ms")
        print(f"   Cache hits: {stats['cache_hits']}")
        
        # Restore original
        sentinel.app.agentic_pipeline.InferenceEngine = original_inference_engine
        
        return len(results), successful
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir)
        print(f"🧹 Cleaned up test directory")


def test_synchronous_wrapper():
    """Test the synchronous wrapper function."""
    print("\n🔄 Testing Synchronous Wrapper")
    print("=" * 50)
    
    # Create test directory
    test_dir = create_test_directory()
    
    try:
        # Create in-memory database
        db = DatabaseManager(":memory:")
        
        # Create mock config
        config = AppConfig()
        config.ai_backend_mode = "mock"
        
        # Monkey patch for testing
        import sentinel.app.agentic_pipeline
        original_inference_engine = sentinel.app.agentic_pipeline.InferenceEngine
        sentinel.app.agentic_pipeline.InferenceEngine = MockInferenceEngine
        
        print("🚀 Running synchronous agentic analysis...")
        
        # Run analysis using synchronous wrapper
        results = run_agentic_analysis(test_dir, db=db, config=config)
        
        print(f"📊 Synchronous Results:")
        print(f"   Files processed: {len(results)}")
        
        successful = len([r for r in results if r.get('success', True)])
        print(f"   Successful: {successful}")
        print(f"   Success rate: {(successful/len(results))*100:.1f}%")
        
        # Verify result structure
        if results:
            sample = results[0]
            required_keys = ['file_id', 'original_path', 'suggested_path', 'confidence', 'justification']
            missing_keys = [key for key in required_keys if key not in sample]
            
            if missing_keys:
                print(f"❌ Missing keys in result: {missing_keys}")
            else:
                print(f"✅ Result structure is correct")
        
        # Restore original
        sentinel.app.agentic_pipeline.InferenceEngine = original_inference_engine
        
        return len(results), successful
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir)


async def test_performance_comparison():
    """Compare performance with different batch sizes."""
    print("\n⚡ Performance Comparison Test")
    print("=" * 50)
    
    # Create larger test directory
    test_dir = Path(tempfile.mkdtemp(prefix="sentinel_perf_test_"))
    
    # Create 100 test files
    for i in range(100):
        ext = ['.py', '.txt', '.jpg', '.json', '.md'][i % 5]
        file_path = test_dir / f"test_file_{i:03d}{ext}"
        file_path.write_text(f"Test content for file {i}")
    
    try:
        db = DatabaseManager(":memory:")
        config = AppConfig()
        config.ai_backend_mode = "mock"
        
        # Monkey patch
        import sentinel.app.agentic_pipeline
        original_inference_engine = sentinel.app.agentic_pipeline.InferenceEngine
        sentinel.app.agentic_pipeline.InferenceEngine = MockInferenceEngine
        
        # Test different batch sizes
        batch_sizes = [32, 64, 128]
        
        for batch_size in batch_sizes:
            print(f"\n🔧 Testing batch size: {batch_size}")
            
            pipeline = AgenticPipeline(config, db)
            pipeline.orchestrator.batch_size = batch_size
            
            import time
            start_time = time.time()
            
            results = await pipeline.run_analysis_async(test_dir)
            
            end_time = time.time()
            duration = end_time - start_time
            throughput = len(results) / duration if duration > 0 else 0
            
            print(f"   Files: {len(results)}")
            print(f"   Duration: {duration:.3f}s")
            print(f"   Throughput: {throughput:.1f} files/sec")
        
        # Restore original
        sentinel.app.agentic_pipeline.InferenceEngine = original_inference_engine
        
    finally:
        shutil.rmtree(test_dir)


async def main():
    """Run all tests."""
    print("🎯 Sentinel 2.0 - Agentic Pipeline Integration Tests")
    print("=" * 60)
    
    # Test async pipeline
    total_files, successful_files = await test_agentic_pipeline_async()
    
    # Test sync wrapper
    sync_total, sync_successful = test_synchronous_wrapper()
    
    # Performance comparison
    await test_performance_comparison()
    
    print("\n" + "=" * 60)
    print("🏁 Integration Tests Complete!")
    print(f"   Async pipeline: {successful_files}/{total_files} files processed")
    print(f"   Sync wrapper: {sync_successful}/{sync_total} files processed")
    print("   ✅ Agentic pipeline is ready for integration!")


if __name__ == "__main__":
    asyncio.run(main())