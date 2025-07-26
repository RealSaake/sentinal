#!/usr/bin/env python3
"""
Sentinel 2.0 - Tagging Agent
Specialized agent for extracting relevant keywords and tags from files
"""

import json
import re
from typing import Dict, Any, List, Set
from .base_agent import BaseAgent, FileContext


class TaggingAgent(BaseAgent):
    """
    Specialized agent for file tagging.
    Extracts relevant keywords and tags based on file content, name, and context.
    """
    
    # Technology/language detection patterns
    TECH_PATTERNS = {
        # Programming languages
        'python': [r'\.py$', r'python', r'import\s+\w+', r'def\s+\w+', r'class\s+\w+'],
        'javascript': [r'\.js$', r'\.ts$', r'javascript', r'function\s+\w+', r'const\s+\w+', r'let\s+\w+'],
        'java': [r'\.java$', r'public\s+class', r'import\s+java\.', r'package\s+\w+'],
        'cpp': [r'\.cpp$', r'\.c$', r'\.h$', r'#include', r'using\s+namespace', r'int\s+main'],
        'csharp': [r'\.cs$', r'using\s+System', r'namespace\s+\w+', r'public\s+class'],
        'php': [r'\.php$', r'<\?php', r'function\s+\w+', r'\$\w+'],
        'ruby': [r'\.rb$', r'def\s+\w+', r'class\s+\w+', r'require\s+'],
        'go': [r'\.go$', r'package\s+main', r'import\s+', r'func\s+\w+'],
        'rust': [r'\.rs$', r'fn\s+\w+', r'use\s+\w+', r'struct\s+\w+'],
        'swift': [r'\.swift$', r'import\s+\w+', r'func\s+\w+', r'class\s+\w+'],
        
        # Web technologies
        'html': [r'\.html?$', r'<html', r'<div', r'<script', r'<!DOCTYPE'],
        'css': [r'\.css$', r'\.scss$', r'\.sass$', r'\{[^}]*\}', r'@media'],
        'react': [r'\.jsx$', r'\.tsx$', r'import\s+React', r'useState', r'useEffect'],
        'vue': [r'\.vue$', r'<template>', r'<script>', r'<style>'],
        'angular': [r'@Component', r'@Injectable', r'@NgModule'],
        
        # Frameworks and libraries
        'django': [r'django', r'models\.py', r'views\.py', r'urls\.py'],
        'flask': [r'flask', r'app\.py', r'@app\.route'],
        'express': [r'express', r'app\.js', r'server\.js', r'router'],
        'spring': [r'spring', r'@Controller', r'@Service', r'@Repository'],
        
        # Data formats
        'json': [r'\.json$', r'\{.*\}', r'"[^"]*":\s*'],
        'xml': [r'\.xml$', r'<\?xml', r'<[^>]+>'],
        'yaml': [r'\.ya?ml$', r'---', r'^\s*\w+:'],
        'csv': [r'\.csv$', r',', r'^\w+,\w+'],
        
        # Databases
        'sql': [r'\.sql$', r'SELECT', r'INSERT', r'UPDATE', r'CREATE TABLE'],
        'sqlite': [r'\.sqlite', r'\.db$'],
        'mysql': [r'mysql', r'MYSQL'],
        'postgresql': [r'postgres', r'psql'],
        
        # DevOps and configuration
        'docker': [r'Dockerfile', r'docker-compose', r'FROM\s+\w+', r'RUN\s+'],
        'kubernetes': [r'\.yaml$', r'apiVersion:', r'kind:', r'metadata:'],
        'terraform': [r'\.tf$', r'resource\s+', r'variable\s+', r'output\s+'],
        'ansible': [r'playbook', r'tasks:', r'hosts:', r'vars:'],
        
        # Build tools
        'maven': [r'pom\.xml', r'<groupId>', r'<artifactId>'],
        'gradle': [r'build\.gradle', r'gradle', r'dependencies\s*\{'],
        'npm': [r'package\.json', r'node_modules', r'"scripts":', r'"dependencies":'],
        'pip': [r'requirements\.txt', r'setup\.py', r'pip install'],
        
        # Version control
        'git': [r'\.git', r'\.gitignore', r'commit', r'branch', r'merge'],
        
        # Testing
        'testing': [r'test_', r'_test\.', r'spec\.', r'\.test\.', r'assert', r'expect'],
        'unittest': [r'unittest', r'pytest', r'jest', r'mocha', r'jasmine'],
        
        # Documentation
        'documentation': [r'README', r'CHANGELOG', r'LICENSE', r'\.md$', r'docs/'],
        'api': [r'api', r'endpoint', r'swagger', r'openapi', r'postman']
    }
    
    # File purpose patterns
    PURPOSE_PATTERNS = {
        'configuration': [r'config', r'settings', r'\.conf$', r'\.ini$', r'\.cfg$'],
        'documentation': [r'readme', r'doc', r'manual', r'guide', r'help'],
        'testing': [r'test', r'spec', r'mock', r'fixture', r'sample'],
        'build': [r'build', r'compile', r'make', r'cmake', r'Makefile'],
        'deployment': [r'deploy', r'release', r'production', r'staging'],
        'backup': [r'backup', r'bak', r'old', r'archive', r'snapshot'],
        'temporary': [r'temp', r'tmp', r'cache', r'log', r'debug'],
        'library': [r'lib', r'vendor', r'third.party', r'external'],
        'utility': [r'util', r'helper', r'tool', r'script', r'automation'],
        'model': [r'model', r'schema', r'entity', r'dto', r'vo'],
        'controller': [r'controller', r'handler', r'router', r'endpoint'],
        'service': [r'service', r'manager', r'provider', r'factory'],
        'component': [r'component', r'widget', r'element', r'module']
    }
    
    def __init__(self, inference_engine):
        """Initialize the tagging agent."""
        super().__init__(inference_engine, "tagging")
        
        # Compile regex patterns for better performance
        self.compiled_tech_patterns = {}
        for tech, patterns in self.TECH_PATTERNS.items():
            self.compiled_tech_patterns[tech] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        self.compiled_purpose_patterns = {}
        for purpose, patterns in self.PURPOSE_PATTERNS.items():
            self.compiled_purpose_patterns[purpose] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for tagging."""
        return """You are a specialized file tagging agent. Your job is to extract 3-7 relevant tags that would help organize and find files.

