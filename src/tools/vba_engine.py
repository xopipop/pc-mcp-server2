"""
MCP Tools для работы с VBA в Excel
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from ..excel_controller import ExcelController
from ..utils.logger import get_logger
from ..utils.error_handler import ExcelErrorHandler, excel_error_handler

logger = get_logger(__name__)


class RunVBAMacroRequest(BaseModel):
    """Запрос на выполнение VBA макроса"""
    file_path: str = Field(..., description="Путь к файлу")
    macro_name: str = Field(..., description="Имя макроса")
    parameters: Optional[List[Any]] = Field(None, description="Параметры макроса")


class ExecuteVBACodeRequest(BaseModel):
    """Запрос на выполнение VBA кода"""
    file_path: str = Field(..., description="Путь к файлу")
    vba_code: str = Field(..., description="VBA код для выполнения")


class CreateVBAModuleRequest(BaseModel):
    """Запрос на создание VBA модуля"""
    file_path: str = Field(..., description="Путь к файлу")
    module_name: str = Field(..., description="Имя модуля")
    code: str = Field(..., description="VBA код модуля")


class VBAEngine:
    """
    MCP Tools для работы с VBA в Excel
    """
    
    def __init__(self, excel_controller: ExcelController):
        """
        Инициализация VBA движка
        
        Args:
            excel_controller: Контроллер Excel
        """
        self.excel_controller = excel_controller
    
    @excel_error_handler
    def run_vba_macro(self, request: RunVBAMacroRequest) -> Dict[str, Any]:
        """
        Выполнить VBA макрос
        
        Args:
            request: Запрос на выполнение макроса
            
        Returns:
            Результат выполнения макроса
        """
        logger.info(f"Выполнение VBA макроса: {request.macro_name}")
        
        try:
            if request.file_path not in self.excel_controller.workbooks:
                raise ExcelErrorHandler.handle_general_error(
                    Exception(f"Рабочая книга {request.file_path} не открыта"),
                    "Выполнение VBA макроса"
                )
            
            workbook = self.excel_controller.workbooks[request.file_path]
            
            # Выполняем макрос
            if request.parameters:
                result = workbook.Application.Run(request.macro_name, *request.parameters)
            else:
                result = workbook.Application.Run(request.macro_name)
            
            return {
                'success': True,
                'message': f'Макрос {request.macro_name} выполнен успешно',
                'macro_name': request.macro_name,
                'file_path': request.file_path,
                'result': result if result is not None else "No return value"
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при выполнении макроса {request.macro_name}: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def execute_vba_code(self, request: ExecuteVBACodeRequest) -> Dict[str, Any]:
        """
        Выполнить произвольный VBA код
        
        Args:
            request: Запрос на выполнение VBA кода
            
        Returns:
            Результат выполнения кода
        """
        logger.info("Выполнение VBA кода")
        
        try:
            if request.file_path not in self.excel_controller.workbooks:
                raise ExcelErrorHandler.handle_general_error(
                    Exception(f"Рабочая книга {request.file_path} не открыта"),
                    "Выполнение VBA кода"
                )
            
            workbook = self.excel_controller.workbooks[request.file_path]
            
            # Выполняем VBA код через Application.Evaluate
            result = workbook.Application.Evaluate(request.vba_code)
            
            return {
                'success': True,
                'message': 'VBA код выполнен успешно',
                'file_path': request.file_path,
                'result': result if result is not None else "No return value"
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при выполнении VBA кода: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def create_vba_module(self, request: CreateVBAModuleRequest) -> Dict[str, Any]:
        """
        Создать VBA модуль
        
        Args:
            request: Запрос на создание VBA модуля
            
        Returns:
            Результат создания модуля
        """
        logger.info(f"Создание VBA модуля: {request.module_name}")
        
        try:
            if request.file_path not in self.excel_controller.workbooks:
                raise ExcelErrorHandler.handle_general_error(
                    Exception(f"Рабочая книга {request.file_path} не открыта"),
                    "Создание VBA модуля"
                )
            
            workbook = self.excel_controller.workbooks[request.file_path]
            
            # Получаем VBA проект
            vba_project = workbook.VBProject
            
            # Создаем новый модуль
            vba_module = vba_project.VBComponents.Add(1)  # 1 = vbext_ct_StdModule
            vba_module.Name = request.module_name
            
            # Добавляем код в модуль
            code_module = vba_module.CodeModule
            code_module.AddFromString(request.code)
            
            return {
                'success': True,
                'message': f'VBA модуль {request.module_name} создан успешно',
                'module_name': request.module_name,
                'file_path': request.file_path,
                'code_lines': len(request.code.split('\n'))
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при создании VBA модуля: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def list_vba_macros(self, file_path: str) -> Dict[str, Any]:
        """
        Получить список доступных VBA макросов
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Список макросов
        """
        logger.info(f"Получение списка VBA макросов для {file_path}")
        
        try:
            if file_path not in self.excel_controller.workbooks:
                raise ExcelErrorHandler.handle_general_error(
                    Exception(f"Рабочая книга {file_path} не открыта"),
                    "Получение списка макросов"
                )
            
            workbook = self.excel_controller.workbooks[file_path]
            
            # Получаем VBA проект
            vba_project = workbook.VBProject
            
            macros = []
            
            # Перебираем все компоненты VBA проекта
            for component in vba_project.VBComponents:
                try:
                    # Получаем код модуля
                    code_module = component.CodeModule
                    
                    # Ищем процедуры (макросы)
                    for i in range(1, code_module.CountOfLines + 1):
                        line = code_module.Lines(i, 1).strip()
                        
                        # Проверяем, является ли строка объявлением процедуры
                        if line.startswith('Sub ') or line.startswith('Function '):
                            # Извлекаем имя процедуры
                            if line.startswith('Sub '):
                                macro_name = line[4:].split('(')[0].strip()
                                macro_type = 'Sub'
                            else:
                                macro_name = line[9:].split('(')[0].strip()
                                macro_type = 'Function'
                            
                            macros.append({
                                'name': macro_name,
                                'type': macro_type,
                                'module': component.Name,
                                'line': i
                            })
                            
                except Exception as e:
                    logger.warning(f"Ошибка при обработке модуля {component.Name}: {e}")
                    continue
            
            return {
                'success': True,
                'macros': macros,
                'count': len(macros),
                'file_path': file_path
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при получении списка макросов: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def list_vba_modules(self, file_path: str) -> Dict[str, Any]:
        """
        Получить список VBA модулей
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Список модулей
        """
        logger.info(f"Получение списка VBA модулей для {file_path}")
        
        try:
            if file_path not in self.excel_controller.workbooks:
                raise ExcelErrorHandler.handle_general_error(
                    Exception(f"Рабочая книга {file_path} не открыта"),
                    "Получение списка модулей"
                )
            
            workbook = self.excel_controller.workbooks[file_path]
            
            # Получаем VBA проект
            vba_project = workbook.VBProject
            
            modules = []
            
            # Перебираем все компоненты VBA проекта
            for component in vba_project.VBComponents:
                try:
                    module_info = {
                        'name': component.Name,
                        'type': self._get_component_type_name(component.Type),
                        'lines': component.CodeModule.CountOfLines if hasattr(component, 'CodeModule') else 0
                    }
                    modules.append(module_info)
                    
                except Exception as e:
                    logger.warning(f"Ошибка при обработке модуля {component.Name}: {e}")
                    continue
            
            return {
                'success': True,
                'modules': modules,
                'count': len(modules),
                'file_path': file_path
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при получении списка модулей: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    @excel_error_handler
    def delete_vba_module(self, file_path: str, module_name: str) -> Dict[str, Any]:
        """
        Удалить VBA модуль
        
        Args:
            file_path: Путь к файлу
            module_name: Имя модуля для удаления
            
        Returns:
            Результат удаления модуля
        """
        logger.info(f"Удаление VBA модуля: {module_name}")
        
        try:
            if file_path not in self.excel_controller.workbooks:
                raise ExcelErrorHandler.handle_general_error(
                    Exception(f"Рабочая книга {file_path} не открыта"),
                    "Удаление VBA модуля"
                )
            
            workbook = self.excel_controller.workbooks[file_path]
            
            # Получаем VBA проект
            vba_project = workbook.VBProject
            
            # Находим модуль
            for component in vba_project.VBComponents:
                if component.Name == module_name:
                    # Удаляем модуль
                    vba_project.VBComponents.Remove(component)
                    
                    return {
                        'success': True,
                        'message': f'VBA модуль {module_name} удален успешно',
                        'module_name': module_name,
                        'file_path': file_path
                    }
            
            # Модуль не найден
            return {
                'success': False,
                'error': {'message': f'VBA модуль {module_name} не найден'}
            }
            
        except Exception as e:
            error_info = ExcelErrorHandler.format_error_response(e)
            logger.error(f"Ошибка при удалении VBA модуля: {error_info}")
            return {
                'success': False,
                'error': error_info
            }
    
    def _get_component_type_name(self, component_type: int) -> str:
        """
        Получить название типа компонента VBA
        
        Args:
            component_type: Тип компонента
            
        Returns:
            Название типа
        """
        type_names = {
            1: 'Standard Module',
            2: 'Class Module',
            3: 'MSForm',
            100: 'Document Module'
        }
        
        return type_names.get(component_type, f'Unknown Type ({component_type})') 