#!/usr/bin/env python3
"""
Speed comparison: Original vs Fast Agentic System
Let's see how much faster we can make this!
"""

import sys
import asyncio
import time
from pathlib import Path

# Add sentinel to path
sys.path.insert(0, str(Path(__file__).parent))

from sentinel.agents.orchestrator import AgentOrchestrator
from sentinel.agents.fast_orchestrator import FastAgentOrchestrator


class SpeedTestInferenceEngine:
    """Ultra-fast inference engine for speed testing."""
    
    def __init__(self, delay_ms: float = 0.0):
        """Initialize with configurable delay."""
        self.delay_ms = delay_ms
        self.call_count = 0
    
    async def generate(self, prompt: str) -> str:
        """Generate response with minimal delay."""
        self.call_count += 1
        
        # Minimal delay for speed testing
        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000)
        
        # Ultra-fast response generation based on prompt analysis
        if "Categorize this file" in prompt:
            if ".zip" in prompt:
                return '{"category": "ARCHIVES", "confidence": 0.94, "reasoning": "Archive file"}'
            elif ".pdf" in prompt:
                return '{"category": "DOCUMENTS", "confidence": 0.92, "reasoning": "Document file"}'
            elif ".exe" in prompt:
                return '{"category": "SYSTEM", "confidence": 0.87, "reasoning": "System file"}'
            elif ".py" in prompt:
                return '{"category": "CODE", "confidence": 0.95, "reasoning": "Python code"}'
            else:
                return '{"category": "DOCUMENTS", "confidence": 0.70, "reasoning": "Default"}'
        
        elif "Extract relevant tags" in prompt:
            if "gaming" in prompt.lower() or "car" in prompt.lower():
                return '{"tags": ["gaming", "forza", "assets"], "confidence": 0.85, "reasoning": "Gaming tags"}'
            elif ".pdf" in prompt:
                return '{"tags": ["document", "text", "file"], "confidence": 0.80, "reasoning": "Document tags"}'
            else:
                return '{"tags": ["file", "data"], "confidence": 0.75, "reasoning": "Generic tags"}'
        
        elif "Generate a structured file path" in prompt:
            if "ARCHIVES" in prompt:
                return '{"suggested_path": "archives/game-assets/file.zip", "confidence": 0.87, "reasoning": "Archive path"}'
            elif "DOCUMENTS" in prompt:
                return '{"suggested_path": "documents/text/file.pdf", "confidence": 0.85, "reasoning": "Document path"}'
            elif "SYSTEM" in prompt:
                return '{"suggested_path": "system/file.exe", "confidence": 0.83, "reasoning": "System path"}'
            else:
                return '{"suggested_path": "misc/file", "confidence": 0.70, "reasoning": "Default path"}'
        
        elif "Evaluate the quality" in prompt:
            return '{"final_confidence": 0.84, "agent_breakdown": {"categorization": 0.90, "tagging": 0.82, "naming": 0.85}, "consistency_score": 0.86, "issues": [], "reasoning": "Good quality"}'
        
        return '{"result": "processed", "confidence": 0.8, "reasoning": "Speed test"}'


def get_test_files(count: int = 100) -> list:
    """Generate test file paths for speed testing."""
    test_files = []
    
    # Mix of different file types
    extensions = ['.zip', '.pdf', '.exe', '.py', '.js', '.txt', '.jpg', '.mp4', '.json', '.xml']
    
    for i in range(count):
        ext = extensions[i % len(extensions)]
        filename = f"test_file_{i:04d}{ext}"
        test_files.append(filename)
    
    return test_files


async def test_original_orchestrator(test_files: list, delay_ms: float = 0.0):
    """Test the original orchestrator."""
    print(f"\n🐌 Testing Original Orchestrator (delay: {delay_ms}ms)")
    print("=" * 60)
    
    inference_engine = SpeedTestInferenceEngine(delay_ms)
    orchestrator = AgentOrchestrator(inference_engine)
    
    start_time = time.time()
    results = await orchestrator.process_file_batch(test_files)
    end_time = time.time()
    
    duration = end_time - start_time
    throughput = len(test_files) / duration
    
    successful = len([r for r in results if r.success])
    
    print(f"📊 Results:")
    print(f"   Files processed: {len(test_files)}")
    print(f"   Successful: {successful}")
    print(f"   Duration: {duration:.2f}s")
    print(f"   Throughput: {throughput:.1f} files/sec")
    print(f"   AI calls: {inference_engine.call_count}")
    print(f"   Avg time per file: {(duration / len(test_files)) * 1000:.1f}ms")
    
    return throughput, successful


