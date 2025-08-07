"""
Platform-specific utilities for PC Control MCP Server.
"""

import sys
import platform
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..core import StructuredLogger

log = StructuredLogger(__name__)


def get_platform() -> str:
    """Get current platform identifier.
    
    Returns:
        Platform identifier: 'windows', 'linux', 'darwin'
    """
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    elif system == "darwin":
        return "darwin"
    else:
        return system


def is_windows() -> bool:
    """Check if running on Windows."""
    return get_platform() == "windows"


def is_linux() -> bool:
    """Check if running on Linux."""
    return get_platform() == "linux"


def is_macos() -> bool:
    """Check if running on macOS."""
    return get_platform() == "darwin"


def is_admin() -> bool:
    """Check if running with administrator/root privileges."""
    if is_windows():
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0


def get_system_info() -> Dict[str, Any]:
    """Get basic system information."""
    return {
        "platform": get_platform(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "is_admin": is_admin()
    }


def get_home_directory() -> Path:
    """Get user home directory."""
    return Path.home()


def get_temp_directory() -> Path:
    """Get system temporary directory."""
    if is_windows():
        return Path(os.environ.get('TEMP', os.environ.get('TMP', '/tmp')))
    else:
        return Path('/tmp')


def get_config_directory() -> Path:
    """Get configuration directory for PC Control MCP."""
    if is_windows():
        config_dir = Path(os.environ.get('APPDATA', '')) / 'PCControlMCP'
    elif is_macos():
        config_dir = Path.home() / 'Library' / 'Application Support' / 'PCControlMCP'
    else:
        config_dir = Path.home() / '.config' / 'pc_control_mcp'
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_log_directory() -> Path:
    """Get log directory for PC Control MCP."""
    config_dir = get_config_directory()
    log_dir = config_dir / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def normalize_path(path: str) -> str:
    """Normalize path for current platform.
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized path
    """
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)
    path = os.path.normpath(path)
    return path


def which(program: str) -> Optional[str]:
    """Find program in PATH.
    
    Args:
        program: Program name to find
        
    Returns:
        Full path to program or None if not found
    """
    import shutil
    return shutil.which(program)


def get_environment_variables() -> Dict[str, str]:
    """Get all environment variables."""
    return dict(os.environ)


def set_environment_variable(name: str, value: str):
    """Set environment variable.
    
    Args:
        name: Variable name
        value: Variable value
    """
    os.environ[name] = value
    log.info(f"Set environment variable: {name}")


def get_shell() -> str:
    """Get default shell for current platform."""
    if is_windows():
        return os.environ.get('COMSPEC', 'cmd.exe')
    else:
        return os.environ.get('SHELL', '/bin/bash')


def get_path_separator() -> str:
    """Get PATH separator for current platform."""
    return os.pathsep


def get_line_separator() -> str:
    """Get line separator for current platform."""
    return os.linesep


def supports_color() -> bool:
    """Check if terminal supports color output."""
    if is_windows():
        # Windows 10+ supports ANSI colors
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    else:
        # Check if terminal supports color
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


def get_cpu_count() -> int:
    """Get number of CPU cores."""
    return os.cpu_count() or 1


def get_memory_page_size() -> int:
    """Get system memory page size."""
    try:
        return os.sysconf('SC_PAGE_SIZE')
    except (AttributeError, ValueError):
        return 4096  # Default to 4KB


def ensure_directory(path: Path) -> Path:
    """Ensure directory exists.
    
    Args:
        path: Directory path
        
    Returns:
        Directory path
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_remove(path: Path) -> bool:
    """Safely remove file or directory.
    
    Args:
        path: Path to remove
        
    Returns:
        True if removed successfully
    """
    try:
        path = Path(path)
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            import shutil
            shutil.rmtree(path)
        return True
    except Exception as e:
        log.error(f"Failed to remove {path}: {e}")
        return False


def get_startup_directory() -> Path:
    """Get startup directory for auto-start applications."""
    if is_windows():
        import winreg
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
            )
            startup_path = winreg.QueryValueEx(key, "Startup")[0]
            winreg.CloseKey(key)
            return Path(startup_path)
        except Exception:
            return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    elif is_macos():
        return Path.home() / "Library" / "LaunchAgents"
    else:
        return Path.home() / ".config" / "autostart"