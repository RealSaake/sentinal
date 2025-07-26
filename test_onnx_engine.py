#!/usr/bin/env python3
"""
Test the ONNX Inference Engine implementation
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add helios to path
sys.path.insert(0, str(Path(__file__).parent))

from helios.inference.onnx_engine import ONNXInferenceEngine
from helios.core.models import FileTask, FileMetadata

def test_onnx_engine():
    """Test ONNX inference engine with mock model."""
    print("🧪 Testing ONNX Inference Engine...")
    
    try:
        # Initialize engine with mock model
        model_path = "helios/models/sentinel_v1.onnx"
        engine = ONNXInferenceEngine(
            model_path=model_path,
            use_cuda=True,
            confidence_threshold=0.7
        )
        
        print(f"✅ Engine initialized successfully")
        print(f"   Device: {engine.device}")
        print(f"   Providers: {engine.providers}")
        print(f"   Batch size: {engine.current_batch_size}")
        
        # Create test file tasks
        test_files = [
            ("screenshot_2024.png", ".png", "image/png", 1024000),
            ("vacation_video.mp4", ".mp4", "video/mp4", 50000000),
            ("music_track.mp3", ".mp3", "audio/mpeg", 5000000),
            ("report.pdf", ".pdf", "application/pdf", 2000000),
            ("script.py", ".py", "text/x-python", 10000),
            ("archive.zip", ".zip", "application/zip", 15000000)
        ]
        
        tasks = []
        for name, ext, mime, size in test_files:
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
            tasks.append(task)
        
        print(f"\n📁 Processing {len(tasks)} test files...")
        
        # Process batch
        start_time = time.time()
        results = engine.process_batch(tasks)
        processing_time = time.time() - start_time
        
        print(f"⚡ Processed in {processing_time:.3f} seconds")
        print(f"📊 Results:")
        
        for i, result in enumerate(results):
            task = tasks[i]
            print(f"\n  {i+1}. {task.metadata.name}")
            print(f"     → {result['categorized_path']}")
            print(f"     Confidence: {result['confidence']:.2f}")
            print(f"     Tags: {', '.join(result['tags'])}")
        
        # Get performance metrics
        print(f"\n📈 Performance Metrics:")
        metrics = engine.get_performance_metrics()
        print(f"   Total inferences: {metrics['total_inferences']}")
        print(f"   Throughput: {metrics['throughput_per_second']:.1f} files/sec")
        print(f"   Average time: {metrics['avg_inference_time']:.3f}s per batch")
        print(f"   Error rate: {metrics['error_rate']:.1f}%")
        
        # Test GPU memory info
        gpu_info = engine.get_gpu_memory_info()
        if gpu_info['total_gb'] > 0:
            print(f"\n🎮 GPU Memory:")
            print(f"   Total: {gpu_info['total_gb']:.1f} GB")
            print(f"   Used: {gpu_info['used_gb']:.1f} GB")
            print(f"   Utilization: {gpu_info['utilization_percent']:.1f}%")
        
        # Test batch size adjustment
        print(f"\n🔧 Testing batch size adjustment...")
        original_size = engine.current_batch_size
        engine._reduce_batch_size()
        print(f"   Batch size: {original_size} → {engine.current_batch_size}")
        
        # Cleanup
        engine.shutdown()
        print(f"\n✅ All tests passed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling scenarios."""
    print("\n🧪 Testing error handling...")
    
    try:
        # Test with invalid model path
        try:
            engine = ONNXInferenceEngine(model_path="/nonexistent/model.onnx")
            print("❌ Should have failed with invalid model path")
            return False
        except FileNotFoundError:
            print("✅ Correctly handled invalid model path")
        
        # Test with valid engine but error conditions
        engine = ONNXInferenceEngine(model_path="helios/models/sentinel_v1.onnx")
        
        # Test empty batch
        results = engine.process_batch([])
        assert len(results) == 0
        print("✅ Correctly handled empty batch")
        
        engine.shutdown()
        print("✅ Error handling tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 ONNX Inference Engine Test Suite")
    print("=" * 50)
    
    # Run tests
    test1_passed = test_onnx_engine()
    test2_passed = test_error_handling()
    
    print("\n" + "=" * 50)
    if test1_passed and test2_passed:
        print("🎉 All tests passed! ONNX Engine is ready!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)