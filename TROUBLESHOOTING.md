# Руководство по устранению неполадок PC Control MCP Server

## Распространенные проблемы и решения

### 1. ImportError: cannot import name 'stdio_transport' from 'mcp.server'

**Проблема:**
```
ImportError: cannot import name 'stdio_transport' from 'mcp.server'
```

**Причины:**
- Пакет MCP не установлен
- Используется устаревший синтаксис импорта

**Решение:**
1. Убедитесь, что импорт в `main.py` исправлен (уже сделано):
   ```python
   from mcp.server import Server
   from mcp.server.stdio import stdio_transport
   ```

2. Установите все зависимости:
   ```bash
   pip install -r requirements.txt
   ```

### 2. ModuleNotFoundError: No module named 'mcp'

**Проблема:**
```
ModuleNotFoundError: No module named 'mcp'
```

**Решение:**
```bash
# Создайте виртуальное окружение
python -m venv venv

# Активируйте его
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Установите зависимости
pip install -r requirements.txt
```

### 3. ModuleNotFoundError: No module named 'loguru'

**Проблема:**
```
ModuleNotFoundError: No module named 'loguru'
```

**Решение:**
Установите все зависимости из requirements.txt:
```bash
pip install loguru
# или
pip install -r requirements.txt
```

### 4. Ошибка в Claude Desktop (Windows)

**Проблема:**
Claude Desktop не может найти Python или main.py

**Решение:**
1. Используйте полные пути в `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "pc-control": {
         "command": "C:\\Python311\\python.exe",
         "args": ["C:\\Users\\User-01\\Desktop\\excel-mcp-server\\main.py"]
       }
     }
   }
   ```

2. Убедитесь, что пути используют двойные обратные слеши `\\`

### 5. Permission denied при запуске

**Проблема:**
```
Permission denied: './main.py'
```

**Решение:**
```bash
# Сделайте файл исполняемым
chmod +x main.py

# Или запускайте через Python
python main.py
```

### 6. Альтернативные варианты запуска

Если основной `main.py` не работает, попробуйте:

1. **FastMCP версию** (использует новый API):
   ```bash
   python main_fastmcp.py
   ```

2. **Прямой запуск с MCP CLI**:
   ```bash
   mcp run main.py
   # или
   mcp dev main.py
   ```

### 7. Проверка установки

Для проверки правильности установки:

```bash
# Проверка MCP
python -c "import mcp; print('MCP установлен')"

# Проверка всех модулей проекта
python test_imports.py
```

### 8. Отладка

Для более подробной информации об ошибках:

1. Включите отладочный режим в логах:
   ```python
   # В файле config/default.yaml
   logging:
     level: DEBUG
   ```

2. Запустите с выводом всех ошибок:
   ```bash
   python -u main.py 2>&1 | tee debug.log
   ```

## Получение помощи

Если проблема не решена:

1. Проверьте версию Python: `python --version` (требуется 3.8+)
2. Проверьте установленные пакеты: `pip list`
3. Создайте issue на GitHub с:
   - Полным текстом ошибки
   - Версией Python
   - Операционной системой
   - Шагами для воспроизведения