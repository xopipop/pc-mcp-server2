#!/usr/bin/env python3
"""
PC Control MCP Server - FastMCP version.
Alternative implementation using the new FastMCP API.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP
from src import (
    setup_logging,
    get_config,
    SecurityManager,
    SystemTools,
    ProcessTools,
    FileTools,
    StructuredLogger,
    __version__
)

# Setup logging
setup_logging()
log = StructuredLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("PC Control MCP Server")

# Initialize components
config = get_config()
security = SecurityManager()
system_tools = SystemTools(security)
process_tools = ProcessTools(security)
file_tools = FileTools(security)

# System Information Tools
@mcp.tool()
async def get_system_info(info_type: str = "all") -> dict:
    """Get system information (hardware, OS, network, etc.)
    
    Args:
        info_type: Type of information: all, basic, cpu, memory, disk, network
    """
    return await system_tools.get_system_info(info_type)

@mcp.tool()
async def get_hardware_info() -> dict:
    """Get detailed hardware information"""
    return await system_tools.get_hardware_info()

@mcp.tool()
async def get_os_info() -> dict:
    """Get operating system information"""
    return await system_tools.get_os_info()

@mcp.tool()
async def get_environment_variables() -> dict:
    """Get environment variables (sensitive values masked)"""
    return await system_tools.get_environment_variables()

@mcp.tool()
async def get_system_uptime() -> dict:
    """Get system uptime information"""
    return await system_tools.get_system_uptime()

@mcp.tool()
async def execute_command(
    command: str,
    shell: bool = True,
    timeout: int | None = None,
    working_directory: str | None = None
) -> dict:
    """Execute a system command (with security validation)
    
    Args:
        command: Command to execute
        shell: Use shell execution
        timeout: Command timeout in seconds
        working_directory: Working directory for command execution
    """
    return await system_tools.execute_command(
        command=command,
        shell=shell,
        timeout=timeout,
        working_directory=working_directory
    )

# Process Management Tools
@mcp.tool()
async def list_processes(filters: dict | None = None) -> dict:
    """List running processes with optional filters
    
    Args:
        filters: Optional filters (name, user, status, min_cpu, min_memory, sort_by, limit)
    """
    return await process_tools.list_processes(filters)

@mcp.tool()
async def get_process_info(pid: int) -> dict:
    """Get detailed information about a process
    
    Args:
        pid: Process ID
    """
    return await process_tools.get_process_info(pid)

@mcp.tool()
async def kill_process(pid: int, signal_type: str | None = None) -> dict:
    """Kill a process by PID
    
    Args:
        pid: Process ID
        signal_type: Signal type (SIGTERM, SIGKILL, SIGINT)
    """
    return await process_tools.kill_process(pid, signal_type)

@mcp.tool()
async def start_process(
    command: str,
    working_directory: str | None = None,
    environment: dict | None = None,
    shell: bool = False,
    capture_output: bool = True
) -> dict:
    """Start a new process
    
    Args:
        command: Command to execute
        working_directory: Working directory
        environment: Environment variables
        shell: Use shell execution
        capture_output: Capture stdout/stderr
    """
    return await process_tools.start_process(
        command=command,
        working_directory=working_directory,
        environment=environment,
        shell=shell,
        capture_output=capture_output
    )

# File Operations Tools
@mcp.tool()
async def read_file(
    path: str,
    encoding: str = "utf-8",
    max_size: int | None = None
) -> dict:
    """Read file contents
    
    Args:
        path: File path
        encoding: Text encoding
        max_size: Maximum file size to read
    """
    return await file_tools.read_file(path, encoding, max_size)

@mcp.tool()
async def write_file(
    path: str,
    content: str,
    encoding: str = "utf-8",
    create_dirs: bool = False,
    append: bool = False
) -> dict:
    """Write content to a file
    
    Args:
        path: File path
        content: Content to write
        encoding: Text encoding
        create_dirs: Create parent directories
        append: Append to file
    """
    return await file_tools.write_file(
        path=path,
        content=content,
        encoding=encoding,
        create_dirs=create_dirs,
        append=append
    )

@mcp.tool()
async def delete_file(path: str, force: bool = False) -> dict:
    """Delete a file
    
    Args:
        path: File path
        force: Force deletion
    """
    return await file_tools.delete_file(path, force)

@mcp.tool()
async def copy_file(
    source: str,
    destination: str,
    overwrite: bool = False,
    preserve_metadata: bool = True
) -> dict:
    """Copy a file
    
    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Overwrite if exists
        preserve_metadata: Preserve file metadata
    """
    return await file_tools.copy_file(
        source=source,
        destination=destination,
        overwrite=overwrite,
        preserve_metadata=preserve_metadata
    )

@mcp.tool()
async def move_file(
    source: str,
    destination: str,
    overwrite: bool = False
) -> dict:
    """Move a file
    
    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Overwrite if exists
    """
    return await file_tools.move_file(
        source=source,
        destination=destination,
        overwrite=overwrite
    )

@mcp.tool()
async def list_directory(
    path: str,
    recursive: bool = False,
    pattern: str | None = None,
    include_hidden: bool = True,
    max_depth: int | None = None
) -> dict:
    """List directory contents
    
    Args:
        path: Directory path
        recursive: List recursively
        pattern: File pattern filter
        include_hidden: Include hidden files
        max_depth: Maximum recursion depth
    """
    return await file_tools.list_directory(
        path=path,
        recursive=recursive,
        pattern=pattern,
        include_hidden=include_hidden,
        max_depth=max_depth
    )

@mcp.tool()
async def create_directory(
    path: str,
    parents: bool = True,
    exist_ok: bool = True
) -> dict:
    """Create a directory
    
    Args:
        path: Directory path
        parents: Create parent directories
        exist_ok: Don't error if exists
    """
    return await file_tools.create_directory(
        path=path,
        parents=parents,
        exist_ok=exist_ok
    )

@mcp.tool()
async def get_file_info(path: str) -> dict:
    """Get detailed file information
    
    Args:
        path: File path
    """
    return await file_tools.get_file_info(path)

@mcp.tool()
async def search_files(
    pattern: str,
    directory: str,
    recursive: bool = True,
    case_sensitive: bool = False,
    file_type: str | None = None
) -> dict:
    """Search for files matching pattern
    
    Args:
        pattern: Search pattern (glob or regex)
        directory: Directory to search in
        recursive: Search recursively
        case_sensitive: Case-sensitive search
        file_type: Filter by type (file, directory)
    """
    return await file_tools.search_files(
        pattern=pattern,
        directory=directory,
        recursive=recursive,
        case_sensitive=case_sensitive,
        file_type=file_type
    )

@mcp.tool()
async def get_disk_usage(path: str) -> dict:
    """Get disk usage for a path
    
    Args:
        path: Path to check
    """
    return await file_tools.get_disk_usage(path)

if __name__ == "__main__":
    log.info(f"PC Control MCP Server v{__version__} (FastMCP) starting...")
    mcp.run(transport="stdio")