#!/usr/bin/env python3
"""
Helios Advanced Configuration System
Loads and validates comprehensive configuration with intelligent defaults
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PerformanceConfig:
    """Performance and resource configuration."""
    io_workers: int = 4
    gpu_workers: int = 2
    batch_size: int = 128
    queue_max_size: int = 10000
    memory_limit_gb: int = 8
    cpu_limit_percent: int = 80


@dataclass
class InferenceConfig:
    """AI inference configuration."""
    runtime: str = "onnx"
    onnx_model_path: str = "helios/models/sentinel_v1.onnx"
    cuda_enabled: bool = True
    fallback_to_cpu: bool = True
    max_sequence_length: int = 512
    confidence_threshold: float = 0.7
    use_context_analysis: bool = True


@dataclass
class OrganizationConfig:
    """File organization configuration."""
    preserve_directory_structure: bool = True
    smart_grouping: bool = True
    skip_system_files: bool = True
    skip_temp_files: bool = True
    create_backups: bool = True
    dry_run_mode: bool = False
    
    # File size limits
    min_size_bytes: int = 1024
    max_size_bytes: int = 10737418240  # 10GB
    skip_empty_files: bool = True
    
    # File age filters
    skip_files_newer_than_days: int = 0
    skip_files_older_than_days: int = 0
    consider_access_time: bool = True
    consider_creation_time: bool = True


@dataclass
class SafetyConfig:
    """Safety and backup configuration."""
    create_backups: bool = True
    backup_location: str = "Backups/File_Operations"
    backup_retention_days: int = 30
    require_confirmation: bool = True
    confirm_large_operations: bool = True
    confirm_destructive_operations: bool = True
    enable_rollback: bool = True
    rollback_retention_days: int = 7
    dry_run_default: bool = False
    show_dry_run_results: bool = True


@dataclass
class ExtensionRule:
    """Configuration for file extension handling."""
    extensions: List[str]
    base_path: str
    smart_categorization: bool = True
    preserve_project_structure: bool = False
    subcategories: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class HeliosConfig:
    """Advanced Helios configuration manager."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager."""
        self.config_path = config_path or "helios/config/helios_config.yaml"
        self.config_data: Dict[str, Any] = {}
        self.extension_rules: Dict[str, ExtensionRule] = {}
        self.skip_rules: Dict[str, Dict[str, Any]] = {}
        self.smart_rules: Dict[str, Dict[str, Any]] = {}
        self.custom_rules: Dict[str, Dict[str, Any]] = {}
        
        # Configuration sections
        self.performance: PerformanceConfig = PerformanceConfig()
        self.inference: InferenceConfig = InferenceConfig()
        self.organization: OrganizationConfig = OrganizationConfig()
        self.safety: SafetyConfig = SafetyConfig()
        
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                logger.warning(f"Config file not found: {self.config_path}. Using defaults.")
                self._create_default_config()
                return
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f)
            
            logger.info(f"✅ Configuration loaded from: {self.config_path}")
            self._parse_config()
            self._validate_config()
            
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            logger.info("Using default configuration")
            self._create_default_config()
    
    def _parse_config(self) -> None:
        """Parse configuration sections."""
        # Performance configuration
        if 'performance' in self.config_data:
            perf_data = self.config_data['performance']
            self.performance = PerformanceConfig(
                io_workers=perf_data.get('io_workers', 4),
                gpu_workers=perf_data.get('gpu_workers', 2),
                batch_size=perf_data.get('batch_size', 128),
                queue_max_size=perf_data.get('queue_max_size', 10000),
                memory_limit_gb=perf_data.get('memory_limit_gb', 8),
                cpu_limit_percent=perf_data.get('cpu_limit_percent', 80)
            )
        
        # Inference configuration
        if 'inference' in self.config_data:
            inf_data = self.config_data['inference']
            self.inference = InferenceConfig(
                runtime=inf_data.get('runtime', 'onnx'),
                onnx_model_path=inf_data.get('onnx_model_path', 'helios/models/sentinel_v1.onnx'),
                cuda_enabled=inf_data.get('cuda_enabled', True),
                fallback_to_cpu=inf_data.get('fallback_to_cpu', True),
                max_sequence_length=inf_data.get('max_sequence_length', 512),
                confidence_threshold=inf_data.get('confidence_threshold', 0.7),
                use_context_analysis=inf_data.get('use_context_analysis', True)
            )
        
        # Organization configuration
        if 'organization' in self.config_data:
            org_data = self.config_data['organization']
            self.organization = OrganizationConfig(
                preserve_directory_structure=org_data.get('preserve_directory_structure', True),
                smart_grouping=org_data.get('smart_grouping', True),
                skip_system_files=org_data.get('skip_system_files', True),
                skip_temp_files=org_data.get('skip_temp_files', True),
                create_backups=org_data.get('create_backups', True),
                dry_run_mode=org_data.get('dry_run_mode', False)
            )
            
            # File size limits
            if 'file_size_limits' in org_data:
                size_limits = org_data['file_size_limits']
                self.organization.min_size_bytes = size_limits.get('min_size_bytes', 1024)
                self.organization.max_size_bytes = size_limits.get('max_size_bytes', 10737418240)
                self.organization.skip_empty_files = size_limits.get('skip_empty_files', True)
        
        # Safety configuration
        if 'safety' in self.config_data:
            safety_data = self.config_data['safety']
            self.safety = SafetyConfig(
                create_backups=safety_data.get('create_backups', True),
                backup_location=safety_data.get('backup_location', 'Backups/File_Operations'),
                backup_retention_days=safety_data.get('backup_retention_days', 30),
                require_confirmation=safety_data.get('require_confirmation', True),
                confirm_large_operations=safety_data.get('confirm_large_operations', True),
                confirm_destructive_operations=safety_data.get('confirm_destructive_operations', True),
                enable_rollback=safety_data.get('enable_rollback', True),
                rollback_retention_days=safety_data.get('rollback_retention_days', 7),
                dry_run_default=safety_data.get('dry_run_default', False),
                show_dry_run_results=safety_data.get('show_dry_run_results', True)
            )
        
        # Parse extension rules
        self._parse_extension_rules()
        
        # Parse skip rules
        self._parse_skip_rules()
        
        # Parse smart rules
        self._parse_smart_rules()
        
        # Parse custom rules
        self._parse_custom_rules()
    
    def _parse_extension_rules(self) -> None:
        """Parse file extension organization rules."""
        if 'organization' not in self.config_data or 'extensions' not in self.config_data['organization']:
            return
        
        extensions_config = self.config_data['organization']['extensions']
        
        for category, config in extensions_config.items():
            if isinstance(config, dict) and 'extensions' in config:
                self.extension_rules[category] = ExtensionRule(
                    extensions=config['extensions'],
                    base_path=config.get('base_path', f'Organized/{category.title()}'),
                    smart_categorization=config.get('smart_categorization', True),
                    preserve_project_structure=config.get('preserve_project_structure', False),
                    subcategories=config.get('subcategories', {})
                )
    
    def _parse_skip_rules(self) -> None:
        """Parse file skip rules."""
        if 'organization' not in self.config_data or 'skip_rules' not in self.config_data['organization']:
            return
        
        self.skip_rules = self.config_data['organization']['skip_rules']
    
    def _parse_smart_rules(self) -> None:
        """Parse smart organization rules."""
        if 'organization' not in self.config_data or 'smart_rules' not in self.config_data['organization']:
            return
        
        self.smart_rules = self.config_data['organization']['smart_rules']
    
    def _parse_custom_rules(self) -> None:
        """Parse custom user rules."""
        if 'organization' not in self.config_data or 'custom_rules' not in self.config_data['organization']:
            return
        
        self.custom_rules = self.config_data['organization']['custom_rules']
    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        # Validate performance settings
        if self.performance.io_workers < 1:
            logger.warning("io_workers must be >= 1, setting to 1")
            self.performance.io_workers = 1
        
        if self.performance.gpu_workers < 1:
            logger.warning("gpu_workers must be >= 1, setting to 1")
            self.performance.gpu_workers = 1
        
        if self.performance.batch_size < 1:
            logger.warning("batch_size must be >= 1, setting to 32")
            self.performance.batch_size = 32
        
        # Validate inference settings
        if not 0.0 <= self.inference.confidence_threshold <= 1.0:
            logger.warning("confidence_threshold must be between 0.0 and 1.0, setting to 0.7")
            self.inference.confidence_threshold = 0.7
        
        # Validate file size limits
        if self.organization.min_size_bytes < 0:
            logger.warning("min_size_bytes must be >= 0, setting to 0")
            self.organization.min_size_bytes = 0
        
        if self.organization.max_size_bytes <= self.organization.min_size_bytes:
            logger.warning("max_size_bytes must be > min_size_bytes, adjusting")
            self.organization.max_size_bytes = self.organization.min_size_bytes + 1024
        
        # Validate model path
        model_path = Path(self.inference.onnx_model_path)
        if not model_path.exists():
            logger.warning(f"ONNX model not found: {self.inference.onnx_model_path}")
    
    def _create_default_config(self) -> None:
        """Create default configuration."""
        logger.info("Creating default configuration")
        self.performance = PerformanceConfig()
        self.inference = InferenceConfig()
        self.organization = OrganizationConfig()
        self.safety = SafetyConfig()
    
    def get_extension_rule(self, extension: str) -> Optional[ExtensionRule]:
        """Get organization rule for file extension."""
        extension = extension.lower()
        
        for category, rule in self.extension_rules.items():
            if extension in [ext.lower() for ext in rule.extensions]:
                return rule
        
        return None
    
    def should_skip_file(self, file_path: str, file_size: int, file_age_days: int) -> Tuple[bool, str]:
        """Check if file should be skipped based on skip rules."""
        file_name = Path(file_path).name.lower()
        file_ext = Path(file_path).suffix.lower()
        
        # Check system files
        if self.skip_rules.get('system_files', {}).get('enabled', True):
            system_patterns = self.skip_rules['system_files'].get('patterns', [])
            system_extensions = self.skip_rules['system_files'].get('extensions', [])
            
            if any(pattern.lower() in file_name for pattern in system_patterns):
                return True, "System file pattern match"
            
            if file_ext in [ext.lower() for ext in system_extensions]:
                return True, "System file extension"
        
        # Check development files
        if self.skip_rules.get('dev_files', {}).get('enabled', True):
            dev_patterns = self.skip_rules['dev_files'].get('patterns', [])
            dev_extensions = self.skip_rules['dev_files'].get('extensions', [])
            
            if any(pattern.lower() in file_name for pattern in dev_patterns):
                return True, "Development file pattern match"
            
            if file_ext in [ext.lower() for ext in dev_extensions]:
                return True, "Development file extension"
        
        # Check temporary files
        if self.skip_rules.get('temp_files', {}).get('enabled', True):
            temp_patterns = self.skip_rules['temp_files'].get('patterns', [])
            temp_age_limit = self.skip_rules['temp_files'].get('age_days', 7)
            
            if any(pattern.lower() in file_name for pattern in temp_patterns):
                return True, "Temporary file pattern match"
            
            if file_age_days > temp_age_limit and any(temp in file_name for temp in ['temp', 'tmp']):
                return True, f"Old temporary file (>{temp_age_limit} days)"
        
        # Check file size limits
        if file_size < self.organization.min_size_bytes:
            return True, f"File too small (<{self.organization.min_size_bytes} bytes)"
        
        if file_size > self.organization.max_size_bytes:
            return True, f"File too large (>{self.organization.max_size_bytes} bytes)"
        
        # Check file age limits
        if self.organization.skip_files_newer_than_days > 0:
            if file_age_days < self.organization.skip_files_newer_than_days:
                return True, f"File too new (<{self.organization.skip_files_newer_than_days} days)"
        
        if self.organization.skip_files_older_than_days > 0:
            if file_age_days > self.organization.skip_files_older_than_days:
                return True, f"File too old (>{self.organization.skip_files_older_than_days} days)"
        
        return False, ""
    
    def is_project_preservation_enabled(self) -> bool:
        """Check if project preservation is enabled."""
        return self.smart_rules.get('project_preservation', {}).get('enabled', True)
    
    def is_game_preservation_enabled(self) -> bool:
        """Check if game preservation is enabled."""
        return self.smart_rules.get('game_preservation', {}).get('enabled', True)
    
    def get_project_indicators(self) -> List[str]:
        """Get list of project indicator files."""
        return self.smart_rules.get('project_preservation', {}).get('indicators', [
            'package.json', 'requirements.txt', 'pom.xml', 'Cargo.toml', 
            '.git', 'makefile', 'Makefile', '.gitignore', 'README.md'
        ])
    
    def get_game_patterns(self) -> List[str]:
        """Get list of game directory patterns."""
        return self.smart_rules.get('game_preservation', {}).get('patterns', [
            'game', 'games', 'steam', 'origin', 'uplay', 'epic', 'gog'
        ])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'performance': {
                'io_workers': self.performance.io_workers,
                'gpu_workers': self.performance.gpu_workers,
                'batch_size': self.performance.batch_size,
                'queue_max_size': self.performance.queue_max_size,
                'memory_limit_gb': self.performance.memory_limit_gb,
                'cpu_limit_percent': self.performance.cpu_limit_percent
            },
            'inference': {
                'runtime': self.inference.runtime,
                'onnx_model_path': self.inference.onnx_model_path,
                'cuda_enabled': self.inference.cuda_enabled,
                'fallback_to_cpu': self.inference.fallback_to_cpu,
                'max_sequence_length': self.inference.max_sequence_length,
                'confidence_threshold': self.inference.confidence_threshold,
                'use_context_analysis': self.inference.use_context_analysis
            },
            'organization': {
                'preserve_directory_structure': self.organization.preserve_directory_structure,
                'smart_grouping': self.organization.smart_grouping,
                'skip_system_files': self.organization.skip_system_files,
                'skip_temp_files': self.organization.skip_temp_files,
                'create_backups': self.organization.create_backups,
                'dry_run_mode': self.organization.dry_run_mode,
                'min_size_bytes': self.organization.min_size_bytes,
                'max_size_bytes': self.organization.max_size_bytes,
                'skip_empty_files': self.organization.skip_empty_files
            },
            'safety': {
                'create_backups': self.safety.create_backups,
                'backup_location': self.safety.backup_location,
                'backup_retention_days': self.safety.backup_retention_days,
                'require_confirmation': self.safety.require_confirmation,
                'enable_rollback': self.safety.enable_rollback,
                'dry_run_default': self.safety.dry_run_default
            }
        }
    
    def save_config(self, path: Optional[str] = None) -> None:
        """Save current configuration to file."""
        save_path = path or self.config_path
        
        try:
            config_file = Path(save_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)
            
            logger.info(f"✅ Configuration saved to: {save_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save config: {e}")


def load_config(config_path: Optional[str] = None) -> HeliosConfig:
    """Load Helios configuration."""
    return HeliosConfig(config_path)