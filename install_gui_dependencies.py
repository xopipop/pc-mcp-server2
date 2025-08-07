#!/usr/bin/env python3
"""
Скрипт для установки зависимостей GUI автоматизации
"""

import subprocess
import sys
import platform

def install_package(package):
    """Установка пакета через pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} установлен успешно")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Ошибка установки {package}")
        return False

def main():
    print("🚀 Установка зависимостей для GUI автоматизации...")
    print("=" * 50)
    
    # Основные зависимости
    packages = [
        "pyautogui>=0.9.54",
        "pillow>=10.0.0",  # Для скриншотов
        "mcp>=1.0.0",
        "psutil>=5.9.8"
    ]
    
    # Платформо-зависимые зависимости
    if platform.system() == "Windows":
        packages.append("pywin32>=306")
    
    print(f"📦 Устанавливаем {len(packages)} пакетов...")
    
    success_count = 0
    for package in packages:
        print(f"\n📥 Устанавливаем {package}...")
        if install_package(package):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Результат: {success_count}/{len(packages)} пакетов установлено")
    
    if success_count == len(packages):
        print("🎉 Все зависимости установлены успешно!")
        print("\nТеперь вы можете:")
        print("1. Запустить тест: python test_gui_automation.py")
        print("2. Использовать MCP сервер с GUI автоматизацией")
        print("3. Посмотреть примеры: examples/gui_automation_examples.py")
    else:
        print("⚠️ Некоторые пакеты не удалось установить")
        print("Попробуйте установить их вручную:")
        for package in packages:
            print(f"   pip install {package}")

if __name__ == "__main__":
    main()



