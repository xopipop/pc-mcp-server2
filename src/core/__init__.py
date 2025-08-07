"""
Core functionality for PC Control MCP Server.
"""

from .exceptions import (
    PCControlException,
    SecurityException,
    AuthenticationException,
    AuthorizationException,
    ValidationException,
    ConfigurationException,
    SystemException,
    ProcessException,
    FileOperationException,
    NetworkException,
    ServiceException,
    RegistryException,
    AutomationException,
    MonitoringException,
    RateLimitException,
    TimeoutException,
    ResourceLimitException
)

from .logger import (
    StructuredLogger,
    AuditLogger,
    setup_logging
)

from .config import (
    Config,
    ConfigManager,
    get_config,
    set_config,
    ServerConfig,
    SecurityConfig,
    GuiAutomationConfig,
    MonitoringConfig,
    ProcessManagementConfig,
    NetworkConfig,
    FileOperationsConfig
)

from .security import (
    SecurityManager,
    User,
    AuthResult,
    Operation,
    SessionManager,
    RateLimiter,
    InputValidator
)

__all__ = [
    # Exceptions
    'PCControlException',
    'SecurityException',
    'AuthenticationException',
    'AuthorizationException',
    'ValidationException',
    'ConfigurationException',
    'SystemException',
    'ProcessException',
    'FileOperationException',
    'NetworkException',
    'ServiceException',
    'RegistryException',
    'AutomationException',
    'MonitoringException',
    'RateLimitException',
    'TimeoutException',
    'ResourceLimitException',
    
    # Logger
    'StructuredLogger',
    'AuditLogger',
    'setup_logging',
    
    # Config
    'Config',
    'ConfigManager',
    'get_config',
    'set_config',
    'ServerConfig',
    'SecurityConfig',
    'GuiAutomationConfig',
    'MonitoringConfig',
    'ProcessManagementConfig',
    'NetworkConfig',
    'FileOperationsConfig',
    
    # Security
    'SecurityManager',
    'User',
    'AuthResult',
    'Operation',
    'SessionManager',
    'RateLimiter',
    'InputValidator',
]