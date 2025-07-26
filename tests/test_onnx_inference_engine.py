#!/usr/bin/env python3
"""
Test suite for ONNX Inference Engine
Following TDD approach - tests first, then implementation
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from helios.inference.onnx_engine import ONNXInferenceEngine
from helios.core.models import FileTask, FileMetadata, SmartCategory, FileType
from datetime import datetime


class TestONNXInferenceEngine:
    """Test cases for ONNX Inference Engine."""
    
    @pytest.fixture
    def mock_model_path(self):
        """Create a mock model file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.onnx', delete=False) as f:
            f.write(b"mock_onnx_model_data")
            return f.name
    
    @pytest.fixture
    def sample_file_task(self):
        """Create a sample file task for testing."""
        metadata = FileMetadata(
            path="/test/image.jpg",
            name="image.jpg",
            extension=".jpg",
            size_bytes=1024000,
            created_time=datetime.now(),
            modified_time=datetime.now(),
            accessed_time=datetime.now(),
            mime_type="image/jpeg"
        )
        
        return FileTask(
            file_path="/test/image.jpg",
            metadata=metadata,
            priority=5
        )
    
    def test_engine_initialization_with_cuda(self, mock_model_path):
        """Test ONNX engine initialization with CUDA support."""
        with patch('onnxruntime.InferenceSession') as mock_session:
            with patch('onnxruntime.get_available_providers') as mock_providers:
                mock_providers.return_value = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                
                engine = ONNXInferenceEngine(
                    model_path=mock_model_path,
                    use_cuda=True
                )
                
                assert engine.model_path == mock_model_path
                assert engine.use_cuda == True
                assert engine.device == "cuda"
                assert engine.session is not None
                
                # Verify CUDA provider was requested
                mock_session.assert_called_once()
                call_args = mock_session.call_args
                assert 'CUDAExecutionProvider' in call_args[1]['providers']
    
    def test_engine_initialization_cpu_fallback(self, mock_model_path):
        """Test ONNX engine falls back to CPU when CUDA unavailable."""
        with patch('onnxruntime.InferenceSession') as mock_session:
            with patch('onnxruntime.get_available_providers') as mock_providers:
                mock_providers.return_value = ['CPUExecutionProvider']
                
                engine = ONNXInferenceEngine(
                    model_path=mock_model_path,
                    use_cuda=True  # Request CUDA but it's not available
                )
                
                assert engine.device == "cpu"  # Should fallback to CPU
                
                # Verify CPU provider was used
                mock_session.assert_called_once()
                call_args = mock_session.call_args
                assert call_args[1]['providers'] == ['CPUExecutionProvider']
    
    def test_engine_initialization_invalid_model_path(self):
        """Test engine handles invalid model path gracefully."""
        with pytest.raises(FileNotFoundError):
            ONNXInferenceEngine(model_path="/nonexistent/model.onnx")
    
    def test_cuda_memory_exhaustion_handling(self, mock_model_path):
        """Test automatic batch size adjustment on CUDA out-of-memory."""
        with patch('onnxruntime.InferenceSession') as mock_session:
            # Mock CUDA OOM error
            mock_session_instance = Mock()
            mock_session_instance.run.side_effect = RuntimeError("CUDA out of memory")
            mock_session.return_value = mock_session_instance
            
            engine = ONNXInferenceEngine(model_path=mock_model_path)
            engine.current_batch_size = 128
            
            # This should trigger batch size reduction
            with pytest.raises(RuntimeError):
                engine._handle_cuda_oom()
            
            # Batch size should be reduced
            assert engine.current_batch_size < 128
    
    def test_batch_processing_success(self, mock_model_path, sample_file_task):
        """Test successful batch processing of file tasks."""
        with patch('onnxruntime.InferenceSession') as mock_session:
            # Mock successful inference
            mock_session_instance = Mock()
            mock_outputs = [np.array([[0.1, 0.9, 0.05, 0.02]])]  # Mock logits
            mock_session_instance.run.return_value = mock_outputs
            mock_session.return_value = mock_session_instance
            
            engine = ONNXInferenceEngine(model_path=mock_model_path)
            
            # Process batch
            tasks = [sample_file_task]
            results = engine.process_batch(tasks)
            
            assert len(results) == 1
            assert isinstance(results[0], dict)
            assert 'categorized_path' in results[0]
            assert 'confidence' in results[0]
            assert 'tags' in results[0]
    
    def test_structured_json_output_validation(self, mock_model_path):
        """Test that AI output conforms to required JSON schema."""
        with patch('onnxruntime.InferenceSession') as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            
            engine = ONNXInferenceEngine(model_path=mock_model_path)
            
            # Test valid JSON output
            valid_json = {
                "categorized_path": "Media/Images/Photos/vacation.jpg",
                "confidence": 0.95,
                "tags": ["photo", "vacation", "personal"]
            }
            
            result = engine._validate_json_output(json.dumps(valid_json))
            assert result == valid_json
            
            # Test invalid JSON output
            invalid_json = '{"invalid": "structure"}'
            result = engine._validate_json_output(invalid_json)
            assert result is None
    
    def test_gpu_memory_monitoring(self, mock_model_path):
        """Test GPU memory usage monitoring."""
        with patch('onnxruntime.InferenceSession'):
            with patch('pynvml.nvmlInit') as mock_nvml_init:
                with patch('pynvml.nvmlDeviceGetMemoryInfo') as mock_memory_info:
                    # Mock GPU memory info
                    mock_memory = Mock()
                    mock_memory.total = 8 * 1024**3  # 8GB
                    mock_memory.used = 2 * 1024**3   # 2GB used
                    mock_memory_info.return_value = mock_memory
                    
                    engine = ONNXInferenceEngine(model_path=mock_model_path)
                    
                    memory_info = engine.get_gpu_memory_info()
                    
                    assert memory_info['total_gb'] == 8.0
                    assert memory_info['used_gb'] == 2.0
                    assert memory_info['utilization_percent'] == 25.0
    
    def test_batch_size_auto_adjustment(self, mock_model_path):
        """Test automatic batch size adjustment based on GPU memory."""
        with patch('onnxruntime.InferenceSession'):
            engine = ONNXInferenceEngine(model_path=mock_model_path)
            
            # Test batch size reduction
            original_size = engine.current_batch_size
            engine._reduce_batch_size()
            assert engine.current_batch_size < original_size
            
            # Test minimum batch size limit
            engine.current_batch_size = 1
            engine._reduce_batch_size()
            assert engine.current_batch_size == 1  # Should not go below 1
    
    def test_inference_performance_tracking(self, mock_model_path, sample_file_task):
        """Test inference performance metrics tracking."""
        with patch('onnxruntime.InferenceSession') as mock_session:
            mock_session_instance = Mock()
            mock_session_instance.run.return_value = [np.array([[0.1, 0.9]])]
            mock_session.return_value = mock_session_instance
            
            engine = ONNXInferenceEngine(model_path=mock_model_path)
            
            # Process batch and check metrics
            tasks = [sample_file_task]
            results = engine.process_batch(tasks)
            
            metrics = engine.get_performance_metrics()
            
            assert metrics['total_inferences'] > 0
            assert metrics['avg_inference_time'] > 0
            assert metrics['throughput_per_second'] > 0
    
    def test_prompt_engineering_for_json(self, mock_model_path, sample_file_task):
        """Test that prompts are engineered to return structured JSON."""
        with patch('onnxruntime.InferenceSession'):
            engine = ONNXInferenceEngine(model_path=mock_model_path)
            
            prompt = engine._build_categorization_prompt(sample_file_task)
            
            # Verify prompt instructs for JSON output
            assert "JSON" in prompt
            assert "categorized_path" in prompt
            assert "confidence" in prompt
            assert "tags" in prompt
            
            # Verify file information is included
            assert sample_file_task.metadata.name in prompt
            assert sample_file_task.metadata.extension in prompt
    
    def test_context_analysis_integration(self, mock_model_path, sample_file_task):
        """Test that context analysis is used in prompts."""
        with patch('onnxruntime.InferenceSession'):
            engine = ONNXInferenceEngine(model_path=mock_model_path, use_context=True)
            
            # Add some context to the file task
            sample_file_task.project_indicators = ['package.json']
            sample_file_task.related_files = ['image.png', 'image.gif']
            
            prompt = engine._build_categorization_prompt(sample_file_task)
            
            # Verify context is included in prompt
            assert "project" in prompt.lower() or "related" in prompt.lower()
    
    def test_confidence_threshold_filtering(self, mock_model_path, sample_file_task):
        """Test that low confidence results are handled appropriately."""
        with patch('onnxruntime.InferenceSession') as mock_session:
            mock_session_instance = Mock()
            # Mock low confidence output
            mock_session_instance.run.return_value = [np.array([[0.4, 0.3, 0.2, 0.1]])]
            mock_session.return_value = mock_session_instance
            
            engine = ONNXInferenceEngine(
                model_path=mock_model_path,
                confidence_threshold=0.7
            )
            
            results = engine.process_batch([sample_file_task])
            
            # Should still return result but mark as low confidence
            assert len(results) == 1
            assert results[0]['confidence'] < 0.7
    
    def test_error_recovery_and_logging(self, mock_model_path, sample_file_task):
        """Test error recovery and proper logging."""
        with patch('onnxruntime.InferenceSession') as mock_session:
            mock_session_instance = Mock()
            mock_session_instance.run.side_effect = Exception("Inference error")
            mock_session.return_value = mock_session_instance
            
            engine = ONNXInferenceEngine(model_path=mock_model_path)
            
            # Should handle errors gracefully
            results = engine.process_batch([sample_file_task])
            
            # Should return error result instead of crashing
            assert len(results) == 1
            assert 'error' in results[0] or results[0]['confidence'] == 0.0


