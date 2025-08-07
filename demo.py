#!/usr/bin/env python3
"""
Демонстрация возможностей PC Control MCP Server.
Запускает сервер и показывает примеры использования.
"""

import os
import sys
from pathlib import Path

# Проверка зависимостей
print("🔍 Проверка зависимостей...")
try:
    import psutil
    import yaml
    import aiofiles
    print("✅ Основные зависимости установлены")
except ImportError as e:
    print(f"❌ Ошибка: {e}")
    print("\nУстановите зависимости:")
    print("  pip install psutil pyyaml aiofiles")
    sys.exit(1)

# Добавляем src в path
sys.path.insert(0, str(Path(__file__).parent))

# Импортируем модули
try:
    from src import (
        SystemTools,
        ProcessTools,
        FileTools,
        NetworkTools,
        MetricsCollector
    )
    print("✅ Модули PC Control загружены")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

import asyncio
from datetime import datetime

async def demo():
    """Демонстрация основных возможностей."""
    
    print("\n" + "="*60)
    print("🚀 PC Control MCP Server - Демонстрация возможностей")
    print("="*60)
    
    # Инициализация инструментов
    system_tools = SystemTools()
    process_tools = ProcessTools()
    file_tools = FileTools()
    network_tools = NetworkTools()
    metrics = MetricsCollector()
    
    # 1. Системная информация
    print("\n📊 СИСТЕМНАЯ ИНФОРМАЦИЯ:")
    print("-" * 40)
    
    try:
        info = await system_tools.get_system_info("basic")
        print(f"🖥️  ОС: {info['platform']} {info['version']}")
        print(f"🏷️  Имя хоста: {info['hostname']}")
        print(f"🏗️  Архитектура: {info['architecture']}")
        print(f"🐍 Python: {info['python_version']}")
        
        cpu_info = await system_tools.get_cpu_info()
        print(f"\n💻 Процессор: {cpu_info['brand']}")
        print(f"   Ядра: {cpu_info['physical_cores']} физических, {cpu_info['logical_cores']} логических")
        print(f"   Частота: {cpu_info['current_freq']:.0f} МГц")
        
        mem_info = await system_tools.get_memory_info()
        print(f"\n🧠 Память: {mem_info['total'] / (1024**3):.1f} ГБ")
        print(f"   Использовано: {mem_info['percent']:.1f}%")
        
    except Exception as e:
        print(f"⚠️  Ошибка получения системной информации: {e}")
    
    # 2. Топ процессов
    print("\n\n🔄 ТОП ПРОЦЕССОВ ПО CPU:")
    print("-" * 40)
    
    try:
        processes = await process_tools.list_processes({
            'sort_by': 'cpu',
            'limit': 5
        })
        
        for i, proc in enumerate(processes[:5], 1):
            print(f"{i}. {proc['name']:<20} PID: {proc['pid']:<8} CPU: {proc['cpu_percent']:>5.1f}%")
    
    except Exception as e:
        print(f"⚠️  Ошибка получения процессов: {e}")
    
    # 3. Сетевые интерфейсы
    print("\n\n🌐 СЕТЕВЫЕ ИНТЕРФЕЙСЫ:")
    print("-" * 40)
    
    try:
        interfaces = await network_tools.get_network_interfaces(include_stats=False)
        
        for iface in interfaces[:3]:  # Показываем первые 3
            if iface['is_up']:
                print(f"📡 {iface['name']}: UP")
                for addr in iface.get('addresses', []):
                    if addr['family'] == 'AF_INET':
                        print(f"   IP: {addr['address']}")
    
    except Exception as e:
        print(f"⚠️  Ошибка получения сетевых интерфейсов: {e}")
    
    # 4. Файловая система
    print("\n\n📁 ФАЙЛОВАЯ СИСТЕМА:")
    print("-" * 40)
    
    try:
        # Создаем тестовый файл
        test_file = Path("demo_test.txt")
        content = f"PC Control Demo - {datetime.now()}"
        
        await file_tools.write_file(str(test_file), content)
        print(f"✍️  Создан файл: {test_file}")
        
        # Читаем его обратно
        read_result = await file_tools.read_file(str(test_file))
        print(f"📖 Содержимое: {read_result['content']}")
        
        # Удаляем
        await file_tools.delete_file(str(test_file))
        print(f"🗑️  Файл удален")
        
    except Exception as e:
        print(f"⚠️  Ошибка работы с файлами: {e}")
    
    # 5. Метрики
    print("\n\n📈 СИСТЕМНЫЕ МЕТРИКИ:")
    print("-" * 40)
    
    try:
        # Запускаем сбор метрик
        await metrics.start(interval=1)
        print("⏱️  Сбор метрик запущен...")
        
        # Ждем немного для сбора данных
        await asyncio.sleep(3)
        
        # Получаем метрики
        all_metrics = metrics.get_all_metrics()
        
        for name, data in list(all_metrics.items())[:5]:
            if data['current'] is not None:
                print(f"📊 {name}: {data['current']:.2f}")
        
        # Останавливаем сбор
        await metrics.stop()
        
    except Exception as e:
        print(f"⚠️  Ошибка сбора метрик: {e}")
    
    print("\n" + "="*60)
    print("✅ Демонстрация завершена!")
    print("="*60)

if __name__ == "__main__":
    # Запускаем демонстрацию
    try:
        asyncio.run(demo())
    except KeyboardInterrupt:
        print("\n\n⛔ Демонстрация прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()