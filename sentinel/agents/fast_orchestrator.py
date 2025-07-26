#!/usr/bin/env python3
"""
Sentinel 2.0 - FAST Agent Orchestrator
Optimized for maximum throughput with your RTX 3060 Ti
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from .base_agent import FileContext, AgentResult, extract_file_context
from .categorization_agent import CategorizationAgent
from .tagging_agent import TaggingAgent
from .naming_agent import NamingAgent
from .confidence_agent import ConfidenceAgent

logger = logging.getLogger(__name__)


@dataclass
class FastOrchestrationResult:
    """Optimized result structure for maximum speed."""
    original_path: str
    suggested_path: str
    category: str
    tags: List[str]
    final_confidence: float
    processing_time_ms: int
    success: bool = True
    error_message: Optional[str] = None


class FastAgentOrchestrator:
    """
    FAST Agent Orchestrator optimized for your RTX 3060 Ti.
    
    Key optimizations:
    - Parallel agent execution where possible
    - Batch processing for GPU efficiency
    - Minimal overhead and fast fallbacks
    - Smart caching for repeated patterns
    """
    
    def __init__(self, inference_engine):
        """Initialize the fast orchestrator."""
        self.inference_engine = inference_engine
        
        # Initialize agents
        self.categorization_agent = CategorizationAgent(inference_engine)
        self.tagging_agent = TaggingAgent(inference_engine)
        self.naming_agent = NamingAgent(inference_engine)
        self.confidence_agent = ConfidenceAgent(inference_engine)
        
        # Performance optimizations
        self.enable_parallel_agents = True
        self.enable_caching = True
        self.skip_confidence_for_speed = False  # Can be enabled for max speed
        self.batch_size = 64  # Optimize for your GPU
        
        # Caching for repeated patterns
        self.category_cache: Dict[str, str] = {}  # extension -> category
        self.path_cache: Dict[tuple, str] = {}    # (category, filename) -> path
        
        # Thread pool for CPU-bound operations
        self.thread_pool = ThreadPoolExecutor(max_workers=6)  # Match your CPU cores
        
        # Performance tracking
        self.total_processed = 0
        self.total_time = 0.0
        
        logger.info("🚀 Fast Agent Orchestrator initialized for maximum throughput")
    
    async def process_file_fast(self, file_path: str) -> FastOrchestrationResult:
        """
        Process a single file with maximum speed optimizations.
        """
        start_time = time.time()
        
        try:
            # Extract file context (fast operation)
            file_context = extract_file_context(file_path)
            
            # Fast categorization with caching
            category = await self._fast_categorize(file_context)
            
            # Parallel tagging and naming (where possible)
            if self.enable_parallel_agents:
                # Run tagging and naming in parallel
                tagging_task = asyncio.create_task(self._fast_tag(file_context, category))
                naming_task = asyncio.create_task(self._fast_name(file_context, category))
                
                # Wait for both to complete
                tags, suggested_path = await asyncio.gather(tagging_task, naming_task)
            else:
                # Sequential processing
                tags = await self._fast_tag(file_context, category)
                suggested_path = await self._fast_name(file_context, category, tags)
            
            # Skip confidence assessment for maximum speed (optional)
            if self.skip_confidence_for_speed:
                final_confidence = 0.85  # Assume good confidence
            else:
                final_confidence = await self._fast_confidence(category, tags, suggested_path)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Update performance tracking
            self.total_processed += 1
            self.total_time += processing_time
            
            return FastOrchestrationResult(
                original_path=file_path,
                suggested_path=suggested_path,
                category=category,
                tags=tags,
                final_confidence=final_confidence,
                processing_time_ms=processing_time,
                success=True
            )
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Fast processing failed for {file_path}: {e}")
            
            return FastOrchestrationResult(
                original_path=file_path,
                suggested_path=file_path,  # Keep original
                category="UNKNOWN",
                tags=[],
                final_confidence=0.0,
                processing_time_ms=processing_time,
                success=False,
                error_message=str(e)
            )
    
    async def process_batch_fast(self, file_paths: List[str]) -> List[FastOrchestrationResult]:
        """
        Process a batch of files with maximum parallelization.
        Optimized for your RTX 3060 Ti's capabilities.
        """
        logger.info(f"🚀 Fast processing batch of {len(file_paths)} files")
        
        # Process files in parallel with controlled concurrency
        semaphore = asyncio.Semaphore(self.batch_size)  # Match your GPU batch size
        
        async def process_with_semaphore(file_path):
            async with semaphore:
                return await self.process_file_fast(file_path)
        
        # Create all tasks
        tasks = [process_with_semaphore(file_path) for file_path in file_paths]
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception processing {file_paths[i]}: {result}")
                processed_results.append(FastOrchestrationResult(
                    original_path=file_paths[i],
                    suggested_path=file_paths[i],
                    category="ERROR",
                    tags=[],
                    final_confidence=0.0,
                    processing_time_ms=0,
                    success=False,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _fast_categorize(self, file_context: FileContext) -> str:
        """Fast categorization with caching."""
        # Check cache first
        if self.enable_caching:
            cached_category = self.category_cache.get(file_context.file_extension)
            if cached_category:
                return cached_category
        
        # Use the categorization agent's quick hint
        quick_category = self.categorization_agent._get_quick_category_hint(file_context)
        if quick_category:
            # Cache the result
            if self.enable_caching:
                self.category_cache[file_context.file_extension] = quick_category
            return quick_category
        
        # Fallback to AI if no quick categorization
        try:
            result = await self.categorization_agent.process(file_context)
            if result.success:
                category = result.raw_output.get('category', 'DOCUMENTS')
                # Cache the result
                if self.enable_caching:
                    self.category_cache[file_context.file_extension] = category
                return category
        except Exception as e:
            logger.debug(f"Categorization failed, using fallback: {e}")
        
        # Ultimate fallback
        return 'DOCUMENTS'
    
    async def _fast_tag(self, file_context: FileContext, category: str) -> List[str]:
        """Fast tagging with smart skipping."""
        # Skip tagging for certain categories to save time
        if category in {'SYSTEM', 'LOGS'} and file_context.file_size_bytes < 1024:
            return []
        
        # Use the tagging agent's detection patterns for speed
        detected_tech = self.tagging_agent._detect_technologies(file_context)
        detected_purpose = self.tagging_agent._detect_purpose(file_context)
        
        # If we have good pattern matches, use them directly
        if detected_tech or detected_purpose:
            tags = (detected_tech + detected_purpose)[:5]  # Limit to 5
            return tags
        
        # Fallback to AI tagging for complex cases
        try:
            if self.tagging_agent.should_tag_file(category, file_context):
                result = await self.tagging_agent.process(file_context, category=category)
                if result.success:
                    return result.raw_output.get('tags', [])
        except Exception as e:
            logger.debug(f"Tagging failed, using fallback: {e}")
        
        # Return empty tags if all else fails
        return []
    
    async def _fast_name(self, file_context: FileContext, category: str, tags: List[str] = None) -> str:
        """Fast naming with caching and fallbacks."""
        tags = tags or []
        
        # Check cache for common patterns
        cache_key = (category, file_context.file_extension)
        if self.enable_caching and cache_key in self.path_cache:
            cached_pattern = self.path_cache[cache_key]
            # Replace filename in cached pattern
            suggested_path = cached_pattern.replace("FILENAME", file_context.file_name)
            return suggested_path
        
        # Use the naming agent's fallback logic for speed
        try:
            fallback_path = self.naming_agent.generate_path_for_category(
                category, file_context, tags
            )
            
            # Cache the pattern
            if self.enable_caching:
                pattern = fallback_path.replace(file_context.file_name, "FILENAME")
                self.path_cache[cache_key] = pattern
            
            return fallback_path
            
        except Exception as e:
            logger.debug(f"Fast naming failed, using ultimate fallback: {e}")
            return f"{category.lower()}/{file_context.file_name}"
    
    async def _fast_confidence(self, category: str, tags: List[str], suggested_path: str) -> float:
        """Fast confidence calculation without AI."""
        # Rule-based confidence calculation for speed
        confidence = 0.8  # Base confidence
        
        # Boost confidence for good categorization
        if category in {'CODE', 'DOCUMENTS', 'MEDIA', 'ARCHIVES'}:
            confidence += 0.1
        
        # Boost confidence for good tagging
        if len(tags) >= 2:
            confidence += 0.05
        
        # Boost confidence for consistent paths
        if category.lower() in suggested_path.lower():
            confidence += 0.05
        
        return min(1.0, confidence)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        avg_time = self.total_time / self.total_processed if self.total_processed > 0 else 0
        throughput = self.total_processed / (self.total_time / 1000) if self.total_time > 0 else 0
        
        return {
            'total_processed': self.total_processed,
            'total_time_ms': self.total_time,
            'avg_processing_time_ms': avg_time,
            'throughput_files_per_sec': throughput,
            'cache_hits': {
                'category_cache_size': len(self.category_cache),
                'path_cache_size': len(self.path_cache)
            },
            'optimizations': {
                'parallel_agents': self.enable_parallel_agents,
                'caching_enabled': self.enable_caching,
                'skip_confidence': self.skip_confidence_for_speed,
                'batch_size': self.batch_size
            }
        }
    
    def enable_maximum_speed_mode(self):
        """Enable all speed optimizations."""
        self.enable_parallel_agents = True
        self.enable_caching = True
        self.skip_confidence_for_speed = True
        self.batch_size = 128  # Larger batches for your 8GB VRAM
        
        logger.info("🚀 MAXIMUM SPEED MODE ENABLED - RTX 3060 Ti optimized!")
    
    def clear_caches(self):
        """Clear all caches."""
        self.category_cache.clear()
        self.path_cache.clear()
        logger.info("🧹 Caches cleared")


# Convenience functions for fast processing
async def fast_analyze_file(file_path: str, inference_engine) -> FastOrchestrationResult:
    """Analyze a single file with maximum speed."""
    orchestrator = FastAgentOrchestrator(inference_engine)
    orchestrator.enable_maximum_speed_mode()
    return await orchestrator.process_file_fast(file_path)


async def fast_analyze_batch(file_paths: List[str], inference_engine) -> List[FastOrchestrationResult]:
    """Analyze multiple files with maximum speed and parallelization."""
    orchestrator = FastAgentOrchestrator(inference_engine)
    orchestrator.enable_maximum_speed_mode()
    return await orchestrator.process_batch_fast(file_paths)