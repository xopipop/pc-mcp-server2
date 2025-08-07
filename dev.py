#!/usr/bin/env python3
"""
Быстрый запуск PC Control MCP Server для разработки.
Автоматически отключает безопасность и включает debug логирование.
"""

import os
import sys
from pathlib import Path

# Добавляем src в path
sys.path.insert(0, str(Path(__file__).parent))

# Устанавливаем переменные окружения для режима разработки
os.environ['PC_CONTROL_SECURITY__ENABLED'] = 'false'
os.environ['PC_CONTROL_LOGGING__LEVEL'] = 'DEBUG'
os.environ['PC_CONTROL_SERVER__HOST'] = 'localhost'
os.environ['PC_CONTROL_SERVER__PORT'] = '3000'

# Информационное сообщение
print("""
╔══════════════════════════════════════════════════════════╗
║        PC Control MCP Server - Режим разработки          ║
╠══════════════════════════════════════════════════════════╣
║  🚨 ВНИМАНИЕ: Безопасность отключена!                    ║
║  📝 Логирование: DEBUG                                   ║
║  🌐 Сервер: localhost:3000                               ║
║                                                          ║
║  Используйте только для разработки!                      ║
╚══════════════════════════════════════════════════════════╝
""")

# Импортируем и запускаем main
try:
    from main import main
    import asyncio
    
    asyncio.run(main())
except KeyboardInterrupt:
    print("\n\n✋ Сервер остановлен пользователем")
except Exception as e:
    print(f"\n❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()