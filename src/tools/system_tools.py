"""
System information and monitoring tools for PC Control MCP Server.
"""

import os
import sys
import platform
import socket
import subprocess
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import psutil

from ..core import (
    StructuredLogger, 
    SecurityManager, 
    Operation,
    SystemException,
    TimeoutException,
    get_config
)
from ..utils.platform_utils import (
    get_platform, 
    is_windows, 
    is_linux,
    is_macos,
    get_system_info as get_basic_system_info
)

log = StructuredLogger(__name__)


class SystemTools:
    """System information and monitoring tools."""
    
    def __init__(self, security_manager: Optional[SecurityManager] = None):
        self.security = security_manager
        self.config = get_config()
    
    async def get_system_info(self, info_type: Optional[str] = None) -> Dict[str, Any]:
        """Get system information.
        
        Args:
            info_type: Type of information to retrieve. Options:
                      - 'all': All system information
                      - 'basic': Basic system info
                      - 'cpu': CPU information
                      - 'memory': Memory information
                      - 'disk': Disk information
                      - 'network': Network information
                      None defaults to 'all'
        
        Returns:
            Dictionary with system information
        """
        try:
            # Security check
            if self.security:
                operation = Operation('read', 'system_info', {'info_type': info_type})
                # Check authorization would be done at the server level
            
            info_type = info_type or 'all'
            
            if info_type == 'basic':
                return await self._get_basic_info()
            elif info_type == 'cpu':
                return await self._get_cpu_info()
            elif info_type == 'memory':
                return await self._get_memory_info()
            elif info_type == 'disk':
                return await self._get_disk_info()
            elif info_type == 'network':
                return await self._get_network_info()
            elif info_type == 'all':
                return {
                    'basic': await self._get_basic_info(),
                    'cpu': await self._get_cpu_info(),
                    'memory': await self._get_memory_info(),
                    'disk': await self._get_disk_info(),
                    'network': await self._get_network_info(),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                raise ValueError(f"Unknown info_type: {info_type}")
                
        except Exception as e:
            log.error(f"Failed to get system info: {e}", exception=e)
            raise SystemException(f"Failed to get system info: {str(e)}")
    
    async def _get_basic_info(self) -> Dict[str, Any]:
        """Get basic system information."""
        basic_info = get_basic_system_info()
        
        # Add additional info
        basic_info.update({
            'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            'users': [user._asdict() for user in psutil.users()],
            'python_implementation': platform.python_implementation(),
            'system_encoding': sys.getdefaultencoding(),
            'file_system_encoding': sys.getfilesystemencoding()
        })
        
        return basic_info
    
    async def _get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information."""
        # Get CPU frequencies
        cpu_freq = psutil.cpu_freq()
        
        return {
            'physical_cores': psutil.cpu_count(logical=False),
            'logical_cores': psutil.cpu_count(logical=True),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'cpu_percent_per_core': psutil.cpu_percent(interval=1, percpu=True),
            'cpu_frequency': {
                'current': cpu_freq.current if cpu_freq else None,
                'min': cpu_freq.min if cpu_freq else None,
                'max': cpu_freq.max if cpu_freq else None
            } if cpu_freq else None,
            'cpu_times': psutil.cpu_times()._asdict(),
            'cpu_stats': psutil.cpu_stats()._asdict() if hasattr(psutil, 'cpu_stats') else None,
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
        }
    
    async def _get_memory_info(self) -> Dict[str, Any]:
        """Get memory information."""
        virtual_mem = psutil.virtual_memory()
        swap_mem = psutil.swap_memory()
        
        return {
            'virtual_memory': {
                'total': virtual_mem.total,
                'available': virtual_mem.available,
                'used': virtual_mem.used,
                'free': virtual_mem.free,
                'percent': virtual_mem.percent,
                'active': getattr(virtual_mem, 'active', None),
                'inactive': getattr(virtual_mem, 'inactive', None),
                'buffers': getattr(virtual_mem, 'buffers', None),
                'cached': getattr(virtual_mem, 'cached', None),
                'shared': getattr(virtual_mem, 'shared', None)
            },
            'swap_memory': {
                'total': swap_mem.total,
                'used': swap_mem.used,
                'free': swap_mem.free,
                'percent': swap_mem.percent,
                'sin': swap_mem.sin,
                'sout': swap_mem.sout
            }
        }
    
    async def _get_disk_info(self) -> Dict[str, Any]:
        """Get disk information."""
        partitions = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partitions.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'opts': partition.opts,
                    'usage': {
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': usage.percent
                    }
                })
            except PermissionError:
                # Some partitions may not be accessible
                continue
        
        # Get disk I/O statistics
        disk_io = psutil.disk_io_counters()
        
        return {
            'partitions': partitions,
            'disk_io': {
                'read_count': disk_io.read_count,
                'write_count': disk_io.write_count,
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes,
                'read_time': disk_io.read_time,
                'write_time': disk_io.write_time
            } if disk_io else None
        }
    
    async def _get_network_info(self) -> Dict[str, Any]:
        """Get network information."""
        interfaces = {}
        for interface, addrs in psutil.net_if_addrs().items():
            interfaces[interface] = []
            for addr in addrs:
                interfaces[interface].append({
                    'family': addr.family.name,
                    'address': addr.address,
                    'netmask': addr.netmask,
                    'broadcast': addr.broadcast,
                    'ptp': addr.ptp
                })
        
        # Get network statistics
        net_stats = {}
        for interface, stats in psutil.net_if_stats().items():
            net_stats[interface] = {
                'isup': stats.isup,
                'duplex': stats.duplex.name if stats.duplex else None,
                'speed': stats.speed,
                'mtu': stats.mtu
            }
        
        # Get network I/O counters
        net_io = psutil.net_io_counters()
        
        return {
            'interfaces': interfaces,
            'interface_stats': net_stats,
            'io_counters': {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errin': net_io.errin,
                'errout': net_io.errout,
                'dropin': net_io.dropin,
                'dropout': net_io.dropout
            } if net_io else None,
            'hostname': socket.gethostname(),
            'fqdn': socket.getfqdn()
        }
    
    async def get_hardware_info(self) -> Dict[str, Any]:
        """Get hardware information."""
        try:
            hardware_info = {
                'cpu': await self._get_cpu_hardware_info(),
                'memory': await self._get_memory_hardware_info(),
                'disks': await self._get_disk_hardware_info(),
                'platform': platform.machine()
            }
            
            # Add platform-specific hardware info
            if is_windows():
                hardware_info['windows'] = await self._get_windows_hardware_info()
            elif is_linux():
                hardware_info['linux'] = await self._get_linux_hardware_info()
            elif is_macos():
                hardware_info['macos'] = await self._get_macos_hardware_info()
            
            return hardware_info
            
        except Exception as e:
            log.error(f"Failed to get hardware info: {e}", exception=e)
            raise SystemException(f"Failed to get hardware info: {str(e)}")
    
    async def _get_cpu_hardware_info(self) -> Dict[str, Any]:
        """Get CPU hardware information."""
        info = {
            'processor': platform.processor(),
            'architecture': platform.machine(),
            'bits': platform.architecture()[0]
        }
        
        # Try to get more detailed CPU info
        if is_linux():
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read()
                    # Parse CPU model name
                    for line in cpuinfo.split('\n'):
                        if 'model name' in line:
                            info['model'] = line.split(':')[1].strip()
                            break
            except Exception:
                pass
        
        return info
    
    async def _get_memory_hardware_info(self) -> Dict[str, Any]:
        """Get memory hardware information."""
        virtual_mem = psutil.virtual_memory()
        return {
            'total_bytes': virtual_mem.total,
            'total_gb': round(virtual_mem.total / (1024**3), 2)
        }
    
    async def _get_disk_hardware_info(self) -> List[Dict[str, Any]]:
        """Get disk hardware information."""
        disks = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    'device': partition.device,
                    'total_bytes': usage.total,
                    'total_gb': round(usage.total / (1024**3), 2),
                    'filesystem': partition.fstype
                })
            except Exception:
                continue
        return disks
    
    async def _get_windows_hardware_info(self) -> Dict[str, Any]:
        """Get Windows-specific hardware information."""
        info = {}
        try:
            import wmi
            c = wmi.WMI()
            
            # Get motherboard info
            for board in c.Win32_BaseBoard():
                info['motherboard'] = {
                    'manufacturer': board.Manufacturer,
                    'product': board.Product,
                    'serial': board.SerialNumber
                }
                break
            
            # Get BIOS info
            for bios in c.Win32_BIOS():
                info['bios'] = {
                    'manufacturer': bios.Manufacturer,
                    'version': bios.Version,
                    'release_date': str(bios.ReleaseDate)
                }
                break
                
        except ImportError:
            log.warning("WMI not available, skipping Windows hardware info")
        except Exception as e:
            log.error(f"Failed to get Windows hardware info: {e}")
            
        return info
    
    async def _get_linux_hardware_info(self) -> Dict[str, Any]:
        """Get Linux-specific hardware information."""
        info = {}
        
        # Try to get DMI information
        try:
            if os.path.exists('/sys/class/dmi/id/board_vendor'):
                with open('/sys/class/dmi/id/board_vendor', 'r') as f:
                    vendor = f.read().strip()
                with open('/sys/class/dmi/id/board_name', 'r') as f:
                    name = f.read().strip()
                info['motherboard'] = {
                    'vendor': vendor,
                    'name': name
                }
        except Exception:
            pass
            
        return info
    
    async def _get_macos_hardware_info(self) -> Dict[str, Any]:
        """Get macOS-specific hardware information."""
        info = {}
        
        try:
            # Get system profiler data
            result = subprocess.run(
                ['system_profiler', 'SPHardwareDataType', '-json'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                # Parse hardware data
                if 'SPHardwareDataType' in data:
                    hw_data = data['SPHardwareDataType'][0]
                    info['model'] = hw_data.get('machine_model')
                    info['serial'] = hw_data.get('serial_number')
        except Exception:
            pass
            
        return info
    
    async def get_os_info(self) -> Dict[str, Any]:
        """Get operating system information."""
        try:
            os_info = {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'platform': platform.platform(),
                'machine': platform.machine(),
                'node': platform.node()
            }
            
            # Add distribution info for Linux
            if is_linux():
                try:
                    import distro
                    os_info['distribution'] = {
                        'name': distro.name(),
                        'version': distro.version(),
                        'codename': distro.codename()
                    }
                except ImportError:
                    # Try to read from os-release
                    try:
                        with open('/etc/os-release', 'r') as f:
                            os_release = {}
                            for line in f:
                                if '=' in line:
                                    key, value = line.strip().split('=', 1)
                                    os_release[key] = value.strip('"')
                            os_info['distribution'] = {
                                'name': os_release.get('NAME', 'Unknown'),
                                'version': os_release.get('VERSION_ID', 'Unknown')
                            }
                    except Exception:
                        pass
            
            # Add Windows-specific info
            elif is_windows():
                os_info['windows'] = {
                    'edition': platform.win32_edition() if hasattr(platform, 'win32_edition') else None,
                    'version': platform.win32_ver()[1]
                }
            
            # Add macOS-specific info
            elif is_macos():
                os_info['macos'] = {
                    'version': platform.mac_ver()[0]
                }
            
            return os_info
            
        except Exception as e:
            log.error(f"Failed to get OS info: {e}", exception=e)
            raise SystemException(f"Failed to get OS info: {str(e)}")
    
    async def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables."""
        try:
            # Security check
            if self.security:
                operation = Operation('read', 'environment_variables')
                # Check authorization would be done at the server level
            
            env_vars = dict(os.environ)
            
            # Mask sensitive variables
            sensitive_keys = [
                'PASSWORD', 'TOKEN', 'KEY', 'SECRET', 'CREDENTIAL',
                'API_KEY', 'ACCESS_KEY', 'PRIVATE_KEY'
            ]
            
            masked_vars = {}
            for key, value in env_vars.items():
                if any(sensitive in key.upper() for sensitive in sensitive_keys):
                    masked_vars[key] = '***MASKED***'
                else:
                    masked_vars[key] = value
            
            return masked_vars
            
        except Exception as e:
            log.error(f"Failed to get environment variables: {e}", exception=e)
            raise SystemException(f"Failed to get environment variables: {str(e)}")
    
    async def get_system_uptime(self) -> Dict[str, Any]:
        """Get system uptime information."""
        try:
            boot_time = psutil.boot_time()
            current_time = datetime.now().timestamp()
            uptime_seconds = int(current_time - boot_time)
            
            # Calculate uptime components
            days = uptime_seconds // 86400
            hours = (uptime_seconds % 86400) // 3600
            minutes = (uptime_seconds % 3600) // 60
            seconds = uptime_seconds % 60
            
            return {
                'boot_time': datetime.fromtimestamp(boot_time).isoformat(),
                'current_time': datetime.now().isoformat(),
                'uptime_seconds': uptime_seconds,
                'uptime_formatted': f"{days}d {hours}h {minutes}m {seconds}s",
                'uptime': {
                    'days': days,
                    'hours': hours,
                    'minutes': minutes,
                    'seconds': seconds
                }
            }
            
        except Exception as e:
            log.error(f"Failed to get system uptime: {e}", exception=e)
            raise SystemException(f"Failed to get system uptime: {str(e)}")
    
    async def execute_command(self, command: str, shell: bool = True, 
                            timeout: Optional[int] = None,
                            working_directory: Optional[str] = None) -> Dict[str, Any]:
        """Execute a system command.
        
        Args:
            command: Command to execute
            shell: Whether to use shell execution
            timeout: Command timeout in seconds
            working_directory: Working directory for command
            
        Returns:
            Dictionary with command result
        """
        try:
            # Security validation
            if self.security:
                validated_command = self.security.validate_input('command', command)
                operation = Operation('execute', 'command', {
                    'command': validated_command,
                    'shell': shell,
                    'working_directory': working_directory
                })
                # Check authorization would be done at the server level
            else:
                validated_command = command
            
            # Use configured timeout if not specified
            if timeout is None:
                timeout = self.config.get('security.authorization.command_timeout', 30)
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                validated_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_directory
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutException(f"Command timed out after {timeout} seconds")
            
            return {
                'command': validated_command,
                'return_code': process.returncode,
                'stdout': stdout.decode('utf-8', errors='replace'),
                'stderr': stderr.decode('utf-8', errors='replace'),
                'success': process.returncode == 0
            }
            
        except TimeoutException:
            raise
        except Exception as e:
            log.error(f"Failed to execute command: {e}", exception=e)
            raise SystemException(f"Failed to execute command: {str(e)}")