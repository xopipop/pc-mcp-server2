# Excel MCP Server

Универсальный MCP сервер для управления Microsoft Excel через ИИ.

## Установка

```bash
pip install -r requirements.txt
pip install -e .
```

## Настройка Cursor

Создайте `.cursorrules`:

```json
{
  "mcpServers": {
    "excel": {
      "command": "python",
      "args": ["-m", "src.server"],
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}
```

## Запуск

```bash
python -m src.server
```

## Доступные инструменты

- **Файлы**: `open_excel_file`, `create_new_workbook`, `save_workbook`, `close_workbook`
- **Данные**: `read_cell`, `write_cell`, `read_range`, `write_range`, `clear_range`
- **Листы**: `create_worksheet`, `delete_worksheet`, `rename_worksheet`, `list_worksheets`
- **Форматирование**: `format_cells`, `set_font`, `set_borders`, `apply_conditional_formatting`
- **VBA**: `run_vba_macro`, `execute_vba_code`, `create_vba_module`, `list_vba_macros`
- **Диаграммы**: `create_chart`, `create_pivot_table`, `apply_autofilter`, `sort_data`
- **Утилиты**: `get_excel_info`, `find_and_replace`, `protect_sheet`

## Требования

- Windows 10/11
- Python 3.10+
- Microsoft Excel 2016+ 