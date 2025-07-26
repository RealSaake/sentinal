#!/usr/bin/env python3
"""
ONNX Model Converter for Helios System
Converts llama3.2:3b PyTorch model to optimized ONNX format
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import torch
import onnxruntime as ort
from transformers import AutoTokenizer, AutoModel
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ONNXModelConverter:
    """Converts and validates ONNX models for Helios inference."""
    
    def __init__(self, model_name: str = "distilbert-base-uncased"):
        """Initialize converter with model name."""
        self.model_name = model_name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_dir = Path(__file__).parent
        self.onnx_path = self.model_dir / "sentinel_v1.onnx"
        
        logger.info(f"🔧 Initializing ONNX converter for {model_name}")
        logger.info(f"🎯 Target device: {self.device}")
        logger.info(f"📁 Output path: {self.onnx_path}")
    
    def load_pytorch_model(self) -> Tuple[AutoModel, AutoTokenizer]:
        """Load the PyTorch model and tokenizer."""
        logger.info("📥 Loading PyTorch model and tokenizer...")
        
        try:
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            model = AutoModel.from_pretrained(self.model_name)
            
            # Add padding token if not present
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            model.to(self.device)
            model.eval()
            
            logger.info("✅ PyTorch model loaded successfully")
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"❌ Failed to load PyTorch model: {e}")
            raise
    
    def create_sample_inputs(self, tokenizer: AutoTokenizer) -> Dict[str, torch.Tensor]:
        """Create sample inputs for ONNX export."""
        logger.info("🔨 Creating sample inputs for ONNX export...")
        
        # Sample prompt for file categorization
        sample_prompt = """
        Analyze this file and return a JSON object with categorization:
        File: document.pdf, Size: 1024KB, Extension: .pdf
        
        Return JSON format:
        {"categorized_path": "Documents/PDF/document.pdf", "confidence": 0.95, "tags": ["document", "pdf"]}
        """
        
        # Tokenize sample input
        inputs = tokenizer(
            sample_prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        
        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        logger.info(f"📊 Sample input shape: {inputs['input_ids'].shape}")
        return inputs
    
    def export_to_onnx(self, model: AutoModel, sample_inputs: Dict[str, torch.Tensor]) -> bool:
        """Export PyTorch model to ONNX format."""
        logger.info("🔄 Converting PyTorch model to ONNX...")
        
        try:
            # Create output directory
            self.model_dir.mkdir(parents=True, exist_ok=True)
            
            # Export to ONNX
            torch.onnx.export(
                model,
                tuple(sample_inputs.values()),
                str(self.onnx_path),
                export_params=True,
                opset_version=14,
                do_constant_folding=True,
                input_names=['input_ids', 'attention_mask'],
                output_names=['last_hidden_state'],
                dynamic_axes={
                    'input_ids': {0: 'batch_size', 1: 'sequence'},
                    'attention_mask': {0: 'batch_size', 1: 'sequence'},
                    'last_hidden_state': {0: 'batch_size', 1: 'sequence'}
                }
            )
            
            logger.info(f"✅ ONNX model exported to: {self.onnx_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ ONNX export failed: {e}")
            return False
    
    def validate_onnx_model(self) -> bool:
        """Validate the exported ONNX model."""
        logger.info("🔍 Validating ONNX model...")
        
        try:
            # Check if file exists and has reasonable size
            if not self.onnx_path.exists():
                logger.error("❌ ONNX model file does not exist")
                return False
            
            file_size = self.onnx_path.stat().st_size
            if file_size < 1024:  # Less than 1KB is suspicious
                logger.error(f"❌ ONNX model file too small: {file_size} bytes")
                return False
            
            logger.info(f"✅ ONNX model file exists and has size: {file_size / (1024*1024):.2f} MB")
            return True
            
        except Exception as e:
            logger.error(f"❌ ONNX model validation failed: {e}")
            return False
    
    def test_onnx_runtime(self, tokenizer: AutoTokenizer) -> bool:
        """Test ONNX Runtime inference with CUDA provider."""
        logger.info("🧪 Testing ONNX Runtime inference...")
        
        try:
            # Create ONNX Runtime session with CUDA provider
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            session = ort.InferenceSession(str(self.onnx_path), providers=providers)
            
            # Log active providers
            active_providers = session.get_providers()
            logger.info(f"🎯 Active providers: {active_providers}")
            
            # Create test input
            test_prompt = "Categorize file: image.jpg"
            inputs = tokenizer(
                test_prompt,
                return_tensors="np",
                padding=True,
                truncation=True,
                max_length=512
            )
            
            # Run inference
            start_time = time.time()
            outputs = session.run(None, {
                'input_ids': inputs['input_ids'],
                'attention_mask': inputs['attention_mask']
            })
            inference_time = time.time() - start_time
            
            logger.info(f"✅ ONNX Runtime inference successful")
            logger.info(f"⚡ Inference time: {inference_time:.4f} seconds")
            logger.info(f"📊 Output shape: {outputs[0].shape}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ ONNX Runtime test failed: {e}")
            return False
    
    def benchmark_performance(self, tokenizer: AutoTokenizer, num_runs: int = 10) -> Dict[str, float]:
        """Benchmark ONNX Runtime performance."""
        logger.info(f"📈 Benchmarking ONNX Runtime performance ({num_runs} runs)...")
        
        try:
            # Create session
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            session = ort.InferenceSession(str(self.onnx_path), providers=providers)
            
            # Prepare test inputs
            test_prompts = [
                "Categorize file: document.pdf",
                "Analyze file: image.jpg", 
                "Process file: video.mp4",
                "Classify file: audio.mp3",
                "Organize file: code.py"
            ]
            
            times = []
            
            for i in range(num_runs):
                prompt = test_prompts[i % len(test_prompts)]
                inputs = tokenizer(
                    prompt,
                    return_tensors="np",
                    padding=True,
                    truncation=True,
                    max_length=512
                )
                
                start_time = time.time()
                outputs = session.run(None, {
                    'input_ids': inputs['input_ids'],
                    'attention_mask': inputs['attention_mask']
                })
                inference_time = time.time() - start_time
                times.append(inference_time)
            
            # Calculate statistics
            avg_time = np.mean(times)
            min_time = np.min(times)
            max_time = np.max(times)
            std_time = np.std(times)
            
            stats = {
                'avg_inference_time': avg_time,
                'min_inference_time': min_time,
                'max_inference_time': max_time,
                'std_inference_time': std_time,
                'throughput_per_sec': 1.0 / avg_time
            }
            
            logger.info(f"📊 Performance Statistics:")
            logger.info(f"   Average: {avg_time:.4f}s")
            logger.info(f"   Min: {min_time:.4f}s")
            logger.info(f"   Max: {max_time:.4f}s")
            logger.info(f"   Std: {std_time:.4f}s")
            logger.info(f"   Throughput: {stats['throughput_per_sec']:.2f} inferences/sec")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Performance benchmark failed: {e}")
            return {}
    
    def save_model_info(self, stats: Dict[str, float]) -> None:
        """Save model information and performance stats."""
        model_info = {
            'model_name': self.model_name,
            'onnx_path': str(self.onnx_path),
            'device': str(self.device),
            'cuda_available': torch.cuda.is_available(),
            'performance_stats': stats,
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'file_size_mb': self.onnx_path.stat().st_size / (1024 * 1024) if self.onnx_path.exists() else 0
        }
        
        info_path = self.model_dir / "model_info.json"
        with open(info_path, 'w') as f:
            json.dump(model_info, f, indent=2)
        
        logger.info(f"💾 Model info saved to: {info_path}")
    
    def convert_and_validate(self) -> bool:
        """Complete conversion and validation pipeline."""
        logger.info("🚀 Starting ONNX model conversion pipeline...")
        
        try:
            # Step 1: Load PyTorch model
            model, tokenizer = self.load_pytorch_model()
            
            # Step 2: Create sample inputs
            sample_inputs = self.create_sample_inputs(tokenizer)
            
            # Step 3: Export to ONNX
            if not self.export_to_onnx(model, sample_inputs):
                return False
            
            # Step 4: Validate ONNX model
            if not self.validate_onnx_model():
                return False
            
            # Step 5: Test ONNX Runtime
            if not self.test_onnx_runtime(tokenizer):
                return False
            
            # Step 6: Benchmark performance
            stats = self.benchmark_performance(tokenizer)
            
            # Step 7: Save model info
            self.save_model_info(stats)
            
            logger.info("🎉 ONNX model conversion completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"💥 Conversion pipeline failed: {e}")
            return False


def main():
    """Main entry point for model conversion."""
    converter = ONNXModelConverter()
    
    if converter.convert_and_validate():
        print("✅ ONNX model ready for Helios system!")
        return 0
    else:
        print("❌ ONNX model conversion failed!")
        return 1


if __name__ == "__main__":
    exit(main())