# Integration tests
class TestONNXEngineIntegration:
    """Integration tests for ONNX engine with real-world scenarios."""
    
    def test_large_batch_processing(self, mock_model_path):
        """Test processing large batches efficiently."""
        with patch('onnxruntime.InferenceSession'):
            engine = ONNXInferenceEngine(model_path=mock_model_path)
            
            # Create large batch of tasks
            tasks = []
            for i in range(1000):
                metadata = FileMetadata(
                    path=f"/test/file_{i}.jpg",
                    name=f"file_{i}.jpg",
                    extension=".jpg",
                    size_bytes=1024,
                    created_time=datetime.now(),
                    modified_time=datetime.now(),
                    accessed_time=datetime.now()
                )
                task = FileTask(file_path=f"/test/file_{i}.jpg", metadata=metadata)
                tasks.append(task)
            
            # Should handle large batch without issues
            results = engine.process_batch(tasks)
            assert len(results) == len(tasks)
    
    def test_mixed_file_types_batch(self, mock_model_path):
        """Test processing batch with mixed file types."""
        with patch('onnxruntime.InferenceSession'):
            engine = ONNXInferenceEngine(model_path=mock_model_path)
            
            # Create mixed file types
            file_types = [
                ("image.jpg", ".jpg", "image/jpeg"),
                ("video.mp4", ".mp4", "video/mp4"),
                ("document.pdf", ".pdf", "application/pdf"),
                ("code.py", ".py", "text/x-python"),
                ("archive.zip", ".zip", "application/zip")
            ]
            
            tasks = []
            for name, ext, mime in file_types:
                metadata = FileMetadata(
                    path=f"/test/{name}",
                    name=name,
                    extension=ext,
                    size_bytes=1024,
                    created_time=datetime.now(),
                    modified_time=datetime.now(),
                    accessed_time=datetime.now(),
                    mime_type=mime
                )
                task = FileTask(file_path=f"/test/{name}", metadata=metadata)
                tasks.append(task)
            
            results = engine.process_batch(tasks)
            assert len(results) == len(tasks)
            
            # Each result should have appropriate categorization
            for result in results:
                assert 'categorized_path' in result
                assert 'confidence' in result
                assert 'tags' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])