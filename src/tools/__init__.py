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

# Import automation tools
from .automation_tools import AutomationTools

__all__ = [
    'SystemTools',
    'ProcessTools',
    'ProcessInfo', 
    'FileTools',
    'FileInfo',
    'NetworkTools',
    'NetworkInfo',
    'ServiceTools',
    'ServiceInfo',
    'AutomationTools'
] + __all_registry__