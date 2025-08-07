"""
PC Control MCP Server - A secure and powerful system control server.
"""

__version__ = "2.0.0"
__author__ = "PC Control MCP Team"

from .core import (
    # Exceptions
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
    ResourceLimitException,
    
    # Core components
    StructuredLogger,
    AuditLogger,
    setup_logging,
    ConfigManager,
    get_config,
    SecurityManager,
    User,
    Operation
)

from .tools import (
    SystemTools,
    ProcessTools,
    FileTools,
    NetworkTools,
    ServiceTools,
    AutomationTools
)

# Conditional import for Windows-only tools
try:
    from .tools import RegistryTools
    _registry_exports = ['RegistryTools']
except ImportError:
    _registry_exports = []

from .monitoring import (
    MetricsCollector,
    AlertManager,
    AlertRule
)

__all__ = [
    # Version
    '__version__',
    '__author__',
    
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
    
    # Core
    'StructuredLogger',
    'AuditLogger',
    'setup_logging',
    'ConfigManager',
    'get_config',
    'SecurityManager',
    'User',
    'Operation',
    
    # Tools
    'SystemTools',
    'ProcessTools',
    'FileTools',
    'NetworkTools',
    'ServiceTools',
    'AutomationTools',
    
    # Monitoring
    'MetricsCollector',
    'AlertManager',
    'AlertRule'
] + _registry_exports