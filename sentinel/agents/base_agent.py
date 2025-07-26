#!/usr/bin/env python3
"""
Sentinel 2.0 - Base Agent Architecture
Foundation for all specialized AI agents in the agentic system
"""

import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Base result structure for all agents."""
    agent_name: str
    confidence: float  # 0.0 to 1.0
    processing_time_ms: int
    reasoning: str
    raw_output: Dict[str, Any]
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class FileContext:
    """Rich context about a file for agent processing."""
    file_path: str
    file_name: str
    file_extension: str
    file_size_bytes: int
    directory_path: str
    directory_name: str
    file_content_preview: Optional[str] = None  # First 1000 chars if text file
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseAgent(ABC):
    """
    Base class for all specialized AI agents.
    Each agent has a specific role and optimized prompt.
    """
    
    def __init__(self, inference_engine, agent_name: str):
        """Initialize the base agent."""
        self.inference_engine = inference_engine
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"agent.{agent_name}")
        
        # Performance tracking
        self.total_requests = 0
        self.total_processing_time = 0.0
        self.success_count = 0
        self.error_count = 0
        
        self.logger.info(f"🤖 {agent_name} agent initialized")
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        pass
    
    @abstractmethod
    def build_user_prompt(self, file_context: FileContext, **kwargs) -> str:
        """Build the user prompt for this specific file context."""
        pass
    
    @abstractmethod
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI response into structured data."""
        pass
    
    @abstractmethod
    def validate_result(self, parsed_result: Dict[str, Any]) -> bool:
        """Validate that the parsed result is acceptable."""
        pass
    
    async def process(self, file_context: FileContext, **kwargs) -> AgentResult:
        """
        Process a file through this agent.
        
        Args:
            file_context: Rich context about the file
            **kwargs: Additional context from other agents
            
        Returns:
            AgentResult with the agent's analysis
        """
        start_time = time.time()
        self.total_requests += 1
        
        try:
            # Build the complete prompt
            system_prompt = self.get_system_prompt()
            user_prompt = self.build_user_prompt(file_context, **kwargs)
            
            # Get AI response
            self.logger.debug(f"Processing {file_context.file_name} with {self.agent_name}")
            
            # Use the inference engine (this would be your existing AI inference)
            ai_response = await self._call_inference_engine(system_prompt, user_prompt)
            
            # Parse and validate response
            parsed_result = self.parse_response(ai_response)
            
            if not self.validate_result(parsed_result):
                raise ValueError(f"Invalid result from {self.agent_name}")
            
            # Calculate metrics
            processing_time = int((time.time() - start_time) * 1000)
            self.total_processing_time += processing_time
            self.success_count += 1
            
            # Extract confidence and reasoning
            confidence = parsed_result.get('confidence', 0.8)
            reasoning = parsed_result.get('reasoning', 'No reasoning provided')
            
            self.logger.debug(f"✅ {self.agent_name} completed in {processing_time}ms (confidence: {confidence:.2f})")
            
            return AgentResult(
                agent_name=self.agent_name,
                confidence=confidence,
                processing_time_ms=processing_time,
                reasoning=reasoning,
                raw_output=parsed_result,
                success=True
            )
            
        except Exception as e:
            self.error_count += 1
            processing_time = int((time.time() - start_time) * 1000)
            
            self.logger.error(f"❌ {self.agent_name} failed: {e}")
            
            return AgentResult(
                agent_name=self.agent_name,
                confidence=0.0,
                processing_time_ms=processing_time,
                reasoning=f"Agent failed: {str(e)}",
                raw_output={},
                success=False,
                error_message=str(e)
            )
    
    async def _call_inference_engine(self, system_prompt: str, user_prompt: str) -> str:
        """Call the inference engine with proper error handling."""
        try:
            # This integrates with the inference engine
            full_prompt = f"{system_prompt}\n\nUser: {user_prompt}"
            
            # Check if inference engine has generate method (for real AI)
            if hasattr(self.inference_engine, 'generate'):
                response = await self.inference_engine.generate(full_prompt)
                return response
            else:
                # Fallback for testing
                return self._generate_mock_response(user_prompt)
            
        except Exception as e:
            self.logger.error(f"Inference engine error: {e}")
            raise
    
    def _generate_mock_response(self, user_prompt: str) -> str:
        """Generate a mock response for testing (remove in production)."""
        # This is just for testing - real implementation uses actual AI
        if "categorize" in user_prompt.lower():
            return '{"category": "CODE", "confidence": 0.9, "reasoning": "File has .py extension and contains Python code"}'
        elif "tags" in user_prompt.lower():
            return '{"tags": ["python", "script", "automation"], "confidence": 0.85, "reasoning": "Identified Python script with automation keywords"}'
        elif "naming" in user_prompt.lower():
            return '{"suggested_path": "code/python/scripts/example.py", "confidence": 0.88, "reasoning": "Following Python project structure"}'
        else:
            return '{"result": "processed", "confidence": 0.8, "reasoning": "Default processing"}'
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for this agent."""
        avg_processing_time = (
            self.total_processing_time / self.total_requests 
            if self.total_requests > 0 else 0
        )
        
        success_rate = (
            self.success_count / self.total_requests 
            if self.total_requests > 0 else 0
        )
        
        return {
            'agent_name': self.agent_name,
            'total_requests': self.total_requests,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': success_rate,
            'avg_processing_time_ms': avg_processing_time,
            'total_processing_time_ms': self.total_processing_time
        }
    
    def reset_stats(self):
        """Reset performance statistics."""
        self.total_requests = 0
        self.total_processing_time = 0.0
        self.success_count = 0
        self.error_count = 0


def extract_file_context(file_path: str) -> FileContext:
    """Extract rich context from a file path."""
    path_obj = Path(file_path)
    
    # Basic file information
    file_name = path_obj.name
    file_extension = path_obj.suffix.lower()
    directory_path = str(path_obj.parent)
    directory_name = path_obj.parent.name
    
    # File size
    try:
        file_size_bytes = path_obj.stat().st_size
    except (OSError, FileNotFoundError):
        file_size_bytes = 0
    
    # Content preview for text files
    content_preview = None
    if file_extension in {'.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md', '.yml', '.yaml'}:
        try:
            with open(path_obj, 'r', encoding='utf-8', errors='ignore') as f:
                content_preview = f.read(1000)  # First 1000 characters
        except:
            content_preview = None
    
    return FileContext(
        file_path=file_path,
        file_name=file_name,
        file_extension=file_extension,
        file_size_bytes=file_size_bytes,
        directory_path=directory_path,
        directory_name=directory_name,
        file_content_preview=content_preview
    )