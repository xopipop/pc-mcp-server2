"""
MCP Tools для файловых операций Excel
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..excel_controller import ExcelController
from ..utils.logger import get_logger
from ..utils.error_handler import ExcelErrorHandler, excel_error_handler

logger = get_logger(__name__)


class OpenExcelFileRequest(BaseModel):
    """Запрос на открытие Excel файла"""
    path: str = Field(..., description="Путь к Excel файлу")
    read_only: bool = Field(False, description="Открыть только для чтения")


class CreateNewWorkbookRequest(BaseModel):
    """Запрос на создание новой рабочей книги"""
    name: Optional[str] = Field(None, description="Имя новой рабочей книги")
    template: Optional[str] = Field(None, description="Путь к шаблону")


class SaveWorkbookRequest(BaseModel):
    """Запрос на сохранение рабочей книги"""
    path: str = Field(..., description="Путь к текущему файлу")
    save_as_path: Optional[str] = Field(None, description="Новый путь для сохранения")
    format: Optional[str] = Field(None, description="Формат файла (xlsx, xls, xlsm, xlsb, csv)")


class CloseWorkbookRequest(BaseModel):
    """Запрос на закрытие рабочей книги"""
    path: str = Field(..., description="Путь к файлу")
    save_changes: bool = Field(True, description="Сохранить изменения перед закрытием")


class FileOperations:
    """
    MCP Tools для файловых операций Excel
    """
    
    def __init__(self, excel_controller: ExcelController):
        """
        Инициализация файловых операций
        
        Args:
            excel_controller: Контроллер Excel
        """
        self.excel_controller = excel_controller
    
    @excel_error_handler
    def open_excel_file(self, request: OpenExcelFileRequest) -> Dict[str, Any]:
        """
        Открыть Excel файл
        
        Args:
            request: Запрос на открытие файла
            
        Returns:
            Информация об открытой рабочей книге
        """
        logger.info(f"Открытие Excel файла: {request.path}")
        
        try:
            result = self.excel_controller.open_workbook(
                file_path=request.path,
                read_only=request.read_only
            )
            
            return {
                'success': True,
                'message': f'Файл {request.path} успешно открыт',
                'workbook_info': result
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при открытии файла {request.path}: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def create_new_workbook(self, request: CreateNewWorkbookRequest) -> Dict[str, Any]:
        """
        Создать новую рабочую книгу
        
        Args:
            request: Запрос на создание рабочей книги
            
        Returns:
            Информация о новой рабочей книге
        """
        logger.info("Создание новой рабочей книги")
        
        try:
            result = self.excel_controller.create_workbook(
                template=request.template
            )
            
            # Если указано имя, переименовываем первый лист
            if request.name:
                try:
                    # Получаем первый лист и переименовываем его
                    workbook_path = result['file_path']
                    worksheet = self.excel_controller.get_worksheet(workbook_path, "Sheet1")
                    worksheet.Name = request.name
                    result['name'] = request.name
                except Exception as e:
                    logger.warning(f"Не удалось переименовать лист: {e}")
            
            return {
                'success': True,
                'message': 'Новая рабочая книга успешно создана',
                'workbook_info': result
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при создании рабочей книги: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def save_workbook(self, request: SaveWorkbookRequest) -> Dict[str, Any]:
        """
        Сохранить рабочую книгу
        
        Args:
            request: Запрос на сохранение
            
        Returns:
            Информация о результате сохранения
        """
        logger.info(f"Сохранение рабочей книги: {request.path}")
        
        try:
            result = self.excel_controller.save_workbook(
                file_path=request.path,
                save_as_path=request.save_as_path,
                file_format=request.format
            )
            
            return {
                'success': True,
                'message': result.get('message', 'Рабочая книга сохранена'),
                'save_info': result
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при сохранении файла {request.path}: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def close_workbook(self, request: CloseWorkbookRequest) -> Dict[str, Any]:
        """
        Закрыть рабочую книгу
        
        Args:
            request: Запрос на закрытие
            
        Returns:
            Информация о результате закрытия
        """
        logger.info(f"Закрытие рабочей книги: {request.path}")
        
        try:
            result = self.excel_controller.close_workbook(
                file_path=request.path,
                save_changes=request.save_changes
            )
            
            return {
                'success': True,
                'message': result.get('message', 'Рабочая книга закрыта'),
                'close_info': result
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при закрытии файла {request.path}: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def list_open_workbooks(self) -> Dict[str, Any]:
        """
        Получить список открытых рабочих книг
        
        Returns:
            Список открытых рабочих книг
        """
        logger.info("Получение списка открытых рабочих книг")
        
        try:
            excel_info = self.excel_controller.get_excel_info()
            
            if excel_info.get('status') != 'initialized':
                return {
                    'success': False,
                    'error': {'message': 'Excel не инициализирован'}
                }
            
            workbooks = []
            for file_path in excel_info.get('workbook_paths', []):
                try:
                    workbook_info = self.excel_controller._get_workbook_info(
                        self.excel_controller.workbooks[file_path], 
                        file_path
                    )
                    workbooks.append(workbook_info)
                except Exception as e:
                    logger.warning(f"Ошибка при получении информации о книге {file_path}: {e}")
                    workbooks.append({
                        'file_path': file_path,
                        'name': 'Unknown',
                        'worksheets_count': 0,
                        'saved': True,
                        'read_only': False,
                        'has_password': False
                    })
            
            return {
                'success': True,
                'workbooks': workbooks,
                'count': len(workbooks)
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при получении списка рабочих книг: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def get_workbook_info(self, file_path: str) -> Dict[str, Any]:
        """
        Получить информацию о рабочей книге
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Информация о рабочей книге
        """
        logger.info(f"Получение информации о рабочей книге: {file_path}")
        
        try:
            if file_path not in self.excel_controller.workbooks:
                return {
                    'success': False,
                    'error': {'message': f'Рабочая книга {file_path} не открыта'}
                }
            
            workbook_info = self.excel_controller._get_workbook_info(
                self.excel_controller.workbooks[file_path],
                file_path
            )
            
            return {
                'success': True,
                'workbook_info': workbook_info
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при получении информации о книге {file_path}: {error_info}")
            return {
                'success': False,
                'error': error_info
            } 