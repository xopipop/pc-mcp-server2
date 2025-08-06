"""
Основной контроллер для работы с Microsoft Excel через COM
"""

import os
import sys
import time
import threading
from typing import Any, Dict, List, Optional, Union, Tuple
from pathlib import Path

import win32com.client
import win32com.client.gencache
from win32com.client import constants

from .utils.logger import get_logger
from .utils.error_handler import (
    ExcelErrorHandler, ExcelConnectionError, ExcelFileError,
    ExcelWorksheetError, ExcelRangeError, excel_error_handler
)
from .utils.cache import excel_object_cache

logger = get_logger(__name__)


class ExcelController:
    """
    Основной контроллер для работы с Microsoft Excel
    """
    
    def __init__(self, visible: bool = False, display_alerts: bool = False):
        """
        Инициализация контроллера Excel
        
        Args:
            visible: Показывать ли Excel приложение
            display_alerts: Показывать ли диалоги Excel
        """
        self.excel_app = None
        self.workbooks = {}  # Словарь открытых рабочих книг
        self.visible = visible
        self.display_alerts = display_alerts
        self._lock = threading.RLock()
        self._initialized = False
        
        logger.info("Инициализация Excel контроллера")
    
    def __enter__(self):
        """Контекстный менеджер - вход"""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        self.cleanup()
    
    @excel_error_handler
    def initialize(self) -> None:
        """
        Инициализация Excel приложения
        
        Raises:
            ExcelConnectionError: При ошибке подключения к Excel
        """
        with self._lock:
            if self._initialized:
                return
            
            try:
                logger.info("Подключение к Microsoft Excel...")
                
                # Пытаемся подключиться к существующему экземпляру Excel
                try:
                    self.excel_app = win32com.client.GetActiveObject("Excel.Application")
                    logger.info("Подключен к существующему экземпляру Excel")
                except:
                    # Создаем новый экземпляр Excel
                    self.excel_app = win32com.client.Dispatch("Excel.Application")
                    logger.info("Создан новый экземпляр Excel")
                
                # Настраиваем параметры Excel
                self.excel_app.Visible = self.visible
                self.excel_app.DisplayAlerts = self.display_alerts
                self.excel_app.EnableEvents = True
                # Пропускаем установку Calculation, так как она может вызвать ошибки
                
                self._initialized = True
                logger.info("Excel контроллер успешно инициализирован")
                
            except Exception as e:
                logger.error(f"Ошибка инициализации Excel: {e}")
                raise ExcelConnectionError(f"Не удалось подключиться к Excel: {e}")
    
    @excel_error_handler
    def cleanup(self) -> None:
        """Очистка ресурсов и закрытие Excel"""
        with self._lock:
            if not self._initialized:
                return
            
            try:
                logger.info("Очистка Excel контроллера...")
                
                # Закрываем все открытые рабочие книги
                for file_path in list(self.workbooks.keys()):
                    try:
                        self.close_workbook(file_path, save_changes=False)
                    except Exception as e:
                        logger.warning(f"Ошибка при закрытии файла {file_path}: {e}")
                
                # Очищаем кэш
                excel_object_cache.workbooks_cache.clear()
                excel_object_cache.worksheets_cache.clear()
                excel_object_cache.range_cache.clear()
                
                # Закрываем Excel приложение
                if self.excel_app:
                    try:
                        self.excel_app.Quit()
                    except:
                        pass
                    finally:
                        self.excel_app = None
                
                self._initialized = False
                logger.info("Excel контроллер очищен")
                
            except Exception as e:
                logger.error(f"Ошибка при очистке Excel контроллера: {e}")
    
    @excel_error_handler
    def open_workbook(self, file_path: str, read_only: bool = False) -> Dict[str, Any]:
        """
        Открыть рабочую книгу Excel
        
        Args:
            file_path: Путь к файлу Excel
            read_only: Открыть только для чтения
            
        Returns:
            Информация о рабочей книге
            
        Raises:
            ExcelFileError: При ошибке открытия файла
        """
        ExcelErrorHandler.validate_file_path(file_path)
        
        with self._lock:
            self.initialize()
            
            # Проверяем кэш
            cached_workbook = excel_object_cache.get_cached_workbook(file_path)
            if cached_workbook:
                logger.info(f"Рабочая книга {file_path} найдена в кэше")
                return self._get_workbook_info(cached_workbook, file_path)
            
            # Проверяем, не открыта ли уже книга
            if file_path in self.workbooks:
                logger.info(f"Рабочая книга {file_path} уже открыта")
                return self._get_workbook_info(self.workbooks[file_path], file_path)
            
            try:
                # Получаем абсолютный путь
                abs_path = os.path.abspath(file_path)
                
                if not os.path.exists(abs_path):
                    raise ExcelFileError(f"Файл не найден: {abs_path}")
                
                logger.info(f"Открытие рабочей книги: {abs_path}")
                
                # Открываем рабочую книгу
                workbook = self.excel_app.Workbooks.Open(
                    abs_path,
                    ReadOnly=read_only,
                    UpdateLinks=3  # xlUpdateLinksAlways
                )
                
                # Сохраняем в кэш и словарь
                excel_object_cache.cache_workbook(file_path, workbook)
                self.workbooks[file_path] = workbook
                
                workbook_info = self._get_workbook_info(workbook, file_path)
                logger.info(f"Рабочая книга {file_path} успешно открыта")
                
                return workbook_info
                
            except Exception as e:
                logger.error(f"Ошибка при открытии файла {file_path}: {e}")
                raise ExcelFileError(f"Не удалось открыть файл {file_path}: {e}")
    
    @excel_error_handler
    def create_workbook(self, template: Optional[str] = None) -> Dict[str, Any]:
        """
        Создать новую рабочую книгу
        
        Args:
            template: Путь к шаблону (опционально)
            
        Returns:
            Информация о новой рабочей книге
        """
        with self._lock:
            self.initialize()
            
            try:
                logger.info("Создание новой рабочей книги")
                
                if template:
                    workbook = self.excel_app.Workbooks.Add(template)
                else:
                    workbook = self.excel_app.Workbooks.Add()
                
                # Генерируем временный путь для новой книги
                temp_path = f"new_workbook_{int(time.time())}.xlsx"
                
                # Сохраняем в кэш и словарь
                excel_object_cache.cache_workbook(temp_path, workbook)
                self.workbooks[temp_path] = workbook
                
                workbook_info = self._get_workbook_info(workbook, temp_path)
                logger.info("Новая рабочая книга успешно создана")
                
                return workbook_info
                
            except Exception as e:
                logger.error(f"Ошибка при создании рабочей книги: {e}")
                raise ExcelFileError(f"Не удалось создать рабочую книгу: {e}")
    
    @excel_error_handler
    def save_workbook(self, file_path: str, save_as_path: Optional[str] = None, 
                     file_format: Optional[str] = None) -> Dict[str, Any]:
        """
        Сохранить рабочую книгу
        
        Args:
            file_path: Путь к текущему файлу
            save_as_path: Новый путь для сохранения (опционально)
            file_format: Формат файла (опционально)
            
        Returns:
            Информация о результате сохранения
        """
        with self._lock:
            if file_path not in self.workbooks:
                raise ExcelFileError(f"Рабочая книга {file_path} не открыта")
            
            workbook = self.workbooks[file_path]
            
            try:
                logger.info(f"Сохранение рабочей книги: {file_path}")
                
                if save_as_path:
                    # Сохранение как новый файл
                    ExcelErrorHandler.validate_file_path(save_as_path)
                    
                    # Определяем формат файла
                    format_constants = {
                        'xlsx': 51,  # xlOpenXMLWorkbook
                        'xls': 56,   # xlWorkbookNormal
                        'xlsm': 52,  # xlOpenXMLWorkbookMacroEnabled
                        'xlsb': 50,  # xlExcel12
                        'csv': 6     # xlCSV
                    }
                    
                    file_format_const = format_constants.get(
                        file_format.lower() if file_format else 'xlsx',
                        51  # xlOpenXMLWorkbook
                    )
                    
                    workbook.SaveAs(save_as_path, FileFormat=file_format_const)
                    logger.info(f"Рабочая книга сохранена как: {save_as_path}")
                    
                    return {
                        'success': True,
                        'message': f'Рабочая книга сохранена как {save_as_path}',
                        'file_path': save_as_path,
                        'format': file_format or 'xlsx'
                    }
                else:
                    # Сохранение текущего файла
                    workbook.Save()
                    logger.info(f"Рабочая книга сохранена: {file_path}")
                    
                    return {
                        'success': True,
                        'message': f'Рабочая книга сохранена: {file_path}',
                        'file_path': file_path
                    }
                    
            except Exception as e:
                logger.error(f"Ошибка при сохранении файла {file_path}: {e}")
                raise ExcelFileError(f"Не удалось сохранить файл {file_path}: {e}")
    
    @excel_error_handler
    def close_workbook(self, file_path: str, save_changes: bool = True) -> Dict[str, Any]:
        """
        Закрыть рабочую книгу
        
        Args:
            file_path: Путь к файлу
            save_changes: Сохранить изменения перед закрытием
            
        Returns:
            Информация о результате закрытия
        """
        with self._lock:
            if file_path not in self.workbooks:
                raise ExcelFileError(f"Рабочая книга {file_path} не открыта")
            
            workbook = self.workbooks[file_path]
            
            try:
                logger.info(f"Закрытие рабочей книги: {file_path}")
                
                if save_changes:
                    workbook.Save()
                    logger.info(f"Изменения сохранены перед закрытием: {file_path}")
                
                workbook.Close(SaveChanges=save_changes)
                
                # Удаляем из кэша и словаря
                excel_object_cache.clear_workbook_cache(file_path)
                del self.workbooks[file_path]
                
                logger.info(f"Рабочая книга закрыта: {file_path}")
                
                return {
                    'success': True,
                    'message': f'Рабочая книга закрыта: {file_path}',
                    'saved': save_changes
                }
                
            except Exception as e:
                logger.error(f"Ошибка при закрытии файла {file_path}: {e}")
                raise ExcelFileError(f"Не удалось закрыть файл {file_path}: {e}")
    
    @excel_error_handler
    def get_worksheet(self, file_path: str, sheet_name: str):
        """
        Получить лист рабочей книги
        
        Args:
            file_path: Путь к файлу
            sheet_name: Имя листа
            
        Returns:
            Объект листа Excel
            
        Raises:
            ExcelWorksheetError: При ошибке получения листа
        """
        ExcelErrorHandler.validate_sheet_name(sheet_name)
        
        with self._lock:
            if file_path not in self.workbooks:
                raise ExcelFileError(f"Рабочая книга {file_path} не открыта")
            
            # Проверяем кэш
            cached_worksheet = excel_object_cache.get_cached_worksheet(file_path, sheet_name)
            if cached_worksheet:
                return cached_worksheet
            
            workbook = self.workbooks[file_path]
            
            try:
                # Пытаемся получить лист по имени
                worksheet = workbook.Worksheets(sheet_name)
                
                # Кэшируем лист
                excel_object_cache.cache_worksheet(file_path, sheet_name, worksheet)
                
                return worksheet
                
            except Exception as e:
                logger.error(f"Ошибка при получении листа {sheet_name}: {e}")
                raise ExcelWorksheetError(f"Не удалось получить лист {sheet_name}: {e}")
    
    @excel_error_handler
    def list_worksheets(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Получить список всех листов в рабочей книге
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Список информации о листах
        """
        with self._lock:
            if file_path not in self.workbooks:
                raise ExcelFileError(f"Рабочая книга {file_path} не открыта")
            
            workbook = self.workbooks[file_path]
            
            try:
                worksheets = []
                for i in range(1, workbook.Worksheets.Count + 1):
                    worksheet = workbook.Worksheets(i)
                    worksheets.append({
                        'name': worksheet.Name,
                        'index': i,
                        'visible': worksheet.Visible == -1  # xlSheetVisible
                    })
                
                logger.info(f"Получен список листов для {file_path}: {len(worksheets)} листов")
                return worksheets
                
            except Exception as e:
                logger.error(f"Ошибка при получении списка листов: {e}")
                raise ExcelWorksheetError(f"Не удалось получить список листов: {e}")
    
    @excel_error_handler
    def create_worksheet(self, file_path: str, sheet_name: str, 
                        after_sheet: Optional[str] = None) -> Dict[str, Any]:
        """
        Создать новый лист
        
        Args:
            file_path: Путь к файлу
            sheet_name: Имя нового листа
            after_sheet: Имя листа, после которого создать новый
            
        Returns:
            Информация о созданном листе
        """
        ExcelErrorHandler.validate_sheet_name(sheet_name)
        
        with self._lock:
            if file_path not in self.workbooks:
                raise ExcelFileError(f"Рабочая книга {file_path} не открыта")
            
            workbook = self.workbooks[file_path]
            
            try:
                logger.info(f"Создание листа {sheet_name} в {file_path}")
                
                if after_sheet:
                    # Создаем после указанного листа
                    after_worksheet = workbook.Worksheets(after_sheet)
                    worksheet = workbook.Worksheets.Add(After=after_worksheet)
                else:
                    # Создаем в конце
                    worksheet = workbook.Worksheets.Add()
                
                # Переименовываем лист
                worksheet.Name = sheet_name
                
                # Кэшируем новый лист
                excel_object_cache.cache_worksheet(file_path, sheet_name, worksheet)
                
                logger.info(f"Лист {sheet_name} успешно создан")
                
                return {
                    'success': True,
                    'name': sheet_name,
                    'index': worksheet.Index,
                    'message': f'Лист {sheet_name} создан'
                }
                
            except Exception as e:
                logger.error(f"Ошибка при создании листа {sheet_name}: {e}")
                raise ExcelWorksheetError(f"Не удалось создать лист {sheet_name}: {e}")
    
    @excel_error_handler
    def delete_worksheet(self, file_path: str, sheet_name: str) -> Dict[str, Any]:
        """
        Удалить лист
        
        Args:
            file_path: Путь к файлу
            sheet_name: Имя листа для удаления
            
        Returns:
            Информация о результате удаления
        """
        ExcelErrorHandler.validate_sheet_name(sheet_name)
        
        with self._lock:
            if file_path not in self.workbooks:
                raise ExcelFileError(f"Рабочая книга {file_path} не открыта")
            
            workbook = self.workbooks[file_path]
            
            try:
                logger.info(f"Удаление листа {sheet_name} из {file_path}")
                
                worksheet = workbook.Worksheets(sheet_name)
                worksheet.Delete()
                
                # Удаляем из кэша
                excel_object_cache.worksheets_cache.delete(
                    excel_object_cache.get_worksheet_key(file_path, sheet_name)
                )
                
                logger.info(f"Лист {sheet_name} успешно удален")
                
                return {
                    'success': True,
                    'message': f'Лист {sheet_name} удален'
                }
                
            except Exception as e:
                logger.error(f"Ошибка при удалении листа {sheet_name}: {e}")
                raise ExcelWorksheetError(f"Не удалось удалить лист {sheet_name}: {e}")
    
    @excel_error_handler
    def rename_worksheet(self, file_path: str, old_name: str, new_name: str) -> Dict[str, Any]:
        """
        Переименовать лист
        
        Args:
            file_path: Путь к файлу
            old_name: Старое имя листа
            new_name: Новое имя листа
            
        Returns:
            Информация о результате переименования
        """
        ExcelErrorHandler.validate_sheet_name(old_name)
        ExcelErrorHandler.validate_sheet_name(new_name)
        
        with self._lock:
            if file_path not in self.workbooks:
                raise ExcelFileError(f"Рабочая книга {file_path} не открыта")
            
            workbook = self.workbooks[file_path]
            
            try:
                logger.info(f"Переименование листа {old_name} в {new_name}")
                
                worksheet = workbook.Worksheets(old_name)
                worksheet.Name = new_name
                
                # Обновляем кэш
                excel_object_cache.worksheets_cache.delete(
                    excel_object_cache.get_worksheet_key(file_path, old_name)
                )
                excel_object_cache.cache_worksheet(file_path, new_name, worksheet)
                
                logger.info(f"Лист {old_name} переименован в {new_name}")
                
                return {
                    'success': True,
                    'old_name': old_name,
                    'new_name': new_name,
                    'message': f'Лист {old_name} переименован в {new_name}'
                }
                
            except Exception as e:
                logger.error(f"Ошибка при переименовании листа {old_name}: {e}")
                raise ExcelWorksheetError(f"Не удалось переименовать лист {old_name}: {e}")
    
    def _get_workbook_info(self, workbook, file_path: str) -> Dict[str, Any]:
        """
        Получить информацию о рабочей книге
        
        Args:
            workbook: Объект рабочей книги
            file_path: Путь к файлу
            
        Returns:
            Информация о рабочей книге
        """
        try:
            return {
                'file_path': file_path,
                'name': workbook.Name,
                'worksheets_count': workbook.Worksheets.Count,
                'saved': workbook.Saved,
                'read_only': workbook.ReadOnly,
                'has_password': workbook.HasPassword,
                'file_format': getattr(workbook, 'FileFormat', None)
            }
        except Exception as e:
            logger.warning(f"Ошибка при получении информации о рабочей книге: {e}")
            return {
                'file_path': file_path,
                'name': 'Unknown',
                'worksheets_count': 0,
                'saved': True,
                'read_only': False,
                'has_password': False,
                'file_format': None
            }
    
    def get_excel_info(self) -> Dict[str, Any]:
        """
        Получить информацию о состоянии Excel
        
        Returns:
            Информация о Excel приложении
        """
        with self._lock:
            if not self._initialized:
                return {'status': 'not_initialized'}
            
            try:
                return {
                    'status': 'initialized',
                    'version': self.excel_app.Version,
                    'build': self.excel_app.Build,
                    'visible': self.excel_app.Visible,
                    'display_alerts': self.excel_app.DisplayAlerts,
                    'calculation': str(self.excel_app.Calculation),
                    'open_workbooks': len(self.workbooks),
                    'workbook_paths': list(self.workbooks.keys())
                }
            except Exception as e:
                logger.error(f"Ошибка при получении информации о Excel: {e}")
                return {
                    'status': 'error',
                    'error': str(e)
                } 