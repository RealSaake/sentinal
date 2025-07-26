#!/usr/bin/env python3
"""
Sentinel 2.0 - Agentic Analysis Pipeline
Integrates the FastAgentOrchestrator with the main Sentinel application
"""

import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from sentinel.app.core import FileMetadata, scan_directory, extract_content
from sentinel.app.db import DatabaseManager
from sentinel.app.config_manager import AppConfig
from sentinel.app.ai import InferenceEngine
from sentinel.agents.fast_orchestrator import FastAgentOrchestrator, FastOrchestrationResult


class MockInferenceEngineForAgentic:
    """Mock inference engine for testing the agentic system."""
    
    def __init__(self):
        self.call_count = 0
    
    async def generate(self, prompt: str) -> str:
        """Generate mock responses for agentic system testing."""
        self.call_count += 1
        
        # Categorization responses
        if "Categorize this file" in prompt:
            if ".py" in prompt:
                return '{"category": "CODE", "confidence": 0.95, "reasoning": "Python source code"}'
            elif ".txt" in prompt:
                return '{"category": "DOCUMENTS", "confidence": 0.90, "reasoning": "Text document"}'
            elif ".jpg" in prompt or ".png" in prompt:
                return '{"category": "MEDIA", "confidence": 0.92, "reasoning": "Image file"}'
            elif ".json" in prompt:
                return '{"category": "DATA", "confidence": 0.91, "reasoning": "JSON data file"}'
            else:
                return '{"category": "DOCUMENTS", "confidence": 0.80, "reasoning": "Generic document"}'
        
        # Tagging responses
        elif "Extract relevant tags" in prompt:
            if "python" in prompt.lower() or ".py" in prompt:
                return '{"tags": ["python", "code", "script"], "confidence": 0.88, "reasoning": "Python tags"}'
            elif ".txt" in prompt:
                return '{"tags": ["text", "document"], "confidence": 0.75, "reasoning": "Text tags"}'
            else:
                return '{"tags": ["file", "data"], "confidence": 0.70, "reasoning": "Generic tags"}'
        
        # Naming responses
        elif "Generate a structured file path" in prompt:
            if "CODE" in prompt:
                return '{"suggested_path": "code/python/script.py", "confidence": 0.90, "reasoning": "Code organization"}'
            elif "DOCUMENTS" in prompt:
                return '{"suggested_path": "documents/text/file.txt", "confidence": 0.85, "reasoning": "Document organization"}'
            elif "MEDIA" in prompt:
                return '{"suggested_path": "media/images/image.jpg", "confidence": 0.88, "reasoning": "Media organization"}'
            else:
                return '{"suggested_path": "misc/file", "confidence": 0.75, "reasoning": "Default organization"}'
        
        # Confidence evaluation
        elif "Evaluate the quality" in prompt:
            return '{"final_confidence": 0.87, "agent_breakdown": {"categorization": 0.90, "tagging": 0.85, "naming": 0.86}, "consistency_score": 0.88, "issues": [], "reasoning": "Good quality analysis"}'
        
        return '{"result": "processed", "confidence": 0.8, "reasoning": "Mock response"}'