Focus on:
1. Technology/language (for code files): python, javascript, react, django, etc.
2. File purpose: configuration, documentation, testing, utility, etc.
3. Project context: web-app, mobile, api, frontend, backend, etc.
4. Domain/subject matter: finance, healthcare, education, gaming, etc.

Rules:
1. Generate 3-7 relevant tags
2. Use lowercase, hyphenated format (e.g., "web-development", "unit-testing")
3. Be specific but not overly granular
4. Prioritize tags that would be useful for organization
5. Avoid redundant or obvious tags
6. ALWAYS respond with valid JSON in this exact format:

{
    "tags": ["tag1", "tag2", "tag3"],
    "confidence": 0.90,
    "reasoning": "Brief explanation of tag selection"
}

Be consistent - similar files should get similar tags."""
    
    def build_user_prompt(self, file_context: FileContext, category: str = None, **kwargs) -> str:
        """Build the user prompt for tagging."""
        # Pre-analyze file for hints
        detected_tech = self._detect_technologies(file_context)
        detected_purpose = self._detect_purpose(file_context)
        
        prompt = f"""Extract relevant tags for this file:

File Path: {file_context.file_path}
File Name: {file_context.file_name}
File Extension: {file_context.file_extension}
Directory: {file_context.directory_name}
"""
        
        if category:
            prompt += f"Category: {category}\n"
        
        # Add content preview if available
        if file_context.file_content_preview:
            preview = file_context.file_content_preview[:800]  # Limit for prompt
            prompt += f"\nContent Preview:\n{preview}\n"
        
        # Add detection hints
        if detected_tech:
            prompt += f"\nDetected Technologies: {', '.join(detected_tech)}\n"
        
        if detected_purpose:
            prompt += f"Detected Purpose: {', '.join(detected_purpose)}\n"
        
        # Add context from directory structure
        path_parts = file_context.file_path.split('/')
        if len(path_parts) > 2:
            prompt += f"Path Context: {' -> '.join(path_parts[-3:])}\n"
        
        prompt += "\nGenerate relevant tags in JSON format."
        
        return prompt
    
    def _detect_technologies(self, file_context: FileContext) -> List[str]:
        """Detect technologies based on file analysis."""
        detected = []
        
        # Check file path and name
        full_text = f"{file_context.file_path} {file_context.file_name}"
        if file_context.file_content_preview:
            full_text += f" {file_context.file_content_preview}"
        
        for tech, patterns in self.compiled_tech_patterns.items():
            for pattern in patterns:
                if pattern.search(full_text):
                    detected.append(tech)
                    break  # Only add once per technology
        
        return detected[:5]  # Limit to top 5
    
    def _detect_purpose(self, file_context: FileContext) -> List[str]:
        """Detect file purpose based on analysis."""
        detected = []
        
        # Check file path and name
        full_text = f"{file_context.file_path} {file_context.file_name}"
        
        for purpose, patterns in self.compiled_purpose_patterns.items():
            for pattern in patterns:
                if pattern.search(full_text):
                    detected.append(purpose)
                    break  # Only add once per purpose
        
        return detected[:3]  # Limit to top 3
    
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
                if 'tags' not in parsed:
                    raise ValueError("Missing 'tags' field")
                
                # Validate and clean tags
                tags = parsed['tags']
                if not isinstance(tags, list):
                    raise ValueError("Tags must be a list")
                
                # Clean and validate tags
                cleaned_tags = self._clean_tags(tags)
                parsed['tags'] = cleaned_tags
                
                # Set defaults for missing fields
                parsed.setdefault('confidence', 0.8)
                parsed.setdefault('reasoning', 'Tags extracted successfully')
                
                return parsed
            else:
                raise ValueError("No JSON found in response")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            self.logger.error(f"Response parsing error: {e}")
            raise
    
    def _clean_tags(self, tags: List[str]) -> List[str]:
        """Clean and validate tags."""
        cleaned = []
        
        for tag in tags:
            if not isinstance(tag, str):
                continue
            
            # Clean the tag
            tag = tag.strip().lower()
            tag = re.sub(r'[^a-z0-9\-_]', '-', tag)  # Replace invalid chars with hyphens
            tag = re.sub(r'-+', '-', tag)  # Collapse multiple hyphens
            tag = tag.strip('-')  # Remove leading/trailing hyphens
            
            # Validate tag
            if len(tag) >= 2 and len(tag) <= 30 and tag not in cleaned:
                cleaned.append(tag)
        
        # Limit to 7 tags maximum
        return cleaned[:7]
    
    def validate_result(self, parsed_result: Dict[str, Any]) -> bool:
        """Validate that the parsed result is acceptable."""
        try:
            # Check required fields
            if 'tags' not in parsed_result:
                return False
            
            # Check tags validity
            tags = parsed_result['tags']
            if not isinstance(tags, list):
                return False
            
            if len(tags) < 1 or len(tags) > 7:
                return False
            
            # Check each tag
            for tag in tags:
                if not isinstance(tag, str) or len(tag) < 2 or len(tag) > 30:
                    return False
            
            # Check confidence range
            confidence = parsed_result.get('confidence', 0.0)
            if not (0.0 <= confidence <= 1.0):
                return False
            
            # Check reasoning exists
            if not parsed_result.get('reasoning'):
                return False
            
            return True
            
        except Exception:
            return False
    
    def should_tag_file(self, category: str, file_context: FileContext) -> bool:
        """Determine if a file should be tagged based on category and context."""
        # Don't tag system files or very small files
        if category == 'SYSTEM' and file_context.file_size_bytes < 1024:
            return False
        
        # Don't tag binary files without content preview
        if not file_context.file_content_preview and file_context.file_extension in {
            '.exe', '.dll', '.so', '.dylib', '.bin', '.dat'
        }:
            return False
        
        # Always tag code, documents, and data files
        if category in {'CODE', 'DOCUMENTS', 'DATA'}:
            return True
        
        # Tag media files if they have meaningful names
        if category == 'MEDIA':
            return len(file_context.file_name) > 10  # Meaningful filename
        
        # Tag logs if they're not too generic
        if category == 'LOGS':
            return 'error' in file_context.file_name.lower() or 'debug' in file_context.file_name.lower()
        
        return True  # Default to tagging
    
    def get_tag_statistics(self) -> Dict[str, int]:
        """Get statistics about generated tags (would be implemented with actual tracking)."""
        # This would track actual tag statistics in a real implementation
        return {}
    
    def suggest_tags_for_category(self, category: str) -> List[str]:
        """Suggest common tags for a given category."""
        suggestions = {
            'CODE': ['programming', 'development', 'source-code', 'script'],
            'DOCUMENTS': ['documentation', 'text', 'manual', 'guide'],
            'MEDIA': ['image', 'video', 'audio', 'graphics'],
            'SYSTEM': ['configuration', 'system', 'binary', 'executable'],
            'LOGS': ['logging', 'debug', 'monitoring', 'trace'],
            'DATA': ['database', 'structured-data', 'export', 'backup'],
            'ARCHIVES': ['compressed', 'archive', 'backup', 'package']
        }
        
        return suggestions.get(category, [])