async def test_fast_orchestrator(test_files: list, delay_ms: float = 0.0):
    """Test the fast orchestrator."""
    print(f"\n🚀 Testing Fast Orchestrator (delay: {delay_ms}ms)")
    print("=" * 60)
    
    inference_engine = SpeedTestInferenceEngine(delay_ms)
    orchestrator = FastAgentOrchestrator(inference_engine)
    orchestrator.enable_maximum_speed_mode()
    
    start_time = time.time()
    results = await orchestrator.process_batch_fast(test_files)
    end_time = time.time()
    
    duration = end_time - start_time
    throughput = len(test_files) / duration
    
    successful = len([r for r in results if r.success])
    
    print(f"📊 Results:")
    print(f"   Files processed: {len(test_files)}")
    print(f"   Successful: {successful}")
    print(f"   Duration: {duration:.2f}s")
    print(f"   Throughput: {throughput:.1f} files/sec")
    print(f"   AI calls: {inference_engine.call_count}")
    print(f"   Avg time per file: {(duration / len(test_files)) * 1000:.1f}ms")
    
    # Show performance stats
    stats = orchestrator.get_performance_stats()
    print(f"   Cache hits: {stats['cache_hits']}")
    print(f"   Optimizations: {stats['optimizations']}")
    
    return throughput, successful


async def run_speed_comparison():
    """Run comprehensive speed comparison."""
    print("🏁 Sentinel 2.0 - Speed Comparison Test")
    print("=" * 70)
    print("Testing Original vs Fast Agentic Orchestrator")
    
    # Test with different file counts
    test_sizes = [50, 100, 200]
    delay_scenarios = [0.0, 10.0, 50.0]  # 0ms, 10ms, 50ms AI delay
    
    for delay_ms in delay_scenarios:
        print(f"\n{'='*70}")
        print(f"🎯 SCENARIO: {delay_ms}ms AI inference delay")
        print(f"{'='*70}")
        
        for file_count in test_sizes:
            print(f"\n📁 Testing with {file_count} files:")
            print("-" * 40)
            
            test_files = get_test_files(file_count)
            
            # Test original orchestrator
            original_throughput, original_success = await test_original_orchestrator(test_files, delay_ms)
            
            # Test fast orchestrator
            fast_throughput, fast_success = await test_fast_orchestrator(test_files, delay_ms)
            
            # Calculate improvement
            if original_throughput > 0:
                speed_improvement = (fast_throughput / original_throughput) * 100
                print(f"\n🚀 SPEED IMPROVEMENT: {speed_improvement:.1f}% faster!")
                print(f"   Original: {original_throughput:.1f} files/sec")
                print(f"   Fast:     {fast_throughput:.1f} files/sec")
                print(f"   Gain:     +{fast_throughput - original_throughput:.1f} files/sec")
            
            print(f"   Success rate: {fast_success}/{file_count} ({(fast_success/file_count)*100:.1f}%)")


async def test_maximum_speed():
    """Test maximum possible speed with optimizations."""
    print(f"\n{'='*70}")
    print("🚀 MAXIMUM SPEED TEST - RTX 3060 Ti Optimized")
    print(f"{'='*70}")
    
    # Large batch test
    test_files = get_test_files(1000)  # 1000 files
    
    inference_engine = SpeedTestInferenceEngine(0.0)  # No AI delay
    orchestrator = FastAgentOrchestrator(inference_engine)
    
    # Enable all optimizations
    orchestrator.enable_maximum_speed_mode()
    orchestrator.batch_size = 128  # Optimize for your 8GB VRAM
    
    print(f"📊 Testing {len(test_files)} files with maximum optimizations...")
    
    start_time = time.time()
    results = await orchestrator.process_batch_fast(test_files)
    end_time = time.time()
    
    duration = end_time - start_time
    throughput = len(test_files) / duration
    
    successful = len([r for r in results if r.success])
    
    print(f"\n🎯 MAXIMUM SPEED RESULTS:")
    print(f"   Files processed: {len(test_files)}")
    print(f"   Successful: {successful}")
    print(f"   Duration: {duration:.3f}s")
    print(f"   Throughput: {throughput:.1f} files/sec")
    print(f"   AI calls: {inference_engine.call_count}")
    print(f"   Time per file: {(duration / len(test_files)) * 1000:.2f}ms")
    
    # Performance breakdown
    stats = orchestrator.get_performance_stats()
    print(f"\n📈 Performance Stats:")
    print(f"   Category cache: {stats['cache_hits']['category_cache_size']} entries")
    print(f"   Path cache: {stats['cache_hits']['path_cache_size']} entries")
    print(f"   Parallel agents: {stats['optimizations']['parallel_agents']}")
    print(f"   Skip confidence: {stats['optimizations']['skip_confidence']}")
    print(f"   Batch size: {stats['optimizations']['batch_size']}")
    
    if throughput > 500:
        print(f"\n🎉 EXCELLENT! {throughput:.0f} files/sec is production-ready speed!")
    elif throughput > 200:
        print(f"\n✅ GOOD! {throughput:.0f} files/sec is solid performance!")
    else:
        print(f"\n⚠️  {throughput:.0f} files/sec - room for improvement")


async def main():
    """Run all speed tests."""
    await run_speed_comparison()
    await test_maximum_speed()
    
    print(f"\n{'='*70}")
    print("🏁 Speed testing complete!")
    print("The Fast Orchestrator is optimized for your RTX 3060 Ti")
    print("Ready to integrate with real Sentinel for maximum performance!")


if __name__ == "__main__":
    asyncio.run(main())