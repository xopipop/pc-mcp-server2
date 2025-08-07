#!/usr/bin/env python3
"""
PC Control MCP Server - Полнофункциональный MCP-сервер для управления компьютером

КРИТИЧЕСКИЕ ПРЕДУПРЕЖДЕНИЯ БЕЗОПАСНОСТИ:
⚠️ ВНИМАНИЕ: Этот сервер предоставляет ПОЛНЫЙ ДОСТУП к вашей системе!
⚠️ Используйте ТОЛЬКО в изолированной среде или виртуальной машине!
⚠️ ОБЯЗАТЕЛЬНО создайте резервные копии перед использованием!
⚠️ НЕ используйте на продакшн-системах или с важными данными!
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

# GUI automation imports
try:
    import pyautogui
    from PIL import Image
    GUI_AUTOMATION_AVAILABLE = True
except ImportError:
    GUI_AUTOMATION_AVAILABLE = False
    logger.warning("pyautogui not available. GUI automation features will be disabled.")

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
    "enable_dangerous_operations": False,  # Set to True at your own risk!
    "gui_automation": {
        "enabled": True,
        "safe_mode": True,  # Adds delays and safety checks
        "max_screen_resolution": (1920, 1080),  # Maximum allowed screen coordinates
        "min_delay": 0.1,  # Minimum delay between actions
        "screenshot_directory": str(Path.home() / ".pc_control_mcp" / "screenshots")
    }
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
        """Логирование операций"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "details": details
        }
        self.operation_log.append(log_entry)
        logger.info(f"Operation logged: {operation}")


