#!/usr/bin/env python3
"""
Sentinel 2.0 - Agent Orchestrator
Coordinates the team of specialized AI agents for superior file analysis
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .base_agent import FileContext, AgentResult, extract_file_context
from .categorization_agent import CategorizationAgent
from .tagging_agent import TaggingAgent
from .naming_agent import NamingAgent
from .confidence_agent import ConfidenceAgent

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationResult:
    """Complete result from the agent orchestration process."""
    original_path: str
    suggested_path: str
    category: str
    tags: List[str]
    final_confidence: float
    
    # Individual agent results
    categorization_result: AgentResult
    tagging_result: AgentResult
    naming_result: AgentResult
    confidence_result: AgentResult
    
    # Metadata
    total_processing_time_ms: int
    consistency_scores: Dict[str, float]
    quality_assessment: str
    issues: List[str]
    reasoning: str
    
    # Success indicators
    success: bool = True
    error_message: Optional[str] = None


class AgentOrchestrator:
    """
    Orchestrates the multi-agent file analysis workflow.
    Coordinates categorization, tagging, naming, and confidence assessment agents.
    """
    
    def __init__(self, inference_engine):
        """Initialize the agent orchestrator."""
        self.inference_engine = inference_engine
        
        # Initialize all agents
        self.agents = {
            'categorization': CategorizationAgent(inference_engine),
            'tagging': TaggingAgent(inference_engine),
            'naming': NamingAgent(inference_engine),
            'confidence': ConfidenceAgent(inference_engine)
        }
        
        # Performance tracking
        self.total_orchestrations = 0
        self.successful_orchestrations = 0
        self.failed_orchestrations = 0
        self.total_processing_time = 0.0
        
        # Configuration
        self.enable_parallel_processing = True
        self.skip_tagging_for_categories = {'SYSTEM'}  # Categories that typically don't need tagging
        self.confidence_threshold = 0.3  # Minimum confidence to accept results
        
        logger.info("🎭 Agent Orchestrator initialized with 4 specialized agents")
    
    async def process_file(self, file_path: str) -> OrchestrationResult:
        """
        Process a single file through the complete multi-agent workflow.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            OrchestrationResult with complete analysis
        """
        start_time = time.time()
        self.total_orchestrations += 1
        
        try:
            # Extract rich file context
            file_context = extract_file_context(file_path)
            
            logger.debug(f"🎭 Starting orchestration for: {file_context.file_name}")
            
            # Step 1: Categorization (always required)
            categorization_result = await self.agents['categorization'].process(file_context)
            
            if not categorization_result.success:
                return self._create_failed_result(
                    file_path, "Categorization failed", start_time,
                    categorization_result=categorization_result
                )
            
            category = categorization_result.raw_output.get('category', 'DOCUMENTS')
            logger.debug(f"📁 Categorized as: {category}")
            
            # Step 2: Tagging (conditional based on category)
            if self._should_tag_file(category, file_context):
                tagging_result = await self.agents['tagging'].process(
                    file_context, category=category
                )
                
                if not tagging_result.success:
                    # Continue with empty tags rather than failing
                    logger.warning(f"Tagging failed for {file_context.file_name}, continuing with empty tags")
                    tags = []
                    tagging_result = self._create_empty_tagging_result()
                else:
                    tags = tagging_result.raw_output.get('tags', [])
                    logger.debug(f"🏷️  Tagged with: {', '.join(tags)}")
            else:
                tags = []
                tagging_result = self._create_empty_tagging_result()
                logger.debug(f"⏭️  Skipped tagging for {category} category")
            
            # Step 3: Naming (uses results from previous agents)
            naming_result = await self.agents['naming'].process(
                file_context, category=category, tags=tags
            )
            
            if not naming_result.success:
                # Use fallback naming logic
                logger.warning(f"Naming failed for {file_context.file_name}, using fallback")
                suggested_path = self.agents['naming'].generate_path_for_category(
                    category, file_context, tags
                )
                naming_result = self._create_fallback_naming_result(suggested_path)
            else:
                suggested_path = naming_result.raw_output.get('suggested_path', file_path)
                logger.debug(f"📝 Suggested path: {suggested_path}")
            
            # Step 4: Confidence Assessment
            confidence_result = await self.agents['confidence'].process(
                file_context,
                categorization_result=categorization_result,
                tagging_result=tagging_result,
                naming_result=naming_result
            )
            
            # Extract confidence data
            if confidence_result.success:
                confidence_data = confidence_result.raw_output
                final_confidence = confidence_data.get('final_confidence', 0.5)
                consistency_scores = confidence_data.get('agent_breakdown', {})
                issues = confidence_data.get('issues', [])
                reasoning = confidence_result.reasoning
            else:
                # Fallback confidence calculation
                logger.warning(f"Confidence assessment failed for {file_context.file_name}, using fallback")
                agent_results = [categorization_result, tagging_result, naming_result]
                consistency_scores = self.agents['confidence'].evaluate_consistency(
                    categorization_result, tagging_result, naming_result
                )
                final_confidence = self.agents['confidence'].calculate_final_confidence(
                    agent_results, consistency_scores
                )
                issues = []
                reasoning = "Fallback confidence calculation used"
            
            # Calculate total processing time
            total_time_ms = int((time.time() - start_time) * 1000)
            self.total_processing_time += total_time_ms
            
            # Determine quality assessment
            quality_assessment = self.agents['confidence'].get_quality_assessment(final_confidence)
            
            # Check if result should be rejected
            if self.agents['confidence'].should_reject_result(final_confidence):
                logger.warning(f"❌ Result rejected for {file_context.file_name} (confidence: {final_confidence:.2f})")
                return self._create_failed_result(
                    file_path, f"Low confidence result rejected ({final_confidence:.2f})", 
                    start_time, categorization_result, tagging_result, naming_result, confidence_result
                )
            
            # Success!
            self.successful_orchestrations += 1
            
            result = OrchestrationResult(
                original_path=file_path,
                suggested_path=suggested_path,
                category=category,
                tags=tags,
                final_confidence=final_confidence,
                categorization_result=categorization_result,
                tagging_result=tagging_result,
                naming_result=naming_result,
                confidence_result=confidence_result,
                total_processing_time_ms=total_time_ms,
                consistency_scores=consistency_scores,
                quality_assessment=quality_assessment,
                issues=issues,
                reasoning=reasoning,
                success=True
            )
            
            logger.debug(f"✅ Orchestration completed for {file_context.file_name} "
                        f"(confidence: {final_confidence:.2f}, time: {total_time_ms}ms)")
            
            return result
            
        except Exception as e:
            self.failed_orchestrations += 1
            logger.error(f"❌ Orchestration failed for {file_path}: {e}")
            
            return self._create_failed_result(
                file_path, f"Orchestration error: {str(e)}", start_time
            )
    
    async def process_file_batch(self, file_paths: List[str]) -> List[OrchestrationResult]:
        """
        Process a batch of files through the multi-agent workflow.
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            List of OrchestrationResults
        """
        logger.info(f"🎭 Processing batch of {len(file_paths)} files")
        
        if self.enable_parallel_processing:
            # Process files in parallel (with reasonable concurrency limit)
            semaphore = asyncio.Semaphore(10)  # Limit concurrent processing
            
            async def process_with_semaphore(file_path):
                async with semaphore:
                    return await self.process_file(file_path)
            
            tasks = [process_with_semaphore(file_path) for file_path in file_paths]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Exception processing {file_paths[i]}: {result}")
                    processed_results.append(self._create_failed_result(
                        file_paths[i], f"Exception: {str(result)}", time.time()
                    ))
                else:
                    processed_results.append(result)
            
            return processed_results
        else:
            # Process files sequentially
            results = []
            for file_path in file_paths:
                result = await self.process_file(file_path)
                results.append(result)
            
            return results
    
    def _should_tag_file(self, category: str, file_context: FileContext) -> bool:
        """Determine if a file should be tagged based on category and context."""
        # Skip tagging for certain categories
        if category in self.skip_tagging_for_categories:
            return False
        
        # Use the tagging agent's logic
        return self.agents['tagging'].should_tag_file(category, file_context)
    
    def _create_empty_tagging_result(self) -> AgentResult:
        """Create an empty tagging result for files that don't need tagging."""
        return AgentResult(
            agent_name="tagging",
            confidence=1.0,
            processing_time_ms=0,
            reasoning="Tagging skipped for this file type",
            raw_output={"tags": [], "confidence": 1.0, "reasoning": "Tagging not applicable"},
            success=True
        )
    
    def _create_fallback_naming_result(self, suggested_path: str) -> AgentResult:
        """Create a fallback naming result when the naming agent fails."""
        return AgentResult(
            agent_name="naming",
            confidence=0.6,
            processing_time_ms=0,
            reasoning="Fallback naming logic used",
            raw_output={
                "suggested_path": suggested_path,
                "confidence": 0.6,
                "reasoning": "Generated using fallback logic"
            },
            success=True
        )
    
    def _create_failed_result(self, file_path: str, error_message: str, start_time: float,
                            categorization_result: AgentResult = None,
                            tagging_result: AgentResult = None,
                            naming_result: AgentResult = None,
                            confidence_result: AgentResult = None) -> OrchestrationResult:
        """Create a failed orchestration result."""
        total_time_ms = int((time.time() - start_time) * 1000)
        
        # Create empty results for missing agents
        empty_result = AgentResult(
            agent_name="unknown",
            confidence=0.0,
            processing_time_ms=0,
            reasoning="Agent not executed due to failure",
            raw_output={},
            success=False,
            error_message="Not executed"
        )
        
        return OrchestrationResult(
            original_path=file_path,
            suggested_path=file_path,  # Keep original path
            category="UNKNOWN",
            tags=[],
            final_confidence=0.0,
            categorization_result=categorization_result or empty_result,
            tagging_result=tagging_result or empty_result,
            naming_result=naming_result or empty_result,
            confidence_result=confidence_result or empty_result,
            total_processing_time_ms=total_time_ms,
            consistency_scores={},
            quality_assessment="FAILED",
            issues=[error_message],
            reasoning=f"Orchestration failed: {error_message}",
            success=False,
            error_message=error_message
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics for the orchestrator and all agents."""
        avg_processing_time = (
            self.total_processing_time / self.total_orchestrations 
            if self.total_orchestrations > 0 else 0
        )
        
        success_rate = (
            self.successful_orchestrations / self.total_orchestrations 
            if self.total_orchestrations > 0 else 0
        )
        
        # Get individual agent stats
        agent_stats = {}
        for agent_name, agent in self.agents.items():
            agent_stats[agent_name] = agent.get_performance_stats()
        
        return {
            'orchestrator': {
                'total_orchestrations': self.total_orchestrations,
                'successful_orchestrations': self.successful_orchestrations,
                'failed_orchestrations': self.failed_orchestrations,
                'success_rate': success_rate,
                'avg_processing_time_ms': avg_processing_time,
                'total_processing_time_ms': self.total_processing_time
            },
            'agents': agent_stats
        }
    
    def reset_stats(self):
        """Reset all performance statistics."""
        self.total_orchestrations = 0
        self.successful_orchestrations = 0
        self.failed_orchestrations = 0
        self.total_processing_time = 0.0
        
        # Reset individual agent stats
        for agent in self.agents.values():
            agent.reset_stats()
    
    def configure_orchestrator(self, **config):
        """Configure orchestrator settings."""
        if 'enable_parallel_processing' in config:
            self.enable_parallel_processing = config['enable_parallel_processing']
        
        if 'skip_tagging_for_categories' in config:
            self.skip_tagging_for_categories = set(config['skip_tagging_for_categories'])
        
        if 'confidence_threshold' in config:
            self.confidence_threshold = config['confidence_threshold']
        
        logger.info(f"🎭 Orchestrator configured: parallel={self.enable_parallel_processing}, "
                   f"threshold={self.confidence_threshold}")
    
    def get_agent_by_name(self, agent_name: str):
        """Get a specific agent by name."""
        return self.agents.get(agent_name)
    
    def is_healthy(self) -> bool:
        """Check if the orchestrator and all agents are healthy."""
        try:
            # Basic health check - ensure all agents are initialized
            return all(agent is not None for agent in self.agents.values())
        except Exception:
            return False


# Convenience function for single file processing
async def analyze_file_with_agents(file_path: str, inference_engine) -> OrchestrationResult:
    """Analyze a single file using the multi-agent system."""
    orchestrator = AgentOrchestrator(inference_engine)
    return await orchestrator.process_file(file_path)


# Convenience function for batch processing
async def analyze_files_with_agents(file_paths: List[str], inference_engine) -> List[OrchestrationResult]:
    """Analyze multiple files using the multi-agent system."""
    orchestrator = AgentOrchestrator(inference_engine)
    return await orchestrator.process_file_batch(file_paths)