"""
Tools for PC Control MCP Server.
"""

from .system_tools import SystemTools
from .process_tools import ProcessTools, ProcessInfo
from .file_tools import FileTools, FileInfo
from .network_tools import NetworkTools, NetworkInfo
from .service_tools import ServiceTools, ServiceInfo

# Only import on Windows
try:
    from .registry_tools import RegistryTools
    __all_registry__ = ['RegistryTools']
except Exception:
    __all_registry__ = []

# Import automation tools conditionally
try:
    from .automation_tools import AutomationTools
    __all_automation__ = ['AutomationTools']
except ImportError:
    __all_automation__ = []

# New optional tools
try:
    from .powershell_tools import PowerShellTools
    __all_powershell__ = ['PowerShellTools']
except Exception:
    __all_powershell__ = []

try:
    from .scheduler_tools import SchedulerTools
    __all_scheduler__ = ['SchedulerTools']
except Exception:
    __all_scheduler__ = []

try:
    from .uia_tools import UIATools
    __all_uia__ = ['UIATools']
except Exception:
    __all_uia__ = []

__all__ = [
    'SystemTools',
    'ProcessTools',
    'ProcessInfo', 
    'FileTools',
    'FileInfo',
    'NetworkTools',
    'NetworkInfo',
    'ServiceTools',
    'ServiceInfo'
] + __all_registry__ + __all_automation__
__all__ += __all_powershell__ + __all_scheduler__ + __all_uia__