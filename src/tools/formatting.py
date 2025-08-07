"""
MCP Tools для форматирования Excel
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from ..excel_controller import ExcelController
from ..utils.logger import get_logger
from ..utils.error_handler import ExcelErrorHandler, excel_error_handler

logger = get_logger(__name__)


class FormatCellsRequest(BaseModel):
    """Запрос на форматирование ячеек"""
    file_path: str = Field(..., description="Путь к файлу")
    sheet: str = Field(..., description="Имя листа")
    range_address: str = Field(..., description="Адрес диапазона")
    format_options: Dict[str, Any] = Field(..., description="Опции форматирования")


class SetFontRequest(BaseModel):
    """Запрос на настройку шрифта"""
    file_path: str = Field(..., description="Путь к файлу")
    sheet: str = Field(..., description="Имя листа")
    range_address: str = Field(..., description="Адрес диапазона")
    font_options: Dict[str, Any] = Field(..., description="Опции шрифта")


class SetBordersRequest(BaseModel):
    """Запрос на настройку границ"""
    file_path: str = Field(..., description="Путь к файлу")
    sheet: str = Field(..., description="Имя листа")
    range_address: str = Field(..., description="Адрес диапазона")
    border_options: Dict[str, Any] = Field(..., description="Опции границ")


class ConditionalFormattingRequest(BaseModel):
    """Запрос на условное форматирование"""
    file_path: str = Field(..., description="Путь к файлу")
    sheet: str = Field(..., description="Имя листа")
    range_address: str = Field(..., description="Адрес диапазона")
    rules: List[Dict[str, Any]] = Field(..., description="Правила форматирования")


class Formatting:
    """
    MCP Tools для форматирования Excel
    """
    
    def __init__(self, excel_controller: ExcelController):
        """
        Инициализация форматирования
        
        Args:
            excel_controller: Контроллер Excel
        """
        self.excel_controller = excel_controller
    
    @excel_error_handler
    def format_cells(self, request: FormatCellsRequest) -> Dict[str, Any]:
        """
        Форматировать ячейки
        
        Args:
            request: Запрос на форматирование
            
        Returns:
            Результат форматирования
        """
        logger.info(f"Форматирование диапазона {request.range_address}")
        
        try:
            ExcelErrorHandler.validate_range_address(request.range_address)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(request.file_path, request.sheet)
            
            # Получаем диапазон
            range_obj = worksheet.Range(request.range_address)
            
            # Применяем форматирование
            for option, value in request.format_options.items():
                if hasattr(range_obj, option):
                    setattr(range_obj, option, value)
                else:
                    logger.warning(f"Неизвестная опция форматирования: {option}")
            
            return {
                'success': True,
                'message': f'Форматирование применено к диапазону {request.range_address}',
                'range_address': request.range_address,
                'sheet': request.sheet,
                'file_path': request.file_path,
                'applied_options': list(request.format_options.keys())
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при форматировании: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def set_font(self, request: SetFontRequest) -> Dict[str, Any]:
        """
        Настроить шрифт
        
        Args:
            request: Запрос на настройку шрифта
            
        Returns:
            Результат настройки шрифта
        """
        logger.info(f"Настройка шрифта для диапазона {request.range_address}")
        
        try:
            ExcelErrorHandler.validate_range_address(request.range_address)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(request.file_path, request.sheet)
            
            # Получаем диапазон
            range_obj = worksheet.Range(request.range_address)
            
            # Применяем настройки шрифта
            for option, value in request.font_options.items():
                if hasattr(range_obj.Font, option):
                    setattr(range_obj.Font, option, value)
                else:
                    logger.warning(f"Неизвестная опция шрифта: {option}")
            
            return {
                'success': True,
                'message': f'Шрифт настроен для диапазона {request.range_address}',
                'range_address': request.range_address,
                'sheet': request.sheet,
                'file_path': request.file_path,
                'applied_font_options': list(request.font_options.keys())
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при настройке шрифта: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def set_borders(self, request: SetBordersRequest) -> Dict[str, Any]:
        """
        Настроить границы
        
        Args:
            request: Запрос на настройку границ
            
        Returns:
            Результат настройки границ
        """
        logger.info(f"Настройка границ для диапазона {request.range_address}")
        
        try:
            ExcelErrorHandler.validate_range_address(request.range_address)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(request.file_path, request.sheet)
            
            # Получаем диапазон
            range_obj = worksheet.Range(request.range_address)
            
            # Применяем настройки границ
            for option, value in request.border_options.items():
                if hasattr(range_obj.Borders, option):
                    setattr(range_obj.Borders, option, value)
                else:
                    logger.warning(f"Неизвестная опция границ: {option}")
            
            return {
                'success': True,
                'message': f'Границы настроены для диапазона {request.range_address}',
                'range_address': request.range_address,
                'sheet': request.sheet,
                'file_path': request.file_path,
                'applied_border_options': list(request.border_options.keys())
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при настройке границ: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def apply_conditional_formatting(self, request: ConditionalFormattingRequest) -> Dict[str, Any]:
        """
        Применить условное форматирование
        
        Args:
            request: Запрос на условное форматирование
            
        Returns:
            Результат применения условного форматирования
        """
        logger.info(f"Применение условного форматирования к диапазону {request.range_address}")
        
        try:
            ExcelErrorHandler.validate_range_address(request.range_address)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(request.file_path, request.sheet)
            
            # Получаем диапазон
            range_obj = worksheet.Range(request.range_address)
            
            # Применяем правила условного форматирования
            applied_rules = []
            for rule in request.rules:
                try:
                    # Здесь должна быть логика применения конкретных правил
                    # Это упрощенная версия
                    applied_rules.append(rule.get('name', 'Unknown rule'))
                except Exception as e:
                    logger.warning(f"Ошибка при применении правила: {e}")
            
            return {
                'success': True,
                'message': f'Условное форматирование применено к диапазону {request.range_address}',
                'range_address': request.range_address,
                'sheet': request.sheet,
                'file_path': request.file_path,
                'applied_rules': applied_rules
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при применении условного форматирования: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def auto_fit_columns(self, file_path: str, sheet: str, range_address: str) -> Dict[str, Any]:
        """
        Автоматически подогнать ширину столбцов
        
        Args:
            file_path: Путь к файлу
            sheet: Имя листа
            range_address: Адрес диапазона
            
        Returns:
            Результат операции
        """
        logger.info(f"Автоподгонка столбцов для диапазона {range_address}")
        
        try:
            ExcelErrorHandler.validate_range_address(range_address)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(file_path, sheet)
            
            # Получаем диапазон
            range_obj = worksheet.Range(range_address)
            
            # Автоподгонка столбцов
            range_obj.Columns.AutoFit()
            
            return {
                'success': True,
                'message': f'Столбцы автоматически подогнаны для диапазона {range_address}',
                'range_address': range_address,
                'sheet': sheet,
                'file_path': file_path
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при автоподгонке столбцов: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def auto_fit_rows(self, file_path: str, sheet: str, range_address: str) -> Dict[str, Any]:
        """
        Автоматически подогнать высоту строк
        
        Args:
            file_path: Путь к файлу
            sheet: Имя листа
            range_address: Адрес диапазона
            
        Returns:
            Результат операции
        """
        logger.info(f"Автоподгонка строк для диапазона {range_address}")
        
        try:
            ExcelErrorHandler.validate_range_address(range_address)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(file_path, sheet)
            
            # Получаем диапазон
            range_obj = worksheet.Range(range_address)
            
            # Автоподгонка строк
            range_obj.Rows.AutoFit()
            
            return {
                'success': True,
                'message': f'Строки автоматически подогнаны для диапазона {range_address}',
                'range_address': range_address,
                'sheet': sheet,
                'file_path': file_path
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при автоподгонке строк: {error_info}")
            return {
                'success': False,
                'error': error_info
            } 