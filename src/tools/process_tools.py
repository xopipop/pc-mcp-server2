"""
Process management tools for PC Control MCP Server.
"""

import os
import signal
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import psutil

from ..core import (
    StructuredLogger,
    SecurityManager,
    Operation,
    ProcessException,
    ValidationException,
    ResourceLimitException,
    get_config
)
from ..utils.platform_utils import is_windows, is_linux, is_macos

log = StructuredLogger(__name__)


class ProcessInfo:
    """Process information container."""
    
    def __init__(self, process: psutil.Process):
        self.process = process
        self._info_cache = {}
    
    def get_info(self) -> Dict[str, Any]:
        """Get process information with caching."""
        try:
            # Basic info that rarely changes
            if 'basic' not in self._info_cache:
                self._info_cache['basic'] = {
                    'pid': self.process.pid,
                    'name': self.process.name(),
                    'exe': self.process.exe() if self.process.exe() else None,
                    'cmdline': self.process.cmdline(),
                    'create_time': datetime.fromtimestamp(self.process.create_time()).isoformat(),
                    'ppid': self.process.ppid(),
                    'status': self.process.status(),
                    'username': self.process.username() if hasattr(self.process, 'username') else None,
                    'cwd': self.process.cwd() if self.process.cwd() else None
                }
            
            # Dynamic info
            cpu_percent = self.process.cpu_percent(interval=0.1)
            memory_info = self.process.memory_info()
            
            return {
                **self._info_cache['basic'],
                'cpu_percent': cpu_percent,
                'memory_info': {
                    'rss': memory_info.rss,
                    'vms': memory_info.vms,
                    'percent': self.process.memory_percent()
                },
                'num_threads': self.process.num_threads(),
                'num_fds': self.process.num_fds() if hasattr(self.process, 'num_fds') else None,
                'io_counters': self._get_io_counters(),
                'connections': self._get_connections(),
                'open_files': self._get_open_files(),
                'children': [child.pid for child in self.process.children()],
                'nice': self.process.nice() if hasattr(self.process, 'nice') else None
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            raise ProcessException(f"Failed to get process info: {str(e)}")
    
    def _get_io_counters(self) -> Optional[Dict[str, Any]]:
        """Get I/O counters if available."""
        try:
            io = self.process.io_counters()
            return {
                'read_count': io.read_count,
                'write_count': io.write_count,
                'read_bytes': io.read_bytes,
                'write_bytes': io.write_bytes
            }
        except (AttributeError, psutil.AccessDenied):
            return None
    
    def _get_connections(self) -> List[Dict[str, Any]]:
        """Get process network connections."""
        try:
            connections = []
            for conn in self.process.connections():
                connections.append({
                    'fd': conn.fd,
                    'family': conn.family.name,
                    'type': conn.type.name,
                    'laddr': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    'raddr': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    'status': conn.status
                })
            return connections
        except (psutil.AccessDenied, AttributeError):
            return []
    
    def _get_open_files(self) -> List[Dict[str, Any]]:
        """Get open files."""
        try:
            files = []
            for file in self.process.open_files():
                files.append({
                    'path': file.path,
                    'fd': file.fd
                })
            return files
        except (psutil.AccessDenied, AttributeError):
            return []


class ProcessTools:
    """Process management tools."""
    
    def __init__(self, security_manager: Optional[SecurityManager] = None):
        self.security = security_manager
        self.config = get_config()
        self._process_cache = {}
    
    async def list_processes(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List running processes with optional filters.
        
        Args:
            filters: Optional filters dictionary with keys:
                    - name: Process name filter (str)
                    - user: Username filter (str)
                    - status: Process status filter (str)
                    - min_cpu: Minimum CPU usage (float)
                    - min_memory: Minimum memory usage (float)
                    - sort_by: Sort field (str) - cpu, memory, name, pid
                    - limit: Maximum number of results (int)
        
        Returns:
            List of process information dictionaries
        """
        log.debug("Listing processes", filters=filters)
        
        try:
            # Security check
            if self.security:
                operation = Operation('read', 'process_list', {'filters': filters})
                # Check authorization would be done at the server level
            
            # Get all processes
            processes = []
            
            # iterating processes
            for proc in psutil.process_iter(['pid', 'name', 'username', 'status', 
                                            'cpu_percent', 'memory_percent', 
                                            'create_time', 'ppid']):
                try:
                    pinfo = proc.info
                    
                    # Apply filters
                    if filters.get('name') and filters['name'].lower() not in pinfo['name'].lower():
                        continue
                    
                    if filters.get('user') and pinfo.get('username') != filters['user']:
                        continue
                    
                    if filters.get('status') and pinfo.get('status') != filters['status']:
                        continue
                    
                    if filters.get('min_cpu') and (pinfo.get('cpu_percent') or 0) < filters['min_cpu']:
                        continue
                    
                    if filters.get('min_memory') and (pinfo.get('memory_percent') or 0) < filters['min_memory']:
                        continue
                    
                    processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'],
                        'username': pinfo.get('username'),
                        'cpu_percent': pinfo.get('cpu_percent', 0),
                        'memory_percent': pinfo.get('memory_percent', 0),
                        'status': pinfo.get('status')
                    })
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort results
            sort_by = filters.get('sort_by', 'pid')
            reverse = sort_by in ['cpu_percent', 'memory_percent']
            
            if sort_by == 'cpu':
                sort_by = 'cpu_percent'
            elif sort_by == 'memory':
                sort_by = 'memory_percent'
            
            processes.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
            
            # Apply limit
            if filters.get('limit'):
                processes = processes[:filters['limit']]
            
            return processes
            
        except Exception as e:
            log.error(f"Failed to list processes: {e}", exception=e)
            raise ProcessException(f"Failed to list processes: {str(e)}")
    
    async def get_process_info(self, pid: int) -> Dict[str, Any]:
        """Get detailed information about a specific process.
        
        Args:
            pid: Process ID
            
        Returns:
            Dictionary with process information
        """
        try:
            # Validate PID
            if pid <= 0:
                raise ValidationException("Invalid PID: must be positive integer")
            
            process = psutil.Process(pid)
            proc_info = ProcessInfo(process)
            return proc_info.get_info()
            
        except psutil.NoSuchProcess:
            raise ProcessException(f"Process with PID {pid} not found")
        except psutil.AccessDenied:
            raise ProcessException(f"Access denied to process with PID {pid}")
        except Exception as e:
            log.error(f"Failed to get process info for PID {pid}: {e}", exception=e)
            raise ProcessException(f"Failed to get process info: {str(e)}")
    
    async def kill_process(self, pid: int, signal_type: Optional[str] = None) -> Dict[str, Any]:
        """Kill a process.
        
        Args:
            pid: Process ID
            signal_type: Signal type ('SIGTERM', 'SIGKILL', 'SIGINT')
                        Default is SIGTERM
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Validate PID
            if pid <= 0:
                raise ValidationException("Invalid PID: must be positive integer")
            
            # Security check
            if self.security:
                operation = Operation('delete', 'process', {'pid': pid, 'signal': signal_type})
                # Authorization check would be done at server level
            
            # Check if process exists
            try:
                process = psutil.Process(pid)
                process_name = process.name()
            except psutil.NoSuchProcess:
                raise ProcessException(f"Process with PID {pid} not found")
            
            # Check blocked processes
            blocked_processes = self.config.get('process_management.blocked_processes', [])
            if process_name in blocked_processes:
                raise ProcessException(f"Process '{process_name}' is protected and cannot be killed")
            
            # Determine signal
            if is_windows():
                # Windows doesn't support POSIX signals
                process.terminate()
                signal_used = "TERMINATE"
            else:
                if signal_type == 'SIGKILL':
                    sig = signal.SIGKILL
                elif signal_type == 'SIGINT':
                    sig = signal.SIGINT
                else:
                    sig = signal.SIGTERM
                
                os.kill(pid, sig)
                signal_used = signal_type or 'SIGTERM'
            
            # Wait a bit to check if process terminated
            await asyncio.sleep(0.5)
            
            # Check if process still exists
            still_running = psutil.pid_exists(pid)
            
            return {
                'pid': pid,
                'process_name': process_name,
                'signal': signal_used,
                'success': not still_running,
                'still_running': still_running
            }
            
        except ProcessException:
            raise
        except Exception as e:
            log.error(f"Failed to kill process {pid}: {e}", exception=e)
            raise ProcessException(f"Failed to kill process: {str(e)}")
    
    async def start_process(self, command: Union[str, List[str]], 
                          working_directory: Optional[str] = None,
                          environment: Optional[Dict[str, str]] = None,
                          shell: bool = False,
                          capture_output: bool = True) -> Dict[str, Any]:
        """Start a new process.
        
        Args:
            command: Command to execute (string or list of arguments)
            working_directory: Working directory for the process
            environment: Environment variables
            shell: Whether to use shell execution
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            Dictionary with process information
        """
        try:
            # Security validation
            if self.security:
                if isinstance(command, str):
                    validated_command = self.security.validate_input('command', command)
                else:
                    validated_command = command
                
                operation = Operation('write', 'process', {
                    'command': validated_command,
                    'working_directory': working_directory
                })
                # Authorization check would be done at server level
            else:
                validated_command = command
            
            # Check allowed processes
            allowed_processes = self.config.get('process_management.allowed_processes', [])
            if allowed_processes:
                cmd_name = validated_command if isinstance(validated_command, str) else validated_command[0]
                if not any(allowed in cmd_name for allowed in allowed_processes):
                    raise ProcessException(f"Process '{cmd_name}' is not in allowed list")
            
            # Prepare environment
            env = os.environ.copy()
            if environment:
                env.update(environment)
            
            # Start process
            if capture_output:
                if shell and isinstance(validated_command, list):
                    validated_command = ' '.join(validated_command)
                
                process = await asyncio.create_subprocess_shell(
                    validated_command if shell else ' '.join(validated_command) if isinstance(validated_command, list) else validated_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=working_directory,
                    env=env
                )
                
                # Get initial output (non-blocking)
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=0.5
                    )
                    stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ''
                    stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ''
                except asyncio.TimeoutError:
                    stdout_text = ''
                    stderr_text = ''
            else:
                # Start without capturing output
                import subprocess
                process = subprocess.Popen(
                    validated_command,
                    shell=shell,
                    cwd=working_directory,
                    env=env
                )
                stdout_text = ''
                stderr_text = ''
            
            return {
                'pid': process.pid,
                'command': validated_command,
                'working_directory': working_directory or os.getcwd(),
                'started': True,
                'stdout': stdout_text,
                'stderr': stderr_text
            }
            
        except ProcessException:
            raise
        except Exception as e:
            log.error(f"Failed to start process: {e}", exception=e)
            raise ProcessException(f"Failed to start process: {str(e)}")
    
    async def suspend_process(self, pid: int) -> Dict[str, Any]:
        """Suspend (pause) a process.
        
        Args:
            pid: Process ID
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Validate PID
            if pid <= 0:
                raise ValidationException("Invalid PID: must be positive integer")
            
            process = psutil.Process(pid)
            process_name = process.name()
            
            # Suspend process
            process.suspend()
            
            # Verify suspension
            await asyncio.sleep(0.1)
            status = process.status()
            
            return {
                'pid': pid,
                'process_name': process_name,
                'suspended': status in [psutil.STATUS_STOPPED, 'stopped'],
                'status': status
            }
            
        except psutil.NoSuchProcess:
            raise ProcessException(f"Process with PID {pid} not found")
        except psutil.AccessDenied:
            raise ProcessException(f"Access denied to process with PID {pid}")
        except Exception as e:
            log.error(f"Failed to suspend process {pid}: {e}", exception=e)
            raise ProcessException(f"Failed to suspend process: {str(e)}")
    
    async def resume_process(self, pid: int) -> Dict[str, Any]:
        """Resume a suspended process.
        
        Args:
            pid: Process ID
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Validate PID
            if pid <= 0:
                raise ValidationException("Invalid PID: must be positive integer")
            
            process = psutil.Process(pid)
            process_name = process.name()
            
            # Resume process
            process.resume()
            
            # Verify resumption
            await asyncio.sleep(0.1)
            status = process.status()
            
            return {
                'pid': pid,
                'process_name': process_name,
                'resumed': status not in [psutil.STATUS_STOPPED, 'stopped'],
                'status': status
            }
            
        except psutil.NoSuchProcess:
            raise ProcessException(f"Process with PID {pid} not found")
        except psutil.AccessDenied:
            raise ProcessException(f"Access denied to process with PID {pid}")
        except Exception as e:
            log.error(f"Failed to resume process {pid}: {e}", exception=e)
            raise ProcessException(f"Failed to resume process: {str(e)}")
    
    async def get_process_resources(self, pid: int) -> Dict[str, Any]:
        """Get resource usage for a process.
        
        Args:
            pid: Process ID
            
        Returns:
            Dictionary with resource usage information
        """
        try:
            # Validate PID
            if pid <= 0:
                raise ValidationException("Invalid PID: must be positive integer")
            
            process = psutil.Process(pid)
            
            # Get CPU times
            cpu_times = process.cpu_times()
            
            # Get memory info
            memory_info = process.memory_info()
            memory_full = process.memory_full_info() if hasattr(process, 'memory_full_info') else None
            
            # Get I/O counters
            try:
                io_counters = process.io_counters()
                io_stats = {
                    'read_count': io_counters.read_count,
                    'write_count': io_counters.write_count,
                    'read_bytes': io_counters.read_bytes,
                    'write_bytes': io_counters.write_bytes
                }
            except (AttributeError, psutil.AccessDenied):
                io_stats = None
            
            # Get context switches
            try:
                ctx_switches = process.num_ctx_switches()
                context_switches = {
                    'voluntary': ctx_switches.voluntary,
                    'involuntary': ctx_switches.involuntary
                }
            except (AttributeError, psutil.AccessDenied):
                context_switches = None
            
            return {
                'pid': pid,
                'name': process.name(),
                'cpu': {
                    'percent': process.cpu_percent(interval=0.1),
                    'times': {
                        'user': cpu_times.user,
                        'system': cpu_times.system,
                        'children_user': getattr(cpu_times, 'children_user', 0),
                        'children_system': getattr(cpu_times, 'children_system', 0)
                    },
                    'affinity': process.cpu_affinity() if hasattr(process, 'cpu_affinity') else None
                },
                'memory': {
                    'rss': memory_info.rss,
                    'vms': memory_info.vms,
                    'percent': process.memory_percent(),
                    'uss': memory_full.uss if memory_full else None,
                    'pss': memory_full.pss if memory_full else None
                },
                'io': io_stats,
                'context_switches': context_switches,
                'num_threads': process.num_threads(),
                'num_fds': process.num_fds() if hasattr(process, 'num_fds') else None,
                'nice_priority': process.nice() if hasattr(process, 'nice') else None
            }
            
        except psutil.NoSuchProcess:
            raise ProcessException(f"Process with PID {pid} not found")
        except psutil.AccessDenied:
            raise ProcessException(f"Access denied to process with PID {pid}")
        except Exception as e:
            log.error(f"Failed to get process resources for PID {pid}: {e}", exception=e)
            raise ProcessException(f"Failed to get process resources: {str(e)}")
    
    async def find_processes_by_name(self, name: str, exact: bool = False) -> List[Dict[str, Any]]:
        """Find processes by name.
        
        Args:
            name: Process name to search for
            exact: Whether to use exact match (default: substring match)
            
        Returns:
            List of matching processes
        """
        try:
            # Validate input
            if self.security:
                name = self.security.validate_input('process_name', name)
            
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    pinfo = proc.info
                    process_name = pinfo['name']
                    
                    # Check name match
                    if exact:
                        match = process_name == name
                    else:
                        match = name.lower() in process_name.lower()
                    
                    # Also check exe and cmdline
                    if not match and not exact:
                        exe = pinfo.get('exe', '')
                        if exe and name.lower() in exe.lower():
                            match = True
                        else:
                            cmdline = ' '.join(pinfo.get('cmdline', []))
                            if cmdline and name.lower() in cmdline.lower():
                                match = True
                    
                    if match:
                        processes.append({
                            'pid': pinfo['pid'],
                            'name': process_name,
                            'exe': pinfo.get('exe'),
                            'cmdline': pinfo.get('cmdline', [])
                        })
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return processes
            
        except Exception as e:
            log.error(f"Failed to find processes by name '{name}': {e}", exception=e)
            raise ProcessException(f"Failed to find processes: {str(e)}")
    
    async def set_process_priority(self, pid: int, priority: Union[int, str]) -> Dict[str, Any]:
        """Set process priority/nice value.
        
        Args:
            pid: Process ID
            priority: Priority value (platform-specific) or string:
                     'low', 'below_normal', 'normal', 'above_normal', 'high', 'realtime'
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Validate PID
            if pid <= 0:
                raise ValidationException("Invalid PID: must be positive integer")
            
            process = psutil.Process(pid)
            process_name = process.name()
            
            # Convert string priority to numeric value
            if isinstance(priority, str):
                if is_windows():
                    priority_map = {
                        'low': psutil.IDLE_PRIORITY_CLASS,
                        'below_normal': psutil.BELOW_NORMAL_PRIORITY_CLASS,
                        'normal': psutil.NORMAL_PRIORITY_CLASS,
                        'above_normal': psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                        'high': psutil.HIGH_PRIORITY_CLASS,
                        'realtime': psutil.REALTIME_PRIORITY_CLASS
                    }
                else:
                    # Unix nice values (inverted: lower = higher priority)
                    priority_map = {
                        'low': 19,
                        'below_normal': 10,
                        'normal': 0,
                        'above_normal': -5,
                        'high': -10,
                        'realtime': -20
                    }
                
                if priority not in priority_map:
                    raise ValidationException(f"Invalid priority: {priority}")
                
                priority_value = priority_map[priority]
            else:
                priority_value = priority
            
            # Set priority
            old_priority = process.nice()
            process.nice(priority_value)
            new_priority = process.nice()
            
            return {
                'pid': pid,
                'process_name': process_name,
                'old_priority': old_priority,
                'new_priority': new_priority,
                'success': True
            }
            
        except psutil.NoSuchProcess:
            raise ProcessException(f"Process with PID {pid} not found")
        except psutil.AccessDenied:
            raise ProcessException(f"Access denied to process with PID {pid}")
        except Exception as e:
            log.error(f"Failed to set process priority for PID {pid}: {e}", exception=e)
            raise ProcessException(f"Failed to set process priority: {str(e)}")
    
    async def limit_process_resources(self, pid: int, 
                                    cpu_limit: Optional[int] = None,
                                    memory_limit: Optional[int] = None) -> Dict[str, Any]:
        """Limit process resource usage (platform-specific).
        
        Args:
            pid: Process ID
            cpu_limit: CPU usage limit in percentage
            memory_limit: Memory limit in MB
            
        Returns:
            Dictionary with operation result
        """
        try:
            # This is platform-specific and requires special privileges
            # For now, we'll just check if limits would be exceeded
            
            process = psutil.Process(pid)
            process_name = process.name()
            
            # Get current usage
            cpu_percent = process.cpu_percent(interval=0.5)
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            warnings = []
            
            if cpu_limit and cpu_percent > cpu_limit:
                warnings.append(f"CPU usage ({cpu_percent:.1f}%) exceeds limit ({cpu_limit}%)")
            
            if memory_limit and memory_mb > memory_limit:
                warnings.append(f"Memory usage ({memory_mb:.1f}MB) exceeds limit ({memory_limit}MB)")
            
            return {
                'pid': pid,
                'process_name': process_name,
                'current_cpu_percent': cpu_percent,
                'current_memory_mb': memory_mb,
                'cpu_limit': cpu_limit,
                'memory_limit': memory_limit,
                'warnings': warnings,
                'note': 'Resource limiting requires platform-specific implementation'
            }
            
        except psutil.NoSuchProcess:
            raise ProcessException(f"Process with PID {pid} not found")
        except Exception as e:
            log.error(f"Failed to limit process resources for PID {pid}: {e}", exception=e)
            raise ProcessException(f"Failed to limit process resources: {str(e)}")