"""
Windows Registry management tools for PC Control MCP Server.
"""

import asyncio
import json
import subprocess
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from ..core import (
    StructuredLogger,
    SecurityManager,
    Operation,
    RegistryException,
    ValidationException,
    get_config
)
from ..utils.platform_utils import is_windows

log = StructuredLogger(__name__)


class RegistryTools:
    """Windows Registry management tools."""
    
    # Registry hives mapping
    HIVES = {
        'HKEY_LOCAL_MACHINE': 'HKLM',
        'HKLM': 'HKLM',
        'HKEY_CURRENT_USER': 'HKCU',
        'HKCU': 'HKCU',
        'HKEY_CLASSES_ROOT': 'HKCR',
        'HKCR': 'HKCR',
        'HKEY_USERS': 'HKU',
        'HKU': 'HKU',
        'HKEY_CURRENT_CONFIG': 'HKCC',
        'HKCC': 'HKCC'
    }
    
    # Registry value types
    VALUE_TYPES = {
        'REG_SZ': 'string',
        'REG_EXPAND_SZ': 'expandable_string',
        'REG_BINARY': 'binary',
        'REG_DWORD': 'dword',
        'REG_DWORD_BIG_ENDIAN': 'dword_big_endian',
        'REG_LINK': 'link',
        'REG_MULTI_SZ': 'multi_string',
        'REG_RESOURCE_LIST': 'resource_list',
        'REG_FULL_RESOURCE_DESCRIPTOR': 'full_resource_descriptor',
        'REG_RESOURCE_REQUIREMENTS_LIST': 'resource_requirements_list',
        'REG_QWORD': 'qword'
    }
    
    def __init__(self, security_manager: Optional[SecurityManager] = None):
        self.security = security_manager
        self.config = get_config()
        
        if not is_windows():
            raise RegistryException("Registry operations are only available on Windows")
    
    def _validate_key_path(self, key_path: str) -> str:
        """Validate and normalize registry key path."""
        if not key_path:
            raise ValidationException("Registry key path cannot be empty")
        
        # Security validation
        if self.security:
            key_path = self.security.validate_input('path', key_path)
        
        # Check for dangerous keys
        dangerous_keys = [
            r'SYSTEM\CurrentControlSet\Control\Session Manager',
            r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon',
            r'SYSTEM\CurrentControlSet\Services',
            r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
        ]
        
        key_upper = key_path.upper()
        for dangerous in dangerous_keys:
            if dangerous.upper() in key_upper:
                log.warning(f"Accessing potentially dangerous registry key: {key_path}")
        
        return key_path
    
    def _parse_key_path(self, full_path: str) -> tuple:
        """Parse registry path into hive and key path."""
        parts = full_path.split('\\', 1)
        if len(parts) < 2:
            raise ValidationException(f"Invalid registry path: {full_path}")
        
        hive = parts[0].upper()
        if hive not in self.HIVES:
            raise ValidationException(f"Invalid registry hive: {hive}")
        
        return self.HIVES[hive], parts[1]
    
    async def read_registry_value(self, key_path: str, value_name: str) -> Dict[str, Any]:
        """Read a registry value.
        
        Args:
            key_path: Full registry key path (e.g., HKLM\\SOFTWARE\\Microsoft)
            value_name: Value name to read
            
        Returns:
            Dictionary with value information
        """
        try:
            key_path = self._validate_key_path(key_path)
            hive, subkey = self._parse_key_path(key_path)
            
            # Use PowerShell to read registry value
            ps_script = f"""
            try {{
                $key = Get-ItemProperty -Path "{hive}:\\{subkey}" -Name "{value_name}" -ErrorAction Stop
                $value = $key."{value_name}"
                
                # Detect type
                if ($value -is [int32] -or $value -is [int64]) {{
                    $type = "REG_DWORD"
                }} elseif ($value -is [string[]]) {{
                    $type = "REG_MULTI_SZ"
                }} elseif ($value -is [byte[]]) {{
                    $type = "REG_BINARY"
                    $value = [System.BitConverter]::ToString($value)
                }} else {{
                    $type = "REG_SZ"
                }}
                
                @{{
                    Success = $true
                    Value = $value
                    Type = $type
                    Key = "{key_path}"
                    Name = "{value_name}"
                }} | ConvertTo-Json -Compress
            }} catch {{
                @{{
                    Success = $false
                    Error = $_.Exception.Message
                }} | ConvertTo-Json -Compress
            }}
            """
            
            process = await asyncio.create_subprocess_exec(
                'powershell', '-NoProfile', '-Command', ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if stdout:
                result = json.loads(stdout.decode('utf-8'))
                if result['Success']:
                    return {
                        'key': key_path,
                        'name': value_name,
                        'value': result['Value'],
                        'type': result['Type'],
                        'exists': True
                    }
                else:
                    raise RegistryException(f"Failed to read registry value: {result.get('Error', 'Unknown error')}")
            else:
                raise RegistryException(f"Failed to read registry value: {stderr.decode('utf-8')}")
                
        except Exception as e:
            log.error(f"Failed to read registry value {key_path}\\{value_name}: {e}", exception=e)
            raise RegistryException(f"Failed to read registry value: {str(e)}")
    
    async def write_registry_value(self, key_path: str, value_name: str, 
                                 value: Any, value_type: str = 'REG_SZ') -> Dict[str, Any]:
        """Write a registry value.
        
        Args:
            key_path: Full registry key path
            value_name: Value name to write
            value: Value to write
            value_type: Registry value type (REG_SZ, REG_DWORD, etc.)
            
        Returns:
            Dictionary with operation result
        """
        try:
            key_path = self._validate_key_path(key_path)
            hive, subkey = self._parse_key_path(key_path)
            
            # Validate value type
            if value_type not in self.VALUE_TYPES:
                raise ValidationException(f"Invalid registry value type: {value_type}")
            
            # Convert value based on type
            if value_type == 'REG_DWORD':
                try:
                    value = int(value)
                except ValueError:
                    raise ValidationException("REG_DWORD value must be an integer")
            elif value_type == 'REG_QWORD':
                try:
                    value = int(value)
                except ValueError:
                    raise ValidationException("REG_QWORD value must be an integer")
            elif value_type == 'REG_BINARY':
                if isinstance(value, str):
                    # Convert hex string to binary
                    value = value.replace('-', '').replace(' ', '')
                    try:
                        value = bytes.fromhex(value)
                    except ValueError:
                        raise ValidationException("REG_BINARY value must be valid hex string")
            elif value_type == 'REG_MULTI_SZ':
                if isinstance(value, str):
                    value = value.split('\n')
                elif not isinstance(value, list):
                    raise ValidationException("REG_MULTI_SZ value must be a list or newline-separated string")
            
            # Use PowerShell to write registry value
            ps_script = f"""
            try {{
                # Create key if it doesn't exist
                if (!(Test-Path "{hive}:\\{subkey}")) {{
                    New-Item -Path "{hive}:\\{subkey}" -Force | Out-Null
                }}
                
                # Set value based on type
                """
            
            if value_type == 'REG_SZ' or value_type == 'REG_EXPAND_SZ':
                ps_script += f'Set-ItemProperty -Path "{hive}:\\{subkey}" -Name "{value_name}" -Value "{value}" -Type String'
            elif value_type == 'REG_DWORD':
                ps_script += f'Set-ItemProperty -Path "{hive}:\\{subkey}" -Name "{value_name}" -Value {value} -Type DWord'
            elif value_type == 'REG_QWORD':
                ps_script += f'Set-ItemProperty -Path "{hive}:\\{subkey}" -Name "{value_name}" -Value {value} -Type QWord'
            elif value_type == 'REG_BINARY':
                hex_value = value.hex() if isinstance(value, bytes) else value
                ps_script += f"""
                $bytes = [byte[]]@({','.join(f'0x{hex_value[i:i+2]}' for i in range(0, len(hex_value), 2))})
                Set-ItemProperty -Path "{hive}:\\{subkey}" -Name "{value_name}" -Value $bytes -Type Binary
                """
            elif value_type == 'REG_MULTI_SZ':
                value_array = json.dumps(value) if isinstance(value, list) else json.dumps([value])
                ps_script += f"""
                $values = {value_array} | ConvertFrom-Json
                Set-ItemProperty -Path "{hive}:\\{subkey}" -Name "{value_name}" -Value $values -Type MultiString
                """
            
            ps_script += """
                
                @{
                    Success = $true
                    Key = $key_path
                    Name = $value_name
                    Type = $value_type
                } | ConvertTo-Json -Compress
            } catch {
                @{
                    Success = $false
                    Error = $_.Exception.Message
                } | ConvertTo-Json -Compress
            }
            """
            
            process = await asyncio.create_subprocess_exec(
                'powershell', '-NoProfile', '-Command', ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if stdout:
                result = json.loads(stdout.decode('utf-8'))
                if result['Success']:
                    return {
                        'key': key_path,
                        'name': value_name,
                        'type': value_type,
                        'action': 'write',
                        'success': True
                    }
                else:
                    raise RegistryException(f"Failed to write registry value: {result.get('Error', 'Unknown error')}")
            else:
                raise RegistryException(f"Failed to write registry value: {stderr.decode('utf-8')}")
                
        except Exception as e:
            log.error(f"Failed to write registry value {key_path}\\{value_name}: {e}", exception=e)
            raise RegistryException(f"Failed to write registry value: {str(e)}")
    
    async def delete_registry_value(self, key_path: str, value_name: str) -> Dict[str, Any]:
        """Delete a registry value.
        
        Args:
            key_path: Full registry key path
            value_name: Value name to delete
            
        Returns:
            Dictionary with operation result
        """
        try:
            key_path = self._validate_key_path(key_path)
            hive, subkey = self._parse_key_path(key_path)
            
            # Check if value exists first
            try:
                await self.read_registry_value(key_path, value_name)
            except RegistryException:
                return {
                    'key': key_path,
                    'name': value_name,
                    'action': 'delete',
                    'success': True,
                    'message': 'Value does not exist'
                }
            
            # Use PowerShell to delete value
            ps_script = f"""
            try {{
                Remove-ItemProperty -Path "{hive}:\\{subkey}" -Name "{value_name}" -Force -ErrorAction Stop
                @{{
                    Success = $true
                }} | ConvertTo-Json -Compress
            }} catch {{
                @{{
                    Success = $false
                    Error = $_.Exception.Message
                }} | ConvertTo-Json -Compress
            }}
            """
            
            process = await asyncio.create_subprocess_exec(
                'powershell', '-NoProfile', '-Command', ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if stdout:
                result = json.loads(stdout.decode('utf-8'))
                if result['Success']:
                    return {
                        'key': key_path,
                        'name': value_name,
                        'action': 'delete',
                        'success': True
                    }
                else:
                    raise RegistryException(f"Failed to delete registry value: {result.get('Error', 'Unknown error')}")
            else:
                raise RegistryException(f"Failed to delete registry value: {stderr.decode('utf-8')}")
                
        except Exception as e:
            log.error(f"Failed to delete registry value {key_path}\\{value_name}: {e}", exception=e)
            raise RegistryException(f"Failed to delete registry value: {str(e)}")
    
    async def create_registry_key(self, key_path: str) -> Dict[str, Any]:
        """Create a registry key.
        
        Args:
            key_path: Full registry key path
            
        Returns:
            Dictionary with operation result
        """
        try:
            key_path = self._validate_key_path(key_path)
            hive, subkey = self._parse_key_path(key_path)
            
            # Use PowerShell to create key
            ps_script = f"""
            try {{
                $existed = Test-Path "{hive}:\\{subkey}"
                New-Item -Path "{hive}:\\{subkey}" -Force | Out-Null
                @{{
                    Success = $true
                    Existed = $existed
                    Key = "{key_path}"
                }} | ConvertTo-Json -Compress
            }} catch {{
                @{{
                    Success = $false
                    Error = $_.Exception.Message
                }} | ConvertTo-Json -Compress
            }}
            """
            
            process = await asyncio.create_subprocess_exec(
                'powershell', '-NoProfile', '-Command', ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if stdout:
                result = json.loads(stdout.decode('utf-8'))
                if result['Success']:
                    return {
                        'key': key_path,
                        'action': 'create',
                        'success': True,
                        'existed': result['Existed']
                    }
                else:
                    raise RegistryException(f"Failed to create registry key: {result.get('Error', 'Unknown error')}")
            else:
                raise RegistryException(f"Failed to create registry key: {stderr.decode('utf-8')}")
                
        except Exception as e:
            log.error(f"Failed to create registry key {key_path}: {e}", exception=e)
            raise RegistryException(f"Failed to create registry key: {str(e)}")
    
    async def delete_registry_key(self, key_path: str, recursive: bool = False) -> Dict[str, Any]:
        """Delete a registry key.
        
        Args:
            key_path: Full registry key path
            recursive: Delete all subkeys recursively
            
        Returns:
            Dictionary with operation result
        """
        try:
            key_path = self._validate_key_path(key_path)
            hive, subkey = self._parse_key_path(key_path)
            
            # Check for dangerous deletions
            if recursive and any(danger in subkey.upper() for danger in ['SYSTEM', 'SOFTWARE\\MICROSOFT']):
                raise ValidationException(f"Recursive deletion of critical registry key blocked: {key_path}")
            
            # Use PowerShell to delete key
            recurse_flag = "-Recurse" if recursive else ""
            ps_script = f"""
            try {{
                if (Test-Path "{hive}:\\{subkey}") {{
                    Remove-Item -Path "{hive}:\\{subkey}" {recurse_flag} -Force -ErrorAction Stop
                    @{{
                        Success = $true
                        Deleted = $true
                    }} | ConvertTo-Json -Compress
                }} else {{
                    @{{
                        Success = $true
                        Deleted = $false
                        Message = "Key does not exist"
                    }} | ConvertTo-Json -Compress
                }}
            }} catch {{
                @{{
                    Success = $false
                    Error = $_.Exception.Message
                }} | ConvertTo-Json -Compress
            }}
            """
            
            process = await asyncio.create_subprocess_exec(
                'powershell', '-NoProfile', '-Command', ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if stdout:
                result = json.loads(stdout.decode('utf-8'))
                if result['Success']:
                    return {
                        'key': key_path,
                        'action': 'delete',
                        'success': True,
                        'deleted': result.get('Deleted', True),
                        'recursive': recursive
                    }
                else:
                    raise RegistryException(f"Failed to delete registry key: {result.get('Error', 'Unknown error')}")
            else:
                raise RegistryException(f"Failed to delete registry key: {stderr.decode('utf-8')}")
                
        except Exception as e:
            log.error(f"Failed to delete registry key {key_path}: {e}", exception=e)
            raise RegistryException(f"Failed to delete registry key: {str(e)}")
    
    async def list_registry_values(self, key_path: str) -> List[Dict[str, Any]]:
        """List all values in a registry key.
        
        Args:
            key_path: Full registry key path
            
        Returns:
            List of value information
        """
        try:
            key_path = self._validate_key_path(key_path)
            hive, subkey = self._parse_key_path(key_path)
            
            # Use PowerShell to list values
            ps_script = f"""
            try {{
                if (Test-Path "{hive}:\\{subkey}") {{
                    $key = Get-Item -Path "{hive}:\\{subkey}"
                    $values = @()
                    
                    foreach ($valueName in $key.GetValueNames()) {{
                        $value = $key.GetValue($valueName)
                        $type = $key.GetValueKind($valueName).ToString()
                        
                        # Convert binary to hex string
                        if ($type -eq "Binary" -and $value) {{
                            $value = [System.BitConverter]::ToString($value)
                        }}
                        
                        $values += @{{
                            Name = $valueName
                            Value = $value
                            Type = "REG_" + $type.ToUpper()
                        }}
                    }}
                    
                    # Also get default value if exists
                    $defaultValue = $key.GetValue("")
                    if ($null -ne $defaultValue) {{
                        $values = ,@{{
                            Name = "(Default)"
                            Value = $defaultValue
                            Type = "REG_SZ"
                        }} + $values
                    }}
                    
                    @{{
                        Success = $true
                        Values = $values
                        Key = "{key_path}"
                    }} | ConvertTo-Json -Compress -Depth 10
                }} else {{
                    @{{
                        Success = $false
                        Error = "Registry key does not exist"
                    }} | ConvertTo-Json -Compress
                }}
            }} catch {{
                @{{
                    Success = $false
                    Error = $_.Exception.Message
                }} | ConvertTo-Json -Compress
            }}
            """
            
            process = await asyncio.create_subprocess_exec(
                'powershell', '-NoProfile', '-Command', ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if stdout:
                result = json.loads(stdout.decode('utf-8'))
                if result['Success']:
                    return result.get('Values', [])
                else:
                    raise RegistryException(f"Failed to list registry values: {result.get('Error', 'Unknown error')}")
            else:
                raise RegistryException(f"Failed to list registry values: {stderr.decode('utf-8')}")
                
        except Exception as e:
            log.error(f"Failed to list registry values for {key_path}: {e}", exception=e)
            raise RegistryException(f"Failed to list registry values: {str(e)}")
    
    async def list_registry_subkeys(self, key_path: str) -> List[str]:
        """List all subkeys of a registry key.
        
        Args:
            key_path: Full registry key path
            
        Returns:
            List of subkey names
        """
        try:
            key_path = self._validate_key_path(key_path)
            hive, subkey = self._parse_key_path(key_path)
            
            # Use PowerShell to list subkeys
            ps_script = f"""
            try {{
                if (Test-Path "{hive}:\\{subkey}") {{
                    $subkeys = Get-ChildItem -Path "{hive}:\\{subkey}" -ErrorAction Stop | 
                               Select-Object -ExpandProperty Name | 
                               ForEach-Object {{ $_.Split('\\')[-1] }}
                    
                    @{{
                        Success = $true
                        Subkeys = @($subkeys)
                    }} | ConvertTo-Json -Compress
                }} else {{
                    @{{
                        Success = $false
                        Error = "Registry key does not exist"
                    }} | ConvertTo-Json -Compress
                }}
            }} catch {{
                @{{
                    Success = $false
                    Error = $_.Exception.Message
                }} | ConvertTo-Json -Compress
            }}
            """
            
            process = await asyncio.create_subprocess_exec(
                'powershell', '-NoProfile', '-Command', ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if stdout:
                result = json.loads(stdout.decode('utf-8'))
                if result['Success']:
                    return result.get('Subkeys', [])
                else:
                    raise RegistryException(f"Failed to list registry subkeys: {result.get('Error', 'Unknown error')}")
            else:
                raise RegistryException(f"Failed to list registry subkeys: {stderr.decode('utf-8')}")
                
        except Exception as e:
            log.error(f"Failed to list registry subkeys for {key_path}: {e}", exception=e)
            raise RegistryException(f"Failed to list registry subkeys: {str(e)}")
    
    async def export_registry_key(self, key_path: str, file_path: str) -> Dict[str, Any]:
        """Export a registry key to a .reg file.
        
        Args:
            key_path: Full registry key path
            file_path: Path to save the .reg file
            
        Returns:
            Dictionary with operation result
        """
        try:
            key_path = self._validate_key_path(key_path)
            
            # Validate file path
            if self.security:
                file_path = self.security.validate_input('path', file_path)
            
            # Ensure .reg extension
            if not file_path.lower().endswith('.reg'):
                file_path += '.reg'
            
            # Use reg export command
            cmd = ['reg', 'export', key_path, file_path, '/y']
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Get file info
                file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
                
                return {
                    'key': key_path,
                    'file': file_path,
                    'action': 'export',
                    'success': True,
                    'file_size': file_size
                }
            else:
                error_msg = stderr.decode('utf-8', errors='replace') or stdout.decode('utf-8', errors='replace')
                raise RegistryException(f"Failed to export registry key: {error_msg}")
                
        except Exception as e:
            log.error(f"Failed to export registry key {key_path}: {e}", exception=e)
            raise RegistryException(f"Failed to export registry key: {str(e)}")
    
    async def import_registry_file(self, file_path: str) -> Dict[str, Any]:
        """Import a .reg file into the registry.
        
        Args:
            file_path: Path to the .reg file
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Validate file path
            if self.security:
                file_path = self.security.validate_input('path', file_path)
                
                # Extra security check for registry imports
                log.warning(f"Registry import requested for file: {file_path}")
            
            # Check if file exists
            if not Path(file_path).exists():
                raise RegistryException(f"Registry file not found: {file_path}")
            
            # Check file extension
            if not file_path.lower().endswith('.reg'):
                raise ValidationException("File must have .reg extension")
            
            # Use reg import command
            cmd = ['reg', 'import', file_path]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return {
                    'file': file_path,
                    'action': 'import',
                    'success': True,
                    'message': 'Registry file imported successfully'
                }
            else:
                error_msg = stderr.decode('utf-8', errors='replace') or stdout.decode('utf-8', errors='replace')
                raise RegistryException(f"Failed to import registry file: {error_msg}")
                
        except Exception as e:
            log.error(f"Failed to import registry file {file_path}: {e}", exception=e)
            raise RegistryException(f"Failed to import registry file: {str(e)}")
    
    async def search_registry(self, key_path: str, search_term: str, 
                            search_values: bool = True,
                            search_data: bool = True,
                            case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Search for a term in the registry.
        
        Args:
            key_path: Starting registry key path
            search_term: Term to search for
            search_values: Search in value names
            search_data: Search in value data
            case_sensitive: Case-sensitive search
            
        Returns:
            List of matching items
        """
        try:
            key_path = self._validate_key_path(key_path)
            hive, subkey = self._parse_key_path(key_path)
            
            # Limit search depth for safety
            max_results = 100
            
            # Use PowerShell for searching
            ps_script = f"""
            $results = @()
            $count = 0
            $searchTerm = "{search_term}"
            $caseSensitive = ${str(case_sensitive).lower()}
            
            function Search-Registry {{
                param($Path, $Depth = 0)
                
                if ($Depth -gt 5 -or $count -ge {max_results}) {{ return }}
                
                try {{
                    $key = Get-Item -Path $Path -ErrorAction SilentlyContinue
                    if (-not $key) {{ return }}
                    
                    # Search values
                    if ({str(search_values).lower()}) {{
                        foreach ($valueName in $key.GetValueNames()) {{
                            $match = if ($caseSensitive) {{
                                $valueName -clike "*$searchTerm*"
                            }} else {{
                                $valueName -ilike "*$searchTerm*"
                            }}
                            
                            if ($match -and $count -lt {max_results}) {{
                                $results += @{{
                                    Type = "ValueName"
                                    Key = $Path
                                    Name = $valueName
                                    Value = $key.GetValue($valueName)
                                }}
                                $count++
                            }}
                        }}
                    }}
                    
                    # Search data
                    if ({str(search_data).lower()}) {{
                        foreach ($valueName in $key.GetValueNames()) {{
                            $value = $key.GetValue($valueName)
                            if ($value) {{
                                $valueStr = $value.ToString()
                                $match = if ($caseSensitive) {{
                                    $valueStr -clike "*$searchTerm*"
                                }} else {{
                                    $valueStr -ilike "*$searchTerm*"
                                }}
                                
                                if ($match -and $count -lt {max_results}) {{
                                    $results += @{{
                                        Type = "ValueData"
                                        Key = $Path
                                        Name = $valueName
                                        Value = $valueStr
                                    }}
                                    $count++
                                }}
                            }}
                        }}
                    }}
                    
                    # Search subkeys
                    Get-ChildItem -Path $Path -ErrorAction SilentlyContinue | ForEach-Object {{
                        Search-Registry -Path $_.PSPath -Depth ($Depth + 1)
                    }}
                }} catch {{
                    # Ignore access denied errors
                }}
            }}
            
            Search-Registry -Path "{hive}:\\{subkey}"
            
            @{{
                Success = $true
                Results = $results
                Count = $count
            }} | ConvertTo-Json -Compress -Depth 10
            """
            
            process = await asyncio.create_subprocess_exec(
                'powershell', '-NoProfile', '-Command', ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if stdout:
                result = json.loads(stdout.decode('utf-8'))
                if result['Success']:
                    return result.get('Results', [])
                else:
                    raise RegistryException("Failed to search registry")
            else:
                raise RegistryException(f"Failed to search registry: {stderr.decode('utf-8')}")
                
        except Exception as e:
            log.error(f"Failed to search registry: {e}", exception=e)
            raise RegistryException(f"Failed to search registry: {str(e)}")