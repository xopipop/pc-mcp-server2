#!/usr/bin/env python3
"""
PC Control MCP Server - Полнофункциональный MCP-сервер для управления компьютером

КРИТИЧЕСКИЕ ПРЕДУПРЕЖДЕНИЯ БЕЗОПАСНОСТИ:
⚠️ ВНИМАНИЕ: Этот сервер предоставляет ПОЛНЫЙ ДОСТУП к вашей системе!
⚠️ Используйте ТОЛЬКО в изолированной среде или виртуальной машине!
⚠️ ОБЯЗАТЕЛЬНО создайте резервные копии перед использованием!
⚠️ НЕ используйте на продакшн-системах или с важными данными!

Потенциально опасные операции:
- Удаление системных файлов
- Изменение реестра Windows
- Остановка критических процессов
- Выполнение произвольных команд
- Изменение сетевых настроек
"""

import asyncio
import json
import logging
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# MCP SDK imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# System monitoring and control imports
import psutil
import subprocess
import shutil

# Platform-specific imports
if platform.system() == "Windows":
    try:
        import winreg
    except ImportError:
        winreg = None

# Logging configuration
LOG_DIR = Path.home() / ".pc_control_mcp" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"pc_control_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Security configuration
SECURITY_CONFIG = {
    "allowed_commands": [
        "ls", "dir", "pwd", "cd", "echo", "cat", "type", "grep", "find",
        "ps", "tasklist", "netstat", "ipconfig", "ifconfig", "ping",
        "systeminfo", "uname", "whoami", "hostname"
    ],
    "blocked_paths": [
        "/", "C:\\", "C:\\Windows", "C:\\Windows\\System32",
        "/System", "/usr/bin", "/etc", "/boot", "/proc", "/sys"
    ],
    "max_file_size": 100 * 1024 * 1024,  # 100MB
    "command_timeout": 30,  # seconds
    "enable_dangerous_operations": False  # Set to True at your own risk!
}


class SecurityManager:
    """Менеджер безопасности для контроля операций"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.operation_log = []
        
    def check_command(self, command: str) -> bool:
        """Проверка разрешенности команды"""
        if not self.config.get("enable_dangerous_operations", False):
            base_command = command.split()[0].lower()
            if base_command not in self.config.get("allowed_commands", []):
                logger.warning(f"Blocked command: {command}")
                return False
        return True
        
    def check_path(self, path: str) -> bool:
        """Проверка безопасности пути"""
        path_obj = Path(path).resolve()
        for blocked in self.config.get("blocked_paths", []):
            if str(path_obj).startswith(blocked):
                logger.warning(f"Blocked path access: {path}")
                return False
        return True
        
    def log_operation(self, operation: str, details: Dict[str, Any]):
        """Логирование операции"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "details": details
        }
        self.operation_log.append(entry)
        logger.info(f"Operation logged: {operation}")


