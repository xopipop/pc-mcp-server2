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
    ServiceTools
)

# Import AutomationTools conditionally
try:
    from .tools import AutomationTools
    _automation_exports = ['AutomationTools']
except ImportError:
    # AutomationTools requires pyautogui which needs tkinter
    _automation_exports = []

try:
    from .tools import PowerShellTools
    _powershell_exports = ['PowerShellTools']
except ImportError:
    _powershell_exports = []

try:
    from .tools import SchedulerTools
    _scheduler_exports = ['SchedulerTools']
except ImportError:
    _scheduler_exports = []

try:
    from .tools import UIATools
    _uia_exports = ['UIATools']
except ImportError:
    _uia_exports = []

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
    
    # Monitoring
    'MetricsCollector',
    'AlertManager',
    'AlertRule'
] + _registry_exports + _automation_exports
__all__ += _powershell_exports + _scheduler_exports + _uia_exports