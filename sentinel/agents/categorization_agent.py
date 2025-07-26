#!/usr/bin/env python3
"""
Sentinel 2.0 - Categorization Agent
Specialized agent for determining high-level file categories
"""

import json
import re
from typing import Dict, Any, Set
from .base_agent import BaseAgent, FileContext


class CategorizationAgent(BaseAgent):
    """
    Specialized agent for file categorization.
    Determines high-level categories: CODE, DOCUMENTS, MEDIA, SYSTEM, LOGS, DATA, ARCHIVES
    """
    
    # Predefined categories with descriptions
    CATEGORIES = {
        'CODE': 'Programming and development files',
        'DOCUMENTS': 'Text documents and office files', 
        'MEDIA': 'Images, videos, and audio files',
        'SYSTEM': 'System and configuration files',
        'LOGS': 'Log files and debugging output',
        'DATA': 'Structured data and databases',
        'ARCHIVES': 'Compressed and archive files'
    }
    
    # Extension mappings for quick categorization
    EXTENSION_MAPPINGS = {
        # Code files
        'CODE': {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
            '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.r',
            '.sql', '.html', '.htm', '.css', '.scss', '.sass', '.less', '.vue',
            '.svelte', '.dart', '.lua', '.perl', '.pl', '.sh', '.bash', '.zsh',
            '.ps1', '.bat', '.cmd', '.vbs', '.asm', '.s', '.f', '.f90', '.f95',
            '.m', '.mm', '.clj', '.cljs', '.elm', '.ex', '.exs', '.erl', '.hrl'
        },
        
        # Document files
        'DOCUMENTS': {
            '.txt', '.md', '.rst', '.doc', '.docx', '.pdf', '.rtf', '.odt',
            '.pages', '.tex', '.latex', '.epub', '.mobi', '.azw', '.azw3',
            '.ppt', '.pptx', '.odp', '.key', '.xls', '.xlsx', '.ods', '.numbers',
            '.csv', '.tsv', '.readme', '.license', '.changelog', '.authors'
        },
        
        # Media files
        'MEDIA': {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp',
            '.svg', '.ico', '.psd', '.ai', '.eps', '.raw', '.cr2', '.nef',
            '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v',
            '.mpg', '.mpeg', '.3gp', '.ogv', '.mp3', '.wav', '.flac', '.aac',
            '.ogg', '.wma', '.m4a', '.opus', '.aiff', '.au', '.ra'
        },
        
        # System files
        'SYSTEM': {
            '.dll', '.so', '.dylib', '.exe', '.msi', '.deb', '.rpm', '.dmg',
            '.app', '.pkg', '.sys', '.ini', '.cfg', '.conf', '.config',
            '.plist', '.reg', '.service', '.socket', '.timer', '.desktop',
            '.lnk', '.url', '.webloc', '.tmp', '.temp', '.cache', '.lock'
        },
        
        # Log files
        'LOGS': {
            '.log', '.out', '.err', '.trace', '.debug', '.audit', '.access',
            '.error', '.warn', '.info', '.fatal', '.crash', '.dump', '.core'
        },
        
        # Data files
        'DATA': {
            '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.properties',
            '.db', '.sqlite', '.sqlite3', '.mdb', '.accdb', '.dbf', '.dat',
            '.bin', '.data', '.backup', '.bak', '.dump', '.export', '.import'
        },
        
        # Archive files
        'ARCHIVES': {
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.lz4',
            '.zst', '.tar.gz', '.tar.bz2', '.tar.xz', '.tgz', '.tbz2',
            '.txz', '.jar', '.war', '.ear', '.apk', '.ipa', '.deb', '.rpm'
        }
    }
    
    def __init__(self, inference_engine):
        """Initialize the categorization agent."""
        super().__init__(inference_engine, "categorization")
        
        # Build reverse mapping for faster lookup
        self.extension_to_category = {}
        for category, extensions in self.EXTENSION_MAPPINGS.items():
            for ext in extensions:
                self.extension_to_category[ext] = category
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for categorization."""
        categories_desc = "\n".join([
            f"- {cat}: {desc}" 
            for cat, desc in self.CATEGORIES.items()
        ])
        
        return f"""You are a specialized file categorization agent. Your ONLY job is to determine the high-level category of files.

Available categories:
{categories_desc}

