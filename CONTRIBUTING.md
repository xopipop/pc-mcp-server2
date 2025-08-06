# Contributing to Excel MCP Server

Спасибо за интерес к проекту Excel MCP Server! Мы приветствуем вклады от сообщества.

## Как внести вклад

### Сообщение об ошибках

1. Проверьте, не была ли ошибка уже зарегистрирована в [Issues](https://github.com/your-username/excel-mcp-server/issues)
2. Создайте новое issue с подробным описанием проблемы
3. Используйте шаблон bug report для структурированного описания

### Предложение новых функций

1. Создайте issue с типом "Feature Request"
2. Опишите предлагаемую функцию и её преимущества
3. Обсудите с сообществом перед началом разработки

### Разработка

#### Настройка окружения

1. Форкните репозиторий
2. Клонируйте ваш форк локально:
   ```bash
   git clone https://github.com/your-username/excel-mcp-server.git
   cd excel-mcp-server
   ```

3. Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # или
   venv\Scripts\activate     # Windows
   ```

4. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

#### Стиль кода

- Следуйте PEP 8
- Используйте type hints
- Добавляйте docstrings для всех функций и классов
- Максимальная длина строки: 127 символов

#### Тестирование

1. Напишите тесты для новых функций
2. Убедитесь, что все тесты проходят:
   ```bash
   pytest tests/
   ```

3. Проверьте покрытие кода:
   ```bash
   pytest tests/ --cov=src --cov-report=html
   ```

#### Коммиты

- Используйте понятные сообщения коммитов
- Следуйте conventional commits:
  - `feat:` для новых функций
  - `fix:` для исправлений ошибок
  - `docs:` для документации
  - `test:` для тестов
  - `refactor:` для рефакторинга

#### Pull Request

1. Создайте ветку для ваших изменений:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Внесите изменения и закоммитьте их

3. Отправьте ветку в ваш форк:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Создайте Pull Request

5. Опишите изменения в PR:
   - Что было изменено
   - Почему это было изменено
   - Как это тестировалось

## Структура проекта

```
excel-mcp-server/
├── src/                    # Основной код
│   ├── server.py          # MCP сервер
│   ├── excel_controller.py # Контроллер Excel
│   ├── tools/             # MCP инструменты
│   └── utils/             # Утилиты
├── tests/                 # Тесты
├── examples/              # Примеры использования
├── config/                # Конфигурация
└── docs/                  # Документация
```

## Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=src --cov-report=html

# Конкретный тест
pytest tests/test_excel_controller.py::test_open_file
```

### Линтинг

```bash
# Проверка стиля
flake8 src/ tests/

# Форматирование
black src/ tests/
```

## Документация

- Обновляйте README.md при добавлении новых функций
- Добавляйте примеры использования в examples/
- Обновляйте docstrings для новых функций

## Лицензия

Внося вклад в проект, вы соглашаетесь с тем, что ваш вклад будет лицензирован под MIT License.

## Поддержка

Если у вас есть вопросы по вкладу в проект, создайте issue или обратитесь к документации. 