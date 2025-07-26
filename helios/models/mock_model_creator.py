#!/usr/bin/env python3
"""
Mock ONNX Model Creator for Helios MVP
Creates a simple mock model for testing the architecture
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any

import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockModelCreator:
    """Creates a mock ONNX model for MVP testing."""
    
    def __init__(self):
        """Initialize mock model creator."""
        self.model_dir = Path(__file__).parent
        self.onnx_path = self.model_dir / "sentinel_v1.onnx"
        
        logger.info("🔧 Initializing Mock ONNX model creator for MVP")
        logger.info(f"📁 Output path: {self.onnx_path}")
    
    def create_mock_model(self) -> bool:
        """Create a mock ONNX model file for testing."""
        logger.info("🔨 Creating mock ONNX model for MVP testing...")
        
        try:
            # Create output directory
            self.model_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a mock binary file that represents an ONNX model
            # This is just for testing the architecture - not a real model
            mock_model_data = b"MOCK_ONNX_MODEL_FOR_HELIOS_MVP_TESTING" * 1000
            
            with open(self.onnx_path, 'wb') as f:
                f.write(mock_model_data)
            
            logger.info(f"✅ Mock ONNX model created: {self.onnx_path}")
            logger.info(f"📊 File size: {len(mock_model_data)} bytes")
            return True
            
        except Exception as e:
            logger.error(f"❌ Mock model creation failed: {e}")
            return False
    
    def create_model_info(self) -> None:
        """Create model info file for the mock model."""
        model_info = {
            'model_name': 'mock-distilbert-for-mvp',
            'onnx_path': str(self.onnx_path),
            'device': 'cpu',
            'cuda_available': False,
            'is_mock': True,
            'performance_stats': {
                'avg_inference_time': 0.001,  # Very fast mock inference
                'min_inference_time': 0.0005,
                'max_inference_time': 0.002,
                'std_inference_time': 0.0003,
                'throughput_per_sec': 1000.0  # 1000 inferences/sec
            },
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'file_size_mb': self.onnx_path.stat().st_size / (1024 * 1024) if self.onnx_path.exists() else 0,
            'note': 'This is a mock model for MVP testing. Replace with real ONNX model for production.'
        }
        
        info_path = self.model_dir / "model_info.json"
        with open(info_path, 'w') as f:
            json.dump(model_info, f, indent=2)
        
        logger.info(f"💾 Mock model info saved to: {info_path}")
    
    def create_mock_model_complete(self) -> bool:
        """Complete mock model creation pipeline."""
        logger.info("🚀 Starting mock ONNX model creation for MVP...")
        
        try:
            # Step 1: Create mock model file
            if not self.create_mock_model():
                return False
            
            # Step 2: Create model info
            self.create_model_info()
            
            logger.info("🎉 Mock ONNX model creation completed successfully!")
            logger.info("⚠️  Remember: This is a mock model for MVP testing only!")
            return True
            
        except Exception as e:
            logger.error(f"💥 Mock model creation failed: {e}")
            return False


def main():
    """Main entry point for mock model creation."""
    creator = MockModelCreator()
    
    if creator.create_mock_model_complete():
        print("✅ Mock ONNX model ready for Helios MVP testing!")
        print("⚠️  This is a mock model - replace with real ONNX model for production")
        return 0
    else:
        print("❌ Mock ONNX model creation failed!")
        return 1


if __name__ == "__main__":
    exit(main())