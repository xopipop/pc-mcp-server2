#!/usr/bin/env python3
"""
Cursor IDE MCP Server Launcher
Упрощенный запуск PC Control MCP Server для Cursor IDE
"""

import sys
import os
import subprocess
import json
from pathlib import Path
import platform

def check_python_version():
    """Проверка версии Python"""
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        print(f"   Текущая версия: {sys.version}")
        return False
    return True

def check_dependencies():
    """Проверка установленных зависимостей"""
    try:
        import mcp
        import pydantic
        import yaml
        import psutil
        return True
    except ImportError as e:
        print(f"❌ Отсутствуют зависимости: {e}")
        print("\n📦 Установка зависимостей...")
        
        # Определяем команду pip
        pip_cmd = [sys.executable, "-m", "pip"]
        
        # Устанавливаем зависимости
        subprocess.run(pip_cmd + ["install", "-r", "requirements.txt"], check=True)
        print("✅ Зависимости установлены")
        return True

def check_venv():
    """Проверка виртуального окружения"""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if not in_venv:
        print("⚠️  Рекомендуется использовать виртуальное окружение")
        print("   Создать: python -m venv venv")
        if platform.system() == "Windows":
            print("   Активировать: venv\\Scripts\\activate")
        else:
            print("   Активировать: source venv/bin/activate")
    
    return in_venv

def create_mcp_config():
    """Создание конфигурации MCP если она не существует"""
    mcp_config_path = Path("mcp.json")
    
    if not mcp_config_path.exists():
        print("📝 Создание конфигурации MCP...")
        
        workspace_folder = Path.cwd()
        
        # Определяем пути для разных ОС
        if platform.system() == "Windows":
            python_path = str(workspace_folder / "venv" / "Scripts" / "python.exe")
            path_sep = "\\"
        else:
            python_path = str(workspace_folder / "venv" / "bin" / "python")
            path_sep = "/"
        
        config = {
            "mcpServers": {
                "pc-control": {
                    "command": python_path if Path(python_path).exists() else "python",
                    "args": [str(workspace_folder / "main.py")],
                    "env": {
                        "PYTHONPATH": str(workspace_folder),
                        "PC_CONTROL_CONFIG_PATH": str(workspace_folder / "config"),
                        "PC_CONTROL_LOG_LEVEL": "INFO"
                    },
                    "capabilities": {
                        "tools": True,
                        "prompts": False,
                        "resources": False
                    },
                    "transport": {
                        "type": "stdio"
                    }
                }
            }
        }
        
        with open(mcp_config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        print("✅ Конфигурация MCP создана")
        return True
    
    return False

def test_server():
    """Тестовый запуск сервера"""
    print("\n🧪 Тестирование сервера...")
    
    try:
        # Импортируем main для проверки
        from main import PCControlServer
        
        print("✅ Сервер готов к запуску")
        return True
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

def show_cursor_instructions():
    """Показать инструкции для Cursor IDE"""
    print("\n" + "="*60)
    print("🚀 PC Control MCP Server готов к использованию в Cursor IDE")
    print("="*60)
    
    print("\n📋 Инструкции по настройке Cursor:")
    print("\n1. Откройте Cursor IDE в этой директории")
    print("2. Файл mcp.json будет автоматически обнаружен")
    print("3. Если сервер не запустился автоматически:")
    print("   - Откройте Command Palette (Ctrl+Shift+P)")
    print("   - Введите 'MCP: Restart Server'")
    print("   - Выберите 'pc-control'")
    
    print("\n🔧 Доступные инструменты:")
    print("   - Системная информация")
    print("   - Управление процессами")
    print("   - Файловые операции")
    print("   - Сетевые операции")
    
    print("\n📚 Примеры использования:")
    print('   - "Покажи информацию о системе"')
    print('   - "Какие процессы используют больше всего памяти?"')
    print('   - "Найди все Python файлы в текущей директории"')
    
    print("\n📄 Документация: CURSOR_SETUP.md")
    print("="*60)

def main():
    """Основная функция"""
    print("🎯 Cursor IDE MCP Server Launcher")
    print("="*60)
    
    # Проверки
    if not check_python_version():
        sys.exit(1)
    
    print("✅ Python версия подходит")
    
    # Проверка виртуального окружения
    check_venv()
    
    # Проверка и установка зависимостей
    if not check_dependencies():
        sys.exit(1)
    
    # Создание конфигурации если нужно
    create_mcp_config()
    
    # Тестирование сервера
    if not test_server():
        sys.exit(1)
    
    # Показать инструкции
    show_cursor_instructions()
    
    # Опционально: запуск сервера для тестирования
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        print("\n🚀 Запуск сервера...")
        subprocess.run([sys.executable, "main.py"])

if __name__ == "__main__":
    main()