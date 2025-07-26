#!/usr/bin/env python3
"""
Helios Core Data Models
Advanced data structures for intelligent file organization
"""

import hashlib
import mimetypes
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
import json


class FileType(Enum):
    """Enhanced file type classification."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    CODE = "code"
    ARCHIVE = "archive"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    FONT = "font"
    CAD_3D = "cad_3d"
    GAME = "game"
    SYSTEM = "system"
    TEMPORARY = "temporary"
    UNKNOWN = "unknown"


class OrganizationAction(Enum):
    """Actions that can be taken on files."""
    MOVE = "move"
    COPY = "copy"
    RENAME = "rename"
    SKIP = "skip"
    PRESERVE = "preserve"
    QUARANTINE = "quarantine"
    DELETE = "delete"


class ConfidenceLevel(Enum):
    """AI confidence levels for categorization."""
    VERY_HIGH = "very_high"  # 0.9+
    HIGH = "high"           # 0.7-0.9
    MEDIUM = "medium"       # 0.5-0.7
    LOW = "low"            # 0.3-0.5
    VERY_LOW = "very_low"  # <0.3


@dataclass
class FileMetadata:
    """Comprehensive file metadata."""
    path: str
    name: str
    extension: str
    size_bytes: int
    created_time: datetime
    modified_time: datetime
    accessed_time: datetime
    mime_type: Optional[str] = None
    file_hash: Optional[str] = None
    is_hidden: bool = False
    is_system: bool = False
    is_readonly: bool = False
    permissions: Optional[str] = None
    
    def __post_init__(self):
        """Calculate additional metadata after initialization."""
        if not self.mime_type:
            self.mime_type, _ = mimetypes.guess_type(self.path)
        
        # Determine if file is hidden or system
        file_path = Path(self.path)
        self.is_hidden = file_path.name.startswith('.')
        
        # Check if it's a system file based on common patterns
        system_patterns = ['thumbs.db', 'desktop.ini', '.ds_store', 'hiberfil.sys']
        self.is_system = any(pattern in file_path.name.lower() for pattern in system_patterns)
    
    def calculate_hash(self, algorithm: str = "md5") -> str:
        """Calculate file hash for duplicate detection."""
        if self.file_hash:
            return self.file_hash
            
        hash_func = hashlib.new(algorithm)
        try:
            with open(self.path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)
            self.file_hash = hash_func.hexdigest()
        except (IOError, OSError):
            self.file_hash = "error"
        
        return self.file_hash
    
    @property
    def size_mb(self) -> float:
        """File size in megabytes."""
        return self.size_bytes / (1024 * 1024)
    
    @property
    def size_gb(self) -> float:
        """File size in gigabytes."""
        return self.size_bytes / (1024 * 1024 * 1024)
    
    @property
    def age_days(self) -> int:
        """Age of file in days since creation."""
        return (datetime.now() - self.created_time).days


@dataclass
class SmartCategory:
    """Intelligent categorization result."""
    primary_type: FileType
    subcategory: Optional[str] = None
    suggested_path: str = ""
    confidence: float = 0.0
    reasoning: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    context_clues: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Convert numeric confidence to level."""
        if self.confidence >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif self.confidence >= 0.7:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif self.confidence >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