class PCControlMCP:
    """Основной класс MCP-сервера для управления компьютером"""
    
    def __init__(self):
        self.server = Server("pc-control-mcp")
        self.security = SecurityManager(SECURITY_CONFIG)
        self._setup_tools()
        
    def _setup_tools(self):
        """Регистрация всех инструментов"""
        
        # Tool: execute_command
        @self.server.tool()
        async def execute_command(
            command: str,
            working_directory: Optional[str] = None,
            timeout: Optional[int] = 30
        ) -> Dict[str, Any]:
            """
            Выполнение системных команд
            
            Args:
                command: Команда для выполнения
                working_directory: Рабочая директория (опционально)
                timeout: Таймаут выполнения в секундах
                
            Returns:
                Dict с return_code, stdout, stderr
            """
            try:
                # Security check
                if not self.security.check_command(command):
                    return {
                        "error": "Command not allowed by security policy",
                        "return_code": -1
                    }
                
                # Log operation
                self.security.log_operation("execute_command", {
                    "command": command,
                    "working_directory": working_directory
                })
                
                # Determine shell based on platform
                if platform.system() == "Windows":
                    shell_cmd = ["powershell", "-Command", command]
                else:
                    shell_cmd = ["bash", "-c", command]
                
                # Execute command
                process = await asyncio.create_subprocess_exec(
                    *shell_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=working_directory
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )
                    
                    return {
                        "return_code": process.returncode,
                        "stdout": stdout.decode('utf-8', errors='replace'),
                        "stderr": stderr.decode('utf-8', errors='replace')
                    }
                    
                except asyncio.TimeoutError:
                    process.terminate()
                    await process.wait()
                    return {
                        "error": f"Command timed out after {timeout} seconds",
                        "return_code": -1
                    }
                    
            except Exception as e:
                logger.error(f"Error executing command: {e}")
                return {
                    "error": str(e),
                    "return_code": -1
                }
        
        # Tool: file_operations
        @self.server.tool()
        async def file_operations(
            operation: str,
            path: str,
            content: Optional[str] = None,
            destination: Optional[str] = None,
            encoding: str = 'utf-8'
        ) -> Dict[str, Any]:
            """
            Операции с файловой системой
            
            Args:
                operation: Тип операции (read, write, delete, create_dir, list_dir, copy, move, rename)
                path: Путь к файлу/директории
                content: Содержимое для записи (для операции write)
                destination: Путь назначения (для copy, move, rename)
                encoding: Кодировка файла
                
            Returns:
                Dict с результатом операции
            """
            try:
                # Security check
                if not self.security.check_path(path):
                    return {"error": "Path not allowed by security policy"}
                
                if destination and not self.security.check_path(destination):
                    return {"error": "Destination path not allowed by security policy"}
                
                # Log operation
                self.security.log_operation("file_operations", {
                    "operation": operation,
                    "path": path,
                    "destination": destination
                })
                
                path_obj = Path(path)
                
                if operation == "read":
                    if not path_obj.exists():
                        return {"error": "File not found"}
                    
                    # Check file size
                    if path_obj.stat().st_size > self.security.config["max_file_size"]:
                        return {"error": "File too large"}
                    
                    try:
                        with open(path_obj, 'r', encoding=encoding) as f:
                            return {"content": f.read(), "encoding": encoding}
                    except UnicodeDecodeError:
                        # Try binary read
                        with open(path_obj, 'rb') as f:
                            return {"content": f.read().hex(), "encoding": "binary"}
                
                elif operation == "write":
                    if content is None:
                        return {"error": "Content is required for write operation"}
                    
                    # Create parent directories if needed
                    path_obj.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(path_obj, 'w', encoding=encoding) as f:
                        f.write(content)
                    return {"success": True, "path": str(path_obj)}
                
                elif operation == "delete":
                    if path_obj.is_file():
                        path_obj.unlink()
                    elif path_obj.is_dir():
                        shutil.rmtree(path_obj)
                    else:
                        return {"error": "Path not found"}
                    return {"success": True, "deleted": str(path_obj)}
                
                elif operation == "create_dir":
                    path_obj.mkdir(parents=True, exist_ok=True)
                    return {"success": True, "created": str(path_obj)}
                
                elif operation == "list_dir":
                    if not path_obj.is_dir():
                        return {"error": "Path is not a directory"}
                    
                    items = []
                    for item in path_obj.iterdir():
                        items.append({
                            "name": item.name,
                            "type": "dir" if item.is_dir() else "file",
                            "size": item.stat().st_size if item.is_file() else None,
                            "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                        })
                    return {"items": items, "count": len(items)}
                
                elif operation == "copy":
                    if not destination:
                        return {"error": "Destination is required for copy operation"}
                    
                    dest_obj = Path(destination)
                    if path_obj.is_file():
                        shutil.copy2(path_obj, dest_obj)
                    elif path_obj.is_dir():
                        shutil.copytree(path_obj, dest_obj)
                    else:
                        return {"error": "Source path not found"}
                    return {"success": True, "copied_to": str(dest_obj)}
                
                elif operation == "move":
                    if not destination:
                        return {"error": "Destination is required for move operation"}
                    
                    dest_obj = Path(destination)
                    shutil.move(str(path_obj), str(dest_obj))
                    return {"success": True, "moved_to": str(dest_obj)}
                
                elif operation == "rename":
                    if not destination:
                        return {"error": "New name is required for rename operation"}
                    
                    new_path = path_obj.parent / destination
                    path_obj.rename(new_path)
                    return {"success": True, "renamed_to": str(new_path)}
                
                else:
                    return {"error": f"Unknown operation: {operation}"}
                
            except Exception as e:
                logger.error(f"Error in file operation: {e}")
                return {"error": str(e)}
        
        # Tool: system_info
        @self.server.tool()
        async def system_info(info_type: str) -> Dict[str, Any]:
            """
            Получение информации о системе
            
            Args:
                info_type: Тип информации (cpu, memory, disk, processes, network, hardware, os_info)
                
            Returns:
                Dict с запрошенной информацией
            """
            try:
                self.security.log_operation("system_info", {"info_type": info_type})
                
                if info_type == "cpu":
                    return {
                        "physical_cores": psutil.cpu_count(logical=False),
                        "logical_cores": psutil.cpu_count(logical=True),
                        "cpu_percent": psutil.cpu_percent(interval=1),
                        "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                        "cpu_stats": psutil.cpu_stats()._asdict() if hasattr(psutil, 'cpu_stats') else None,
                        "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None
                    }
                
                elif info_type == "memory":
                    vm = psutil.virtual_memory()
                    swap = psutil.swap_memory()
                    return {
                        "virtual_memory": {
                            "total": vm.total,
                            "available": vm.available,
                            "used": vm.used,
                            "percent": vm.percent
                        },
                        "swap_memory": {
                            "total": swap.total,
                            "used": swap.used,
                            "free": swap.free,
                            "percent": swap.percent
                        }
                    }
                
                elif info_type == "disk":
                    disks = []
                    for partition in psutil.disk_partitions():
                        try:
                            usage = psutil.disk_usage(partition.mountpoint)
                            disks.append({
                                "device": partition.device,
                                "mountpoint": partition.mountpoint,
                                "fstype": partition.fstype,
                                "total": usage.total,
                                "used": usage.used,
                                "free": usage.free,
                                "percent": usage.percent
                            })
                        except:
                            pass
                    return {"disks": disks}
                
                elif info_type == "processes":
                    processes = []
                    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                        try:
                            processes.append(proc.info)
                        except:
                            pass
                    return {
                        "processes": sorted(processes, key=lambda x: x.get('cpu_percent', 0), reverse=True)[:20],
                        "total_processes": len(processes)
                    }
                
                elif info_type == "network":
                    net_io = psutil.net_io_counters()
                    net_if = psutil.net_if_addrs()
                    interfaces = {}
                    
                    for name, addrs in net_if.items():
                        interfaces[name] = []
                        for addr in addrs:
                            interfaces[name].append({
                                "family": str(addr.family),
                                "address": addr.address,
                                "netmask": addr.netmask,
                                "broadcast": addr.broadcast
                            })
                    
                    return {
                        "io_counters": {
                            "bytes_sent": net_io.bytes_sent,
                            "bytes_recv": net_io.bytes_recv,
                            "packets_sent": net_io.packets_sent,
                            "packets_recv": net_io.packets_recv
                        },
                        "interfaces": interfaces
                    }
                
                elif info_type == "hardware":
                    return {
                        "platform": platform.platform(),
                        "processor": platform.processor(),
                        "architecture": platform.machine(),
                        "hostname": platform.node()
                    }
                
                elif info_type == "os_info":
                    return {
                        "system": platform.system(),
                        "release": platform.release(),
                        "version": platform.version(),
                        "python_version": sys.version,
                        "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
                    }
                
                else:
                    return {"error": f"Unknown info type: {info_type}"}
                
            except Exception as e:
                logger.error(f"Error getting system info: {e}")
                return {"error": str(e)}
        
        # Tool: process_management
        @self.server.tool()
        async def process_management(
            action: str,
            pid: Optional[int] = None,
            name: Optional[str] = None,
            signal: Optional[str] = "SIGTERM"
        ) -> Dict[str, Any]:
            """
            Управление процессами
            
            Args:
                action: Действие (list, kill, start, suspend, resume, get_info)
                pid: ID процесса
                name: Имя процесса
                signal: Сигнал для завершения (SIGTERM, SIGKILL)
                
            Returns:
                Dict с результатом операции
            """
            try:
                self.security.log_operation("process_management", {
                    "action": action,
                    "pid": pid,
                    "name": name
                })
                
                if action == "list":
                    processes = []
                    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 
                                                   'memory_percent', 'status', 'create_time']):
                        try:
                            info = proc.info
                            if name and name.lower() not in info['name'].lower():
                                continue
                            processes.append(info)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    return {
                        "processes": sorted(processes, key=lambda x: x.get('cpu_percent', 0), reverse=True),
                        "count": len(processes)
                    }
                
                elif action == "get_info":
                    if not pid:
                        return {"error": "PID is required for get_info action"}
                    
                    try:
                        proc = psutil.Process(pid)
                        with proc.oneshot():
                            info = {
                                "pid": proc.pid,
                                "name": proc.name(),
                                "exe": proc.exe() if hasattr(proc, 'exe') else None,
                                "cmdline": proc.cmdline(),
                                "status": proc.status(),
                                "username": proc.username(),
                                "create_time": datetime.fromtimestamp(proc.create_time()).isoformat(),
                                "cpu_percent": proc.cpu_percent(),
                                "memory_info": proc.memory_info()._asdict(),
                                "num_threads": proc.num_threads(),
                                "connections": [conn._asdict() for conn in proc.connections()] if hasattr(proc, 'connections') else []
                            }
                        return info
                    except psutil.NoSuchProcess:
                        return {"error": f"Process with PID {pid} not found"}
                    except psutil.AccessDenied:
                        return {"error": f"Access denied to process {pid}"}
                
                elif action == "kill":
                    if not self.security.config.get("enable_dangerous_operations", False):
                        return {"error": "Killing processes is disabled by security policy"}
                    
                    if not pid and not name:
                        return {"error": "PID or name is required for kill action"}
                    
                    killed = []
                    if pid:
                        try:
                            proc = psutil.Process(pid)
                            proc.terminate() if signal == "SIGTERM" else proc.kill()
                            killed.append({"pid": pid, "name": proc.name()})
                        except psutil.NoSuchProcess:
                            return {"error": f"Process with PID {pid} not found"}
                        except psutil.AccessDenied:
                            return {"error": f"Access denied to kill process {pid}"}
                    
                    elif name:
                        for proc in psutil.process_iter(['pid', 'name']):
                            try:
                                if name.lower() in proc.info['name'].lower():
                                    proc.terminate() if signal == "SIGTERM" else proc.kill()
                                    killed.append(proc.info)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                    
                    return {"killed": killed, "count": len(killed)}
                
                elif action == "suspend":
                    if not pid:
                        return {"error": "PID is required for suspend action"}
                    
                    try:
                        proc = psutil.Process(pid)
                        proc.suspend()
                        return {"success": True, "pid": pid, "name": proc.name()}
                    except psutil.NoSuchProcess:
                        return {"error": f"Process with PID {pid} not found"}
                    except psutil.AccessDenied:
                        return {"error": f"Access denied to suspend process {pid}"}
                
                elif action == "resume":
                    if not pid:
                        return {"error": "PID is required for resume action"}
                    
                    try:
                        proc = psutil.Process(pid)
                        proc.resume()
                        return {"success": True, "pid": pid, "name": proc.name()}
                    except psutil.NoSuchProcess:
                        return {"error": f"Process with PID {pid} not found"}
                    except psutil.AccessDenied:
                        return {"error": f"Access denied to resume process {pid}"}
                
                elif action == "start":
                    # Start new process would require command parameter
                    return {"error": "Use execute_command tool to start new processes"}
                
                else:
                    return {"error": f"Unknown action: {action}"}
                
            except Exception as e:
                logger.error(f"Error in process management: {e}")
                return {"error": str(e)}
        
        # Tool: network_operations
        @self.server.tool()
        async def network_operations(
            operation: str,
            target: Optional[str] = None,
            port: Optional[int] = None,
            count: int = 4,
            timeout: int = 5
        ) -> Dict[str, Any]:
            """
            Сетевые операции
            
            Args:
                operation: Тип операции (ping, port_scan, connection_info, dns_lookup)
                target: Целевой хост/IP
                port: Порт для сканирования
                count: Количество пингов
                timeout: Таймаут операции
                
            Returns:
                Dict с результатом операции
            """
            try:
                self.security.log_operation("network_operations", {
                    "operation": operation,
                    "target": target,
                    "port": port
                })
                
                if operation == "ping":
                    if not target:
                        return {"error": "Target is required for ping operation"}
                    
                    if platform.system() == "Windows":
                        cmd = f"ping -n {count} -w {timeout*1000} {target}"
                    else:
                        cmd = f"ping -c {count} -W {timeout} {target}"
                    
                    # Use execute_command internally
                    result = await execute_command(cmd, timeout=timeout+5)
                    return {
                        "target": target,
                        "output": result.get("stdout", ""),
                        "success": result.get("return_code", -1) == 0
                    }
                
                elif operation == "port_scan":
                    if not target or not port:
                        return {"error": "Target and port are required for port scan"}
                    
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    
                    try:
                        result = sock.connect_ex((target, port))
                        sock.close()
                        return {
                            "target": target,
                            "port": port,
                            "open": result == 0,
                            "status": "open" if result == 0 else "closed"
                        }
                    except socket.gaierror:
                        return {"error": f"Failed to resolve hostname: {target}"}
                    except Exception as e:
                        return {"error": str(e)}
                
                elif operation == "connection_info":
                    connections = []
                    for conn in psutil.net_connections():
                        if conn.status != 'NONE':
                            connections.append({
                                "family": str(conn.family),
                                "type": str(conn.type),
                                "local_address": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                                "remote_address": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                                "status": conn.status,
                                "pid": conn.pid
                            })
                    
                    return {
                        "connections": connections,
                        "count": len(connections)
                    }
                
                elif operation == "dns_lookup":
                    if not target:
                        return {"error": "Target is required for DNS lookup"}
                    
                    import socket
                    try:
                        # Forward lookup
                        ips = socket.gethostbyname_ex(target)
                        result = {
                            "hostname": ips[0],
                            "aliases": ips[1],
                            "addresses": ips[2]
                        }
                        
                        # Reverse lookup for first IP
                        if ips[2]:
                            try:
                                reverse = socket.gethostbyaddr(ips[2][0])
                                result["reverse_lookup"] = {
                                    "hostname": reverse[0],
                                    "aliases": reverse[1]
                                }
                            except:
                                pass
                        
                        return result
                    except socket.gaierror as e:
                        return {"error": f"DNS lookup failed: {str(e)}"}
                
                else:
                    return {"error": f"Unknown operation: {operation}"}
                
            except Exception as e:
                logger.error(f"Error in network operation: {e}")
                return {"error": str(e)}
        
        # Tool: registry_operations (Windows only)
        @self.server.tool()
        async def registry_operations(
            operation: str,
            hive: str,
            key_path: str,
            value_name: Optional[str] = None,
            value_data: Optional[Any] = None,
            value_type: Optional[str] = "REG_SZ"
        ) -> Dict[str, Any]:
            """
            Операции с реестром Windows
            
            Args:
                operation: Тип операции (read_key, write_key, delete_key, list_subkeys)
                hive: Корневой раздел (HKEY_LOCAL_MACHINE, HKEY_CURRENT_USER, etc.)
                key_path: Путь к ключу
                value_name: Имя значения
                value_data: Данные для записи
                value_type: Тип значения (REG_SZ, REG_DWORD, etc.)
                
            Returns:
                Dict с результатом операции
            """
            if platform.system() != "Windows":
                return {"error": "Registry operations are only available on Windows"}
            
            if not winreg:
                return {"error": "winreg module not available"}
            
            if not self.security.config.get("enable_dangerous_operations", False):
                return {"error": "Registry operations are disabled by security policy"}
            
            try:
                self.security.log_operation("registry_operations", {
                    "operation": operation,
                    "hive": hive,
                    "key_path": key_path,
                    "value_name": value_name
                })
                
                # Map hive names to constants
                hive_map = {
                    "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
                    "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
                    "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
                    "HKEY_USERS": winreg.HKEY_USERS,
                    "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG
                }
                
                if hive not in hive_map:
                    return {"error": f"Unknown hive: {hive}"}
                
                hive_key = hive_map[hive]
                
                if operation == "read_key":
                    try:
                        with winreg.OpenKey(hive_key, key_path) as key:
                            if value_name:
                                value, reg_type = winreg.QueryValueEx(key, value_name)
                                return {
                                    "value": value,
                                    "type": reg_type,
                                    "value_name": value_name
                                }
                            else:
                                # List all values
                                values = []
                                i = 0
                                while True:
                                    try:
                                        name, data, reg_type = winreg.EnumValue(key, i)
                                        values.append({
                                            "name": name,
                                            "data": data,
                                            "type": reg_type
                                        })
                                        i += 1
                                    except WindowsError:
                                        break
                                return {"values": values}
                    except FileNotFoundError:
                        return {"error": "Registry key not found"}
                
                elif operation == "write_key":
                    if not value_name or value_data is None:
                        return {"error": "value_name and value_data are required for write operation"}
                    
                    type_map = {
                        "REG_SZ": winreg.REG_SZ,
                        "REG_DWORD": winreg.REG_DWORD,
                        "REG_BINARY": winreg.REG_BINARY,
                        "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ,
                        "REG_MULTI_SZ": winreg.REG_MULTI_SZ
                    }
                    
                    reg_type = type_map.get(value_type, winreg.REG_SZ)
                    
                    with winreg.CreateKeyEx(hive_key, key_path) as key:
                        winreg.SetValueEx(key, value_name, 0, reg_type, value_data)
                    
                    return {"success": True, "written": f"{hive}\\{key_path}\\{value_name}"}
                
                elif operation == "delete_key":
                    if value_name:
                        # Delete value
                        with winreg.OpenKey(hive_key, key_path, 0, winreg.KEY_WRITE) as key:
                            winreg.DeleteValue(key, value_name)
                        return {"success": True, "deleted_value": value_name}
                    else:
                        # Delete key
                        winreg.DeleteKey(hive_key, key_path)
                        return {"success": True, "deleted_key": key_path}
                
                elif operation == "list_subkeys":
                    try:
                        with winreg.OpenKey(hive_key, key_path) as key:
                            subkeys = []
                            i = 0
                            while True:
                                try:
                                    subkey = winreg.EnumKey(key, i)
                                    subkeys.append(subkey)
                                    i += 1
                                except WindowsError:
                                    break
                            return {"subkeys": subkeys, "count": len(subkeys)}
                    except FileNotFoundError:
                        return {"error": "Registry key not found"}
                
                else:
                    return {"error": f"Unknown operation: {operation}"}
                
            except Exception as e:
                logger.error(f"Error in registry operation: {e}")
                return {"error": str(e)}
        
        # Tool: service_management
        @self.server.tool()
        async def service_management(
            action: str,
            service_name: Optional[str] = None,
            startup_type: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Управление службами системы
            
            Args:
                action: Действие (list, start, stop, restart, status, configure)
                service_name: Имя службы
                startup_type: Тип запуска (auto, manual, disabled) для configure
                
            Returns:
                Dict с результатом операции
            """
            try:
                self.security.log_operation("service_management", {
                    "action": action,
                    "service_name": service_name
                })
                
                if platform.system() == "Windows":
                    if action == "list":
                        # List all services
                        cmd = "Get-Service | Select-Object Name, DisplayName, Status, StartType | ConvertTo-Json"
                        result = await execute_command(cmd, timeout=10)
                        if result.get("return_code") == 0:
                            services = json.loads(result.get("stdout", "[]"))
                            return {"services": services, "count": len(services)}
                        else:
                            return {"error": "Failed to list services"}
                    
                    elif action in ["start", "stop", "restart"]:
                        if not service_name:
                            return {"error": "service_name is required"}
                        
                        if not self.security.config.get("enable_dangerous_operations", False):
                            return {"error": "Service control is disabled by security policy"}
                        
                        ps_action = {
                            "start": "Start-Service",
                            "stop": "Stop-Service",
                            "restart": "Restart-Service"
                        }[action]
                        
                        cmd = f"{ps_action} -Name '{service_name}' -Force"
                        result = await execute_command(cmd, timeout=30)
                        
                        if result.get("return_code") == 0:
                            return {"success": True, "action": action, "service": service_name}
                        else:
                            return {"error": result.get("stderr", "Failed to control service")}
                    
                    elif action == "status":
                        if not service_name:
                            return {"error": "service_name is required"}
                        
                        cmd = f"Get-Service -Name '{service_name}' | Select-Object Name, DisplayName, Status, StartType | ConvertTo-Json"
                        result = await execute_command(cmd, timeout=5)
                        
                        if result.get("return_code") == 0:
                            service_info = json.loads(result.get("stdout", "{}"))
                            return service_info
                        else:
                            return {"error": "Service not found"}
                    
                    elif action == "configure":
                        if not service_name or not startup_type:
                            return {"error": "service_name and startup_type are required"}
                        
                        if not self.security.config.get("enable_dangerous_operations", False):
                            return {"error": "Service configuration is disabled by security policy"}
                        
                        type_map = {
                            "auto": "Automatic",
                            "manual": "Manual",
                            "disabled": "Disabled"
                        }
                        
                        if startup_type not in type_map:
                            return {"error": f"Invalid startup_type: {startup_type}"}
                        
                        cmd = f"Set-Service -Name '{service_name}' -StartupType {type_map[startup_type]}"
                        result = await execute_command(cmd, timeout=10)
                        
                        if result.get("return_code") == 0:
                            return {"success": True, "service": service_name, "startup_type": startup_type}
                        else:
                            return {"error": result.get("stderr", "Failed to configure service")}
                    
                else:  # Linux/macOS
                    # Use systemctl for systemd systems
                    if action == "list":
                        cmd = "systemctl list-units --type=service --all --no-pager --output=json"
                        result = await execute_command(cmd, timeout=10)
                        
                        if result.get("return_code") == 0:
                            # Parse systemctl output
                            output = result.get("stdout", "")
                            services = []
                            for line in output.strip().split('\n')[1:]:  # Skip header
                                parts = line.split()
                                if len(parts) >= 4:
                                    services.append({
                                        "name": parts[0],
                                        "status": parts[2],
                                        "description": " ".join(parts[4:])
                                    })
                            return {"services": services[:50], "count": len(services)}  # Limit output
                        else:
                            return {"error": "Failed to list services"}
                    
                    elif action in ["start", "stop", "restart", "status"]:
                        if not service_name:
                            return {"error": "service_name is required"}
                        
                        if action != "status" and not self.security.config.get("enable_dangerous_operations", False):
                            return {"error": "Service control is disabled by security policy"}
                        
                        cmd = f"systemctl {action} {service_name}"
                        result = await execute_command(cmd, timeout=30)
                        
                        if result.get("return_code") == 0 or action == "status":
                            return {
                                "success": result.get("return_code") == 0,
                                "action": action,
                                "service": service_name,
                                "output": result.get("stdout", "")
                            }
                        else:
                            return {"error": result.get("stderr", "Failed to control service")}
                
                return {"error": f"Unknown action: {action}"}
                
            except Exception as e:
                logger.error(f"Error in service management: {e}")
                return {"error": str(e)}
        
        # Tool: environment_management
        @self.server.tool()
        async def environment_management(
            action: str,
            name: Optional[str] = None,
            value: Optional[str] = None,
            scope: str = "user"
        ) -> Dict[str, Any]:
            """
            Управление переменными окружения
            
            Args:
                action: Действие (list, get, set, delete)
                name: Имя переменной
                value: Значение переменной (для set)
                scope: Область видимости (user, system) - для Windows
                
            Returns:
                Dict с результатом операции
            """
            try:
                self.security.log_operation("environment_management", {
                    "action": action,
                    "name": name,
                    "scope": scope
                })
                
                if action == "list":
                    env_vars = dict(os.environ)
                    return {"variables": env_vars, "count": len(env_vars)}
                
                elif action == "get":
                    if not name:
                        return {"error": "name is required for get action"}
                    
                    value = os.environ.get(name)
                    if value is not None:
                        return {"name": name, "value": value}
                    else:
                        return {"error": f"Environment variable '{name}' not found"}
                
                elif action == "set":
                    if not name or value is None:
                        return {"error": "name and value are required for set action"}
                    
                    if not self.security.config.get("enable_dangerous_operations", False):
                        return {"error": "Setting environment variables is disabled by security policy"}
                    
                    # Set in current process
                    os.environ[name] = value
                    
                    # Try to set persistently based on platform
                    if platform.system() == "Windows":
                        if scope == "system" and not self.security.config.get("enable_dangerous_operations", False):
                            return {"error": "Setting system environment variables requires dangerous operations enabled"}
                        
                        cmd = f'setx {name} "{value}"' if scope == "user" else f'setx {name} "{value}" /M'
                        result = await execute_command(cmd, timeout=5)
                        
                        if result.get("return_code") == 0:
                            return {"success": True, "name": name, "value": value, "scope": scope}
                        else:
                            return {"warning": "Set in current process only, persistent set failed"}
                    
                    else:  # Linux/macOS
                        # For bash
                        profile_file = Path.home() / ".bashrc"
                        if profile_file.exists():
                            with open(profile_file, 'a') as f:
                                f.write(f'\nexport {name}="{value}"\n')
                        
                        return {"success": True, "name": name, "value": value, "note": "Added to .bashrc"}
                
                elif action == "delete":
                    if not name:
                        return {"error": "name is required for delete action"}
                    
                    if not self.security.config.get("enable_dangerous_operations", False):
                        return {"error": "Deleting environment variables is disabled by security policy"}
                    
                    # Delete from current process
                    if name in os.environ:
                        del os.environ[name]
                    
                    if platform.system() == "Windows":
                        # Delete using reg command
                        cmd = f'reg delete "HKCU\\Environment" /v {name} /f'
                        await execute_command(cmd, timeout=5)
                    
                    return {"success": True, "deleted": name}
                
                else:
                    return {"error": f"Unknown action: {action}"}
                
            except Exception as e:
                logger.error(f"Error in environment management: {e}")
                return {"error": str(e)}
        
        # Tool: scheduled_tasks
        @self.server.tool()
        async def scheduled_tasks(
            action: str,
            task_name: Optional[str] = None,
            command: Optional[str] = None,
            schedule: Optional[str] = None,
            description: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Управление запланированными задачами
            
            Args:
                action: Действие (list, create, delete, run, info)
                task_name: Имя задачи
                command: Команда для выполнения
                schedule: Расписание (daily, weekly, once, at startup)
                description: Описание задачи
                
            Returns:
                Dict с результатом операции
            """
            try:
                if not self.security.config.get("enable_dangerous_operations", False):
                    return {"error": "Scheduled tasks management is disabled by security policy"}
                
                self.security.log_operation("scheduled_tasks", {
                    "action": action,
                    "task_name": task_name
                })
                
                if platform.system() == "Windows":
                    if action == "list":
                        cmd = "schtasks /query /fo json"
                        result = await execute_command(cmd, timeout=10)
                        
                        if result.get("return_code") == 0:
                            # Parse output
                            output = result.get("stdout", "")
                            tasks = []
                            for line in output.strip().split('\n'):
                                if line.strip() and not line.startswith('='):
                                    parts = line.split()
                                    if len(parts) >= 3:
                                        tasks.append({
                                            "name": parts[0],
                                            "next_run": parts[1],
                                            "status": parts[2]
                                        })
                            return {"tasks": tasks[:50], "count": len(tasks)}
                        else:
                            return {"error": "Failed to list tasks"}
                    
                    elif action == "create":
                        if not task_name or not command or not schedule:
                            return {"error": "task_name, command, and schedule are required"}
                        
                        schedule_map = {
                            "daily": "/sc daily",
                            "weekly": "/sc weekly",
                            "once": "/sc once",
                            "startup": "/sc onstart"
                        }
                        
                        if schedule not in schedule_map:
                            return {"error": f"Invalid schedule: {schedule}"}
                        
                        cmd = f'schtasks /create /tn "{task_name}" /tr "{command}" {schedule_map[schedule]} /f'
                        if description:
                            cmd += f' /d "{description}"'
                        
                        result = await execute_command(cmd, timeout=10)
                        
                        if result.get("return_code") == 0:
                            return {"success": True, "created": task_name}
                        else:
                            return {"error": result.get("stderr", "Failed to create task")}
                    
                    elif action == "delete":
                        if not task_name:
                            return {"error": "task_name is required"}
                        
                        cmd = f'schtasks /delete /tn "{task_name}" /f'
                        result = await execute_command(cmd, timeout=10)
                        
                        if result.get("return_code") == 0:
                            return {"success": True, "deleted": task_name}
                        else:
                            return {"error": result.get("stderr", "Failed to delete task")}
                    
                    elif action == "run":
                        if not task_name:
                            return {"error": "task_name is required"}
                        
                        cmd = f'schtasks /run /tn "{task_name}"'
                        result = await execute_command(cmd, timeout=10)
                        
                        if result.get("return_code") == 0:
                            return {"success": True, "running": task_name}
                        else:
                            return {"error": result.get("stderr", "Failed to run task")}
                
                else:  # Linux/macOS - use cron
                    if action == "list":
                        cmd = "crontab -l"
                        result = await execute_command(cmd, timeout=5)
                        
                        if result.get("return_code") == 0:
                            cron_lines = result.get("stdout", "").strip().split('\n')
                            tasks = []
                            for line in cron_lines:
                                if line and not line.startswith('#'):
                                    tasks.append({"entry": line})
                            return {"tasks": tasks, "count": len(tasks)}
                        else:
                            return {"tasks": [], "count": 0}
                    
                    elif action == "create":
                        if not command or not schedule:
                            return {"error": "command and schedule are required"}
                        
                        # Simple schedule mapping for cron
                        schedule_map = {
                            "daily": "0 0 * * *",
                            "weekly": "0 0 * * 0",
                            "hourly": "0 * * * *"
                        }
                        
                        cron_schedule = schedule_map.get(schedule, schedule)
                        cron_entry = f"{cron_schedule} {command}"
                        
                        # Get current crontab
                        result = await execute_command("crontab -l", timeout=5)
                        current_cron = result.get("stdout", "") if result.get("return_code") == 0 else ""
                        
                        # Add new entry
                        new_cron = current_cron + f"\n{cron_entry}\n"
                        
                        # Set new crontab
                        cmd = f'echo "{new_cron}" | crontab -'
                        result = await execute_command(cmd, timeout=5)
                        
                        if result.get("return_code") == 0:
                            return {"success": True, "created": cron_entry}
                        else:
                            return {"error": "Failed to create cron job"}
                
                return {"error": f"Unknown action: {action}"}
                
            except Exception as e:
                logger.error(f"Error in scheduled tasks: {e}")
                return {"error": str(e)}
        
        # Tool: backup_operations
        @self.server.tool()
        async def backup_operations(
            operation: str,
            source: str,
            destination: Optional[str] = None,
            compress: bool = True,
            include_pattern: Optional[str] = None,
            exclude_pattern: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Операции резервного копирования
            
            Args:
                operation: Тип операции (create, restore, list)
                source: Источник для резервного копирования
                destination: Путь назначения
                compress: Сжимать ли архив
                include_pattern: Паттерн включения файлов
                exclude_pattern: Паттерн исключения файлов
                
            Returns:
                Dict с результатом операции
            """
            try:
                self.security.log_operation("backup_operations", {
                    "operation": operation,
                    "source": source,
                    "destination": destination
                })
                
                source_path = Path(source)
                
                if operation == "create":
                    if not source_path.exists():
                        return {"error": "Source path does not exist"}
                    
                    # Default destination
                    if not destination:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        backup_name = f"{source_path.name}_backup_{timestamp}"
                        if compress:
                            backup_name += ".tar.gz"
                        destination = str(Path.home() / "backups" / backup_name)
                    
                    dest_path = Path(destination)
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    if compress:
                        import tarfile
                        
                        with tarfile.open(dest_path, "w:gz") as tar:
                            def filter_func(tarinfo):
                                if exclude_pattern and exclude_pattern in tarinfo.name:
                                    return None
                                if include_pattern and include_pattern not in tarinfo.name:
                                    return None
                                return tarinfo
                            
                            tar.add(source_path, arcname=source_path.name, filter=filter_func)
                        
                        return {
                            "success": True,
                            "backup_path": str(dest_path),
                            "size": dest_path.stat().st_size,
                            "compressed": True
                        }
                    
                    else:
                        # Simple copy for directories
                        if source_path.is_dir():
                            shutil.copytree(source_path, dest_path)
                        else:
                            shutil.copy2(source_path, dest_path)
                        
                        return {
                            "success": True,
                            "backup_path": str(dest_path),
                            "compressed": False
                        }
                
                elif operation == "restore":
                    if not source_path.exists():
                        return {"error": "Backup file does not exist"}
                    
                    if not destination:
                        return {"error": "Destination is required for restore operation"}
                    
                    dest_path = Path(destination)
                    
                    if source_path.suffix == ".gz" or source_path.suffix == ".tar":
                        import tarfile
                        
                        with tarfile.open(source_path, "r:*") as tar:
                            tar.extractall(dest_path)
                        
                        return {
                            "success": True,
                            "restored_to": str(dest_path),
                            "from_backup": str(source_path)
                        }
                    
                    else:
                        # Simple copy
                        if source_path.is_dir():
                            shutil.copytree(source_path, dest_path)
                        else:
                            shutil.copy2(source_path, dest_path)
                        
                        return {
                            "success": True,
                            "restored_to": str(dest_path)
                        }
                
                elif operation == "list":
                    # List backups in default location
                    backup_dir = Path.home() / "backups"
                    if not backup_dir.exists():
                        return {"backups": [], "count": 0}
                    
                    backups = []
                    for backup_file in backup_dir.iterdir():
                        if backup_file.is_file() and "backup" in backup_file.name:
                            backups.append({
                                "name": backup_file.name,
                                "size": backup_file.stat().st_size,
                                "created": datetime.fromtimestamp(backup_file.stat().st_ctime).isoformat(),
                                "path": str(backup_file)
                            })
                    
                    return {
                        "backups": sorted(backups, key=lambda x: x["created"], reverse=True),
                        "count": len(backups)
                    }
                
                else:
                    return {"error": f"Unknown operation: {operation}"}
                
            except Exception as e:
                logger.error(f"Error in backup operations: {e}")
                return {"error": str(e)}
        
        # Tool: automation_tools
        @self.server.tool()
        async def automation_tools(
            action: str,
            x: Optional[int] = None,
            y: Optional[int] = None,
            text: Optional[str] = None,
            key: Optional[str] = None,
            button: str = "left",
            duration: float = 0.25
        ) -> Dict[str, Any]:
            """
            Инструменты автоматизации GUI (требует pyautogui)
            
            Args:
                action: Действие (mouse_move, mouse_click, type_text, press_key, screenshot, get_position)
                x, y: Координаты для мыши
                text: Текст для ввода
                key: Клавиша для нажатия
                button: Кнопка мыши (left, right, middle)
                duration: Длительность действия
                
            Returns:
                Dict с результатом операции
            """
            try:
                import pyautogui
                pyautogui.FAILSAFE = True  # Safety feature
                
                self.security.log_operation("automation_tools", {
                    "action": action,
                    "x": x,
                    "y": y
                })
                
                if action == "mouse_move":
                    if x is None or y is None:
                        return {"error": "x and y coordinates are required"}
                    
                    pyautogui.moveTo(x, y, duration=duration)
                    return {"success": True, "moved_to": {"x": x, "y": y}}
                
                elif action == "mouse_click":
                    if x is not None and y is not None:
                        pyautogui.click(x, y, button=button)
                    else:
                        pyautogui.click(button=button)
                    
                    return {"success": True, "clicked": button}
                
                elif action == "type_text":
                    if not text:
                        return {"error": "text is required"}
                    
                    pyautogui.typewrite(text, interval=0.05)
                    return {"success": True, "typed": text}
                
                elif action == "press_key":
                    if not key:
                        return {"error": "key is required"}
                    
                    pyautogui.press(key)
                    return {"success": True, "pressed": key}
                
                elif action == "screenshot":
                    screenshot = pyautogui.screenshot()
                    
                    # Save to default location
                    screenshot_dir = Path.home() / "screenshots"
                    screenshot_dir.mkdir(exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = screenshot_dir / f"screenshot_{timestamp}.png"
                    screenshot.save(screenshot_path)
                    
                    return {
                        "success": True,
                        "saved_to": str(screenshot_path),
                        "resolution": {"width": screenshot.width, "height": screenshot.height}
                    }
                
                elif action == "get_position":
                    x, y = pyautogui.position()
                    return {"x": x, "y": y}
                
                else:
                    return {"error": f"Unknown action: {action}"}
                
            except ImportError:
                return {"error": "pyautogui is not installed. Install with: pip install pyautogui"}
            except Exception as e:
                logger.error(f"Error in automation tools: {e}")
                return {"error": str(e)}
    
    async def run(self):
        """Запуск MCP-сервера"""
        logger.info("Starting PC Control MCP Server...")
        logger.warning("⚠️  This server provides FULL SYSTEM ACCESS! Use with extreme caution!")
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)


async def main():
    """Точка входа"""
    server = PCControlMCP()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())