Rules:
1. Analyze the file extension, path, name, and content preview (if available)
2. Choose the MOST APPROPRIATE category from the list above
3. Provide a confidence score (0.0 to 1.0)
4. Give a brief reasoning for your decision
5. ALWAYS respond with valid JSON in this exact format:

{{
    "category": "CATEGORY_NAME",
    "confidence": 0.95,
    "reasoning": "Brief explanation of categorization decision"
}}

Be decisive and consistent. The same file type should always get the same category."""
    
    def build_user_prompt(self, file_context: FileContext, **kwargs) -> str:
        """Build the user prompt for categorization."""
        # Get quick categorization hint
        quick_category = self._get_quick_category_hint(file_context)
        
        prompt = f"""Categorize this file:

File Path: {file_context.file_path}
File Name: {file_context.file_name}
File Extension: {file_context.file_extension}
File Size: {file_context.file_size_bytes / 1024:.1f} KB
Directory: {file_context.directory_name}
"""
        
        # Add content preview if available
        if file_context.file_content_preview:
            preview = file_context.file_content_preview[:500]  # Limit for prompt
            prompt += f"\nContent Preview:\n{preview}\n"
        
        # Add quick hint if available
        if quick_category:
            prompt += f"\nHint: Extension suggests {quick_category} category\n"
        
        prompt += "\nProvide categorization in JSON format."
        
        return prompt
    
    def _get_quick_category_hint(self, file_context: FileContext) -> str:
        """Get a quick category hint based on extension."""
        return self.extension_to_category.get(file_context.file_extension, "")
    
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
                if 'category' not in parsed:
                    raise ValueError("Missing 'category' field")
                
                # Validate category
                if parsed['category'] not in self.CATEGORIES:
                    # Try to map to valid category
                    parsed['category'] = self._map_to_valid_category(parsed['category'])
                
                # Set defaults for missing fields
                parsed.setdefault('confidence', 0.8)
                parsed.setdefault('reasoning', 'Categorization completed')
                
                return parsed
            else:
                raise ValueError("No JSON found in response")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error: {e}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            self.logger.error(f"Response parsing error: {e}")
            raise
    
    def _map_to_valid_category(self, category: str) -> str:
        """Map invalid category to valid one."""
        category_upper = category.upper()
        
        # Direct match
        if category_upper in self.CATEGORIES:
            return category_upper
        
        # Fuzzy matching
        mappings = {
            'PROGRAMMING': 'CODE',
            'DEVELOPMENT': 'CODE',
            'SOURCE': 'CODE',
            'SCRIPT': 'CODE',
            'TEXT': 'DOCUMENTS',
            'OFFICE': 'DOCUMENTS',
            'DOCUMENT': 'DOCUMENTS',
            'IMAGE': 'MEDIA',
            'VIDEO': 'MEDIA',
            'AUDIO': 'MEDIA',
            'PICTURE': 'MEDIA',
            'CONFIGURATION': 'SYSTEM',
            'CONFIG': 'SYSTEM',
            'BINARY': 'SYSTEM',
            'EXECUTABLE': 'SYSTEM',
            'DATABASE': 'DATA',
            'STRUCTURED': 'DATA',
            'COMPRESSED': 'ARCHIVES',
            'ARCHIVE': 'ARCHIVES',
            'PACKAGE': 'ARCHIVES'
        }
        
        return mappings.get(category_upper, 'DOCUMENTS')  # Default fallback
    
    def validate_result(self, parsed_result: Dict[str, Any]) -> bool:
        """Validate that the parsed result is acceptable."""
        try:
            # Check required fields
            if 'category' not in parsed_result:
                return False
            
            # Check category validity
            if parsed_result['category'] not in self.CATEGORIES:
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
    
    def get_category_statistics(self) -> Dict[str, int]:
        """Get statistics about categorized files (would be implemented with actual tracking)."""
        # This would track actual categorization statistics in a real implementation
        return {category: 0 for category in self.CATEGORIES}
    
    def is_high_confidence_extension(self, extension: str) -> bool:
        """Check if an extension typically results in high confidence categorization."""
        return extension in self.extension_to_category
    
    def get_category_for_extension(self, extension: str) -> str:
        """Get the expected category for a file extension."""
        return self.extension_to_category.get(extension, "DOCUMENTS")