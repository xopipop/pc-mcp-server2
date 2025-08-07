#!/usr/bin/env python3
"""
Примеры использования PC Control MCP Server

⚠️ ВНИМАНИЕ: Эти примеры предназначены только для демонстрации!
Используйте их только в безопасной изолированной среде!
"""

# Примеры показывают, как ИИ-ассистент может использовать инструменты MCP

# =============================================================================
# ПРИМЕР 1: Создание и редактирование файла
# =============================================================================
"""
AI Assistant может создать новый файл с содержимым:

1. Создать директорию для проекта:
   tool: file_operations
   parameters: {
     "operation": "create_dir",
     "path": "/home/user/my_project"
   }

2. Создать файл с кодом:
   tool: file_operations
   parameters: {
     "operation": "write",
     "path": "/home/user/my_project/hello.py",
     "content": "#!/usr/bin/env python3\n\ndef main():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    main()"
   }

3. Прочитать созданный файл:
   tool: file_operations
   parameters: {
     "operation": "read",
     "path": "/home/user/my_project/hello.py"
   }
"""

# =============================================================================
# ПРИМЕР 2: Установка программы через пакетный менеджер
# =============================================================================
"""
AI Assistant может установить программное обеспечение:

1. Проверить операционную систему:
   tool: system_info
   parameters: {
     "info_type": "os_info"
   }

2. Для Ubuntu/Debian - установить программу:
   tool: execute_command
   parameters: {
     "command": "sudo apt-get update && sudo apt-get install -y htop",
     "timeout": 60
   }

3. Для Windows - установить через Chocolatey:
   tool: execute_command
   parameters: {
     "command": "choco install notepadplusplus -y",
     "timeout": 60
   }

4. Проверить установку:
   tool: execute_command
   parameters: {
     "command": "which htop"  # или "where notepad++" для Windows
   }
"""

# =============================================================================
# ПРИМЕР 3: Мониторинг системных ресурсов
# =============================================================================
"""
AI Assistant может отслеживать состояние системы:

1. Получить информацию о CPU:
   tool: system_info
   parameters: {
     "info_type": "cpu"
   }
   
2. Проверить использование памяти:
   tool: system_info
   parameters: {
     "info_type": "memory"
   }

3. Посмотреть топ процессов по CPU:
   tool: system_info
   parameters: {
     "info_type": "processes"
   }

4. Проверить дисковое пространство:
   tool: system_info
   parameters: {
     "info_type": "disk"
   }

5. Создать отчет о системе:
   tool: file_operations
   parameters: {
     "operation": "write",
     "path": "/home/user/system_report.txt",
     "content": "[Собранная информация о системе]"
   }
"""

# =============================================================================
# ПРИМЕР 4: Автоматизация рутинных задач
# =============================================================================
"""
AI Assistant может автоматизировать повторяющиеся задачи:

1. Создать резервную копию важных файлов:
   tool: backup_operations
   parameters: {
     "operation": "create",
     "source": "/home/user/documents",
     "compress": true
   }

2. Настроить автоматическое резервное копирование:
   tool: scheduled_tasks
   parameters: {
     "action": "create",
     "task_name": "daily_backup",
     "command": "python /home/user/backup_script.py",
     "schedule": "daily",
     "description": "Daily backup of documents"
   }

3. Очистить временные файлы:
   tool: execute_command
   parameters: {
     "command": "find /tmp -type f -mtime +7 -delete",
     "timeout": 30
   }

4. Проверить и оптимизировать автозапуск:
   tool: service_management
   parameters: {
     "action": "list"
   }
"""

# =============================================================================
# ПРИМЕР 5: Управление процессами и службами
# =============================================================================
"""
AI Assistant может управлять процессами и службами:

1. Найти процесс, потребляющий много ресурсов:
   tool: process_management
   parameters: {
     "action": "list",
     "name": "chrome"
   }

2. Получить детальную информацию о процессе:
   tool: process_management
   parameters: {
     "action": "get_info",
     "pid": 1234
   }

3. Перезапустить зависшую службу:
   tool: service_management
   parameters: {
     "action": "restart",
     "service_name": "nginx"
   }

4. Изменить тип запуска службы:
   tool: service_management
   parameters: {
     "action": "configure",
     "service_name": "mysql",
     "startup_type": "manual"
   }
"""

# =============================================================================
# ПРИМЕР 6: Сетевая диагностика
# =============================================================================
"""
AI Assistant может выполнять сетевую диагностику:

1. Проверить доступность сервера:
   tool: network_operations
   parameters: {
     "operation": "ping",
     "target": "google.com",
     "count": 4
   }

2. Проверить открытые порты:
   tool: network_operations
   parameters: {
     "operation": "port_scan",
     "target": "localhost",
     "port": 80
   }

3. Посмотреть активные соединения:
   tool: network_operations
   parameters: {
     "operation": "connection_info"
   }

4. Выполнить DNS lookup:
   tool: network_operations
   parameters: {
     "operation": "dns_lookup",
     "target": "example.com"
   }
"""

# =============================================================================
# ПРИМЕР 7: Работа с переменными окружения
# =============================================================================
"""
AI Assistant может управлять переменными окружения:

1. Посмотреть все переменные:
   tool: environment_management
   parameters: {
     "action": "list"
   }

2. Установить новую переменную:
   tool: environment_management
   parameters: {
     "action": "set",
     "name": "MY_APP_CONFIG",
     "value": "/home/user/config",
     "scope": "user"
   }

3. Проверить переменную PATH:
   tool: environment_management
   parameters: {
     "action": "get",
     "name": "PATH"
   }
"""

# =============================================================================
# ПРИМЕР 8: GUI автоматизация (требует pyautogui)
# =============================================================================
"""
AI Assistant может автоматизировать действия с GUI:

1. Сделать скриншот экрана:
   tool: automation_tools
   parameters: {
     "action": "screenshot"
   }

2. Переместить мышь в позицию:
   tool: automation_tools
   parameters: {
     "action": "mouse_move",
     "x": 500,
     "y": 300,
     "duration": 1.0
   }

3. Кликнуть по кнопке:
   tool: automation_tools
   parameters: {
     "action": "mouse_click",
     "x": 500,
     "y": 300,
     "button": "left"
   }

4. Ввести текст:
   tool: automation_tools
   parameters: {
     "action": "type_text",
     "text": "Hello, World!"
   }
"""

# =============================================================================
# БЕЗОПАСНОЕ ИСПОЛЬЗОВАНИЕ
# =============================================================================
"""
ВАЖНЫЕ ПРАВИЛА БЕЗОПАСНОСТИ:

1. ВСЕГДА используйте сервер в изолированной среде (VM, Docker)
2. НЕ запускайте на продакшн системах
3. Регулярно проверяйте логи операций
4. Держите enable_dangerous_operations = false
5. Создавайте резервные копии перед критическими операциями
6. Ограничивайте доступ к определенным путям и командам
7. Используйте белые списки для разрешенных операций

ПРИМЕР БЕЗОПАСНОЙ КОНФИГУРАЦИИ:
{
  "enable_dangerous_operations": false,
  "allowed_commands": ["ls", "cat", "echo", "pwd"],
  "blocked_paths": ["/", "/etc", "/sys", "/boot", "C:\\Windows"],
  "max_file_size": 10485760,  # 10MB
  "command_timeout": 10
}
"""

if __name__ == "__main__":
    print("Это файл с примерами. Не запускайте его напрямую!")
    print("Используйте эти примеры как справочник для работы с MCP сервером.")