class GUIAutomationManager:
    """Менеджер GUI автоматизации"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("gui_automation", {})
        self.screenshot_dir = Path(self.config.get("screenshot_directory", ""))
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        if GUI_AUTOMATION_AVAILABLE and self.config.get("enabled", True):
            # Настройка pyautogui для безопасной работы
            if self.config.get("safe_mode", True):
                pyautogui.FAILSAFE = True  # Остановка при движении мыши в угол экрана
                pyautogui.PAUSE = self.config.get("min_delay", 0.1)  # Задержка между действиями
            
            logger.info("GUI automation initialized successfully")
        else:
            logger.warning("GUI automation is disabled or pyautogui not available")
    
    def validate_coordinates(self, x: int, y: int) -> bool:
        """Проверка валидности координат экрана"""
        max_x, max_y = self.config.get("max_screen_resolution", (1920, 1080))
        if x < 0 or y < 0 or x > max_x or y > max_y:
            logger.warning(f"Invalid coordinates: ({x}, {y})")
            return False
        return True
    
    def mouse_move(self, x: int, y: int, duration: float = 0.25) -> Dict[str, Any]:
        """Перемещение мыши в указанную позицию"""
        try:
            if not self.validate_coordinates(x, y):
                return {"error": "Invalid coordinates"}
            
            if not GUI_AUTOMATION_AVAILABLE:
                return {"error": "GUI automation not available"}
            
            pyautogui.moveTo(x, y, duration=duration)
            return {"success": True, "position": (x, y)}
            
        except Exception as e:
            logger.error(f"Error moving mouse: {e}")
            return {"error": str(e)}
    
    def mouse_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> Dict[str, Any]:
        """Клик мышью в указанной позиции"""
        try:
            if not self.validate_coordinates(x, y):
                return {"error": "Invalid coordinates"}
            
            if not GUI_AUTOMATION_AVAILABLE:
                return {"error": "GUI automation not available"}
            
            # Сначала перемещаем мышь
            pyautogui.moveTo(x, y, duration=0.1)
            # Затем кликаем
            pyautogui.click(x, y, clicks=clicks, button=button)
            
            return {"success": True, "click": {"x": x, "y": y, "button": button, "clicks": clicks}}
            
        except Exception as e:
            logger.error(f"Error clicking mouse: {e}")
            return {"error": str(e)}
    
    def type_text(self, text: str, interval: float = 0.01) -> Dict[str, Any]:
        """Ввод текста"""
        try:
            if not GUI_AUTOMATION_AVAILABLE:
                return {"error": "GUI automation not available"}
            
            pyautogui.typewrite(text, interval=interval)
            return {"success": True, "text_length": len(text)}
            
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return {"error": str(e)}
    
    def press_key(self, key: str) -> Dict[str, Any]:
        """Нажатие клавиши"""
        try:
            if not GUI_AUTOMATION_AVAILABLE:
                return {"error": "GUI automation not available"}
            
            pyautogui.press(key)
            return {"success": True, "key": key}
            
        except Exception as e:
            logger.error(f"Error pressing key: {e}")
            return {"error": str(e)}
    
    def hotkey(self, *keys) -> Dict[str, Any]:
        """Комбинация клавиш"""
        try:
            if not GUI_AUTOMATION_AVAILABLE:
                return {"error": "GUI automation not available"}
            
            pyautogui.hotkey(*keys)
            return {"success": True, "keys": keys}
            
        except Exception as e:
            logger.error(f"Error pressing hotkey: {e}")
            return {"error": str(e)}
    
    def screenshot(self, region: Optional[tuple] = None) -> Dict[str, Any]:
        """Создание скриншота"""
        try:
            if not GUI_AUTOMATION_AVAILABLE:
                return {"error": "GUI automation not available"}
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = self.screenshot_dir / filename
            
            screenshot = pyautogui.screenshot(region=region)
            screenshot.save(filepath)
            
            return {
                "success": True,
                "filepath": str(filepath),
                "size": screenshot.size,
                "region": region
            }
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return {"error": str(e)}
    
    def get_position(self) -> Dict[str, Any]:
        """Получение текущей позиции мыши"""
        try:
            if not GUI_AUTOMATION_AVAILABLE:
                return {"error": "GUI automation not available"}
            
            x, y = pyautogui.position()
            return {"success": True, "position": (x, y)}
            
        except Exception as e:
            logger.error(f"Error getting mouse position: {e}")
            return {"error": str(e)}
    
    def get_screen_size(self) -> Dict[str, Any]:
        """Получение размера экрана"""
        try:
            if not GUI_AUTOMATION_AVAILABLE:
                return {"error": "GUI automation not available"}
            
            width, height = pyautogui.size()
            return {"success": True, "size": (width, height)}
            
        except Exception as e:
            logger.error(f"Error getting screen size: {e}")
            return {"error": str(e)}


class PCControlMCP:
    """Основной класс MCP-сервера для управления компьютером"""
    
    def __init__(self):
        self.server = Server("pc-control-mcp")
        self.security = SecurityManager(SECURITY_CONFIG)
        self.gui_automation = GUIAutomationManager(SECURITY_CONFIG)
        self._setup_tools()
        
    def _setup_tools(self):
        """Регистрация всех инструментов"""
        
        # Tool: execute_command
        @self.server.call_tool()
        async def execute_command(command: str, working_directory: Optional[str] = None, timeout: Optional[int] = 30) -> Dict[str, Any]:
            """Выполнение системных команд"""
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
        @self.server.call_tool()
        async def file_operations(operation: str, path: str, content: Optional[str] = None, destination: Optional[str] = None, encoding: str = 'utf-8') -> Dict[str, Any]:
            """Операции с файловой системой"""
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
                        return {"error": "File does not exist"}
                    
                    if path_obj.stat().st_size > SECURITY_CONFIG["max_file_size"]:
                        return {"error": "File too large"}
                    
                    with open(path_obj, 'r', encoding=encoding) as f:
                        content = f.read()
                    return {"content": content}
                
                elif operation == "write":
                    path_obj.parent.mkdir(parents=True, exist_ok=True)
                    with open(path_obj, 'w', encoding=encoding) as f:
                        f.write(content or "")
                    return {"success": True, "message": "File written successfully"}
                
                elif operation == "delete":
                    if path_obj.is_file():
                        path_obj.unlink()
                    elif path_obj.is_dir():
                        shutil.rmtree(path_obj)
                    else:
                        return {"error": "Path does not exist"}
                    return {"success": True, "message": "Deleted successfully"}
                
                elif operation == "create_dir":
                    path_obj.mkdir(parents=True, exist_ok=True)
                    return {"success": True, "message": "Directory created successfully"}
                
                elif operation == "list_dir":
                    if not path_obj.exists():
                        return {"error": "Directory does not exist"}
                    
                    items = []
                    for item in path_obj.iterdir():
                        items.append({
                            "name": item.name,
                            "type": "file" if item.is_file() else "directory",
                            "size": item.stat().st_size if item.is_file() else None
                        })
                    return {"items": items}
                
                elif operation == "copy":
                    if not path_obj.exists():
                        return {"error": "Source does not exist"}
                    
                    dest_obj = Path(destination)
                    if path_obj.is_file():
                        shutil.copy2(path_obj, dest_obj)
                    else:
                        shutil.copytree(path_obj, dest_obj, dirs_exist_ok=True)
                    return {"success": True, "message": "Copied successfully"}
                
                elif operation == "move":
                    if not path_obj.exists():
                        return {"error": "Source does not exist"}
                    
                    dest_obj = Path(destination)
                    shutil.move(str(path_obj), str(dest_obj))
                    return {"success": True, "message": "Moved successfully"}
                
                elif operation == "rename":
                    if not path_obj.exists():
                        return {"error": "File does not exist"}
                    
                    new_name = Path(destination)
                    path_obj.rename(new_name)
                    return {"success": True, "message": "Renamed successfully"}
                
                else:
                    return {"error": "Unknown operation"}
                    
            except Exception as e:
                logger.error(f"Error in file operation: {e}")
                return {"error": str(e)}
        
        # Tool: system_info
        @self.server.call_tool()
        async def system_info(info_type: str) -> Dict[str, Any]:
            """Получение системной информации"""
            try:
                if info_type == "os_info":
                    return {
                        "platform": platform.system(),
                        "platform_version": platform.version(),
                        "architecture": platform.machine(),
                        "processor": platform.processor(),
                        "hostname": platform.node()
                    }
                
                elif info_type == "cpu":
                    cpu_percent = psutil.cpu_percent(interval=1)
                    cpu_count = psutil.cpu_count()
                    cpu_freq = psutil.cpu_freq()
                    return {
                        "cpu_percent": cpu_percent,
                        "cpu_count": cpu_count,
                        "cpu_freq": {
                            "current": cpu_freq.current if cpu_freq else None,
                            "min": cpu_freq.min if cpu_freq else None,
                            "max": cpu_freq.max if cpu_freq else None
                        }
                    }
                
                elif info_type == "memory":
                    memory = psutil.virtual_memory()
                    swap = psutil.swap_memory()
                    return {
                        "memory": {
                            "total": memory.total,
                            "available": memory.available,
                            "percent": memory.percent,
                            "used": memory.used,
                            "free": memory.free
                        },
                        "swap": {
                            "total": swap.total,
                            "used": swap.used,
                            "free": swap.free,
                            "percent": swap.percent
                        }
                    }
                
                elif info_type == "disk":
                    partitions = []
                    for partition in psutil.disk_partitions():
                        try:
                            usage = psutil.disk_usage(partition.mountpoint)
                            partitions.append({
                                "device": partition.device,
                                "mountpoint": partition.mountpoint,
                                "fstype": partition.fstype,
                                "total": usage.total,
                                "used": usage.used,
                                "free": usage.free,
                                "percent": usage.percent
                            })
                        except PermissionError:
                            continue
                    return {"partitions": partitions}
                
                elif info_type == "processes":
                    processes = []
                    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                        try:
                            processes.append(proc.info)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    # Sort by CPU usage
                    processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
                    return {"processes": processes[:20]}  # Top 20 processes
                
                elif info_type == "network":
                    interfaces = []
                    for name, stats in psutil.net_if_stats().items():
                        try:
                            addrs = psutil.net_if_addrs().get(name, [])
                            interfaces.append({
                                "name": name,
                                "is_up": stats.isup,
                                "speed": stats.speed,
                                "addresses": [addr.address for addr in addrs if addr.family == psutil.AF_INET]
                            })
                        except Exception:
                            continue
                    return {"interfaces": interfaces}
                
                else:
                    return {"error": "Unknown info type"}
                    
            except Exception as e:
                logger.error(f"Error getting system info: {e}")
                return {"error": str(e)}
        
        # Tool: automation_tools
        @self.server.call_tool()
        async def automation_tools(action: str, x: Optional[int] = None, y: Optional[int] = None, 
                                         text: Optional[str] = None, key: Optional[str] = None, 
                                         button: str = "left", duration: float = 0.25, keys: Optional[str] = None) -> Dict[str, Any]:
            """Инструменты GUI автоматизации"""
            try:
                # Log operation
                self.security.log_operation("automation_tools", {
                    "action": action,
                    "coordinates": (x, y) if x is not None and y is None else None,
                    "text_length": len(text) if text else None,
                    "key": key
                })
                
                if action == "mouse_move":
                    if x is None or y is None:
                        return {"error": "Coordinates (x, y) are required for mouse_move"}
                    return self.gui_automation.mouse_move(x, y, duration)
                
                elif action == "mouse_click":
                    if x is None or y is None:
                        return {"error": "Coordinates (x, y) are required for mouse_click"}
                    return self.gui_automation.mouse_click(x, y, button)
                
                elif action == "type_text":
                    if not text:
                        return {"error": "Text is required for type_text"}
                    return self.gui_automation.type_text(text)
                
                elif action == "press_key":
                    if not key:
                        return {"error": "Key is required for press_key"}
                    return self.gui_automation.press_key(key)
                
                elif action == "screenshot":
                    return self.gui_automation.screenshot()
                
                elif action == "get_position":
                    return self.gui_automation.get_position()
                
                elif action == "get_screen_size":
                    return self.gui_automation.get_screen_size()
                
                elif action == "hotkey":
                    if not keys:
                        return {"error": "Keys are required for hotkey action"}
                    # Разбираем ключи из строки (например, "alt+f4" -> ["alt", "f4"])
                    key_list = keys.split("+")
                    return self.gui_automation.hotkey(*key_list)
                
                else:
                    return {"error": f"Unknown action: {action}"}
                    
            except Exception as e:
                logger.error(f"Error in automation_tools: {e}")
                return {"error": str(e)}
        
    async def run(self):
        """Запуск сервера"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                None
            )


async def main():
    """Основная функция"""
    server = PCControlMCP()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
