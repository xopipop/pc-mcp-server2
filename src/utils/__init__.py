"""
Utility functions for PC Control MCP Server.
"""

from .platform_utils import (
    get_platform,
    is_windows,
    is_linux,
    is_macos,
    is_admin,
    get_system_info,
    get_home_directory,
    get_temp_directory,
    get_config_directory,
    get_log_directory,
    normalize_path,
    which,
    get_environment_variables,
    set_environment_variable,
    get_shell,
    get_path_separator,
    get_line_separator,
    supports_color,
    get_cpu_count,
    get_memory_page_size,
    ensure_directory,
    safe_remove,
    get_startup_directory
)

__all__ = [
    'get_platform',
    'is_windows',
    'is_linux',
    'is_macos',
    'is_admin',
    'get_system_info',
    'get_home_directory',
    'get_temp_directory',
    'get_config_directory',
    'get_log_directory',
    'normalize_path',
    'which',
    'get_environment_variables',
    'set_environment_variable',
    'get_shell',
    'get_path_separator',
    'get_line_separator',
    'supports_color',
    'get_cpu_count',
    'get_memory_page_size',
    'ensure_directory',
    'safe_remove',
    'get_startup_directory'
]