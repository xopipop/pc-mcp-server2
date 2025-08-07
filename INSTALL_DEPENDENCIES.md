# Инструкция по установке зависимостей

## Проблема

При запуске `main.py` возникает ошибка импорта:
```
ImportError: cannot import name 'stdio_transport' from 'mcp.server'
```

## Причина

1. Пакет `mcp` и другие зависимости не установлены
2. В коде используется старый способ импорта из mcp.server

## Решение

### Шаг 1: Создание виртуального окружения (рекомендуется)

#### Для Linux/macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Для Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### Шаг 2: Установка зависимостей

```bash
pip install -r requirements.txt
```

### Шаг 3: Исправление импортов (уже выполнено)

В файле `main.py` импорт был изменен с:
```python
from mcp.server import Server, stdio_transport
```

На:
```python
from mcp.server import Server
from mcp.server.stdio import stdio_transport
```

### Шаг 4: Запуск сервера

После установки всех зависимостей:
```bash
python main.py
```

## Примечание для пользователей Windows

Если вы используете Windows и видите ошибку с путями в config файле:
- Измените пути в claude_desktop_config.json на правильные Windows пути
- Используйте двойные обратные слеши: `C:\\Users\\User-01\\Desktop\\excel-mcp-server\\main.py`

## Альтернативный способ установки (без venv)

Если вы не можете создать виртуальное окружение:
```bash
pip install --user -r requirements.txt
```

## Проверка установки

После установки проверьте:
```bash
python -c "import mcp; print('MCP установлен успешно')"
```