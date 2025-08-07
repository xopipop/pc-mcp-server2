"""
MCP Tools для продвинутых операций Excel
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from ..excel_controller import ExcelController
from ..utils.logger import get_logger
from ..utils.error_handler import ExcelErrorHandler, excel_error_handler

logger = get_logger(__name__)


class CreateChartRequest(BaseModel):
    """Запрос на создание диаграммы"""
    file_path: str = Field(..., description="Путь к файлу")
    sheet: str = Field(..., description="Имя листа")
    data_range: str = Field(..., description="Диапазон данных")
    chart_type: str = Field(..., description="Тип диаграммы")
    chart_title: Optional[str] = Field(None, description="Заголовок диаграммы")
    chart_location: Optional[str] = Field(None, description="Расположение диаграммы")


class CreatePivotTableRequest(BaseModel):
    """Запрос на создание сводной таблицы"""
    file_path: str = Field(..., description="Путь к файлу")
    sheet: str = Field(..., description="Имя листа")
    source_data: str = Field(..., description="Диапазон исходных данных")
    destination: str = Field(..., description="Место размещения сводной таблицы")
    fields: Dict[str, List[str]] = Field(..., description="Поля для сводной таблицы")


class SortDataRequest(BaseModel):
    """Запрос на сортировку данных"""
    file_path: str = Field(..., description="Путь к файлу")
    sheet: str = Field(..., description="Имя листа")
    range_address: str = Field(..., description="Диапазон для сортировки")
    sort_options: Dict[str, Any] = Field(..., description="Опции сортировки")


class FilterDataRequest(BaseModel):
    """Запрос на фильтрацию данных"""
    file_path: str = Field(..., description="Путь к файлу")
    sheet: str = Field(..., description="Имя листа")
    range_address: str = Field(..., description="Диапазон для фильтрации")
    filter_criteria: Dict[str, Any] = Field(..., description="Критерии фильтрации")


class AdvancedOperations:
    """
    MCP Tools для продвинутых операций Excel
    """
    
    def __init__(self, excel_controller: ExcelController):
        """
        Инициализация продвинутых операций
        
        Args:
            excel_controller: Контроллер Excel
        """
        self.excel_controller = excel_controller
    
    @excel_error_handler
    def create_chart(self, request: CreateChartRequest) -> Dict[str, Any]:
        """
        Создать диаграмму
        
        Args:
            request: Запрос на создание диаграммы
            
        Returns:
            Результат создания диаграммы
        """
        logger.info(f"Создание диаграммы типа {request.chart_type}")
        
        try:
            ExcelErrorHandler.validate_range_address(request.data_range)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(request.file_path, request.sheet)
            
            # Получаем диапазон данных
            data_range = worksheet.Range(request.data_range)
            
            # Создаем диаграмму
            chart = worksheet.Shapes.AddChart2()
            chart_object = chart.Chart
            
            # Устанавливаем тип диаграммы
            chart_types = {
                'line': 4,
                'column': 51,
                'bar': 57,
                'pie': 5,
                'scatter': -4169,
                'area': 1
            }
            
            chart_type_const = chart_types.get(request.chart_type.lower(), 51)
            chart_object.ChartType = chart_type_const
            
            # Устанавливаем данные
            chart_object.SetSourceData(Source=data_range)
            
            # Устанавливаем заголовок
            if request.chart_title:
                chart_object.ChartTitle.Text = request.chart_title
            
            return {
                'success': True,
                'message': f'Диаграмма типа {request.chart_type} создана',
                'chart_type': request.chart_type,
                'data_range': request.data_range,
                'sheet': request.sheet,
                'file_path': request.file_path
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при создании диаграммы: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def create_pivot_table(self, request: CreatePivotTableRequest) -> Dict[str, Any]:
        """
        Создать сводную таблицу
        
        Args:
            request: Запрос на создание сводной таблицы
            
        Returns:
            Результат создания сводной таблицы
        """
        logger.info("Создание сводной таблицы")
        
        try:
            ExcelErrorHandler.validate_range_address(request.source_data)
            ExcelErrorHandler.validate_range_address(request.destination)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(request.file_path, request.sheet)
            
            # Получаем диапазоны
            source_range = worksheet.Range(request.source_data)
            destination_range = worksheet.Range(request.destination)
            
            # Создаем сводную таблицу
            pivot_cache = self.excel_controller.excel_app.ActiveWorkbook.PivotCaches().Create(
                SourceType=1,  # xlDatabase
                SourceData=source_range
            )
            
            pivot_table = pivot_cache.CreatePivotTable(
                TableDestination=destination_range,
                TableName="PivotTable1"
            )
            
            return {
                'success': True,
                'message': 'Сводная таблица создана',
                'source_data': request.source_data,
                'destination': request.destination,
                'sheet': request.sheet,
                'file_path': request.file_path
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при создании сводной таблицы: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def sort_data(self, request: SortDataRequest) -> Dict[str, Any]:
        """
        Сортировать данные
        
        Args:
            request: Запрос на сортировку
            
        Returns:
            Результат сортировки
        """
        logger.info(f"Сортировка данных в диапазоне {request.range_address}")
        
        try:
            ExcelErrorHandler.validate_range_address(request.range_address)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(request.file_path, request.sheet)
            
            # Получаем диапазон
            range_obj = worksheet.Range(request.range_address)
            
            # Применяем сортировку
            sort_key = request.sort_options.get('key', 1)
            sort_order = request.sort_options.get('order', 1)  # 1 = ascending, 2 = descending
            
            range_obj.Sort(
                Key1=range_obj.Columns(sort_key),
                Order1=sort_order
            )
            
            return {
                'success': True,
                'message': f'Данные отсортированы в диапазоне {request.range_address}',
                'range_address': request.range_address,
                'sheet': request.sheet,
                'file_path': request.file_path,
                'sort_options': request.sort_options
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при сортировке данных: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def apply_autofilter(self, file_path: str, sheet: str, range_address: str) -> Dict[str, Any]:
        """
        Применить автофильтр
        
        Args:
            file_path: Путь к файлу
            sheet: Имя листа
            range_address: Адрес диапазона
            
        Returns:
            Результат применения автофильтра
        """
        logger.info(f"Применение автофильтра к диапазону {range_address}")
        
        try:
            ExcelErrorHandler.validate_range_address(range_address)
            
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(file_path, sheet)
            
            # Получаем диапазон
            range_obj = worksheet.Range(range_address)
            
            # Применяем автофильтр
            range_obj.AutoFilter()
            
            return {
                'success': True,
                'message': f'Автофильтр применен к диапазону {range_address}',
                'range_address': range_address,
                'sheet': sheet,
                'file_path': file_path
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при применении автофильтра: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def remove_autofilter(self, file_path: str, sheet: str) -> Dict[str, Any]:
        """
        Удалить автофильтр
        
        Args:
            file_path: Путь к файлу
            sheet: Имя листа
            
        Returns:
            Результат удаления автофильтра
        """
        logger.info(f"Удаление автофильтра с листа {sheet}")
        
        try:
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(file_path, sheet)
            
            # Удаляем автофильтр
            if worksheet.AutoFilterMode:
                worksheet.AutoFilterMode = False
            
            return {
                'success': True,
                'message': f'Автофильтр удален с листа {sheet}',
                'sheet': sheet,
                'file_path': file_path
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при удалении автофильтра: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def protect_sheet(self, file_path: str, sheet: str, password: Optional[str] = None,
                     options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Защитить лист
        
        Args:
            file_path: Путь к файлу
            sheet: Имя листа
            password: Пароль для защиты
            options: Опции защиты
            
        Returns:
            Результат защиты листа
        """
        logger.info(f"Защита листа {sheet}")
        
        try:
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(file_path, sheet)
            
            # Опции защиты по умолчанию
            default_options = {
                'DrawingObjects': True,
                'Contents': True,
                'Scenarios': True,
                'UserInterfaceOnly': False
            }
            
            if options:
                default_options.update(options)
            
            # Защищаем лист
            worksheet.Protect(
                Password=password,
                **default_options
            )
            
            return {
                'success': True,
                'message': f'Лист {sheet} защищен',
                'sheet': sheet,
                'file_path': file_path,
                'protected': True
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при защите листа: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def unprotect_sheet(self, file_path: str, sheet: str, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Снять защиту с листа
        
        Args:
            file_path: Путь к файлу
            sheet: Имя листа
            password: Пароль для снятия защиты
            
        Returns:
            Результат снятия защиты
        """
        logger.info(f"Снятие защиты с листа {sheet}")
        
        try:
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(file_path, sheet)
            
            # Снимаем защиту
            worksheet.Unprotect(Password=password)
            
            return {
                'success': True,
                'message': f'Защита снята с листа {sheet}',
                'sheet': sheet,
                'file_path': file_path,
                'protected': False
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при снятии защиты с листа: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def find_and_replace(self, file_path: str, sheet: str, find_text: str, 
                        replace_text: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Найти и заменить текст
        
        Args:
            file_path: Путь к файлу
            sheet: Имя листа
            find_text: Текст для поиска
            replace_text: Текст для замены
            options: Опции поиска
            
        Returns:
            Результат поиска и замены
        """
        logger.info(f"Поиск и замена '{find_text}' на '{replace_text}'")
        
        try:
            # Получаем лист
            worksheet = self.excel_controller.get_worksheet(file_path, sheet)
            
            # Опции поиска по умолчанию
            default_options = {
                'LookIn': -4163,  # xlValues
                'LookAt': 1,      # xlPart
                'SearchOrder': 1,  # xlByRows
                'MatchCase': False,
                'MatchWholeWord': False
            }
            
            if options:
                default_options.update(options)
            
            # Выполняем поиск и замену
            worksheet.Cells.Replace(
                What=find_text,
                Replacement=replace_text,
                **default_options
            )
            
            return {
                'success': True,
                'message': f"Выполнен поиск и замена '{find_text}' на '{replace_text}'",
                'sheet': sheet,
                'file_path': file_path,
                'find_text': find_text,
                'replace_text': replace_text
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при поиске и замене: {error_info}")
            return {
                'success': False,
                'error': error_info
            } 