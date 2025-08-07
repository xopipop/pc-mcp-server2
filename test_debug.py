#!/usr/bin/env python3
"""
Простой тест для отладки ошибок.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем src в path
sys.path.insert(0, str(Path(__file__).parent))

print("DEBUG: Starting test_debug.py")
print(f"DEBUG: Python version: {sys.version}")
print(f"DEBUG: Platform: {sys.platform}")

# Тест 1: Проверка импорта модулей
print("\n=== TEST 1: Module imports ===")
try:
    from src import setup_logging, get_config, __version__
    print(f"✅ Basic imports successful, version: {__version__}")
except Exception as e:
    print(f"❌ Basic imports failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Тест 2: Проверка конфигурации
print("\n=== TEST 2: Configuration ===")
try:
    config = get_config()
    print(f"✅ Config loaded successfully")
    print(f"   Server name: {config.config.server.name}")
    print(f"   Log level: {config.config.server.log_level}")
except Exception as e:
    print(f"❌ Config loading failed: {e}")
    import traceback
    traceback.print_exc()

# Тест 3: Проверка системных инструментов
print("\n=== TEST 3: System Tools ===")
try:
    from src.tools import SystemTools
    system_tools = SystemTools()
    print("✅ SystemTools created successfully")
    
    async def test_system_info():
        print("   Testing get_system_info()...")
        info = await system_tools.get_system_info("basic")
        print(f"   ✅ System info retrieved: {info.get('platform', 'Unknown')}")
        return info
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    info = loop.run_until_complete(test_system_info())
    
except Exception as e:
    print(f"❌ SystemTools test failed: {e}")
    import traceback
    traceback.print_exc()

# Тест 4: Проверка MCP сервера (без запуска)
print("\n=== TEST 4: MCP Server ===")
try:
    from main import PCControlServer
    print("✅ PCControlServer import successful")
    
    # Попробуем создать экземпляр
    server = PCControlServer()
    print("✅ PCControlServer instance created")
    
except Exception as e:
    print(f"❌ MCP Server test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== All tests completed ===")