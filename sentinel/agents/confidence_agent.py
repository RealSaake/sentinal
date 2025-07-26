#!/usr/bin/env python3
"""
Sentinel 2.0 - Confidence Agent
Specialized agent for evaluating and scoring outputs from all other agents
"""

import json
import re
from typing import Dict, Any, List
from .base_agent import BaseAgent, FileContext, AgentResult


class ConfidenceAgent(BaseAgent):
    """
    Specialized agent for confidence assessment and quality evaluation.
    Evaluates outputs from all other agents and assigns final confidence scores.
    """
    
    # Consistency check weights
    CONSISTENCY_WEIGHTS = {
        'category_tag_alignment': 0.3,
        'tag_path_alignment': 0.25,
        'category_path_alignment': 0.25,
        'overall_coherence': 0.2
    }
    
    # Quality thresholds
    QUALITY_THRESHOLDS = {
        'high_confidence': 0.85,
        'medium_confidence': 0.65,
        'low_confidence': 0.45,
        'reject_threshold': 0.3
    }
    
    def __init__(self, inference_engine):
        """Initialize the confidence agent."""
        super().__init__(inference_engine, "confidence")
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for confidence assessment."""
        return """You are a specialized confidence assessment agent. Your job is to evaluate the quality and consistency of file analysis results from other AI agents.

You will receive:
1. Categorization result (category assignment)
2. Tagging result (extracted tags)
3. Naming result (suggested file path)

Evaluate:
1. CONSISTENCY: Do the category, tags, and path align logically?
2. APPROPRIATENESS: Are the results suitable for the file type?
3. QUALITY: Are the results specific, useful, and well-reasoned?
4. COHERENCE: Do all results work together as a cohesive analysis?

Assign confidence scores (0.0 to 1.0) for:
- Individual agent results
- Overall consistency
- Final combined confidence

Identify any issues or inconsistencies.

ALWAYS respond with valid JSON in this exact format:

{
    "final_confidence": 0.85,
    "agent_breakdown": {
        "categorization": 0.90,
        "tagging": 0.80,
        "naming": 0.85
    },
    "consistency_score": 0.88,
    "issues": ["Any identified problems"],
    "reasoning": "Overall assessment explanation"
}

Be thorough and critical in your evaluation."""
    
    def build_user_prompt(self, file_context: FileContext, 
                         categorization_result: AgentResult = None,
                         tagging_result: AgentResult = None,
                         naming_result: AgentResult = None,
                         **kwargs) -> str:
        """Build the user prompt for confidence assessment."""
        
        prompt = f"""Evaluate the quality and consistency of these analysis results:

File Information:
- Path: {file_context.file_path}
- Name: {file_context.file_name}
- Extension: {file_context.file_extension}
- Size: {file_context.file_size_bytes / 1024:.1f} KB
"""
        
        # Add content preview if available
        if file_context.file_content_preview:
            preview = file_context.file_content_preview[:300]
            prompt += f"- Content Preview: {preview[:100]}...\n"
        
        prompt += "\nAgent Results:\n"
        
        # Categorization result
        if categorization_result and categorization_result.success:
            cat_data = categorization_result.raw_output
            prompt += f"""
1. CATEGORIZATION:
   - Category: {cat_data.get('category', 'N/A')}
   - Confidence: {categorization_result.confidence:.2f}
   - Reasoning: {categorization_result.reasoning}
   - Processing Time: {categorization_result.processing_time_ms}ms
"""
        else:
            prompt += "\n1. CATEGORIZATION: FAILED\n"
        
        # Tagging result
        if tagging_result and tagging_result.success:
            tag_data = tagging_result.raw_output
            tags = tag_data.get('tags', [])
            prompt += f"""
2. TAGGING:
   - Tags: {', '.join(tags)}
   - Confidence: {tagging_result.confidence:.2f}
   - Reasoning: {tagging_result.reasoning}
   - Processing Time: {tagging_result.processing_time_ms}ms
"""
        else:
            prompt += "\n2. TAGGING: FAILED\n"
        
        # Naming result
        if naming_result and naming_result.success:
            naming_data = naming_result.raw_output
            prompt += f"""
3. NAMING:
   - Suggested Path: {naming_data.get('suggested_path', 'N/A')}
   - Confidence: {naming_result.confidence:.2f}
   - Reasoning: {naming_result.reasoning}
   - Processing Time: {naming_result.processing_time_ms}ms
