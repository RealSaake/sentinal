#!/usr/bin/env python3
"""Test script to verify Ollama integration with Sentinel and logging."""

import sys
import os
import yaml
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sentinel'))

from sentinel.app.ai.inference_engine import InferenceEngine
from sentinel.app.logging import LoggerManager, PerformanceMonitor

def test_ollama_with_logging():
    """Test the Ollama integration with full logging."""
    print("Testing Ollama integration with logging...")
    
    # Load configuration
    config_path = Path('sentinel/config/config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize logging system
    logger_manager = LoggerManager(config)
    perf_monitor = PerformanceMonitor(logger_manager)
    
    # Create inference engine with logging
    engine = InferenceEngine(
        backend_mode="local", 
        logger_manager=logger_manager,
        performance_monitor=perf_monitor
    )
    
    # Test metadata and content
    test_metadata = {
        "path": "/test/document.txt",
        "size": 1024,
        "extension": ".txt"
    }
    
    test_content = "This is a test document about project management and meeting notes."
    
    try:
        result = engine.analyze(test_metadata, test_content)
        print(f"✅ Success!")
        print(f"Suggested path: {result.suggested_path}")
        print(f"Confidence: {result.confidence}")
        print(f"Justification: {result.justification}")
        
        # Show performance metrics
        metrics = perf_monitor.get_metrics()
        if 'ai_inference' in metrics:
            ai_metrics = metrics['ai_inference']
            print(f"\n📊 Performance Metrics:")
            print(f"   • Total AI requests: {ai_metrics['total_calls']}")
            print(f"   • Average duration: {ai_metrics['average_duration']:.3f}s")
            print(f"   • Success rate: {ai_metrics['success_rate']:.1f}%")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_ollama_with_logging()
    sys.exit(0 if success else 1)