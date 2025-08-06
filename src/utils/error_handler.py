"""
Модуль обработки ошибок для Excel MCP Server
"""

import sys
import traceback
from typing import Any, Dict, Optional, Union
from .logger import get_logger

logger = get_logger(__name__)


class ExcelError(Exception):
    """Базовый класс для ошибок Excel"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать ошибку в словарь"""
        return {
            'error': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details
        }


class ExcelConnectionError(ExcelError):
    """Ошибка подключения к Excel"""
    pass


class ExcelFileError(ExcelError):
    """Ошибка работы с файлом Excel"""
    pass


class ExcelWorksheetError(ExcelError):
    """Ошибка работы с листом Excel"""
    pass


class ExcelRangeError(ExcelError):
    """Ошибка работы с диапазоном Excel"""
    pass


class ExcelVBAError(ExcelError):
    """Ошибка выполнения VBA"""
    pass


class ExcelFormatError(ExcelError):
    """Ошибка форматирования"""
    pass


class ExcelErrorHandler:
    """
    Обработчик ошибок для Excel операций
    """
    
    # Словарь соответствия COM ошибок нашим исключениям
    COM_ERROR_MAPPING = {
        -2146827284: ExcelConnectionError,  # Excel не запущен
        -2146827283: ExcelFileError,        # Файл не найден
        -2146827282: ExcelFileError,        # Файл поврежден
        -2146827281: ExcelWorksheetError,   # Лист не найден
        -2146827280: ExcelRangeError,       # Неверный диапазон
        -2146827279: ExcelVBAError,         # Ошибка VBA
        -2146827278: ExcelFormatError,      # Ошибка форматирования
    }
    
    @classmethod
    def handle_com_error(cls, com_error, context: str = "") -> ExcelError:
        """
        Обработать COM ошибку Excel
        
        Args:
            com_error: COM исключение
            context: Контекст операции
            
        Returns:
            Соответствующее исключение ExcelError
        """
        error_code = getattr(com_error, 'hresult', None)
        error_message = str(com_error)
        
        # Определяем тип ошибки по коду
        error_class = cls.COM_ERROR_MAPPING.get(error_code, ExcelError)
        
        # Формируем сообщение об ошибке
        if context:
            message = f"{context}: {error_message}"
        else:
            message = error_message
        
        # Создаем исключение
        exception = error_class(
            message=message,
            error_code=str(error_code) if error_code else None,
            details={
                'com_error': error_message,
                'context': context,
                'traceback': traceback.format_exc()
            }
        )
        
        logger.error(f"COM ошибка Excel: {message}", extra={'error_code': error_code})
        return exception
    
    @classmethod
    def handle_general_error(cls, error: Exception, context: str = "") -> ExcelError:
        """
        Обработать общую ошибку
        
        Args:
            error: Исключение
            context: Контекст операции
            
        Returns:
            ExcelError исключение
        """
        error_message = str(error)
        
        if context:
            message = f"{context}: {error_message}"
        else:
            message = error_message
        
        exception = ExcelError(
            message=message,
            details={
                'original_error': error_message,
                'error_type': type(error).__name__,
                'context': context,
                'traceback': traceback.format_exc()
            }
        )
        
        logger.error(f"Общая ошибка: {message}")
        return exception
    
    @classmethod
    def safe_execute(cls, func, *args, context: str = "", **kwargs) -> Any:
        """
        Безопасное выполнение функции с обработкой ошибок
        
        Args:
            func: Функция для выполнения
            *args: Аргументы функции
            context: Контекст операции
            **kwargs: Именованные аргументы
            
        Returns:
            Результат выполнения функции
            
        Raises:
            ExcelError: При возникновении ошибки
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Проверяем, является ли это COM ошибкой
            if hasattr(e, 'hresult'):
                raise cls.handle_com_error(e, context)
            else:
                raise cls.handle_general_error(e, context)
    
    @classmethod
    def validate_file_path(cls, file_path: str) -> None:
        """
        Проверить корректность пути к файлу
        
        Args:
            file_path: Путь к файлу
            
        Raises:
            ExcelFileError: При некорректном пути
        """
        if not file_path:
            raise ExcelFileError("Путь к файлу не может быть пустым")
        
        if not isinstance(file_path, str):
            raise ExcelFileError("Путь к файлу должен быть строкой")
        
        # Проверяем расширение файла
        valid_extensions = ['.xlsx', '.xls', '.xlsm', '.xlsb', '.csv']
        file_extension = file_path.lower().split('.')[-1] if '.' in file_path else ''
        
        if file_extension not in [ext[1:] for ext in valid_extensions]:
            raise ExcelFileError(f"Неподдерживаемое расширение файла: {file_extension}")
    
    @classmethod
    def validate_sheet_name(cls, sheet_name: str) -> None:
        """
        Проверить корректность имени листа
        
        Args:
            sheet_name: Имя листа
            
        Raises:
            ExcelWorksheetError: При некорректном имени
        """
        if not sheet_name:
            raise ExcelWorksheetError("Имя листа не может быть пустым")
        
        if not isinstance(sheet_name, str):
            raise ExcelWorksheetError("Имя листа должно быть строкой")
        
        # Проверяем длину имени (Excel ограничение)
        if len(sheet_name) > 31:
            raise ExcelWorksheetError("Имя листа не может быть длиннее 31 символа")
        
        # Проверяем запрещенные символы
        invalid_chars = ['\\', '/', '*', '?', ':', '[', ']']
        for char in invalid_chars:
            if char in sheet_name:
                raise ExcelWorksheetError(f"Имя листа содержит запрещенный символ: {char}")
    
    @classmethod
    def validate_range_address(cls, range_address: str) -> None:
        """
        Проверить корректность адреса диапазона
        
        Args:
            range_address: Адрес диапазона
            
        Raises:
            ExcelRangeError: При некорректном адресе
        """
        if not range_address:
            raise ExcelRangeError("Адрес диапазона не может быть пустым")
        
        if not isinstance(range_address, str):
            raise ExcelRangeError("Адрес диапазона должен быть строкой")
        
        # Простая проверка формата (A1:B10)
        import re
        pattern = r'^[A-Z]+\d+(?::[A-Z]+\d+)?$'
        if not re.match(pattern, range_address.upper()):
            raise ExcelRangeError(f"Некорректный формат адреса диапазона: {range_address}")
    
    @classmethod
    def format_error_response(cls, error: Exception) -> Dict[str, Any]:
        """
        Форматировать ошибку для ответа MCP
        
        Args:
            error: Исключение
            
        Returns:
            Словарь с информацией об ошибке
        """
        if isinstance(error, ExcelError):
            return error.to_dict()
        else:
            return {
                'error': 'UnexpectedError',
                'message': str(error),
                'error_code': None,
                'details': {
                    'error_type': type(error).__name__,
                    'traceback': traceback.format_exc()
                }
            }


def excel_error_handler(func):
    """
    Декоратор для автоматической обработки ошибок Excel
    
    Args:
        func: Функция для декорирования
        
    Returns:
        Обернутая функция
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if hasattr(e, 'hresult'):
                raise ExcelErrorHandler.handle_com_error(e, f"В функции {func.__name__}")
            else:
                raise ExcelErrorHandler.handle_general_error(e, f"В функции {func.__name__}")
    
    return wrapper 