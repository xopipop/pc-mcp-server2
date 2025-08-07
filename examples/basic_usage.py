"""
Примеры использования универсального Excel MCP Server
"""

import asyncio
import json
from src.server import ExcelMCPServer


async def example_basic_operations():
    """Пример базовых операций с Excel"""
    print("=== Пример базовых операций с Excel ===")
    
    # Создаем сервер
    server = ExcelMCPServer()
    
    # Пример 1: Создание новой рабочей книги
    print("\n1. Создание новой рабочей книги...")
    result = await server.file_operations.create_new_workbook({
        "name": "Пример_отчета"
    })
    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # Пример 2: Запись данных в ячейки
    print("\n2. Запись данных в ячейки...")
    result = await server.data_operations.write_cell({
        "file_path": "new_workbook_123.xlsx",
        "sheet": "Sheet1",
        "cell_address": "A1",
        "value": "Заголовок отчета"
    })
    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # Пример 3: Запись диапазона данных
    print("\n3. Запись диапазона данных...")
    data = [
        ["Имя", "Возраст", "Город"],
        ["Иван", 25, "Москва"],
        ["Мария", 30, "Санкт-Петербург"],
        ["Петр", 35, "Новосибирск"]
    ]
    result = await server.data_operations.write_range({
        "file_path": "new_workbook_123.xlsx",
        "sheet": "Sheet1",
        "range_address": "A2:D5",
        "data": data
    })
    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # Пример 4: Форматирование ячеек
    print("\n4. Форматирование ячеек...")
    result = await server.formatting.set_font({
        "file_path": "new_workbook_123.xlsx",
        "sheet": "Sheet1",
        "range_address": "A1:D1",
        "font_options": {
            "Bold": True,
            "Size": 14,
            "Color": 1  # Черный цвет
        }
    })
    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # Пример 5: Сохранение файла
    print("\n5. Сохранение файла...")
    result = await server.file_operations.save_workbook({
        "path": "new_workbook_123.xlsx",
        "save_as_path": "пример_отчета.xlsx",
        "format": "xlsx"
    })
    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # Очистка
    await server.excel_controller.cleanup()


async def example_advanced_operations():
    """Пример продвинутых операций"""
    print("\n=== Пример продвинутых операций ===")
    
    server = ExcelMCPServer()
    
    # Пример 1: Создание диаграммы
    print("\n1. Создание диаграммы...")
    result = await server.advanced_operations.create_chart({
        "file_path": "new_workbook_123.xlsx",
        "sheet": "Sheet1",
        "data_range": "B2:C5",
        "chart_type": "column",
        "chart_title": "Возраст по городам"
    })
    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # Пример 2: Применение автофильтра
    print("\n2. Применение автофильтра...")
    result = await server.advanced_operations.apply_autofilter({
        "file_path": "new_workbook_123.xlsx",
        "sheet": "Sheet1",
        "range_address": "A2:D5"
    })
    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # Пример 3: Сортировка данных
    print("\n3. Сортировка данных...")
    result = await server.advanced_operations.sort_data({
        "file_path": "new_workbook_123.xlsx",
        "sheet": "Sheet1",
        "range_address": "A2:D5",
        "sort_options": {
            "key": 2,  # Сортировка по столбцу B (Возраст)
            "order": 1  # По возрастанию
        }
    })
    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # Очистка
    await server.excel_controller.cleanup()


async def example_vba_operations():
    """Пример работы с VBA"""
    print("\n=== Пример работы с VBA ===")
    
    server = ExcelMCPServer()
    
    # Пример 1: Создание VBA модуля
    print("\n1. Создание VBA модуля...")
    vba_code = """
Sub HelloWorld()
    MsgBox "Привет, мир!"
End Sub

Function AddNumbers(a As Integer, b As Integer) As Integer
    AddNumbers = a + b
End Function
"""
    result = await server.vba_engine.create_vba_module({
        "file_path": "new_workbook_123.xlsx",
        "module_name": "TestModule",
        "code": vba_code
    })
    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # Пример 2: Выполнение VBA макроса
    print("\n2. Выполнение VBA макроса...")
    result = await server.vba_engine.run_vba_macro({
        "file_path": "new_workbook_123.xlsx",
        "macro_name": "HelloWorld"
    })
    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # Пример 3: Выполнение VBA функции
    print("\n3. Выполнение VBA функции...")
    result = await server.vba_engine.run_vba_macro({
        "file_path": "new_workbook_123.xlsx",
        "macro_name": "AddNumbers",
        "parameters": [5, 3]
    })
    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # Очистка
    await server.excel_controller.cleanup()


async def example_data_analysis():
    """Пример анализа данных"""
    print("\n=== Пример анализа данных ===")
    
    server = ExcelMCPServer()
    
    # Пример 1: Создание сводной таблицы
    print("\n1. Создание сводной таблицы...")
    result = await server.advanced_operations.create_pivot_table({
        "file_path": "new_workbook_123.xlsx",
        "sheet": "Sheet1",
        "source_data": "A2:D5",
        "destination": "F1",
        "fields": {
            "rows": ["Город"],
            "values": ["Возраст"],
            "aggregation": "average"
        }
    })
    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # Пример 2: Условное форматирование
    print("\n2. Применение условного форматирования...")
    result = await server.formatting.apply_conditional_formatting({
        "file_path": "new_workbook_123.xlsx",
        "sheet": "Sheet1",
        "range_address": "B2:B5",
        "rules": [
            {
                "type": "cell_value",
                "operator": "greater_than",
                "value": 30,
                "format": {"font_color": "red", "bold": True}
            }
        ]
    })
    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # Очистка
    await server.excel_controller.cleanup()


async def main():
    """Главная функция с примерами"""
    try:
        await example_basic_operations()
        await example_advanced_operations()
        await example_vba_operations()
        await example_data_analysis()
        
        print("\n=== Все примеры выполнены успешно! ===")
        print("Этот универсальный MCP сервер может работать с любыми данными Excel.")
        
    except Exception as e:
        print(f"Ошибка при выполнении примеров: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 