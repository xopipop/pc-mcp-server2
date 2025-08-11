#!/usr/bin/env python3
"""
PC Control MCP Server - Main entry point.
"""

import asyncio
import os
import sys
import traceback
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
try:
    from mcp.types import Prompt, PromptArgument
except Exception:
    Prompt = None  # type: ignore
    PromptArgument = None  # type: ignore
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
try:
    from src import NetworkTools  # type: ignore
except Exception:
    NetworkTools = None  # type: ignore
try:
    from src import RegistryTools  # type: ignore
except Exception:
    RegistryTools = None  # type: ignore
try:
    from src import AutomationTools  # type: ignore
except Exception:
    AutomationTools = None  # type: ignore

# Setup logging
setup_logging()
TEST_LOG = None
if '--test-log' in sys.argv:
    try:
        from src.core.logger import enable_test_logging
        TEST_LOG = enable_test_logging(Path(__file__).parent)
        log = StructuredLogger(__name__)
        log.info("Test logging enabled", path=str(TEST_LOG))
    except Exception as _e:
        log = StructuredLogger(__name__)
        log.warning("Failed to enable test logging", error=str(_e))

# PID file management (single-instance helper)
PID_FILE = Path(__file__).parent / 'server.pid'
_HAS_PSUTIL = False
try:
    import psutil  # type: ignore
    _HAS_PSUTIL = True
