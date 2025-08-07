"""
Configuration management for PC Control MCP Server.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, field_validator, ValidationError
import yaml
from dotenv import load_dotenv

from .exceptions import ConfigurationException
from .logger import StructuredLogger

log = StructuredLogger(__name__)


class AuthenticationConfig(BaseModel):
    """Authentication configuration."""
    type: str = Field(default="none", pattern="^(none|basic|token)$")
    token_expiry: int = Field(default=3600, gt=0)


class AuthorizationConfig(BaseModel):
    """Authorization configuration."""
    allowed_commands: List[str] = Field(default_factory=list)
    blocked_paths: List[str] = Field(default_factory=list)
    max_file_size: int = Field(default=104857600, gt=0)  # 100MB
    command_timeout: int = Field(default=30, gt=0)


class AuditConfig(BaseModel):
    """Audit configuration."""
    enabled: bool = Field(default=True)
    log_all_operations: bool = Field(default=True)
    retention_days: int = Field(default=30, gt=0)


class SecurityConfig(BaseModel):
    """Security configuration."""
    enabled: bool = Field(default=True)
    authentication: AuthenticationConfig = Field(default_factory=AuthenticationConfig)
    authorization: AuthorizationConfig = Field(default_factory=AuthorizationConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)


class ImageRecognitionConfig(BaseModel):
    """Image recognition configuration."""
    enabled: bool = Field(default=True)
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class GuiAutomationConfig(BaseModel):
    """GUI automation configuration."""
    enabled: bool = Field(default=True)
    safe_mode: bool = Field(default=True)
    failsafe: bool = Field(default=True)
    min_delay: float = Field(default=0.1, ge=0.0)
    max_screen_resolution: List[int] = Field(default=[1920, 1080])
    screenshot_directory: str = Field(default="~/.pc_control_mcp/screenshots")
    image_recognition: ImageRecognitionConfig = Field(default_factory=ImageRecognitionConfig)
    
    @field_validator('screenshot_directory')
    @classmethod
    def expand_screenshot_directory(cls, v):
        return str(Path(v).expanduser())


class MetricsConfig(BaseModel):
    """Metrics configuration."""
    cpu_threshold: int = Field(default=80, ge=0, le=100)
    memory_threshold: int = Field(default=90, ge=0, le=100)
    disk_threshold: int = Field(default=85, ge=0, le=100)


class AlertsConfig(BaseModel):
    """Alerts configuration."""
    enabled: bool = Field(default=True)
    email: bool = Field(default=False)
    webhook: bool = Field(default=False)
    log: bool = Field(default=True)


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    enabled: bool = Field(default=True)
    interval: int = Field(default=5, gt=0)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)


class ResourceLimitsConfig(BaseModel):
    """Resource limits configuration."""
    cpu_percent: int = Field(default=100, ge=0, le=100)
    memory_mb: int = Field(default=1024, gt=0)


class ProcessManagementConfig(BaseModel):
    """Process management configuration."""
    max_processes: int = Field(default=100, gt=0)
    allowed_processes: List[str] = Field(default_factory=list)
    blocked_processes: List[str] = Field(default_factory=list)
    resource_limits: ResourceLimitsConfig = Field(default_factory=ResourceLimitsConfig)


class NetworkConfig(BaseModel):
    """Network configuration."""
    allowed_ports: List[int] = Field(default_factory=list)
    blocked_ports: List[int] = Field(default_factory=list)
    interface_monitoring: bool = Field(default=True)
    traffic_analysis: bool = Field(default=False)


class FileOperationsConfig(BaseModel):
    """File operations configuration."""
    allowed_paths: List[str] = Field(default_factory=list)
    blocked_paths: List[str] = Field(default_factory=lambda: [
        "/etc", "/sys", "/proc", 
        "C:\\Windows\\System32", "C:\\Program Files"
    ])
    max_file_size: int = Field(default=104857600, gt=0)  # 100MB
    allowed_extensions: List[str] = Field(default_factory=list)
    blocked_extensions: List[str] = Field(default_factory=lambda: [
        ".exe", ".dll", ".sys", ".bat", ".cmd"
    ])


class ServerConfig(BaseModel):
    """Server configuration."""
    name: str = Field(default="pc-control-mcp")
    version: str = Field(default="2.0.0")
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    max_connections: int = Field(default=10, gt=0)


class Config(BaseModel):
    """Main configuration model."""
    server: ServerConfig = Field(default_factory=ServerConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    gui_automation: GuiAutomationConfig = Field(default_factory=GuiAutomationConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    process_management: ProcessManagementConfig = Field(default_factory=ProcessManagementConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    file_operations: FileOperationsConfig = Field(default_factory=FileOperationsConfig)


class ConfigManager:
    """Configuration manager for PC Control MCP Server."""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file. If not provided,
                        will look for config/default.yaml
        """
        self.config_path = self._resolve_config_path(config_path)
        self.config = self._load_config()
        self._apply_env_overrides()
        
    def _resolve_config_path(self, config_path: Optional[Union[str, Path]]) -> Path:
        """Resolve configuration file path."""
        if config_path:
            path = Path(config_path)
            if path.exists():
                return path
            else:
                raise ConfigurationException(f"Configuration file not found: {path}")
        
        # Look for default configuration
        default_paths = [
            Path("config/default.yaml"),
            Path(__file__).parent.parent.parent / "config" / "default.yaml",
            Path.home() / ".pc_control_mcp" / "config.yaml"
        ]
        
        for path in default_paths:
            if path.exists():
                log.info(f"Using configuration file: {path}")
                return path
        
        # No configuration file found, will use defaults
        log.warning("No configuration file found, using defaults")
        return None
    
    def _load_config(self) -> Config:
        """Load configuration from file."""
        if self.config_path:
            try:
                with open(self.config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    return Config(**config_data)
            except (yaml.YAMLError, ValidationError) as e:
                raise ConfigurationException(f"Failed to load configuration: {e}")
        else:
            # Use default configuration
            return Config()
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        load_dotenv()
        
        # Override configuration with environment variables
        env_mappings = {
            'PC_CONTROL_LOG_LEVEL': ('server', 'log_level'),
            'PC_CONTROL_MAX_CONNECTIONS': ('server', 'max_connections'),
            'PC_CONTROL_SECURITY_ENABLED': ('security', 'enabled'),
            'PC_CONTROL_AUTH_TYPE': ('security', 'authentication', 'type'),
            'PC_CONTROL_GUI_ENABLED': ('gui_automation', 'enabled'),
            'PC_CONTROL_MONITORING_ENABLED': ('monitoring', 'enabled'),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_config_value(config_path, value)
    
    def _set_config_value(self, path: tuple, value: str):
        """Set configuration value by path."""
        obj = self.config
        for key in path[:-1]:
            obj = getattr(obj, key)
        
        # Convert value to appropriate type
        field_type = obj.__fields__[path[-1]].type_
        if field_type == bool:
            value = value.lower() in ('true', '1', 'yes', 'on')
        elif field_type == int:
            value = int(value)
        elif field_type == float:
            value = float(value)
        
        setattr(obj, path[-1], value)
        log.info(f"Configuration override: {'.'.join(path)} = {value}")
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path.
        
        Args:
            path: Dot-separated path (e.g., 'server.log_level')
            default: Default value if path not found
            
        Returns:
            Configuration value
        """
        try:
            obj = self.config
            for key in path.split('.'):
                obj = getattr(obj, key)
            return obj
        except AttributeError:
            return default
    
    def reload(self):
        """Reload configuration from file."""
        log.info("Reloading configuration")
        self.config = self._load_config()
        self._apply_env_overrides()
    
    def validate(self) -> bool:
        """Validate configuration.
        
        Returns:
            True if configuration is valid
        """
        try:
            # Pydantic handles validation automatically
            self.config.dict()
            return True
        except ValidationError as e:
            log.error(f"Configuration validation failed: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration as dictionary
        """
        return self.config.dict()
    
    def save(self, path: Optional[Union[str, Path]] = None):
        """Save current configuration to file.
        
        Args:
            path: Path to save configuration. If not provided,
                  will use current config_path
        """
        save_path = path or self.config_path
        if not save_path:
            raise ConfigurationException("No path specified for saving configuration")
        
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
        
        log.info(f"Configuration saved to: {save_path}")


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def set_config(config_manager: ConfigManager):
    """Set global configuration manager instance."""
    global _config_manager
    _config_manager = config_manager