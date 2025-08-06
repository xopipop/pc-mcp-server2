# Структура проекта

## Файлы
- `README.md` - Основная документация
- `requirements.txt` - Зависимости Python
- `setup.py` - Установка пакета
- `.cursorrules` - Конфигурация Cursor IDE
- `.gitignore` - Исключения Git
- `LICENSE` - Лицензия MIT
- `mcp.json` - Конфигурация MCP

## Папки
- `src/` - Основной код
  - `server.py` - MCP сервер
  - `excel_controller.py` - Контроллер Excel
  - `tools/` - MCP инструменты
  - `utils/` - Утилиты
- `config/` - Конфигурация
- `examples/` - Примеры использования
- `tests/` - Тесты

## Минимальная структура для работы
```
excel-mcp-server/
├── src/                    # Код
├── config/                 # Конфигурация
├── examples/               # Примеры
├── tests/                  # Тесты
├── README.md              # Документация
├── requirements.txt       # Зависимости
├── setup.py              # Установка
├── .cursorrules          # Cursor IDE
└── .gitignore           # Git
``` 