except Exception:
    _HAS_PSUTIL = False
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
        log.debug("PCControlServer.__init__ called")
        # Use name from config to match Cursor's mcp.json key
        self.server = Server(get_config().server.name)
        log.debug("Server instance created")
        
        self.config = get_config()
        log.debug("Config loaded", config=str(self.config))
        
        self.security = SecurityManager()
        log.debug("SecurityManager created")
        
        # Initialize tools
        self.system_tools = SystemTools(self.security)
        log.debug("SystemTools created")
        
        self.process_tools = ProcessTools(self.security)
        log.debug("ProcessTools created")
        
        self.file_tools = FileTools(self.security)
        log.debug("FileTools created")

        # New tools (Windows-focused)
        self.service_tools = ServiceTools(self.security)
        self.powershell_tools = PowerShellTools(self.security) if PowerShellTools else None
        self.scheduler_tools = SchedulerTools(self.security) if SchedulerTools else None
        self.uia_tools = UIATools(self.security) if UIATools else None
        self.network_tools = NetworkTools(self.security) if NetworkTools else None
        self.registry_tools = RegistryTools(self.security) if RegistryTools else None
        self.automation_tools = AutomationTools(self.security) if AutomationTools else None
        log.debug(
            "Optional tools",
            powershell=bool(self.powershell_tools),
            scheduler=bool(self.scheduler_tools),
            uia=bool(self.uia_tools),
            network=bool(self.network_tools),
            registry=bool(self.registry_tools),
            automation=bool(self.automation_tools),
        )
        
        # Register handlers
        log.debug("Registering tools...")
        self._register_tools()
        log.debug("Tools registered")
        
        log.info(f"PC Control MCP Server v{__version__} initialized")
    
    def _register_tools(self):
        """Register all available tools."""
        
        # System tools
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available tools."""
            tools: List[Tool] = [
                Tool(
                    name="echo",
                    description="Echo back provided text (diagnostics)",
                    inputSchema={
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"]
                    }
                ),
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
                # Extended processes
                Tool(
                    name="set_process_priority",
                    description="Set process priority (or nice on Unix)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pid": {"type": "integer"},
                            "priority": {"oneOf": [{"type": "integer"}, {"type": "string"}]}
                        },
                        "required": ["pid", "priority"]
                    }
                ),
                Tool(
                    name="limit_process_resources",
                    description="Limit process CPU and/or memory usage (best-effort)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pid": {"type": "integer"},
                            "cpu_limit": {"oneOf": [{"type": "integer"}, {"type": "null"}]},
                            "memory_limit": {"oneOf": [{"type": "integer"}, {"type": "null"}]}
                        },
                        "required": ["pid"]
                    }
                ),

                # Network tools
                *([] if not self.network_tools else [
                    Tool(
                        name="get_network_interfaces",
                        description="List network interfaces with stats",
                        inputSchema={
                            "type": "object",
                            "properties": {"include_stats": {"type": "boolean", "default": True}}
                        }
                    ),
                    Tool(
                        name="get_network_stats",
                        description="Get network I/O and connection stats",
                        inputSchema={"type": "object", "properties": {}}
                    ),
                    Tool(
                        name="ping_host",
                        description="Ping a host",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "host": {"type": "string"},
                                "count": {"type": "integer", "default": 4},
                                "timeout": {"type": "integer", "default": 5},
                                "packet_size": {"type": "integer", "default": 32}
                            },
                            "required": ["host"]
                        }
                    )
                ]),

                # Service tools
                Tool(
                    name="list_services",
                    description="List system services",
                    inputSchema={
                        "type": "object",
                        "properties": {"include_drivers": {"type": "boolean", "default": False}}
                    }
                ),
                Tool(
                    name="get_service_info",
                    description="Get detailed information about a service",
                    inputSchema={
                        "type": "object",
                        "properties": {"service_name": {"type": "string"}},
                        "required": ["service_name"]
                    }
                ),
                Tool(
                    name="start_service",
                    description="Start a service",
                    inputSchema={
                        "type": "object",
                        "properties": {"service_name": {"type": "string"}},
                        "required": ["service_name"]
                    }
                ),
                Tool(
                    name="stop_service",
                    description="Stop a service",
                    inputSchema={
                        "type": "object",
                        "properties": {"service_name": {"type": "string"}},
                        "required": ["service_name"]
                    }
                ),
                Tool(
                    name="restart_service",
                    description="Restart a service",
                    inputSchema={
                        "type": "object",
                        "properties": {"service_name": {"type": "string"}},
                        "required": ["service_name"]
                    }
                ),

                # Registry tools (Windows)
                *([] if not self.registry_tools else [
                    Tool(
                        name="read_registry_value",
                        description="Read a Windows registry value",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "key_path": {"type": "string"},
                                "value_name": {"type": "string"}
                            },
                            "required": ["key_path", "value_name"]
                        }
                    ),
                    Tool(
                        name="write_registry_value",
                        description="Write a Windows registry value",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "key_path": {"type": "string"},
                                "value_name": {"type": "string"},
                                "value": {
                                    "oneOf": [
                                        {"type": "string"},
                                        {"type": "number"},
                                        {"type": "integer"},
                                        {"type": "boolean"},
                                        {"type": "array"},
                                        {"type": "object"},
                                        {"type": "null"}
                                    ]
                                },
                                "value_type": {"type": "string", "default": "REG_SZ"}
                            },
                            "required": ["key_path", "value_name", "value"]
                        }
                    )
                ]),

                # GUI automation (PyAutoGUI)
                *([] if not self.automation_tools else [
                    Tool(
                        name="move_mouse",
                        description="Move mouse to position",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "x": {"type": "integer"},
                                "y": {"type": "integer"},
                                "duration": {"type": "number", "default": 0},
                                "relative": {"type": "boolean", "default": False}
                            },
                            "required": ["x", "y"]
                        }
                    ),
                    Tool(
                        name="click_mouse",
                        description="Click mouse at position",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "x": {"oneOf": [{"type": "integer"}, {"type": "null"}]},
                                "y": {"oneOf": [{"type": "integer"}, {"type": "null"}]},
                                "button": {"type": "string", "default": "left"},
                                "clicks": {"type": "integer", "default": 1},
                                "interval": {"type": "number", "default": 0}
                            }
                        }
                    ),
                    Tool(
                        name="type_text",
                        description="Type text into focused element",
                        inputSchema={
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"]
                        }
                    ),
                    Tool(
                        name="take_screenshot",
                        description="Take a screenshot (full or region)",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "region": {"oneOf": [{"type": "array"}, {"type": "null"}]},
                                "save_path": {"oneOf": [{"type": "string"}, {"type": "null"}]}
                            }
                        }
                    )
                ]),

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
            log.info("list_tools called", tool_count=len(tools))
            log.debug("tools", names=[t.name for t in tools])
            return tools

        # Prompts (diagnostic)
        if Prompt is not None and PromptArgument is not None:
            @self.server.list_prompts()
            async def list_prompts() -> List[Any]:  # type: ignore[valid-type]
                try:
                    prompts = [
                        Prompt(
                            name="hello",
                            description="Simple diagnostic prompt",
                            arguments=[
                                PromptArgument(name="name", description="Your name", required=False)
                            ],
                        )
                    ]
                    log.info("list_prompts called", prompt_count=len(prompts))
                    return prompts
                except Exception as _e:  # pragma: no cover
                    log.error("list_prompts failed", exception=_e)
                    return []

        # Expose list_tools callback for self-test logging later
        try:
            self._debug_list_tools_cb = list_tools  # type: ignore[attr-defined]
        except Exception:
            pass
        
        # Tool handlers
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            try:
                log.info(f"Tool call: {name}", tool=name, arguments=arguments)
                
                # System tools
                if name == "echo":
                    return [TextContent(type="text", text=str(arguments.get("text", "")))]
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
                elif name == "set_process_priority":
                    result = await self.process_tools.set_process_priority(
                        pid=arguments["pid"],
                        priority=arguments["priority"],
                    )
                elif name == "limit_process_resources":
                    result = await self.process_tools.limit_process_resources(
                        pid=arguments["pid"],
                        cpu_limit=arguments.get("cpu_limit"),
                        memory_limit=arguments.get("memory_limit"),
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
                
                # Network tools
                elif name == "get_network_interfaces":
                    if not self.network_tools:
                        raise ValueError("NetworkTools is not available on this system")
                    result = await self.network_tools.get_network_interfaces(
                        include_stats=arguments.get("include_stats", True)
                    )
                elif name == "get_network_stats":
                    if not self.network_tools:
                        raise ValueError("NetworkTools is not available on this system")
                    result = await self.network_tools.get_network_stats()
                elif name == "ping_host":
                    if not self.network_tools:
                        raise ValueError("NetworkTools is not available on this system")
                    result = await self.network_tools.ping_host(
                        host=arguments["host"],
                        count=arguments.get("count", 4),
                        timeout=arguments.get("timeout", 5),
                        packet_size=arguments.get("packet_size", 32)
                    )

                # Service tools
                elif name == "list_services":
                    result = await self.service_tools.list_services(
                        include_drivers=arguments.get("include_drivers", False)
                    )
                elif name == "get_service_info":
                    result = await self.service_tools.get_service_info(arguments["service_name"])
                elif name == "start_service":
                    result = await self.service_tools.start_service(arguments["service_name"])
                elif name == "stop_service":
                    result = await self.service_tools.stop_service(arguments["service_name"])
                elif name == "restart_service":
                    result = await self.service_tools.restart_service(arguments["service_name"]) 

                # Registry tools
                elif name == "read_registry_value":
                    if not self.registry_tools:
                        raise ValueError("RegistryTools is not available on this system")
                    result = await self.registry_tools.read_registry_value(
                        key_path=arguments["key_path"],
                        value_name=arguments["value_name"]
                    )
                elif name == "write_registry_value":
                    if not self.registry_tools:
                        raise ValueError("RegistryTools is not available on this system")
                    result = await self.registry_tools.write_registry_value(
                        key_path=arguments["key_path"],
                        value_name=arguments["value_name"],
                        value=arguments["value"],
                        value_type=arguments.get("value_type", "REG_SZ")
                    )

                # Automation tools
                elif name == "move_mouse":
                    if not self.automation_tools:
                        raise ValueError("AutomationTools is not available on this system")
                    result = await self.automation_tools.move_mouse(
                        x=arguments["x"],
                        y=arguments["y"],
                        duration=arguments.get("duration", 0.0),
                        relative=arguments.get("relative", False)
                    )
                elif name == "click_mouse":
                    if not self.automation_tools:
                        raise ValueError("AutomationTools is not available on this system")
                    result = await self.automation_tools.click_mouse(
                        x=arguments.get("x"),
                        y=arguments.get("y"),
                        button=arguments.get("button", "left"),
                        clicks=arguments.get("clicks", 1),
                        interval=arguments.get("interval", 0.0)
                    )
                elif name == "type_text":
                    if not self.automation_tools:
                        raise ValueError("AutomationTools is not available on this system")
                    result = await self.automation_tools.type_text(text=arguments["text"]) 
                elif name == "take_screenshot":
                    if not self.automation_tools:
                        raise ValueError("AutomationTools is not available on this system")
                    result = await self.automation_tools.take_screenshot(
                        region=arguments.get("region"),
                        save_path=arguments.get("save_path")
                    )

                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                # Format result
                # Prefer orjson if available
                text: str
                try:
                    import orjson  # type: ignore
                    pretty = self.config.server.pretty_json if hasattr(self.config, 'server') else False
                    opts = orjson.OPT_NON_STR_KEYS
                    if pretty:
                        opts |= orjson.OPT_INDENT_2
                    text = orjson.dumps(result, option=opts, default=str).decode('utf-8')
                except Exception:
                    import json
                    pretty = self.config.server.pretty_json if hasattr(self.config, 'server') else False
                    text = json.dumps(
                        result,
                        indent=2 if pretty else None,
                        separators=None if pretty else (",", ":"),
                        default=str
                    )
                return [TextContent(type="text", text=text)]
                
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
            log.debug("Creating stdio server...")
            async with stdio_server() as (read_stream, write_stream):
                log.debug("Stdio server created")
                log.info("Stdio server initialized")
                
                log.debug("Running server...")
                # Always provide capability objects (real classes if available, shims otherwise)
                # Provide capabilities using the most compatible signature
                capabilities = None
                # Prepare options
                notification_options = NotificationOptions(
                    tools_changed=True,
                    prompts_changed=True,
                    resources_changed=True,
                    models_changed=True,
                    sampling_chains_changed=True
                )
                experimental_capabilities = ExperimentalCapabilities()

                # Try with notification object and empty experimental dict
                try:
                    capabilities = self.server.get_capabilities(notification_options, {})
                    log.debug("Capabilities obtained with notification object and empty dict")
                except Exception as _e1:
                    log.warning("get_capabilities with object and dict failed, trying with objects", error=str(_e1))
                    experimental_capabilities = ExperimentalCapabilities()
                    try:
                        capabilities = self.server.get_capabilities(notification_options, experimental_capabilities)
                        log.debug("Capabilities obtained with objects")
                    except Exception as _e2:
                        log.warning("get_capabilities with objects failed, trying no-arg", error=str(_e2))
                        try:
                            capabilities = self.server.get_capabilities()
                            log.debug("Capabilities obtained with no-arg")
                        except Exception as _e3:
                            log.warning("get_capabilities no-arg failed, trying with dicts", error=str(_e3))
                            notifications_dict = {
                                "toolsChanged": True,
                                "promptsChanged": True,
                                "resourcesChanged": True,
                                "modelsChanged": True,
                                "samplingChainsChanged": True
                            }
                            experimental_dict = {}
                            try:
                                capabilities = self.server.get_capabilities(notifications_dict, experimental_dict)
                                log.debug("Capabilities obtained with dicts")
                            except Exception as _e4:
                                try:
                                    capabilities = self.server.get_capabilities(notifications_dict)
                                    log.debug("Capabilities obtained with notifications dict only")
                                except Exception as _e5:
                                    log.error("All get_capabilities attempts failed", error=str(_e5))
                                    raise
                log.debug("Capabilities prepared")

                # Proactive self-test to ensure tools are registered
                try:
                    if hasattr(self, '_debug_list_tools_cb'):
                        tools = await self._debug_list_tools_cb()  # type: ignore[misc]
                        log.info("self_test list_tools", tool_count=len(tools))
                        log.debug("self_test tools", names=[t.name for t in tools])
                except Exception as _e:
                    log.warning("self_test list_tools failed", error=str(_e))

                # Try multiple run signatures for compatibility
                try:
                    await self.server.run(read_stream, write_stream)
                except Exception as _e1:
                    log.warning("server.run signature 1 failed, trying with InitializationOptions", error=str(_e1))
                    try:
                        await self.server.run(
                            read_stream,
                            write_stream,
                            InitializationOptions(
                                server_name=self.config.server.name,
                                server_version=self.config.server.version,
                                capabilities=capabilities
                            )
                        )
                    except Exception as _e2:
                        log.error("server.run failed with both signatures", error=str(_e2))
                        raise
                log.debug("Server finished")
        except Exception as e:
            log.error("Error in server.run", exception=e)
            raise


async def main():
    """Main entry point."""
    try:
        # Write PID file if possible
        try:
            PID_FILE.write_text(str(os.getpid()), encoding='utf-8')
        except Exception:
            pass
        log.debug("Creating PCControlServer instance...")
        server = PCControlServer()
        log.debug("Server instance created, starting run...")
        await server.run()
    except KeyboardInterrupt:
        log.info("Server stopped by user")
    except Exception as e:
        full_trace = traceback.format_exc()
        log.error(f"Server error: {e}\nFull traceback:\n{full_trace}", exception=e)
        if hasattr(e, 'exceptions'):
            for i, sub_e in enumerate(e.exceptions):
                log.error(f"Sub-exception {i}: {type(sub_e).__name__}: {sub_e}", exception=sub_e)
                if hasattr(sub_e, '__traceback__'):
                    sub_trace = ''.join(traceback.format_tb(sub_e.__traceback__))
                    log.error(f"Sub-traceback {i}:\n{sub_trace}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        # Cleanup PID file on normal exit
        try:
            if PID_FILE.exists():
                PID_FILE.unlink()
        except Exception:
            pass