#!/usr/bin/env python3
"""
Sentinel 2.0 - Naming Agent
Specialized agent for enforcing consistent naming conventions and path structures
"""

import json
import re
from typing import Dict, Any, List
from pathlib import Path
from .base_agent import BaseAgent, FileContext


class NamingAgent(BaseAgent):
    """
    Specialized agent for file naming and path structure.
    Enforces consistent naming conventions based on category and tags.
    """
    
    # Naming conventions for each category
    NAMING_CONVENTIONS = {
        'CODE': {
            'template': 'code/{language}/{project_type}/{filename}',
            'description': 'Organized by programming language and project type',
            'examples': [
                'code/python/web-app/main.py',
                'code/javascript/frontend/components/Header.js',
                'code/java/backend/services/UserService.java'
            ]
        },
        'DOCUMENTS': {
            'template': 'documents/{document_type}/{subject}/{filename}',
            'description': 'Organized by document type and subject matter',
            'examples': [
                'documents/manuals/user-guide/installation.pdf',
                'documents/reports/quarterly/q3-2024.docx',
                'documents/specifications/api/endpoints.md'
            ]
        },
        'MEDIA': {
            'template': 'media/{media_type}/{category}/{filename}',
            'description': 'Organized by media type and category',
            'examples': [
                'media/images/screenshots/login-page.png',
                'media/videos/tutorials/setup-guide.mp4',
                'media/audio/sounds/notification.wav'
            ]
        },
        'SYSTEM': {
            'template': 'system/{component}/{filename}',
            'description': 'Organized by system component',
            'examples': [
                'system/configuration/app.config',
                'system/libraries/utils.dll',
                'system/executables/installer.exe'
            ]
        },
        'LOGS': {
            'template': 'logs/{application}/{date}/{filename}',
            'description': 'Organized by application and date',
            'examples': [
                'logs/web-server/2024-01/access.log',
                'logs/database/2024-01/error.log',
                'logs/application/debug/trace.log'
            ]
        },
        'DATA': {
            'template': 'data/{format}/{purpose}/{filename}',
            'description': 'Organized by data format and purpose',
            'examples': [
                'data/json/configuration/settings.json',
                'data/csv/exports/users.csv',
                'data/database/backups/backup.db'
            ]
        },
        'ARCHIVES': {
            'template': 'archives/{content_type}/{filename}',
            'description': 'Organized by content type',
            'examples': [
                'archives/source-code/project-v1.0.zip',
                'archives/documents/reports-2024.tar.gz',
                'archives/media/photos-vacation.rar'
            ]
        }
    }
    
    # Language mappings for code files
    LANGUAGE_MAPPINGS = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'react',
        '.tsx': 'react-typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.cs': 'csharp',
        '.php': 'php',
        '.rb': 'ruby',
        '.go': 'go',
        '.rs': 'rust',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'sass',
        '.vue': 'vue',
        '.sql': 'sql'
    }
    
    # Project type detection patterns
    PROJECT_TYPE_PATTERNS = {
        'web-app': ['app', 'web', 'frontend', 'backend', 'server', 'client'],
        'mobile-app': ['mobile', 'android', 'ios', 'app', 'flutter', 'react-native'],
        'api': ['api', 'rest', 'graphql', 'endpoint', 'service'],
        'library': ['lib', 'library', 'package', 'module', 'framework'],
        'tool': ['tool', 'utility', 'script', 'automation', 'cli'],
        'game': ['game', 'unity', 'unreal', 'engine', 'gameplay'],
        'data-science': ['data', 'ml', 'ai', 'analysis', 'model', 'jupyter'],
        'desktop-app': ['desktop', 'gui', 'window', 'form', 'application'],
        'test': ['test', 'spec', 'mock', 'fixture', 'unit', 'integration']
    }
    
    def __init__(self, inference_engine):
        """Initialize the naming agent."""
        super().__init__(inference_engine, "naming")
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for naming."""
        conventions_desc = "\n".join([
            f"{cat}:\n  Template: {conv['template']}\n  Example: {conv['examples'][0]}"
            for cat, conv in self.NAMING_CONVENTIONS.items()
        ])
        
        return f"""You are a specialized file naming agent. Your job is to generate consistent, organized file paths based on category and tags.

Naming Conventions:
{conventions_desc}