class AgenticPipeline:
    """
    Enhanced pipeline that uses the FastAgentOrchestrator for maximum performance.
    
    This replaces the traditional single-file processing with batch-optimized
    agentic analysis that can process thousands of files per second.
    """
    
    def __init__(self, config: AppConfig, db: DatabaseManager, logger_manager=None, performance_monitor=None):
        """Initialize the agentic pipeline."""
        self.config = config
        self.db = db
        self.logger_manager = logger_manager
        self.performance_monitor = performance_monitor
        
        # Get logger
        self.logger = None
        if logger_manager:
            self.logger = logger_manager.get_logger('agentic_pipeline')
        
        # Initialize inference engine for the orchestrator
        # Handle mock mode for testing
        if config.ai_backend_mode == "mock":
            # Use a mock inference engine for testing
            self.inference_engine = MockInferenceEngineForAgentic()
        else:
            self.inference_engine = InferenceEngine(
                backend_mode=config.ai_backend_mode,
                logger_manager=logger_manager,
                performance_monitor=performance_monitor
            )
        
        # Initialize the fast orchestrator
        self.orchestrator = FastAgentOrchestrator(self.inference_engine)
        self.orchestrator.enable_maximum_speed_mode()
        
        if self.logger:
            self.logger.info("🚀 Agentic Pipeline initialized with FastAgentOrchestrator")
    
    async def run_analysis_async(self, directory: str | Path) -> List[Dict[str, Any]]:
        """
        Run the full agentic analysis pipeline asynchronously.
        
        This is the main entry point that replaces the traditional pipeline
        with our optimized agentic system.
        """
        if self.logger:
            self.logger.info(f"🎯 Starting agentic analysis for directory: {directory}")
        
        start_time = time.time()
        results = []
        
        try:
            # Initialize database
            self.db.init_schema()
            
            # Phase 1: Scan directory and collect file metadata
            if self.logger:
                self.logger.info("📁 Phase 1: Scanning directory...")
            
            file_metadata_list = []
            file_paths = []
            
            for meta in scan_directory(directory):
                file_metadata_list.append(meta)
                file_paths.append(str(meta.path))
            
            if self.logger:
                self.logger.info(f"📊 Found {len(file_paths)} files to analyze")
            
            if not file_paths:
                if self.logger:
                    self.logger.warning("No files found in directory")
                return []
            
            # Phase 2: Batch agentic analysis
            if self.logger:
                self.logger.info("🤖 Phase 2: Running agentic analysis...")
            
            # Process files in batches using our optimized orchestrator
            agentic_results = await self.orchestrator.process_batch_fast(file_paths)
            
            # Phase 3: Persist results and format for UI
            if self.logger:
                self.logger.info("💾 Phase 3: Persisting results...")
            
            for i, (meta, agentic_result) in enumerate(zip(file_metadata_list, agentic_results)):
                try:
                    # Save file metadata to database
                    file_id = self.db.save_scan_result(meta.as_dict())
                    
                    # Convert agentic result to inference result format
                    inference_dict = {
                        'suggested_path': agentic_result.suggested_path,
                        'confidence': agentic_result.final_confidence,
                        'justification': self._build_justification(agentic_result),
                        'category': agentic_result.category,
                        'tags': agentic_result.tags,
                        'processing_time_ms': agentic_result.processing_time_ms
                    }
                    
                    # Save inference result
                    self.db.save_inference(file_id, inference_dict)
                    
                    # Format for UI
                    results.append({
                        "file_id": file_id,
                        "original_path": str(meta.path),
                        "suggested_path": agentic_result.suggested_path,
                        "confidence": agentic_result.final_confidence,
                        "justification": inference_dict['justification'],
                        "category": agentic_result.category,
                        "tags": agentic_result.tags,
                        "processing_time_ms": agentic_result.processing_time_ms,
                        "success": agentic_result.success
                    })
                    
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Failed to persist result for {meta.path}: {e}")
                    
                    # Add error result
                    results.append({
                        "file_id": -1,
                        "original_path": str(meta.path),
                        "suggested_path": str(meta.path),
                        "confidence": 0.0,
                        "justification": f"Persistence failed: {str(e)}",
                        "category": "ERROR",
                        "tags": [],
                        "processing_time_ms": 0,
                        "success": False
                    })
            
            # Phase 4: Performance reporting
            total_time = time.time() - start_time
            throughput = len(file_paths) / total_time if total_time > 0 else 0
            
            if self.logger:
                self.logger.info(f"🎉 Agentic analysis completed!")
                self.logger.info(f"   Files processed: {len(file_paths)}")
                self.logger.info(f"   Total time: {total_time:.2f}s")
                self.logger.info(f"   Throughput: {throughput:.1f} files/sec")
                self.logger.info(f"   Success rate: {len([r for r in results if r.get('success', True)])}/{len(results)}")
            
            # Log performance stats
            stats = self.orchestrator.get_performance_stats()
            if self.logger:
                self.logger.info(f"📈 Orchestrator stats: {stats}")
            
            return results
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Agentic pipeline failed: {e}", exc_info=True)
            raise
    
    def _build_justification(self, result: FastOrchestrationResult) -> str:
        """Build a human-readable justification from the agentic result."""
        if not result.success:
            return f"Analysis failed: {result.error_message}"
        
        justification_parts = [
            f"Categorized as {result.category} (confidence: {result.final_confidence:.2f})"
        ]
        
        if result.tags:
            justification_parts.append(f"Tags: {', '.join(result.tags[:3])}")
        
        justification_parts.append(f"Processed in {result.processing_time_ms}ms")
        
        return " | ".join(justification_parts)


def run_agentic_analysis(directory: str | Path, *, db: DatabaseManager, config: AppConfig, 
                        logger_manager=None, performance_monitor=None) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for the agentic analysis pipeline.
    
    This function maintains compatibility with the existing Sentinel interface
    while providing the performance benefits of the agentic system.
    """
    pipeline = AgenticPipeline(config, db, logger_manager, performance_monitor)
    
    # Run the async pipeline in a new event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an event loop, we need to use a different approach
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, pipeline.run_analysis_async(directory))
                return future.result()
        else:
            return loop.run_until_complete(pipeline.run_analysis_async(directory))
    except RuntimeError:
        # No event loop exists, create a new one
        return asyncio.run(pipeline.run_analysis_async(directory))


# Backward compatibility - this can replace the original run_analysis function
def run_analysis(directory: str | Path, *, db: DatabaseManager, config: AppConfig, 
                logger_manager=None, performance_monitor=None) -> List[Dict[str, Any]]:
    """
    Enhanced analysis pipeline using the agentic system.
    
    This is a drop-in replacement for the original run_analysis function
    that provides massive performance improvements through the FastAgentOrchestrator.
    """
    return run_agentic_analysis(directory, db=db, config=config, 
                               logger_manager=logger_manager, performance_monitor=performance_monitor)