"""
Service management tools for PC Control MCP Server.
"""

import asyncio
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime
import psutil

from ..core import (
    StructuredLogger,
    SecurityManager,
    Operation,
    ServiceException,
    ValidationException,
    get_config
)
from ..utils.platform_utils import is_windows, is_linux, is_macos, is_admin

log = StructuredLogger(__name__)


class ServiceInfo:
    """Service information container."""
    
    def __init__(self, name: str, info: Dict[str, Any]):
        self.name = name
        self.info = info
    
    def get_info(self) -> Dict[str, Any]:
        """Get service information."""
        return {
            'name': self.name,
            'display_name': self.info.get('display_name', self.name),
            'status': self.info.get('status', 'unknown'),
            'pid': self.info.get('pid'),
            'startup_type': self.info.get('startup_type', 'unknown'),
            'description': self.info.get('description', ''),
            'binary_path': self.info.get('binary_path', ''),
            'dependencies': self.info.get('dependencies', []),
            'username': self.info.get('username', '')
        }


class ServiceTools:
    """Service management tools."""
    
    def __init__(self, security_manager: Optional[SecurityManager] = None):
        self.security = security_manager
        self.config = get_config()
        self._cache = {}
        self._cache_time = None
        self._cache_ttl = 60  # Cache for 60 seconds
    
    def _check_admin(self):
        """Check if running with admin privileges."""
        if not is_admin():
            raise ServiceException("Administrator privileges required for service operations")
    
    async def list_services(self, include_drivers: bool = False) -> List[Dict[str, Any]]:
        """List all services.
        
        Args:
            include_drivers: Include driver services (Windows)
            
        Returns:
            List of service information
        """
        try:
            services = []
            
            if is_windows():
                services = await self._list_windows_services(include_drivers)
            elif is_linux():
                services = await self._list_linux_services()
            elif is_macos():
                services = await self._list_macos_services()
            else:
                raise ServiceException("Unsupported platform for service management")
            
            # Sort by name
            services.sort(key=lambda x: x['name'].lower())
            
            return services
            
        except Exception as e:
            log.error(f"Failed to list services: {e}", exception=e)
            raise ServiceException(f"Failed to list services: {str(e)}")
    
    async def _list_windows_services(self, include_drivers: bool) -> List[Dict[str, Any]]:
        """List Windows services using sc or wmic."""
        services = []
        
        try:
            # Use PowerShell for more detailed information
            ps_script = """
            Get-Service | Select-Object Name, DisplayName, Status, StartType | 
            ConvertTo-Json -Compress
            """
            
            process = await asyncio.create_subprocess_exec(
                'powershell', '-NoProfile', '-Command', ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                import json
                service_data = json.loads(stdout.decode('utf-8'))
                
                for svc in service_data:
                    service_info = {
                        'name': svc['Name'],
                        'display_name': svc['DisplayName'],
                        'status': svc['Status'].lower(),
                        'startup_type': svc.get('StartType', 'Unknown').lower()
                    }
                    
                    # Map status values
                    status_map = {
                        'running': 'running',
                        'stopped': 'stopped',
                        'paused': 'paused',
                        'startpending': 'starting',
                        'stoppending': 'stopping'
                    }
                    service_info['status'] = status_map.get(
                        service_info['status'], 
                        service_info['status']
                    )
                    
                    services.append(service_info)
            else:
                # Fallback to sc command
                process = await asyncio.create_subprocess_exec(
                    'sc', 'query', 'type=', 'service',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, _ = await process.communicate()
                output = stdout.decode('utf-8', errors='replace')
                
                # Parse sc output
                current_service = {}
                for line in output.split('\n'):
                    line = line.strip()
                    
                    if line.startswith('SERVICE_NAME:'):
                        if current_service:
                            services.append(current_service)
                        current_service = {
                            'name': line.split(':', 1)[1].strip(),
                            'status': 'unknown'
                        }
                    elif line.startswith('DISPLAY_NAME:'):
                        current_service['display_name'] = line.split(':', 1)[1].strip()
                    elif line.startswith('STATE'):
                        if 'RUNNING' in line:
                            current_service['status'] = 'running'
                        elif 'STOPPED' in line:
                            current_service['status'] = 'stopped'
                        elif 'PAUSED' in line:
                            current_service['status'] = 'paused'
                
                if current_service:
                    services.append(current_service)
            
        except Exception as e:
            log.warning(f"Failed to list Windows services: {e}")
            
            # Try WMI as last resort
            try:
                import wmi
                c = wmi.WMI()
                
                for service in c.Win32_Service():
                    services.append({
                        'name': service.Name,
                        'display_name': service.DisplayName,
                        'status': 'running' if service.State == 'Running' else 'stopped',
                        'startup_type': service.StartMode.lower() if service.StartMode else 'unknown',
                        'pid': service.ProcessId if service.ProcessId else None,
                        'binary_path': service.PathName,
                        'description': service.Description
                    })
            except ImportError:
                log.error("WMI not available and other methods failed")
                raise
        
        return services
    
    async def _list_linux_services(self) -> List[Dict[str, Any]]:
        """List Linux services using systemctl."""
        services = []
        
        try:
            # Use systemctl to list services
            process = await asyncio.create_subprocess_exec(
                'systemctl', 'list-units', '--type=service', '--all', '--no-pager',
                '--no-legend', '--plain',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='replace')
                
                for line in output.split('\n'):
                    if line.strip():
                        parts = line.split(None, 4)
                        if len(parts) >= 4:
                            service_name = parts[0]
                            if service_name.endswith('.service'):
                                service_name = service_name[:-8]  # Remove .service suffix
                            
                            status = parts[2].lower()
                            if status == 'active':
                                status = 'running'
                            elif status == 'inactive':
                                status = 'stopped'
                            elif status == 'failed':
                                status = 'failed'
                            
                            services.append({
                                'name': service_name,
                                'display_name': parts[4] if len(parts) > 4 else service_name,
                                'status': status,
                                'load_state': parts[1].lower(),
                                'sub_state': parts[3].lower() if len(parts) > 3 else ''
                            })
            else:
                # Fallback to service command for older systems
                process = await asyncio.create_subprocess_exec(
                    'service', '--status-all',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                output = stdout.decode('utf-8', errors='replace') + stderr.decode('utf-8', errors='replace')
                
                for line in output.split('\n'):
                    if line.strip():
                        # Parse service --status-all output
                        if '[ + ]' in line:
                            status = 'running'
                        elif '[ - ]' in line:
                            status = 'stopped'
                        elif '[ ? ]' in line:
                            status = 'unknown'
                        else:
                            continue
                        
                        service_name = line.split(']')[1].strip() if ']' in line else line.strip()
                        
                        services.append({
                            'name': service_name,
                            'display_name': service_name,
                            'status': status
                        })
        
        except FileNotFoundError:
            log.error("systemctl not found")
            raise ServiceException("systemctl not found - systemd not available")
        except Exception as e:
            log.error(f"Failed to list Linux services: {e}")
            raise
        
        return services
    
    async def _list_macos_services(self) -> List[Dict[str, Any]]:
        """List macOS services using launchctl."""
        services = []
        
        try:
            # List launchd services
            process = await asyncio.create_subprocess_exec(
                'launchctl', 'list',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await process.communicate()
            output = stdout.decode('utf-8', errors='replace')
            
            for line in output.split('\n')[1:]:  # Skip header
                if line.strip():
                    parts = line.split(None, 2)
                    if len(parts) >= 3:
                        pid = parts[0]
                        status = parts[1]
                        label = parts[2]
                        
                        services.append({
                            'name': label,
                            'display_name': label,
                            'status': 'running' if pid != '-' else 'stopped',
                            'pid': int(pid) if pid != '-' else None,
                            'exit_code': int(status) if status != '-' else None
                        })
        
        except Exception as e:
            log.error(f"Failed to list macOS services: {e}")
            raise
        
        return services
    
    async def get_service_info(self, service_name: str) -> Dict[str, Any]:
        """Get detailed information about a service.
        
        Args:
            service_name: Service name
            
        Returns:
            Dictionary with service information
        """
        try:
            # Validate service name
            if self.security:
                service_name = self.security.validate_input('command', service_name)
            
            if is_windows():
                return await self._get_windows_service_info(service_name)
            elif is_linux():
                return await self._get_linux_service_info(service_name)
            elif is_macos():
                return await self._get_macos_service_info(service_name)
            else:
                raise ServiceException("Unsupported platform")
                
        except Exception as e:
            log.error(f"Failed to get service info for {service_name}: {e}", exception=e)
            raise ServiceException(f"Failed to get service info: {str(e)}")
    
    async def _get_windows_service_info(self, service_name: str) -> Dict[str, Any]:
        """Get Windows service information."""
        try:
            # Use PowerShell for detailed info
            ps_script = f"""
            $service = Get-Service -Name '{service_name}' -ErrorAction SilentlyContinue
            if ($service) {{
                $wmiService = Get-WmiObject Win32_Service -Filter "Name='$($service.Name)'"
                @{{
                    Name = $service.Name
                    DisplayName = $service.DisplayName
                    Status = $service.Status.ToString()
                    StartType = $service.StartType.ToString()
                    Description = $wmiService.Description
                    PathName = $wmiService.PathName
                    ProcessId = $wmiService.ProcessId
                    StartName = $wmiService.StartName
                    State = $wmiService.State
                    AcceptPause = $wmiService.AcceptPause
                    AcceptStop = $wmiService.AcceptStop
                    Dependencies = @($service.DependentServices | ForEach-Object {{ $_.Name }})
                }} | ConvertTo-Json -Compress
            }}
            """
            
            process = await asyncio.create_subprocess_exec(
                'powershell', '-NoProfile', '-Command', ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and stdout:
                import json
                service_data = json.loads(stdout.decode('utf-8'))
                
                return {
                    'name': service_data['Name'],
                    'display_name': service_data['DisplayName'],
                    'status': service_data['Status'].lower(),
                    'startup_type': service_data['StartType'].lower(),
                    'description': service_data.get('Description', ''),
                    'binary_path': service_data.get('PathName', ''),
                    'pid': service_data.get('ProcessId'),
                    'username': service_data.get('StartName', ''),
                    'can_pause': service_data.get('AcceptPause', False),
                    'can_stop': service_data.get('AcceptStop', False),
                    'dependencies': service_data.get('Dependencies', [])
                }
            else:
                raise ServiceException(f"Service '{service_name}' not found")
                
        except Exception as e:
            log.error(f"Failed to get Windows service info: {e}")
            raise
    
    async def _get_linux_service_info(self, service_name: str) -> Dict[str, Any]:
        """Get Linux service information."""
        try:
            # Use systemctl show
            process = await asyncio.create_subprocess_exec(
                'systemctl', 'show', service_name, '--no-pager',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='replace')
                
                info = {}
                for line in output.split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        info[key] = value
                
                # Map systemd properties to our format
                status = info.get('ActiveState', 'unknown').lower()
                if status == 'active':
                    status = 'running'
                elif status == 'inactive':
                    status = 'stopped'
                
                return {
                    'name': service_name,
                    'display_name': info.get('Description', service_name),
                    'status': status,
                    'sub_status': info.get('SubState', ''),
                    'startup_type': info.get('UnitFileState', 'unknown'),
                    'pid': int(info.get('MainPID', 0)) if info.get('MainPID', '0') != '0' else None,
                    'binary_path': info.get('ExecStart', ''),
                    'active_enter_timestamp': info.get('ActiveEnterTimestamp', ''),
                    'memory_current': int(info.get('MemoryCurrent', 0)) if info.get('MemoryCurrent') else None,
                    'cpu_usage_nsec': int(info.get('CPUUsageNSec', 0)) if info.get('CPUUsageNSec') else None,
                    'restart_count': int(info.get('NRestarts', 0)),
                    'result': info.get('Result', ''),
                    'load_state': info.get('LoadState', ''),
                    'user': info.get('User', ''),
                    'group': info.get('Group', '')
                }
            else:
                raise ServiceException(f"Service '{service_name}' not found")
                
        except Exception as e:
            log.error(f"Failed to get Linux service info: {e}")
            raise
    
    async def _get_macos_service_info(self, service_name: str) -> Dict[str, Any]:
        """Get macOS service information."""
        try:
            # Use launchctl print
            process = await asyncio.create_subprocess_exec(
                'launchctl', 'print', f'system/{service_name}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='replace')
                
                info = {
                    'name': service_name,
                    'display_name': service_name,
                    'status': 'unknown'
                }
                
                # Parse launchctl output
                for line in output.split('\n'):
                    if 'state =' in line:
                        if 'running' in line:
                            info['status'] = 'running'
                        else:
                            info['status'] = 'stopped'
                    elif 'pid =' in line:
                        try:
                            info['pid'] = int(line.split('=')[1].strip())
                        except:
                            pass
                
                return info
            else:
                raise ServiceException(f"Service '{service_name}' not found")
                
        except Exception as e:
            log.error(f"Failed to get macOS service info: {e}")
            raise
    
    async def start_service(self, service_name: str) -> Dict[str, Any]:
        """Start a service.
        
        Args:
            service_name: Service name
            
        Returns:
            Dictionary with operation result
        """
        try:
            self._check_admin()
            
            # Validate service name
            if self.security:
                service_name = self.security.validate_input('command', service_name)
            
            # Get current status
            current_info = await self.get_service_info(service_name)
            
            if current_info['status'] == 'running':
                return {
                    'service': service_name,
                    'action': 'start',
                    'success': True,
                    'message': 'Service already running',
                    'status': 'running'
                }
            
            # Start service
            if is_windows():
                result = await self._start_windows_service(service_name)
            elif is_linux():
                result = await self._start_linux_service(service_name)
            elif is_macos():
                result = await self._start_macos_service(service_name)
            else:
                raise ServiceException("Unsupported platform")
            
            # Wait a bit and check status
            await asyncio.sleep(2)
            new_info = await self.get_service_info(service_name)
            
            result.update({
                'status': new_info['status'],
                'pid': new_info.get('pid')
            })
            
            return result
            
        except Exception as e:
            log.error(f"Failed to start service {service_name}: {e}", exception=e)
            raise ServiceException(f"Failed to start service: {str(e)}")
    
    async def _start_windows_service(self, service_name: str) -> Dict[str, Any]:
        """Start Windows service."""
        process = await asyncio.create_subprocess_exec(
            'net', 'start', service_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            'service': service_name,
            'action': 'start',
            'success': process.returncode == 0,
            'message': stdout.decode('utf-8', errors='replace') if process.returncode == 0 
                      else stderr.decode('utf-8', errors='replace')
        }
    
    async def _start_linux_service(self, service_name: str) -> Dict[str, Any]:
        """Start Linux service."""
        process = await asyncio.create_subprocess_exec(
            'systemctl', 'start', service_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            'service': service_name,
            'action': 'start',
            'success': process.returncode == 0,
            'message': 'Service started' if process.returncode == 0 
                      else stderr.decode('utf-8', errors='replace')
        }
    
    async def _start_macos_service(self, service_name: str) -> Dict[str, Any]:
        """Start macOS service."""
        process = await asyncio.create_subprocess_exec(
            'launchctl', 'start', service_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            'service': service_name,
            'action': 'start',
            'success': process.returncode == 0,
            'message': 'Service started' if process.returncode == 0 
                      else stderr.decode('utf-8', errors='replace')
        }
    
    async def stop_service(self, service_name: str) -> Dict[str, Any]:
        """Stop a service.
        
        Args:
            service_name: Service name
            
        Returns:
            Dictionary with operation result
        """
        try:
            self._check_admin()
            
            # Validate service name
            if self.security:
                service_name = self.security.validate_input('command', service_name)
            
            # Get current status
            current_info = await self.get_service_info(service_name)
            
            if current_info['status'] == 'stopped':
                return {
                    'service': service_name,
                    'action': 'stop',
                    'success': True,
                    'message': 'Service already stopped',
                    'status': 'stopped'
                }
            
            # Stop service
            if is_windows():
                result = await self._stop_windows_service(service_name)
            elif is_linux():
                result = await self._stop_linux_service(service_name)
            elif is_macos():
                result = await self._stop_macos_service(service_name)
            else:
                raise ServiceException("Unsupported platform")
            
            # Wait a bit and check status
            await asyncio.sleep(2)
            new_info = await self.get_service_info(service_name)
            
            result.update({
                'status': new_info['status']
            })
            
            return result
            
        except Exception as e:
            log.error(f"Failed to stop service {service_name}: {e}", exception=e)
            raise ServiceException(f"Failed to stop service: {str(e)}")
    
    async def _stop_windows_service(self, service_name: str) -> Dict[str, Any]:
        """Stop Windows service."""
        process = await asyncio.create_subprocess_exec(
            'net', 'stop', service_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            'service': service_name,
            'action': 'stop',
            'success': process.returncode == 0,
            'message': stdout.decode('utf-8', errors='replace') if process.returncode == 0 
                      else stderr.decode('utf-8', errors='replace')
        }
    
    async def _stop_linux_service(self, service_name: str) -> Dict[str, Any]:
        """Stop Linux service."""
        process = await asyncio.create_subprocess_exec(
            'systemctl', 'stop', service_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            'service': service_name,
            'action': 'stop',
            'success': process.returncode == 0,
            'message': 'Service stopped' if process.returncode == 0 
                      else stderr.decode('utf-8', errors='replace')
        }
    
    async def _stop_macos_service(self, service_name: str) -> Dict[str, Any]:
        """Stop macOS service."""
        process = await asyncio.create_subprocess_exec(
            'launchctl', 'stop', service_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            'service': service_name,
            'action': 'stop',
            'success': process.returncode == 0,
            'message': 'Service stopped' if process.returncode == 0 
                      else stderr.decode('utf-8', errors='replace')
        }
    
    async def restart_service(self, service_name: str) -> Dict[str, Any]:
        """Restart a service.
        
        Args:
            service_name: Service name
            
        Returns:
            Dictionary with operation result
        """
        try:
            self._check_admin()
            
            # Validate service name
            if self.security:
                service_name = self.security.validate_input('command', service_name)
            
            if is_windows():
                # Windows doesn't have a restart command, so stop then start
                stop_result = await self.stop_service(service_name)
                if stop_result['success'] or stop_result['status'] == 'stopped':
                    await asyncio.sleep(1)
                    start_result = await self.start_service(service_name)
                    return {
                        'service': service_name,
                        'action': 'restart',
                        'success': start_result['success'],
                        'message': start_result['message'],
                        'status': start_result['status']
                    }
                else:
                    return stop_result
            elif is_linux():
                result = await self._restart_linux_service(service_name)
            elif is_macos():
                # macOS also needs stop then start
                stop_result = await self.stop_service(service_name)
                if stop_result['success']:
                    await asyncio.sleep(1)
                    start_result = await self.start_service(service_name)
                    return {
                        'service': service_name,
                        'action': 'restart',
                        'success': start_result['success'],
                        'message': start_result['message'],
                        'status': start_result['status']
                    }
                else:
                    return stop_result
            else:
                raise ServiceException("Unsupported platform")
            
            # Check final status
            await asyncio.sleep(2)
            new_info = await self.get_service_info(service_name)
            
            result.update({
                'status': new_info['status'],
                'pid': new_info.get('pid')
            })
            
            return result
            
        except Exception as e:
            log.error(f"Failed to restart service {service_name}: {e}", exception=e)
            raise ServiceException(f"Failed to restart service: {str(e)}")
    
    async def _restart_linux_service(self, service_name: str) -> Dict[str, Any]:
        """Restart Linux service."""
        process = await asyncio.create_subprocess_exec(
            'systemctl', 'restart', service_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            'service': service_name,
            'action': 'restart',
            'success': process.returncode == 0,
            'message': 'Service restarted' if process.returncode == 0 
                      else stderr.decode('utf-8', errors='replace')
        }
    
    async def set_service_startup_type(self, service_name: str, 
                                     startup_type: str) -> Dict[str, Any]:
        """Set service startup type.
        
        Args:
            service_name: Service name
            startup_type: Startup type (auto, manual, disabled)
            
        Returns:
            Dictionary with operation result
        """
        try:
            self._check_admin()
            
            # Validate inputs
            if self.security:
                service_name = self.security.validate_input('command', service_name)
            
            valid_types = ['auto', 'automatic', 'manual', 'disabled']
            if startup_type.lower() not in valid_types:
                raise ValidationException(f"Invalid startup type: {startup_type}")
            
            if is_windows():
                result = await self._set_windows_service_startup(service_name, startup_type)
            elif is_linux():
                result = await self._set_linux_service_startup(service_name, startup_type)
            elif is_macos():
                result = await self._set_macos_service_startup(service_name, startup_type)
            else:
                raise ServiceException("Unsupported platform")
            
            return result
            
        except Exception as e:
            log.error(f"Failed to set startup type for {service_name}: {e}", exception=e)
            raise ServiceException(f"Failed to set startup type: {str(e)}")
    
    async def _set_windows_service_startup(self, service_name: str, 
                                         startup_type: str) -> Dict[str, Any]:
        """Set Windows service startup type."""
        # Map startup types
        type_map = {
            'auto': 'auto',
            'automatic': 'auto',
            'manual': 'demand',
            'disabled': 'disabled'
        }
        
        sc_type = type_map[startup_type.lower()]
        
        process = await asyncio.create_subprocess_exec(
            'sc', 'config', service_name, 'start=', sc_type,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            'service': service_name,
            'action': 'set_startup_type',
            'startup_type': startup_type,
            'success': process.returncode == 0,
            'message': 'Startup type updated' if process.returncode == 0 
                      else stderr.decode('utf-8', errors='replace')
        }
    
    async def _set_linux_service_startup(self, service_name: str, 
                                       startup_type: str) -> Dict[str, Any]:
        """Set Linux service startup type."""
        if startup_type.lower() in ['auto', 'automatic']:
            cmd = ['systemctl', 'enable', service_name]
        elif startup_type.lower() == 'disabled':
            cmd = ['systemctl', 'disable', service_name]
        else:  # manual
            # In systemd, manual means don't start at boot but can be started manually
            cmd = ['systemctl', 'disable', service_name]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            'service': service_name,
            'action': 'set_startup_type',
            'startup_type': startup_type,
            'success': process.returncode == 0,
            'message': 'Startup type updated' if process.returncode == 0 
                      else stderr.decode('utf-8', errors='replace')
        }
    
    async def _set_macos_service_startup(self, service_name: str, 
                                        startup_type: str) -> Dict[str, Any]:
        """Set macOS service startup type."""
        # macOS uses different mechanism with launchd
        # This is simplified - real implementation would modify plist files
        
        if startup_type.lower() in ['auto', 'automatic']:
            cmd = ['launchctl', 'enable', f'system/{service_name}']
        else:
            cmd = ['launchctl', 'disable', f'system/{service_name}']
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            'service': service_name,
            'action': 'set_startup_type',
            'startup_type': startup_type,
            'success': process.returncode == 0,
            'message': 'Startup type updated' if process.returncode == 0 
                      else stderr.decode('utf-8', errors='replace')
        }