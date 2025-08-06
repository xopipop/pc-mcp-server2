"""
Универсальный MCP сервер для Excel
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest, CallToolResult, ListToolsRequest, ListToolsResult,
    Tool, TextContent, ImageContent, EmbeddedResource
)

from .excel_controller import ExcelController
from .tools import (
    FileOperations, DataOperations, Formatting, 
    AdvancedOperations, VBAEngine
)
from .utils.logger import setup_logger, get_logger
from .utils.error_handler import ExcelErrorHandler

logger = get_logger(__name__)


class ExcelMCPServer:
    """
    Универсальный MCP сервер для управления Microsoft Excel
    """
    
    def __init__(self):
        """Инициализация MCP сервера"""
        self.server = Server("excel-mcp-server")
        self.excel_controller = None
        self.file_operations = None
        self.data_operations = None
        self.formatting = None
        self.advanced_operations = None
        self.vba_engine = None
        
        # Регистрируем обработчики
        self._register_handlers()
        
        logger.info("Excel MCP сервер инициализирован")
    
    def _register_handlers(self):
        """Регистрация обработчиков MCP"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """Получить список доступных инструментов"""
            tools = [
                # Файловые операции
                Tool(
                    name="open_excel_file",
                    description="Открыть Excel файл",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Путь к Excel файлу"},
                            "read_only": {"type": "boolean", "description": "Открыть только для чтения", "default": False}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="create_new_workbook",
                    description="Создать новую рабочую книгу",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Имя новой рабочей книги"},
                            "template": {"type": "string", "description": "Путь к шаблону"}
                        }
                    }
                ),
                Tool(
                    name="save_workbook",
                    description="Сохранить рабочую книгу",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Путь к текущему файлу"},
                            "save_as_path": {"type": "string", "description": "Новый путь для сохранения"},
                            "format": {"type": "string", "description": "Формат файла (xlsx, xls, xlsm, xlsb, csv)"}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="close_workbook",
                    description="Закрыть рабочую книгу",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Путь к файлу"},
                            "save_changes": {"type": "boolean", "description": "Сохранить изменения перед закрытием", "default": True}
                        },
                        "required": ["path"]
                    }
                ),
                
                # Операции с листами
                Tool(
                    name="create_worksheet",
                    description="Создать новый лист",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet_name": {"type": "string", "description": "Имя нового листа"},
                            "after_sheet": {"type": "string", "description": "Имя листа, после которого создать новый"}
                        },
                        "required": ["file_path", "sheet_name"]
                    }
                ),
                Tool(
                    name="delete_worksheet",
                    description="Удалить лист",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet_name": {"type": "string", "description": "Имя листа для удаления"}
                        },
                        "required": ["file_path", "sheet_name"]
                    }
                ),
                Tool(
                    name="rename_worksheet",
                    description="Переименовать лист",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "old_name": {"type": "string", "description": "Старое имя листа"},
                            "new_name": {"type": "string", "description": "Новое имя листа"}
                        },
                        "required": ["file_path", "old_name", "new_name"]
                    }
                ),
                Tool(
                    name="list_worksheets",
                    description="Получить список всех листов",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"}
                        },
                        "required": ["file_path"]
                    }
                ),
                
                # Операции с данными
                Tool(
                    name="read_cell",
                    description="Прочитать значение ячейки",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "cell_address": {"type": "string", "description": "Адрес ячейки (например, A1)"}
                        },
                        "required": ["file_path", "sheet", "cell_address"]
                    }
                ),
                Tool(
                    name="write_cell",
                    description="Записать значение в ячейку",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "cell_address": {"type": "string", "description": "Адрес ячейки (например, A1)"},
                            "value": {"description": "Значение для записи"}
                        },
                        "required": ["file_path", "sheet", "cell_address", "value"]
                    }
                ),
                Tool(
                    name="read_range",
                    description="Прочитать диапазон ячеек",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "range_address": {"type": "string", "description": "Адрес диапазона (например, A1:D10)"}
                        },
                        "required": ["file_path", "sheet", "range_address"]
                    }
                ),
                Tool(
                    name="write_range",
                    description="Записать данные в диапазон",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "range_address": {"type": "string", "description": "Адрес диапазона (например, A1:D10)"},
                            "data": {"type": "array", "description": "Данные для записи (двумерный массив)"}
                        },
                        "required": ["file_path", "sheet", "range_address", "data"]
                    }
                ),
                Tool(
                    name="clear_range",
                    description="Очистить диапазон ячеек",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "range_address": {"type": "string", "description": "Адрес диапазона (например, A1:D10)"}
                        },
                        "required": ["file_path", "sheet", "range_address"]
                    }
                ),
                
                # Форматирование
                Tool(
                    name="format_cells",
                    description="Форматировать ячейки",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "range_address": {"type": "string", "description": "Адрес диапазона"},
                            "format_options": {"type": "object", "description": "Опции форматирования"}
                        },
                        "required": ["file_path", "sheet", "range_address", "format_options"]
                    }
                ),
                Tool(
                    name="set_font",
                    description="Настроить шрифт",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "range_address": {"type": "string", "description": "Адрес диапазона"},
                            "font_options": {"type": "object", "description": "Опции шрифта"}
                        },
                        "required": ["file_path", "sheet", "range_address", "font_options"]
                    }
                ),
                Tool(
                    name="set_borders",
                    description="Настроить границы",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "range_address": {"type": "string", "description": "Адрес диапазона"},
                            "border_options": {"type": "object", "description": "Опции границ"}
                        },
                        "required": ["file_path", "sheet", "range_address", "border_options"]
                    }
                ),
                Tool(
                    name="apply_conditional_formatting",
                    description="Применить условное форматирование",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "range_address": {"type": "string", "description": "Адрес диапазона"},
                            "rules": {"type": "array", "description": "Правила форматирования"}
                        },
                        "required": ["file_path", "sheet", "range_address", "rules"]
                    }
                ),
                
                # VBA операции
                Tool(
                    name="run_vba_macro",
                    description="Выполнить VBA макрос",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "macro_name": {"type": "string", "description": "Имя макроса"},
                            "parameters": {"type": "array", "description": "Параметры макроса"}
                        },
                        "required": ["file_path", "macro_name"]
                    }
                ),
                Tool(
                    name="execute_vba_code",
                    description="Выполнить произвольный VBA код",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "vba_code": {"type": "string", "description": "VBA код для выполнения"}
                        },
                        "required": ["file_path", "vba_code"]
                    }
                ),
                Tool(
                    name="create_vba_module",
                    description="Создать VBA модуль",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "module_name": {"type": "string", "description": "Имя модуля"},
                            "code": {"type": "string", "description": "VBA код модуля"}
                        },
                        "required": ["file_path", "module_name", "code"]
                    }
                ),
                Tool(
                    name="list_vba_macros",
                    description="Получить список доступных VBA макросов",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"}
                        },
                        "required": ["file_path"]
                    }
                ),
                
                # Продвинутые функции
                Tool(
                    name="create_chart",
                    description="Создать диаграмму",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "data_range": {"type": "string", "description": "Диапазон данных"},
                            "chart_type": {"type": "string", "description": "Тип диаграммы (line, column, bar, pie, scatter, area)"},
                            "chart_title": {"type": "string", "description": "Заголовок диаграммы"},
                            "chart_location": {"type": "string", "description": "Расположение диаграммы"}
                        },
                        "required": ["file_path", "sheet", "data_range", "chart_type"]
                    }
                ),
                Tool(
                    name="create_pivot_table",
                    description="Создать сводную таблицу",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "source_data": {"type": "string", "description": "Диапазон исходных данных"},
                            "destination": {"type": "string", "description": "Место размещения сводной таблицы"},
                            "fields": {"type": "object", "description": "Поля для сводной таблицы"}
                        },
                        "required": ["file_path", "sheet", "source_data", "destination", "fields"]
                    }
                ),
                Tool(
                    name="apply_autofilter",
                    description="Применить автофильтр",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "range_address": {"type": "string", "description": "Адрес диапазона"}
                        },
                        "required": ["file_path", "sheet", "range_address"]
                    }
                ),
                Tool(
                    name="sort_data",
                    description="Сортировать данные",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "range_address": {"type": "string", "description": "Диапазон для сортировки"},
                            "sort_options": {"type": "object", "description": "Опции сортировки"}
                        },
                        "required": ["file_path", "sheet", "range_address", "sort_options"]
                    }
                ),
                
                # Утилиты
                Tool(
                    name="get_excel_info",
                    description="Получить информацию о состоянии Excel",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="find_and_replace",
                    description="Найти и заменить текст",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "find_text": {"type": "string", "description": "Текст для поиска"},
                            "replace_text": {"type": "string", "description": "Текст для замены"},
                            "options": {"type": "object", "description": "Опции поиска"}
                        },
                        "required": ["file_path", "sheet", "find_text", "replace_text"]
                    }
                ),
                Tool(
                    name="protect_sheet",
                    description="Защитить лист",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Путь к файлу"},
                            "sheet": {"type": "string", "description": "Имя листа"},
                            "password": {"type": "string", "description": "Пароль для защиты"},
                            "options": {"type": "object", "description": "Опции защиты"}
                        },
                        "required": ["file_path", "sheet"]
                    }
                )
            ]
            
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Обработка вызова инструмента"""
            try:
                # Инициализируем Excel контроллер при первом вызове
                if self.excel_controller is None:
                    self.excel_controller = ExcelController()
                    self.file_operations = FileOperations(self.excel_controller)
                    self.data_operations = DataOperations(self.excel_controller)
                    self.formatting = Formatting(self.excel_controller)
                    self.advanced_operations = AdvancedOperations(self.excel_controller)
                    self.vba_engine = VBAEngine(self.excel_controller)
                
                logger.info(f"Вызов инструмента: {name}")
                
                # Обрабатываем вызовы инструментов
                if name == "open_excel_file":
                    from .tools.file_operations import OpenExcelFileRequest
                    request = OpenExcelFileRequest(**arguments)
                    result = self.file_operations.open_excel_file(request)
                
                elif name == "create_new_workbook":
                    from .tools.file_operations import CreateNewWorkbookRequest
                    request = CreateNewWorkbookRequest(**arguments)
                    result = self.file_operations.create_new_workbook(request)
                
                elif name == "save_workbook":
                    from .tools.file_operations import SaveWorkbookRequest
                    request = SaveWorkbookRequest(**arguments)
                    result = self.file_operations.save_workbook(request)
                
                elif name == "close_workbook":
                    from .tools.file_operations import CloseWorkbookRequest
                    request = CloseWorkbookRequest(**arguments)
                    result = self.file_operations.close_workbook(request)
                
                elif name == "create_worksheet":
                    result = self.excel_controller.create_worksheet(
                        arguments["file_path"], 
                        arguments["sheet_name"],
                        arguments.get("after_sheet")
                    )
                
                elif name == "delete_worksheet":
                    result = self.excel_controller.delete_worksheet(
                        arguments["file_path"], 
                        arguments["sheet_name"]
                    )
                
                elif name == "rename_worksheet":
                    result = self.excel_controller.rename_worksheet(
                        arguments["file_path"], 
                        arguments["old_name"],
                        arguments["new_name"]
                    )
                
                elif name == "list_worksheets":
                    result = self.excel_controller.list_worksheets(arguments["file_path"])
                
                elif name == "read_cell":
                    from .tools.data_operations import ReadCellRequest
                    request = ReadCellRequest(**arguments)
                    result = self.data_operations.read_cell(request)
                
                elif name == "write_cell":
                    from .tools.data_operations import WriteCellRequest
                    request = WriteCellRequest(**arguments)
                    result = self.data_operations.write_cell(request)
                
                elif name == "read_range":
                    from .tools.data_operations import ReadRangeRequest
                    request = ReadRangeRequest(**arguments)
                    result = self.data_operations.read_range(request)
                
                elif name == "write_range":
                    from .tools.data_operations import WriteRangeRequest
                    request = WriteRangeRequest(**arguments)
                    result = self.data_operations.write_range(request)
                
                elif name == "clear_range":
                    from .tools.data_operations import ClearRangeRequest
                    request = ClearRangeRequest(**arguments)
                    result = self.data_operations.clear_range(request)
                
                elif name == "format_cells":
                    from .tools.formatting import FormatCellsRequest
                    request = FormatCellsRequest(**arguments)
                    result = self.formatting.format_cells(request)
                
                elif name == "set_font":
                    from .tools.formatting import SetFontRequest
                    request = SetFontRequest(**arguments)
                    result = self.formatting.set_font(request)
                
                elif name == "set_borders":
                    from .tools.formatting import SetBordersRequest
                    request = SetBordersRequest(**arguments)
                    result = self.formatting.set_borders(request)
                
                elif name == "apply_conditional_formatting":
                    from .tools.formatting import ConditionalFormattingRequest
                    request = ConditionalFormattingRequest(**arguments)
                    result = self.formatting.apply_conditional_formatting(request)
                
                elif name == "run_vba_macro":
                    from .tools.vba_engine import RunVBAMacroRequest
                    request = RunVBAMacroRequest(**arguments)
                    result = self.vba_engine.run_vba_macro(request)
                
                elif name == "execute_vba_code":
                    from .tools.vba_engine import ExecuteVBACodeRequest
                    request = ExecuteVBACodeRequest(**arguments)
                    result = self.vba_engine.execute_vba_code(request)
                
                elif name == "create_vba_module":
                    from .tools.vba_engine import CreateVBAModuleRequest
                    request = CreateVBAModuleRequest(**arguments)
                    result = self.vba_engine.create_vba_module(request)
                
                elif name == "list_vba_macros":
                    result = self.vba_engine.list_vba_macros(arguments["file_path"])
                
                elif name == "create_chart":
                    from .tools.advanced import CreateChartRequest
                    request = CreateChartRequest(**arguments)
                    result = self.advanced_operations.create_chart(request)
                
                elif name == "create_pivot_table":
                    from .tools.advanced import CreatePivotTableRequest
                    request = CreatePivotTableRequest(**arguments)
                    result = self.advanced_operations.create_pivot_table(request)
                
                elif name == "apply_autofilter":
                    result = self.advanced_operations.apply_autofilter(
                        arguments["file_path"],
                        arguments["sheet"],
                        arguments["range_address"]
                    )
                
                elif name == "sort_data":
                    from .tools.advanced import SortDataRequest
                    request = SortDataRequest(**arguments)
                    result = self.advanced_operations.sort_data(request)
                
                elif name == "get_excel_info":
                    result = self.excel_controller.get_excel_info()
                
                elif name == "find_and_replace":
                    result = self.advanced_operations.find_and_replace(
                        arguments["file_path"],
                        arguments["sheet"],
                        arguments["find_text"],
                        arguments["replace_text"],
                        arguments.get("options")
                    )
                
                elif name == "protect_sheet":
                    result = self.advanced_operations.protect_sheet(
                        arguments["file_path"],
                        arguments["sheet"],
                        arguments.get("password"),
                        arguments.get("options")
                    )
                
                else:
                    result = {
                        'success': False,
                        'error': {'message': f'Неизвестный инструмент: {name}'}
                    }
                
                # Формируем ответ
                if result.get('success', False):
                    content = [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
                else:
                    error_msg = result.get('error', {}).get('message', 'Неизвестная ошибка')
                    content = [TextContent(type="text", text=f"Ошибка: {error_msg}")]
                
                return CallToolResult(content=content)
                
            except Exception as e:
                logger.error(f"Ошибка при выполнении инструмента {name}: {e}")
                error_info = ExcelErrorHandler.format_error_response(e)
                content = [TextContent(type="text", text=f"Ошибка: {error_info.get('message', str(e))}")]
                return CallToolResult(content=content)
    
    async def run(self):
        """Запуск MCP сервера"""
        try:
            # Настраиваем логирование
            setup_logger(
                level="INFO",
                log_file="excel_mcp.log",
                rotation="10 MB",
                retention="7 days"
            )
            
            logger.info("Запуск Excel MCP сервера...")
            
            # Запускаем сервер
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="excel-mcp-server",
                        server_version="1.0.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=None,
                            experimental_capabilities=None,
                        ),
                    ),
                )
                
        except Exception as e:
            logger.error(f"Ошибка при запуске сервера: {e}")
            raise
        finally:
            # Очищаем ресурсы
            if self.excel_controller:
                self.excel_controller.cleanup()


async def main():
    """Главная функция"""
    server = ExcelMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main()) 