Rules:
1. Follow the template for the given category
2. Use lowercase with hyphens for spaces (kebab-case)
3. Group similar files together in logical hierarchies
4. Keep paths descriptive but not too long
5. Ensure consistency - similar files should have similar paths
6. Preserve the original filename and extension
7. ALWAYS respond with valid JSON in this exact format:

{{
    "suggested_path": "category/subcategory/filename.ext",
    "confidence": 0.88,
    "reasoning": "Explanation of path structure decision"
}}

Be consistent and logical in your path structures."""
    
    def build_user_prompt(self, file_context: FileContext, category: str = None, tags: List[str] = None, **kwargs) -> str:
        """Build the user prompt for naming."""
        # Analyze file for naming hints
        language_hint = self._detect_language(file_context)
        project_type_hint = self._detect_project_type(file_context, tags or [])
        
        prompt = f"""Generate a structured file path for this file:

Original Path: {file_context.file_path}
File Name: {file_context.file_name}
File Extension: {file_context.file_extension}
Directory Context: {file_context.directory_name}
"""
        
        if category:
            prompt += f"Category: {category}\n"
            convention = self.NAMING_CONVENTIONS.get(category, {})
            if convention:
                prompt += f"Naming Template: {convention['template']}\n"
        
        if tags:
            prompt += f"Tags: {', '.join(tags)}\n"
        
        if language_hint:
            prompt += f"Detected Language: {language_hint}\n"
        
        if project_type_hint:
            prompt += f"Detected Project Type: {project_type_hint}\n"
        
        # Add content preview for better context
        if file_context.file_content_preview:
            preview = file_context.file_content_preview[:400]  # Limit for prompt
            prompt += f"\nContent Preview:\n{preview}\n"
        
        # Add path analysis
        path_parts = file_context.file_path.split('/')
        if len(path_parts) > 1:
            prompt += f"Current Structure: {' -> '.join(path_parts[-3:])}\n"
        
        prompt += f"\nGenerate a structured path following the {category or 'appropriate'} naming convention."
        
        return prompt
    
    def _detect_language(self, file_context: FileContext) -> str:
        """Detect programming language from file extension."""
        return self.LANGUAGE_MAPPINGS.get(file_context.file_extension, "")
    
    def _detect_project_type(self, file_context: FileContext, tags: List[str]) -> str:
        """Detect project type from context and tags."""
        # Check tags first
        for project_type, keywords in self.PROJECT_TYPE_PATTERNS.items():
            for tag in tags:
                if any(keyword in tag for keyword in keywords):
                    return project_type
        
        # Check file path and name
        full_text = f"{file_context.file_path} {file_context.file_name}".lower()
        
        for project_type, keywords in self.PROJECT_TYPE_PATTERNS.items():
            if any(keyword in full_text for keyword in keywords):
                return project_type
        
        return ""
    
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
                if 'suggested_path' not in parsed:
                    raise ValueError("Missing 'suggested_path' field")
                
                # Clean and validate the suggested path
                suggested_path = parsed['suggested_path']
                cleaned_path = self._clean_path(suggested_path)
                parsed['suggested_path'] = cleaned_path
                
                # Set defaults for missing fields
                parsed.setdefault('confidence', 0.8)
                parsed.setdefault('reasoning', 'Path structure generated')
                
                return parsed
            else:
                raise ValueError("No JSON found in response")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            self.logger.error(f"Response parsing error: {e}")
            raise
    
    def _clean_path(self, path: str) -> str:
        """Clean and validate the suggested path."""
        # Remove leading/trailing slashes and whitespace
        path = path.strip().strip('/')
        
        # Split into parts
        parts = path.split('/')
        cleaned_parts = []
        
        for part in parts:
            # Clean each part
            part = part.strip()
            if not part:
                continue
            
            # Convert to lowercase and replace spaces/invalid chars with hyphens
            part = re.sub(r'[^a-zA-Z0-9\-_.]', '-', part)
            part = re.sub(r'-+', '-', part)  # Collapse multiple hyphens
            part = part.strip('-')  # Remove leading/trailing hyphens
            
            if part:
                cleaned_parts.append(part)
        
        # Rejoin parts
        cleaned_path = '/'.join(cleaned_parts)
        
        # Ensure path is not too long
        if len(cleaned_path) > 200:
            # Truncate middle parts if too long
            parts = cleaned_parts
            if len(parts) > 3:
                cleaned_path = '/'.join([parts[0], '...', parts[-1]])
        
        return cleaned_path
    
    def validate_result(self, parsed_result: Dict[str, Any]) -> bool:
        """Validate that the parsed result is acceptable."""
        try:
            # Check required fields
            if 'suggested_path' not in parsed_result:
                return False
            
            # Check path validity
            suggested_path = parsed_result['suggested_path']
            if not isinstance(suggested_path, str) or not suggested_path.strip():
                return False
            
            # Check path length
            if len(suggested_path) > 250:
                return False
            
            # Check for invalid characters
            if re.search(r'[<>:"|?*]', suggested_path):
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
    
    def generate_path_for_category(self, category: str, file_context: FileContext, tags: List[str] = None) -> str:
        """Generate a path using category-specific logic (fallback method)."""
        tags = tags or []
        
        if category == 'CODE':
            language = self._detect_language(file_context)
            project_type = self._detect_project_type(file_context, tags)
            
            if language and project_type:
                return f"code/{language}/{project_type}/{file_context.file_name}"
            elif language:
                return f"code/{language}/{file_context.file_name}"
            else:
                return f"code/misc/{file_context.file_name}"
        
        elif category == 'DOCUMENTS':
            # Try to determine document type from extension
            doc_types = {
                '.pdf': 'pdf',
                '.doc': 'word', '.docx': 'word',
                '.xls': 'excel', '.xlsx': 'excel',
                '.ppt': 'powerpoint', '.pptx': 'powerpoint',
                '.txt': 'text',
                '.md': 'markdown'
            }
            doc_type = doc_types.get(file_context.file_extension, 'misc')
            
            # Try to determine subject from tags
            subject = 'general'
            for tag in tags:
                if tag in ['manual', 'guide', 'documentation', 'spec', 'report']:
                    subject = tag
                    break
            
            return f"documents/{doc_type}/{subject}/{file_context.file_name}"
        
        elif category == 'MEDIA':
            media_types = {
                '.jpg': 'images', '.jpeg': 'images', '.png': 'images', '.gif': 'images',
                '.mp4': 'videos', '.avi': 'videos', '.mkv': 'videos',
                '.mp3': 'audio', '.wav': 'audio', '.flac': 'audio'
            }
            media_type = media_types.get(file_context.file_extension, 'misc')
            
            return f"media/{media_type}/{file_context.file_name}"
        
        elif category == 'SYSTEM':
            return f"system/misc/{file_context.file_name}"
        
        elif category == 'LOGS':
            return f"logs/application/{file_context.file_name}"
        
        elif category == 'DATA':
            data_types = {
                '.json': 'json',
                '.xml': 'xml',
                '.csv': 'csv',
                '.db': 'database',
                '.sql': 'database'
            }
            data_type = data_types.get(file_context.file_extension, 'misc')
            
            return f"data/{data_type}/{file_context.file_name}"
        
        elif category == 'ARCHIVES':
            return f"archives/misc/{file_context.file_name}"
        
        else:
            return f"misc/{file_context.file_name}"
    
    def check_path_conflicts(self, suggested_path: str, existing_paths: List[str]) -> bool:
        """Check if the suggested path conflicts with existing paths."""
        return suggested_path in existing_paths
    
    def resolve_path_conflict(self, suggested_path: str, existing_paths: List[str]) -> str:
        """Resolve path conflicts by adding a suffix."""
        if not self.check_path_conflicts(suggested_path, existing_paths):
            return suggested_path
        
        # Extract path parts
        path_obj = Path(suggested_path)
        stem = path_obj.stem
        suffix = path_obj.suffix
        parent = path_obj.parent
        
        # Try adding numbers
        counter = 1
        while counter < 100:  # Prevent infinite loop
            new_name = f"{stem}-{counter}{suffix}"
            new_path = str(parent / new_name)
            
            if not self.check_path_conflicts(new_path, existing_paths):
                return new_path
            
            counter += 1
        
        # Fallback: add timestamp
        import time
        timestamp = int(time.time())
        new_name = f"{stem}-{timestamp}{suffix}"
        return str(parent / new_name)
    
    def get_naming_statistics(self) -> Dict[str, Any]:
        """Get statistics about naming patterns (would be implemented with actual tracking)."""
        return {
            'total_paths_generated': 0,
            'category_distribution': {},
            'average_path_length': 0,
            'conflict_resolution_count': 0
        }