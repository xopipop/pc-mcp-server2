"""
MCP Tools для операций с данными Excel
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from ..excel_controller import ExcelController
from ..utils.logger import get_logger
from ..utils.error_handler import ExcelErrorHandler, excel_error_handler

logger = get_logger(__name__)


class ReadCellRequest(BaseModel):
    """Запрос на чтение ячейки"""
    file_path: str = Field(..., description="Путь к файлу")
    sheet: str = Field(..., description="Имя листа")
    cell_address: str = Field(..., description="Адрес ячейки (например, A1)")


class WriteCellRequest(BaseModel):
    """Запрос на запись в ячейку"""
    file_path: str = Field(..., description="Путь к файлу")
    sheet: str = Field(..., description="Имя листа")
    cell_address: str = Field(..., description="Адрес ячейки (например, A1)")
    value: Any = Field(..., description="Значение для записи")


class ReadRangeRequest(BaseModel):
    """Запрос на чтение диапазона"""
    file_path: str = Field(..., description="Путь к файлу")
    sheet: str = Field(..., description="Имя листа")
    range_address: str = Field(..., description="Адрес диапазона (например, A1:D10)")


class WriteRangeRequest(BaseModel):
    """Запрос на запись диапазона"""
    file_path: str = Field(..., description="Путь к файлу")
    sheet: str = Field(..., description="Имя листа")
    range_address: str = Field(..., description="Адрес диапазона (например, A1:D10)")
    data: List[List[Any]] = Field(..., description="Данные для записи (двумерный массив)")


class ClearRangeRequest(BaseModel):
    """Запрос на очистку диапазона"""
    file_path: str = Field(..., description="Путь к файлу")
    sheet: str = Field(..., description="Имя листа")
    range_address: str = Field(..., description="Адрес диапазона (например, A1:D10)")


class DataOperations:
    """
    MCP Tools для операций с данными Excel
    """
    
    def __init__(self, excel_controller: ExcelController):
        """
        Инициализация операций с данными
        
        Args:
            excel_controller: Контроллер Excel
        """
        self.excel_controller = excel_controller
    
    @excel_error_handler
    def read_cell(self, request: ReadCellRequest) -> Dict[str, Any]:
        """
        Прочитать значение ячейки
        
        Args:
            request: Запрос на чтение ячейки
            
        Returns:
            Значение ячейки
        """
        logger.info(f"Чтение ячейки {request.cell_address} на листе {request.sheet}")
        
        try:
            ExcelErrorHandler.validate_range_address(request.cell_address)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(request.file_path, request.sheet)
            
            # Читаем значение ячейки
            cell = worksheet.Range(request.cell_address)
            value = cell.Value
            
            # Определяем тип значения
            value_type = type(value).__name__
            
            # Обрабатываем специальные случаи
            if value is None:
                value = ""
                value_type = "empty"
            elif isinstance(value, (int, float)):
                value_type = "number"
            elif isinstance(value, bool):
                value_type = "boolean"
            elif isinstance(value, str):
                value_type = "text"
            
            return {
                'success': True,
                'value': value,
                'value_type': value_type,
                'cell_address': request.cell_address,
                'sheet': request.sheet,
                'file_path': request.file_path
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при чтении ячейки {request.cell_address}: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def write_cell(self, request: WriteCellRequest) -> Dict[str, Any]:
        """
        Записать значение в ячейку
        
        Args:
            request: Запрос на запись ячейки
            
        Returns:
            Результат записи
        """
        logger.info(f"Запись в ячейку {request.cell_address} на листе {request.sheet}")
        
        try:
            ExcelErrorHandler.validate_range_address(request.cell_address)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(request.file_path, request.sheet)
            
            # Записываем значение в ячейку
            cell = worksheet.Range(request.cell_address)
            cell.Value = request.value
            
            return {
                'success': True,
                'message': f'Значение записано в ячейку {request.cell_address}',
                'cell_address': request.cell_address,
                'sheet': request.sheet,
                'file_path': request.file_path,
                'value': request.value
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при записи в ячейку {request.cell_address}: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def read_range(self, request: ReadRangeRequest) -> Dict[str, Any]:
        """
        Прочитать диапазон ячеек
        
        Args:
            request: Запрос на чтение диапазона
            
        Returns:
            Данные диапазона
        """
        logger.info(f"Чтение диапазона {request.range_address} на листе {request.sheet}")
        
        try:
            ExcelErrorHandler.validate_range_address(request.range_address)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(request.file_path, request.sheet)
            
            # Читаем диапазон
            range_obj = worksheet.Range(request.range_address)
            
            # Получаем значения как массив
            values = range_obj.Value
            
            # Преобразуем в список списков
            if values is None:
                data = []
            elif isinstance(values, (list, tuple)):
                # Если это двумерный массив
                if values and isinstance(values[0], (list, tuple)):
                    data = [[str(cell) if cell is not None else "" for cell in row] for row in values]
                else:
                    # Если это одномерный массив
                    data = [[str(cell) if cell is not None else "" for cell in values]]
            else:
                # Если это одна ячейка
                data = [[str(values) if values is not None else ""]]
            
            # Получаем информацию о диапазоне
            rows_count = range_obj.Rows.Count
            columns_count = range_obj.Columns.Count
            
            return {
                'success': True,
                'data': data,
                'range_address': request.range_address,
                'sheet': request.sheet,
                'file_path': request.file_path,
                'rows_count': rows_count,
                'columns_count': columns_count
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при чтении диапазона {request.range_address}: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def write_range(self, request: WriteRangeRequest) -> Dict[str, Any]:
        """
        Записать данные в диапазон
        
        Args:
            request: Запрос на запись диапазона
            
        Returns:
            Результат записи
        """
        logger.info(f"Запись в диапазон {request.range_address} на листе {request.sheet}")
        
        try:
            ExcelErrorHandler.validate_range_address(request.range_address)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(request.file_path, request.sheet)
            
            # Записываем данные в диапазон
            range_obj = worksheet.Range(request.range_address)
            range_obj.Value = request.data
            
            return {
                'success': True,
                'message': f'Данные записаны в диапазон {request.range_address}',
                'range_address': request.range_address,
                'sheet': request.sheet,
                'file_path': request.file_path,
                'data_rows': len(request.data),
                'data_columns': len(request.data[0]) if request.data else 0
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при записи в диапазон {request.range_address}: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def clear_range(self, request: ClearRangeRequest) -> Dict[str, Any]:
        """
        Очистить диапазон ячеек
        
        Args:
            request: Запрос на очистку диапазона
            
        Returns:
            Результат очистки
        """
        logger.info(f"Очистка диапазона {request.range_address} на листе {request.sheet}")
        
        try:
            ExcelErrorHandler.validate_range_address(request.range_address)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(request.file_path, request.sheet)
            
            # Очищаем диапазон
            range_obj = worksheet.Range(request.range_address)
            range_obj.ClearContents()
            
            return {
                'success': True,
                'message': f'Диапазон {request.range_address} очищен',
                'range_address': request.range_address,
                'sheet': request.sheet,
                'file_path': request.file_path
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при очистке диапазона {request.range_address}: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def get_used_range(self, file_path: str, sheet: str) -> Dict[str, Any]:
        """
        Получить используемый диапазон на листе
        
        Args:
            file_path: Путь к файлу
            sheet: Имя листа
            
        Returns:
            Информация об используемом диапазоне
        """
        logger.info(f"Получение используемого диапазона на листе {sheet}")
        
        try:
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(file_path, sheet)
            
            # Получаем используемый диапазон
            used_range = worksheet.UsedRange
            
            if used_range is None:
                return {
                    'success': True,
                    'has_data': False,
                    'range_address': None,
                    'rows_count': 0,
                    'columns_count': 0
                }
            
            # Получаем адрес диапазона
            range_address = used_range.Address
            
            # Получаем размеры
            rows_count = used_range.Rows.Count
            columns_count = used_range.Columns.Count
            
            return {
                'success': True,
                'has_data': True,
                'range_address': range_address,
                'rows_count': rows_count,
                'columns_count': columns_count,
                'sheet': sheet,
                'file_path': file_path
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при получении используемого диапазона: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def copy_range(self, source_file: str, source_sheet: str, source_range: str,
                  target_file: str, target_sheet: str, target_range: str) -> Dict[str, Any]:
        """
        Скопировать диапазон из одного места в другое
        
        Args:
            source_file: Исходный файл
            source_sheet: Исходный лист
            source_range: Исходный диапазон
            target_file: Целевой файл
            target_sheet: Целевой лист
            target_range: Целевой диапазон
            
        Returns:
            Результат копирования
        """
        logger.info(f"Копирование диапазона {source_range} в {target_range}")
        
        try:
            ExcelErrorHandler.validate_range_address(source_range)
            ExcelErrorHandler.validate_range_address(target_range)
            
            # Получаем исходный и целевой листы
            source_worksheet = self.excel_controller.get_worksheet(source_file, source_sheet)
            target_worksheet = self.excel_controller.get_worksheet(target_file, target_sheet)
            
            # Копируем диапазон
            source_range_obj = source_worksheet.Range(source_range)
            target_range_obj = target_worksheet.Range(target_range)
            
            source_range_obj.Copy(target_range_obj)
            
            return {
                'success': True,
                'message': f'Диапазон {source_range} скопирован в {target_range}',
                'source': {
                    'file': source_file,
                    'sheet': source_sheet,
                    'range': source_range
                },
                'target': {
                    'file': target_file,
                    'sheet': target_sheet,
                    'range': target_range
                }
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при копировании диапазона: {error_info}")
            return {
                'success': False,
                'error': error_info
            } 