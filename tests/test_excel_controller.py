"""
Тесты для Excel контроллера
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from src.excel_controller import ExcelController
from src.utils.error_handler import ExcelFileError, ExcelWorksheetError


class TestExcelController(unittest.TestCase):
    """Тесты для Excel контроллера"""
    
    def setUp(self):
        """Настройка тестов"""
        self.controller = ExcelController()
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.xlsx")
    
    def tearDown(self):
        """Очистка после тестов"""
        if self.controller:
            self.controller.cleanup()
        
        # Удаляем временные файлы
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    @patch('src.excel_controller.win32com.client')
    def test_initialize(self, mock_win32com):
        """Тест инициализации Excel контроллера"""
        # Мокаем Excel приложение
        mock_excel = Mock()
        mock_win32com.Dispatch.return_value = mock_excel
        
        # Выполняем инициализацию
        self.controller.initialize()
        
        # Проверяем, что Excel был создан
        mock_win32com.Dispatch.assert_called_with("Excel.Application")
        
        # Проверяем настройки Excel
        self.assertEqual(mock_excel.Visible, False)
        self.assertEqual(mock_excel.DisplayAlerts, False)
        self.assertEqual(mock_excel.EnableEvents, True)
    
    def test_validate_file_path(self):
        """Тест валидации пути к файлу"""
        from src.utils.error_handler import ExcelErrorHandler
        
        # Валидные пути
        valid_paths = [
            "test.xlsx",
            "data.xls",
            "report.xlsm",
            "backup.xlsb",
            "export.csv"
        ]
        
        for path in valid_paths:
            try:
                ExcelErrorHandler.validate_file_path(path)
            except ExcelFileError:
                self.fail(f"Валидный путь {path} был отклонен")
        
        # Невалидные пути
        invalid_paths = [
            "",
            None,
            "test.txt",
            "data.doc"
        ]
        
        for path in invalid_paths:
            with self.assertRaises(ExcelFileError):
                ExcelErrorHandler.validate_file_path(path)
    
    def test_validate_sheet_name(self):
        """Тест валидации имени листа"""
        from src.utils.error_handler import ExcelErrorHandler
        
        # Валидные имена
        valid_names = [
            "Sheet1",
            "Data",
            "Report_2024",
            "Анализ"
        ]
        
        for name in valid_names:
            try:
                ExcelErrorHandler.validate_sheet_name(name)
            except ExcelWorksheetError:
                self.fail(f"Валидное имя {name} было отклонено")
        
        # Невалидные имена
        invalid_names = [
            "",
            None,
            "Sheet with spaces",
            "Sheet*with*invalid*chars",
            "VeryLongSheetNameThatExceedsTheMaximumAllowedLength"
        ]
        
        for name in invalid_names:
            with self.assertRaises(ExcelWorksheetError):
                ExcelErrorHandler.validate_sheet_name(name)
    
    def test_validate_range_address(self):
        """Тест валидации адреса диапазона"""
        from src.utils.error_handler import ExcelErrorHandler
        
        # Валидные адреса
        valid_ranges = [
            "A1",
            "B2:C10",
            "D5:E20",
            "A1:Z1000"
        ]
        
        for range_addr in valid_ranges:
            try:
                ExcelErrorHandler.validate_range_address(range_addr)
            except Exception:
                self.fail(f"Валидный адрес {range_addr} был отклонен")
        
        # Невалидные адреса
        invalid_ranges = [
            "",
            None,
            "A",
            "1",
            "A1:B",
            "A:B1"
        ]
        
        for range_addr in invalid_ranges:
            with self.assertRaises(Exception):
                ExcelErrorHandler.validate_range_address(range_addr)


if __name__ == '__main__':
    unittest.main() 