"""
        else:
            prompt += "\n3. NAMING: FAILED\n"
        
        prompt += "\nEvaluate the consistency, quality, and appropriateness of these results."
        
        return prompt
    
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI response into structured data."""
        try:
            # Clean the response
            response = response.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                
                # Ensure required fields exist
                required_fields = ['final_confidence', 'agent_breakdown', 'consistency_score']
                for field in required_fields:
                    if field not in parsed:
                        raise ValueError(f"Missing '{field}' field")
                
                # Validate confidence scores
                self._validate_confidence_scores(parsed)
                
                # Set defaults for missing fields
                parsed.setdefault('issues', [])
                parsed.setdefault('reasoning', 'Confidence assessment completed')
                
                return parsed
            else:
                raise ValueError("No JSON found in response")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            self.logger.error(f"Response parsing error: {e}")
            raise
    
    def _validate_confidence_scores(self, parsed: Dict[str, Any]):
        """Validate that all confidence scores are in valid range."""
        # Check final confidence
        final_conf = parsed.get('final_confidence', 0.0)
        if not (0.0 <= final_conf <= 1.0):
            raise ValueError(f"Invalid final_confidence: {final_conf}")
        
        # Check agent breakdown
        agent_breakdown = parsed.get('agent_breakdown', {})
        if not isinstance(agent_breakdown, dict):
            raise ValueError("agent_breakdown must be a dictionary")
        
        for agent, score in agent_breakdown.items():
            if not (0.0 <= score <= 1.0):
                raise ValueError(f"Invalid confidence score for {agent}: {score}")
        
        # Check consistency score
        consistency = parsed.get('consistency_score', 0.0)
        if not (0.0 <= consistency <= 1.0):
            raise ValueError(f"Invalid consistency_score: {consistency}")
    
    def validate_result(self, parsed_result: Dict[str, Any]) -> bool:
        """Validate that the parsed result is acceptable."""
        try:
            # Check required fields
            required_fields = ['final_confidence', 'agent_breakdown', 'consistency_score']
            for field in required_fields:
                if field not in parsed_result:
                    return False
            
            # Validate confidence scores
            self._validate_confidence_scores(parsed_result)
            
            # Check issues field
            issues = parsed_result.get('issues', [])
            if not isinstance(issues, list):
                return False
            
            # Check reasoning exists
            if not parsed_result.get('reasoning'):
                return False
            
            return True
            
        except Exception:
            return False
    
    def evaluate_consistency(self, categorization_result: AgentResult,
                           tagging_result: AgentResult,
                           naming_result: AgentResult) -> Dict[str, float]:
        """
        Evaluate consistency between agent results using rule-based analysis.
        This provides a fallback when AI evaluation is not available.
        """
        consistency_scores = {}
        
        # Extract data from results
        category = categorization_result.raw_output.get('category', '') if categorization_result.success else ''
        tags = tagging_result.raw_output.get('tags', []) if tagging_result.success else []
        suggested_path = naming_result.raw_output.get('suggested_path', '') if naming_result.success else ''
        
        # 1. Category-Tag Alignment
        consistency_scores['category_tag_alignment'] = self._check_category_tag_alignment(category, tags)
        
        # 2. Tag-Path Alignment
        consistency_scores['tag_path_alignment'] = self._check_tag_path_alignment(tags, suggested_path)
        
        # 3. Category-Path Alignment
        consistency_scores['category_path_alignment'] = self._check_category_path_alignment(category, suggested_path)
        
        # 4. Overall Coherence
        consistency_scores['overall_coherence'] = self._check_overall_coherence(
            category, tags, suggested_path
        )
        
        return consistency_scores
    
    def _check_category_tag_alignment(self, category: str, tags: List[str]) -> float:
        """Check if tags align with the assigned category."""
        if not category or not tags:
            return 0.5  # Neutral score if missing data
        
        category_lower = category.lower()
        tags_text = ' '.join(tags).lower()
        
        # Define expected tag patterns for each category
        category_patterns = {
            'code': ['python', 'javascript', 'java', 'programming', 'script', 'development'],
            'documents': ['documentation', 'manual', 'guide', 'text', 'report', 'spec'],
            'media': ['image', 'video', 'audio', 'graphics', 'photo', 'sound'],
            'system': ['configuration', 'system', 'binary', 'executable', 'config'],
            'logs': ['logging', 'debug', 'trace', 'error', 'monitoring'],
            'data': ['database', 'json', 'csv', 'export', 'structured', 'backup'],
            'archives': ['compressed', 'archive', 'zip', 'backup', 'package']
        }
        
        expected_patterns = category_patterns.get(category_lower, [])
        
        # Check how many expected patterns appear in tags
        matches = sum(1 for pattern in expected_patterns if pattern in tags_text)
        
        if not expected_patterns:
            return 0.7  # Neutral score for unknown categories
        
        return min(1.0, matches / len(expected_patterns) + 0.3)  # Boost base score
    
    def _check_tag_path_alignment(self, tags: List[str], suggested_path: str) -> float:
        """Check if the suggested path reflects the tags."""
        if not tags or not suggested_path:
            return 0.5
        
        path_lower = suggested_path.lower()
        
        # Count how many tags appear in the path
        tag_matches = sum(1 for tag in tags if tag.lower() in path_lower)
        
        if not tags:
            return 0.7
        
        # Higher score if more tags are reflected in the path
        return min(1.0, (tag_matches / len(tags)) * 1.2 + 0.2)
    
    def _check_category_path_alignment(self, category: str, suggested_path: str) -> float:
        """Check if the suggested path starts with the appropriate category."""
        if not category or not suggested_path:
            return 0.5
        
        category_lower = category.lower()
        path_lower = suggested_path.lower()
        
        # Expected path prefixes for each category
        expected_prefixes = {
            'code': ['code/', 'src/', 'source/'],
            'documents': ['documents/', 'docs/', 'doc/'],
            'media': ['media/', 'images/', 'videos/', 'audio/'],
            'system': ['system/', 'bin/', 'lib/'],
            'logs': ['logs/', 'log/'],
            'data': ['data/', 'database/', 'db/'],
            'archives': ['archives/', 'archive/']
        }
        
        expected = expected_prefixes.get(category_lower, [])
        
        # Check if path starts with expected prefix
        for prefix in expected:
            if path_lower.startswith(prefix):
                return 0.9
        
        # Partial credit if category name appears anywhere in path
        if category_lower in path_lower:
            return 0.6
        
        return 0.3  # Low score if no alignment
    
    def _check_overall_coherence(self, category: str, tags: List[str], suggested_path: str) -> float:
        """Check overall coherence of the analysis."""
        if not all([category, tags, suggested_path]):
            return 0.4
        
        # Check for obvious inconsistencies
        inconsistencies = 0
        
        # Example: CODE category but no programming-related tags
        if category == 'CODE':
            programming_tags = ['python', 'javascript', 'java', 'programming', 'script', 'code']
            if not any(tag in ' '.join(tags).lower() for tag in programming_tags):
                inconsistencies += 1
        
        # Example: MEDIA category but path doesn't suggest media
        if category == 'MEDIA':
            if not any(word in suggested_path.lower() for word in ['media', 'image', 'video', 'audio']):
                inconsistencies += 1
        
        # More coherence checks can be added here
        
        # Return score based on inconsistencies found
        return max(0.2, 1.0 - (inconsistencies * 0.3))
    
    def calculate_final_confidence(self, agent_results: List[AgentResult],
                                 consistency_scores: Dict[str, float]) -> float:
        """Calculate final confidence score based on agent results and consistency."""
        if not agent_results:
            return 0.0
        
        # Average individual agent confidences
        individual_confidences = [result.confidence for result in agent_results if result.success]
        if not individual_confidences:
            return 0.0
        
        avg_individual = sum(individual_confidences) / len(individual_confidences)
        
        # Calculate weighted consistency score
        weighted_consistency = sum(
            score * self.CONSISTENCY_WEIGHTS.get(metric, 0.25)
            for metric, score in consistency_scores.items()
        )
        
        # Combine individual confidence with consistency
        final_confidence = (avg_individual * 0.6) + (weighted_consistency * 0.4)
        
        # Apply penalties for failed agents
        failed_agents = len([r for r in agent_results if not r.success])
        if failed_agents > 0:
            penalty = failed_agents * 0.15
            final_confidence = max(0.0, final_confidence - penalty)
        
        return min(1.0, final_confidence)
    
    def get_quality_assessment(self, final_confidence: float) -> str:
        """Get quality assessment based on confidence score."""
        if final_confidence >= self.QUALITY_THRESHOLDS['high_confidence']:
            return "HIGH"
        elif final_confidence >= self.QUALITY_THRESHOLDS['medium_confidence']:
            return "MEDIUM"
        elif final_confidence >= self.QUALITY_THRESHOLDS['low_confidence']:
            return "LOW"
        else:
            return "REJECT"
    
    def should_reject_result(self, final_confidence: float) -> bool:
        """Determine if the result should be rejected based on confidence."""
        return final_confidence < self.QUALITY_THRESHOLDS['reject_threshold']
    
    def generate_improvement_suggestions(self, consistency_scores: Dict[str, float],
                                       agent_results: List[AgentResult]) -> List[str]:
        """Generate suggestions for improving low-confidence results."""
        suggestions = []
        
        # Check for low consistency scores
        for metric, score in consistency_scores.items():
            if score < 0.5:
                if metric == 'category_tag_alignment':
                    suggestions.append("Tags don't align well with the assigned category")
                elif metric == 'tag_path_alignment':
                    suggestions.append("Suggested path doesn't reflect the extracted tags")
                elif metric == 'category_path_alignment':
                    suggestions.append("Path structure doesn't match the file category")
                elif metric == 'overall_coherence':
                    suggestions.append("Overall analysis lacks coherence")
        
        # Check for failed agents
        for result in agent_results:
            if not result.success:
                suggestions.append(f"{result.agent_name} agent failed: {result.error_message}")
        
        # Check for low individual confidences
        for result in agent_results:
            if result.success and result.confidence < 0.6:
                suggestions.append(f"{result.agent_name} agent has low confidence ({result.confidence:.2f})")
        
        return suggestions