@dataclass
class FileTask:
    """Enhanced file analysis task."""
    file_path: str
    metadata: FileMetadata
    priority: int = 1
    context: Dict[str, Any] = field(default_factory=dict)
    parent_directory: Optional[str] = None
    related_files: List[str] = field(default_factory=list)
    project_indicators: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize additional context."""
        path = Path(self.file_path)
        self.parent_directory = str(path.parent)
        
        # Look for project indicators in the same directory
        try:
            parent_files = list(path.parent.iterdir())
            project_files = ['package.json', 'requirements.txt', 'pom.xml', 'Cargo.toml', 
                           '.git', 'makefile', 'Makefile', '.gitignore', 'README.md']
            
            self.project_indicators = [
                f.name for f in parent_files 
                if f.name.lower() in [pf.lower() for pf in project_files]
            ]
            
            # Find related files (same name, different extension)
            base_name = path.stem
            self.related_files = [
                str(f) for f in parent_files 
                if f.stem == base_name and f != path
            ]
            
        except (OSError, PermissionError):
            pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert FileTask to dictionary for serialization."""
        return {
            'file_path': self.file_path,
            'metadata': {
                'path': self.metadata.path,
                'name': self.metadata.name,
                'extension': self.metadata.extension,
                'size_bytes': self.metadata.size_bytes,
                'created_time': self.metadata.created_time.isoformat(),
                'modified_time': self.metadata.modified_time.isoformat(),
                'accessed_time': self.metadata.accessed_time.isoformat(),
                'mime_type': self.metadata.mime_type,
                'file_hash': self.metadata.file_hash,
                'is_hidden': self.metadata.is_hidden,
                'is_system': self.metadata.is_system,
                'is_readonly': self.metadata.is_readonly,
                'permissions': self.metadata.permissions
            },
            'priority': self.priority,
            'context': self.context,
            'parent_directory': self.parent_directory,
            'related_files': self.related_files,
            'project_indicators': self.project_indicators
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileTask':
        """Create FileTask from dictionary."""
        metadata_data = data['metadata']
        metadata = FileMetadata(
            path=metadata_data['path'],
            name=metadata_data['name'],
            extension=metadata_data['extension'],
            size_bytes=metadata_data['size_bytes'],
            created_time=datetime.fromisoformat(metadata_data['created_time']),
            modified_time=datetime.fromisoformat(metadata_data['modified_time']),
            accessed_time=datetime.fromisoformat(metadata_data['accessed_time']),
            mime_type=metadata_data.get('mime_type'),
            file_hash=metadata_data.get('file_hash'),
            is_hidden=metadata_data.get('is_hidden', False),
            is_system=metadata_data.get('is_system', False),
            is_readonly=metadata_data.get('is_readonly', False),
            permissions=metadata_data.get('permissions')
        )
        
        task = cls(
            file_path=data['file_path'],
            metadata=metadata,
            priority=data.get('priority', 1),
            context=data.get('context', {}),
            parent_directory=data.get('parent_directory'),
            related_files=data.get('related_files', []),
            project_indicators=data.get('project_indicators', [])
        )
        
        return task
    
    @property
    def is_part_of_project(self) -> bool:
        """Check if file is part of a development project."""
        return len(self.project_indicators) > 0
    
    @property
    def has_related_files(self) -> bool:
        """Check if file has related files."""
        return len(self.related_files) > 0


@dataclass
class OrganizationRule:
    """Advanced organization rule."""
    name: str
    enabled: bool = True
    priority: int = 1
    conditions: Dict[str, Any] = field(default_factory=dict)
    actions: List[OrganizationAction] = field(default_factory=list)
    target_path: Optional[str] = None
    preserve_structure: bool = False
    apply_to_related: bool = False
    
    def matches(self, task: FileTask) -> bool:
        """Check if rule matches the given file task."""
        if not self.enabled:
            return False
        
        # Check extension conditions
        if 'extensions' in self.conditions:
            if task.metadata.extension.lower() not in self.conditions['extensions']:
                return False
        
        # Check size conditions
        if 'min_size' in self.conditions:
            if task.metadata.size_bytes < self.conditions['min_size']:
                return False
        
        if 'max_size' in self.conditions:
            if task.metadata.size_bytes > self.conditions['max_size']:
                return False
        
        # Check pattern conditions
        if 'patterns' in self.conditions:
            file_name = task.metadata.name.lower()
            if not any(pattern.lower() in file_name for pattern in self.conditions['patterns']):
                return False
        
        # Check age conditions
        if 'max_age_days' in self.conditions:
            if task.metadata.age_days > self.conditions['max_age_days']:
                return False
        
        return True


@dataclass
class AnalysisResult:
    """Comprehensive analysis result."""
    original_path: str
    suggested_path: str
    action: OrganizationAction
    category: SmartCategory
    processing_time: float
    worker_id: int
    timestamp: datetime = field(default_factory=datetime.now)
    applied_rules: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Optional[FileMetadata] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'original_path': self.original_path,
            'suggested_path': self.suggested_path,
            'action': self.action.value,
            'category': {
                'primary_type': self.category.primary_type.value,
                'subcategory': self.category.subcategory,
                'confidence': self.category.confidence,
                'reasoning': self.category.reasoning,
                'tags': self.category.tags
            },
            'processing_time': self.processing_time,
            'worker_id': self.worker_id,
            'timestamp': self.timestamp.isoformat(),
            'applied_rules': self.applied_rules,
            'warnings': self.warnings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """Create from dictionary."""
        category = SmartCategory(
            primary_type=FileType(data['category']['primary_type']),
            subcategory=data['category']['subcategory'],
            confidence=data['category']['confidence'],
            reasoning=data['category']['reasoning'],
            tags=data['category']['tags']
        )
        
        return cls(
            original_path=data['original_path'],
            suggested_path=data['suggested_path'],
            action=OrganizationAction(data['action']),
            category=category,
            processing_time=data['processing_time'],
            worker_id=data['worker_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            applied_rules=data['applied_rules'],
            warnings=data['warnings']
        )


@dataclass
class BatchResult:
    """Result of processing a batch of files."""
    batch_id: str
    results: List[AnalysisResult]
    total_files: int
    successful: int
    failed: int
    skipped: int
    processing_time: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        return self.successful / self.total_files if self.total_files > 0 else 0.0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get batch processing statistics."""
        file_types = {}
        actions = {}
        confidence_levels = {}
        
        for result in self.results:
            # Count file types
            file_type = result.category.primary_type.value
            file_types[file_type] = file_types.get(file_type, 0) + 1
            
            # Count actions
            action = result.action.value
            actions[action] = actions.get(action, 0) + 1
            
            # Count confidence levels
            conf_level = result.category.confidence_level.value
            confidence_levels[conf_level] = confidence_levels.get(conf_level, 0) + 1
        
        return {
            'batch_id': self.batch_id,
            'total_files': self.total_files,
            'successful': self.successful,
            'failed': self.failed,
            'skipped': self.skipped,
            'success_rate': self.success_rate,
            'processing_time': self.processing_time,
            'avg_time_per_file': self.processing_time / self.total_files if self.total_files > 0 else 0,
            'file_types': file_types,
            'actions': actions,
            'confidence_levels': confidence_levels,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class SystemHealth:
    """Enhanced system health metrics."""
    gpu_available: bool
    gpu_name: str
    gpu_memory_total: int
    gpu_memory_used: int
    gpu_utilization: float
    cpu_usage: float
    memory_usage: float
    disk_free_gb: float
    disk_usage_percent: float
    active_workers: int
    queue_size: int
    files_processed: int
    files_per_second: float
    errors_count: int
    warnings_count: int
    uptime_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def gpu_memory_usage_percent(self) -> float:
        """GPU memory usage percentage."""
        return (self.gpu_memory_used / self.gpu_memory_total * 100) if self.gpu_memory_total > 0 else 0.0
    
    @property
    def is_healthy(self) -> bool:
        """Overall system health check."""
        return (
            self.cpu_usage < 90 and
            self.memory_usage < 90 and
            self.disk_usage_percent < 95 and
            self.errors_count < 10
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for metrics export."""
        return {
            'gpu_available': self.gpu_available,
            'gpu_name': self.gpu_name,
            'gpu_memory_total': self.gpu_memory_total,
            'gpu_memory_used': self.gpu_memory_used,
            'gpu_utilization': self.gpu_utilization,
            'gpu_memory_usage_percent': self.gpu_memory_usage_percent,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'disk_free_gb': self.disk_free_gb,
            'disk_usage_percent': self.disk_usage_percent,
            'active_workers': self.active_workers,
            'queue_size': self.queue_size,
            'files_processed': self.files_processed,
            'files_per_second': self.files_per_second,
            'errors_count': self.errors_count,
            'warnings_count': self.warnings_count,
            'uptime_seconds': self.uptime_seconds,
            'is_healthy': self.is_healthy,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class OperationHistory:
    """Track file operations for rollback capability."""
    operation_id: str
    timestamp: datetime
    operation_type: str  # move, copy, rename, delete
    source_path: str
    destination_path: Optional[str]
    success: bool
    error_message: Optional[str] = None
    rollback_info: Optional[Dict[str, Any]] = None
    
    def can_rollback(self) -> bool:
        """Check if operation can be rolled back."""
        return self.success and self.rollback_info is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'operation_id': self.operation_id,
            'timestamp': self.timestamp.isoformat(),
            'operation_type': self.operation_type,
            'source_path': self.source_path,
            'destination_path': self.destination_path,
            'success': self.success,
            'error_message': self.error_message,
            'rollback_info': self.rollback_info
        }