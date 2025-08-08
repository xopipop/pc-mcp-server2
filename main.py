#!/usr/bin/env python3
"""
PC Control MCP Server - Main entry point.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
_HAS_MCP_CAP_MODELS = False
NotificationOptions = None  # type: ignore
ExperimentalCapabilities = None  # type: ignore
try:
    # Preferred location (newer versions)
    from mcp.server.models import NotificationOptions as _NO1, ExperimentalCapabilities as _EC1  # type: ignore
    NotificationOptions = _NO1  # type: ignore
    ExperimentalCapabilities = _EC1  # type: ignore
    _HAS_MCP_CAP_MODELS = True
except Exception:
    try:
        # Fallback location (some versions expose via mcp.types)
        from mcp.types import NotificationOptions as _NO2, ExperimentalCapabilities as _EC2  # type: ignore
        NotificationOptions = _NO2  # type: ignore
        ExperimentalCapabilities = _EC2  # type: ignore
        _HAS_MCP_CAP_MODELS = True
    except Exception:
        _HAS_MCP_CAP_MODELS = False

# Define compatibility shims if models are unavailable
if not _HAS_MCP_CAP_MODELS:
    class NotificationOptions:  # type: ignore[no-redef]
        def __init__(self,
                     tools_changed: bool = False,
                     prompts_changed: bool = False,
                     resources_changed: bool = False,
                     models_changed: bool = False,
                     sampling_chains_changed: bool = False,
                     **kwargs):
            self.tools_changed = tools_changed
            self.prompts_changed = prompts_changed
            self.resources_changed = resources_changed
            self.models_changed = models_changed
            self.sampling_chains_changed = sampling_chains_changed
        
        def __getattr__(self, _name: str):
            # Default to False for any unknown change flags
            return False
    
    class ExperimentalCapabilities:  # type: ignore[no-redef]
        def __init__(self, **_kwargs):
            pass
        
        def __getattr__(self, _name: str):
            # Default to None for unknown experimental fields
            return None
from mcp.types import Tool, TextContent, ImageContent
from pydantic import BaseModel, Field

from src import (
    setup_logging,
    get_config,
    SecurityManager,
    SystemTools,
    ProcessTools,
    FileTools,
    ServiceTools,
    StructuredLogger,
    __version__
)

# Optional tool imports (server must start even if these are missing)
try:
    from src import PowerShellTools  # type: ignore
except Exception:
    PowerShellTools = None  # type: ignore
try:
    from src import SchedulerTools  # type: ignore
except Exception:
    SchedulerTools = None  # type: ignore
try:
    from src import UIATools  # type: ignore
except Exception:
    UIATools = None  # type: ignore

# Setup logging
setup_logging()
TEST_LOG = None
if '--test-log' in sys.argv:
    try:
        from src.core.logger import enable_test_logging
        TEST_LOG = enable_test_logging(Path(__file__).parent)
        print(f"DEBUG: Test logging enabled -> {TEST_LOG}")
    except Exception as _e:
        print(f"DEBUG: Failed to enable test logging: {_e}")
log = StructuredLogger(__name__)

# Tool parameter models
class SystemInfoParams(BaseModel):
    info_type: Optional[str] = Field(
        None,
        description="Type of information: all, basic, cpu, memory, disk, network"
    )

class ExecuteCommandParams(BaseModel):
    command: str = Field(..., description="Command to execute")
    shell: bool = Field(True, description="Use shell execution")
    timeout: Optional[int] = Field(None, description="Command timeout in seconds")
    working_directory: Optional[str] = Field(None, description="Working directory")

class ProcessListParams(BaseModel):
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Filters: name, user, status, min_cpu, min_memory, sort_by, limit"
    )

class ProcessInfoParams(BaseModel):
    pid: int = Field(..., description="Process ID")

class ProcessKillParams(BaseModel):
    pid: int = Field(..., description="Process ID")
    signal_type: Optional[str] = Field(
        None,
        description="Signal type: SIGTERM, SIGKILL, SIGINT"
    )

class ProcessStartParams(BaseModel):
    command: str = Field(..., description="Command to execute")
    working_directory: Optional[str] = Field(None, description="Working directory")
    environment: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    shell: bool = Field(False, description="Use shell execution")
    capture_output: bool = Field(True, description="Capture stdout/stderr")

class FileReadParams(BaseModel):
    path: str = Field(..., description="File path")
    encoding: str = Field("utf-8", description="Text encoding")
    max_size: Optional[int] = Field(None, description="Maximum file size to read")

class FileWriteParams(BaseModel):
    path: str = Field(..., description="File path")
    content: str = Field(..., description="Content to write")
    encoding: str = Field("utf-8", description="Text encoding")
    create_dirs: bool = Field(False, description="Create parent directories")
    append: bool = Field(False, description="Append to file")

class FileDeleteParams(BaseModel):
    path: str = Field(..., description="File path")
    force: bool = Field(False, description="Force deletion")

class FileCopyParams(BaseModel):
    source: str = Field(..., description="Source file path")
    destination: str = Field(..., description="Destination file path")
    overwrite: bool = Field(False, description="Overwrite if exists")
    preserve_metadata: bool = Field(True, description="Preserve file metadata")

class FileMoveParams(BaseModel):
    source: str = Field(..., description="Source file path")
    destination: str = Field(..., description="Destination file path")
    overwrite: bool = Field(False, description="Overwrite if exists")

class DirectoryListParams(BaseModel):
    path: str = Field(..., description="Directory path")
    recursive: bool = Field(False, description="List recursively")
    pattern: Optional[str] = Field(None, description="File pattern filter")
    include_hidden: bool = Field(True, description="Include hidden files")
    max_depth: Optional[int] = Field(None, description="Maximum recursion depth")

class DirectoryCreateParams(BaseModel):
    path: str = Field(..., description="Directory path")
    parents: bool = Field(True, description="Create parent directories")
    exist_ok: bool = Field(True, description="Don't error if exists")

class FileSearchParams(BaseModel):
    pattern: str = Field(..., description="Search pattern (glob or regex)")
    directory: str = Field(..., description="Directory to search in")
    recursive: bool = Field(True, description="Search recursively")
    case_sensitive: bool = Field(False, description="Case-sensitive search")
    file_type: Optional[str] = Field(None, description="Filter by type: file, directory")


class PCControlServer:
    """PC Control MCP Server implementation."""
    
    def __init__(self):
        print("DEBUG: PCControlServer.__init__() called")
        self.server = Server("pc-control-mcp")
        print("DEBUG: Server instance created")
        
        self.config = get_config()
        print(f"DEBUG: Config loaded: {self.config}")
        
        self.security = SecurityManager()
        print("DEBUG: SecurityManager created")
        
        # Initialize tools
        self.system_tools = SystemTools(self.security)
        print("DEBUG: SystemTools created")
        
        self.process_tools = ProcessTools(self.security)
        print("DEBUG: ProcessTools created")
        
        self.file_tools = FileTools(self.security)
        print("DEBUG: FileTools created")

        # New tools (Windows-focused)
        self.service_tools = ServiceTools(self.security)
        self.powershell_tools = PowerShellTools(self.security) if PowerShellTools else None
        self.scheduler_tools = SchedulerTools(self.security) if SchedulerTools else None
        self.uia_tools = UIATools(self.security) if UIATools else None
        print(f"DEBUG: Optional tools -> PowerShell: {self.powershell_tools is not None}, "
              f"Scheduler: {self.scheduler_tools is not None}, UIA: {self.uia_tools is not None}")
        
        # Register handlers
        print("DEBUG: Registering tools...")
        self._register_tools()
        print("DEBUG: Tools registered")
        
        log.info(f"PC Control MCP Server v{__version__} initialized")
    
    def _register_tools(self):
        """Register all available tools."""
        
        # System tools
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available tools."""
            return [
                # System Information
                Tool(
                    name="get_system_info",
                    description="Get system information (hardware, OS, network, etc.)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "info_type": {
                                "type": "string",
                                "enum": ["all", "basic", "cpu", "memory", "disk", "network"],
                                "description": "Type of information to retrieve"
                            }
                        }
                    }
                ),

                # UI Automation (Windows)
                *([] if not self.uia_tools else [Tool(
                    name="uia_focus_window",
                    description="Focus a window by name/class (Windows UIA)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "class_name": {"type": "string"}
                        }
                    }
                ),
                Tool(
                    name="uia_click",
                    description="Click a UI element by name/control type (Windows UIA)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "control_type": {"type": "string"}
                        }
                    }
                ),
                Tool(
                    name="uia_type_text",
                    description="Type text into focused/target control (Windows UIA)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "name": {"type": "string"}
                        },
                        "required": ["text"]
                    }
                )]),
                Tool(
                    name="get_hardware_info",
                    description="Get detailed hardware information",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="get_os_info",
                    description="Get operating system information",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="get_environment_variables",
                    description="Get environment variables (sensitive values masked)",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="get_system_uptime",
                    description="Get system uptime information",
                    inputSchema={"type": "object", "properties": {}}
                ),
                Tool(
                    name="execute_command",
                    description="Execute a system command (with security validation)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Command to execute"},
                            "shell": {"type": "boolean", "default": True},
                            "timeout": {"type": "integer", "description": "Timeout in seconds"},
                            "working_directory": {"type": "string"}
                        },
                        "required": ["command"]
                    }
                ),

                # PowerShell (safe)
                *([] if not self.powershell_tools else [Tool(
                    name="invoke_powershell",
                    description="Safely execute a PowerShell script block (Windows only)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "script": {"type": "string"},
                            "timeout": {"type": "integer", "default": 30},
                            "safe_mode": {"type": "boolean", "default": True}
                        },
                        "required": ["script"]
                    }
                )]),

                # Scheduler
                *([] if not self.scheduler_tools else [Tool(
                    name="scheduler_create_task",
                    description="Create a Windows scheduled task (admin)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "command": {"type": "string"},
                            "schedule": {"type": "string", "default": "ONCE"},
                            "start_time": {"type": "string"},
                            "start_date": {"type": "string"},
                            "run_as": {"type": "string"},
                            "password": {"type": "string"}
                        },
                        "required": ["name", "command"]
                    }
                ),
                Tool(
                    name="scheduler_run_task",
                    description="Run a Windows scheduled task now (admin)",
                    inputSchema={
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"]
                    }
                ),
                Tool(
                    name="scheduler_delete_task",
                    description="Delete a Windows scheduled task (admin)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "force": {"type": "boolean", "default": False}
                        },
                        "required": ["name"]
                    }
                ),
                Tool(
                    name="scheduler_query_task",
                    description="Query a Windows scheduled task (admin)",
                    inputSchema={
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"]
                    }
                )]),
                
                # Process Management
                Tool(
                    name="list_processes",
                    description="List running processes with optional filters",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filters": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "user": {"type": "string"},
                                    "status": {"type": "string"},
                                    "min_cpu": {"type": "number"},
                                    "min_memory": {"type": "number"},
                                    "sort_by": {"type": "string"},
                                    "limit": {"type": "integer"}
                                }
                            }
                        }
                    }
                ),
                Tool(
                    name="get_process_info",
                    description="Get detailed information about a process",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pid": {"type": "integer", "description": "Process ID"}
                        },
                        "required": ["pid"]
                    }
                ),
                Tool(
                    name="kill_process",
                    description="Kill a process by PID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pid": {"type": "integer"},
                            "signal_type": {
                                "type": "string",
                                "enum": ["SIGTERM", "SIGKILL", "SIGINT"]
                            }
                        },
                        "required": ["pid"]
                    }
                ),
                Tool(
                    name="start_process",
                    description="Start a new process",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"},
                            "working_directory": {"type": "string"},
                            "environment": {"type": "object"},
                            "shell": {"type": "boolean", "default": False},
                            "capture_output": {"type": "boolean", "default": True}
                        },
                        "required": ["command"]
                    }
                ),
                Tool(
                    name="suspend_process",
                    description="Suspend (pause) a process",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pid": {"type": "integer"}
                        },
                        "required": ["pid"]
                    }
                ),
                Tool(
                    name="resume_process",
                    description="Resume a suspended process",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pid": {"type": "integer"}
                        },
                        "required": ["pid"]
                    }
                ),
                Tool(
                    name="get_process_resources",
                    description="Get resource usage for a process",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pid": {"type": "integer"}
                        },
                        "required": ["pid"]
                    }
                ),
                Tool(
                    name="find_processes_by_name",
                    description="Find processes by name",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "exact": {"type": "boolean", "default": False}
                        },
                        "required": ["name"]
                    }
                ),
                
                # File Operations
                Tool(
                    name="read_file",
                    description="Read file contents",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "encoding": {"type": "string", "default": "utf-8"},
                            "max_size": {"type": "integer"}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="write_file",
                    description="Write content to a file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                            "encoding": {"type": "string", "default": "utf-8"},
                            "create_dirs": {"type": "boolean", "default": False},
                            "append": {"type": "boolean", "default": False}
                        },
                        "required": ["path", "content"]
                    }
                ),
                Tool(
                    name="delete_file",
                    description="Delete a file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "force": {"type": "boolean", "default": False}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="copy_file",
                    description="Copy a file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                            "overwrite": {"type": "boolean", "default": False},
                            "preserve_metadata": {"type": "boolean", "default": True}
                        },
                        "required": ["source", "destination"]
                    }
                ),
                Tool(
                    name="move_file",
                    description="Move a file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "destination": {"type": "string"},
                            "overwrite": {"type": "boolean", "default": False}
                        },
                        "required": ["source", "destination"]
                    }
                ),
                Tool(
                    name="list_directory",
                    description="List directory contents",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "recursive": {"type": "boolean", "default": False},
                            "pattern": {"type": "string"},
                            "include_hidden": {"type": "boolean", "default": True},
                            "max_depth": {"type": "integer"}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="create_directory",
                    description="Create a directory",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "parents": {"type": "boolean", "default": True},
                            "exist_ok": {"type": "boolean", "default": True}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="get_file_info",
                    description="Get detailed file information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="search_files",
                    description="Search for files matching pattern",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string"},
                            "directory": {"type": "string"},
                            "recursive": {"type": "boolean", "default": True},
                            "case_sensitive": {"type": "boolean", "default": False},
                            "file_type": {"type": "string", "enum": ["file", "directory"]}
                        },
                        "required": ["pattern", "directory"]
                    }
                ),
                Tool(
                    name="get_disk_usage",
                    description="Get disk usage for a path",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"}
                        },
                        "required": ["path"]
                    }
                )
            ]
        
        # Tool handlers
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            try:
                log.info(f"Tool call: {name}", tool=name, arguments=arguments)
                
                # System tools
                if name == "get_system_info":
                    params = SystemInfoParams(**arguments)
                    result = await self.system_tools.get_system_info(params.info_type)
                
                elif name == "get_hardware_info":
                    result = await self.system_tools.get_hardware_info()
                
                elif name == "get_os_info":
                    result = await self.system_tools.get_os_info()
                
                elif name == "get_environment_variables":
                    result = await self.system_tools.get_environment_variables()
                
                elif name == "get_system_uptime":
                    result = await self.system_tools.get_system_uptime()
                
                elif name == "execute_command":
                    params = ExecuteCommandParams(**arguments)
                    result = await self.system_tools.execute_command(
                        command=params.command,
                        shell=params.shell,
                        timeout=params.timeout,
                        working_directory=params.working_directory
                    )

                # PowerShell
                elif name == "invoke_powershell":
                    if not self.powershell_tools:
                        raise ValueError("PowerShellTools is not available on this system")
                    result = await self.powershell_tools.invoke(
                        script=arguments["script"],
                        timeout=arguments.get("timeout", 30),
                        safe_mode=arguments.get("safe_mode", True)
                    )

                # Scheduler
                elif name == "scheduler_create_task":
                    if not self.scheduler_tools:
                        raise ValueError("SchedulerTools is not available on this system")
                    result = await self.scheduler_tools.create_task(
                        name=arguments["name"],
                        command=arguments["command"],
                        schedule=arguments.get("schedule", "ONCE"),
                        start_time=arguments.get("start_time"),
                        start_date=arguments.get("start_date"),
                        run_as=arguments.get("run_as"),
                        password=arguments.get("password"),
                    )
                elif name == "scheduler_run_task":
                    if not self.scheduler_tools:
                        raise ValueError("SchedulerTools is not available on this system")
                    result = await self.scheduler_tools.run_task(arguments["name"])
                elif name == "scheduler_delete_task":
                    if not self.scheduler_tools:
                        raise ValueError("SchedulerTools is not available on this system")
                    result = await self.scheduler_tools.delete_task(
                        name=arguments["name"],
                        force=arguments.get("force", False)
                    )
                elif name == "scheduler_query_task":
                    if not self.scheduler_tools:
                        raise ValueError("SchedulerTools is not available on this system")
                    result = await self.scheduler_tools.query_task(arguments["name"])

                # UIA
                elif name == "uia_focus_window":
                    if not self.uia_tools:
                        raise ValueError("UIATools is not available on this system")
                    result = await self.uia_tools.focus_window(
                        name=arguments.get("name"),
                        class_name=arguments.get("class_name")
                    )
                elif name == "uia_click":
                    if not self.uia_tools:
                        raise ValueError("UIATools is not available on this system")
                    result = await self.uia_tools.click(
                        name=arguments.get("name"),
                        control_type=arguments.get("control_type")
                    )
                elif name == "uia_type_text":
                    if not self.uia_tools:
                        raise ValueError("UIATools is not available on this system")
                    result = await self.uia_tools.type_text(
                        text=arguments["text"],
                        name=arguments.get("name")
                    )
                
                # Process tools
                elif name == "list_processes":
                    params = ProcessListParams(**arguments)
                    result = await self.process_tools.list_processes(params.filters)
                
                elif name == "get_process_info":
                    params = ProcessInfoParams(**arguments)
                    result = await self.process_tools.get_process_info(params.pid)
                
                elif name == "kill_process":
                    params = ProcessKillParams(**arguments)
                    result = await self.process_tools.kill_process(
                        pid=params.pid,
                        signal_type=params.signal_type
                    )
                
                elif name == "start_process":
                    params = ProcessStartParams(**arguments)
                    result = await self.process_tools.start_process(
                        command=params.command,
                        working_directory=params.working_directory,
                        environment=params.environment,
                        shell=params.shell,
                        capture_output=params.capture_output
                    )
                
                elif name == "suspend_process":
                    params = ProcessInfoParams(**arguments)
                    result = await self.process_tools.suspend_process(params.pid)
                
                elif name == "resume_process":
                    params = ProcessInfoParams(**arguments)
                    result = await self.process_tools.resume_process(params.pid)
                
                elif name == "get_process_resources":
                    params = ProcessInfoParams(**arguments)
                    result = await self.process_tools.get_process_resources(params.pid)
                
                elif name == "find_processes_by_name":
                    result = await self.process_tools.find_processes_by_name(
                        name=arguments["name"],
                        exact=arguments.get("exact", False)
                    )
                
                # File tools
                elif name == "read_file":
                    params = FileReadParams(**arguments)
                    result = await self.file_tools.read_file(
                        path=params.path,
                        encoding=params.encoding,
                        max_size=params.max_size
                    )
                
                elif name == "write_file":
                    params = FileWriteParams(**arguments)
                    result = await self.file_tools.write_file(
                        path=params.path,
                        content=params.content,
                        encoding=params.encoding,
                        create_dirs=params.create_dirs,
                        append=params.append
                    )
                
                elif name == "delete_file":
                    params = FileDeleteParams(**arguments)
                    result = await self.file_tools.delete_file(
                        path=params.path,
                        force=params.force
                    )
                
                elif name == "copy_file":
                    params = FileCopyParams(**arguments)
                    result = await self.file_tools.copy_file(
                        source=params.source,
                        destination=params.destination,
                        overwrite=params.overwrite,
                        preserve_metadata=params.preserve_metadata
                    )
                
                elif name == "move_file":
                    params = FileMoveParams(**arguments)
                    result = await self.file_tools.move_file(
                        source=params.source,
                        destination=params.destination,
                        overwrite=params.overwrite
                    )
                
                elif name == "list_directory":
                    params = DirectoryListParams(**arguments)
                    result = await self.file_tools.list_directory(
                        path=params.path,
                        recursive=params.recursive,
                        pattern=params.pattern,
                        include_hidden=params.include_hidden,
                        max_depth=params.max_depth
                    )
                
                elif name == "create_directory":
                    params = DirectoryCreateParams(**arguments)
                    result = await self.file_tools.create_directory(
                        path=params.path,
                        parents=params.parents,
                        exist_ok=params.exist_ok
                    )
                
                elif name == "get_file_info":
                    result = await self.file_tools.get_file_info(arguments["path"])
                
                elif name == "search_files":
                    params = FileSearchParams(**arguments)
                    result = await self.file_tools.search_files(
                        pattern=params.pattern,
                        directory=params.directory,
                        recursive=params.recursive,
                        case_sensitive=params.case_sensitive,
                        file_type=params.file_type
                    )
                
                elif name == "get_disk_usage":
                    result = await self.file_tools.get_disk_usage(arguments["path"])
                
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                # Format result
                import json
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, default=str)
                )]
                
            except Exception as e:
                log.error(f"Tool execution failed: {name}", exception=e)
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
    
    async def run(self):
        """Run the MCP server."""
        log.info("Starting PC Control MCP Server...")
        try:
            print(f"DEBUG: Creating stdio server...")
            async with stdio_server() as (read_stream, write_stream):
                print(f"DEBUG: Stdio server created, streams: read={read_stream}, write={write_stream}")
                log.info("Stdio server initialized")
                
                print(f"DEBUG: Running server...")
                # Always provide capability objects (real classes if available, shims otherwise)
                capabilities = self.server.get_capabilities(
                    NotificationOptions(),
                    {}
                )

                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name=self.config.server.name,
                        server_version=self.config.server.version,
                        capabilities=capabilities
                    )
                )
                print(f"DEBUG: Server finished")
        except Exception as e:
            print(f"DEBUG: Error in server.run: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise


async def main():
    """Main entry point."""
    try:
        print("DEBUG: Creating PCControlServer instance...")
        server = PCControlServer()
        print("DEBUG: Server instance created, starting run...")
        await server.run()
    except KeyboardInterrupt:
        print("DEBUG: KeyboardInterrupt received")
        log.info("Server stopped by user")
    except Exception as e:
        print(f"DEBUG: Exception in main: {type(e).__name__}: {e}")
        log.error(f"Server error: {e}", exception=e)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())