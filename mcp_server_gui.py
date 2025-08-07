#!/usr/bin/env python3
"""
Excel MCP Server GUI Controller
Графический интерфейс для управления MCP сервером Excel
"""

import sys
import os
import subprocess
import threading
import time
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QGroupBox, QTabWidget,
    QScrollArea, QFrame, QSplitter, QMessageBox, QFileDialog,
    QLineEdit, QCheckBox, QComboBox, QSpinBox, QProgressBar
)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QPalette, QColor


class MCPProcessThread(QThread):
    """Поток для управления MCP сервером"""
    output_received = pyqtSignal(str)
    error_received = pyqtSignal(str)
    process_started = pyqtSignal()
    process_stopped = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.process = None
        self.is_running = False
        
    def start_server(self, python_path="python", args=None):
        """Запуск MCP сервера"""
        if args is None:
            args = ["-m", "src.server"]
            
        try:
            # Установка переменных окружения
            env = os.environ.copy()
            env['PYTHONPATH'] = os.getcwd()
            
            self.process = subprocess.Popen(
                [python_path] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,
                cwd=os.getcwd()
            )
            self.is_running = True
            self.process_started.emit()
            
            # Запускаем чтение вывода в отдельном потоке
            self.start()
                    
        except Exception as e:
            self.error_received.emit(f"Ошибка запуска сервера: {str(e)}")
            self.is_running = False
            self.process_stopped.emit()
    
    def stop_server(self):
        """Остановка MCP сервера"""
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            finally:
                self.process = None
        self.process_stopped.emit()
    
    def run(self):
        """Основной метод потока"""
        try:
            # Чтение вывода в отдельном потоке
            while self.is_running and self.process and self.process.poll() is None:
                output = self.process.stdout.readline()
                if output:
                    self.output_received.emit(output.strip())
                    
            # Чтение ошибок
            if self.process:
                stderr_output = self.process.stderr.read()
                if stderr_output:
                    self.error_received.emit(stderr_output.strip())
                    
        except Exception as e:
            self.error_received.emit(f"Ошибка чтения вывода: {str(e)}")
        finally:
            self.is_running = False
            self.process_stopped.emit()


class ExcelMCPServerGUI(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.mcp_thread = None
        self.init_ui()
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setWindowTitle("Excel MCP Server Controller")
        self.setGeometry(100, 100, 1200, 800)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QVBoxLayout(central_widget)
        
        # Заголовок
        title_label = QLabel("Excel MCP Server Controller")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Создание вкладок
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Вкладка управления сервером
        self.create_server_control_tab()
        
        # Вкладка с инструкциями
        self.create_instructions_tab()
        
        # Вкладка с примерами
        self.create_examples_tab()
        
        # Вкладка настроек
        self.create_settings_tab()
        
        # Статус бар
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Готов к работе")
        
        # Таймер для обновления статуса
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)
        
    def create_server_control_tab(self):
        """Создание вкладки управления сервером"""
        server_widget = QWidget()
        layout = QVBoxLayout(server_widget)
        
        # Панель управления
        control_group = QGroupBox("Управление сервером")
        control_layout = QHBoxLayout(control_group)
        
        self.start_button = QPushButton("Запустить сервер")
        self.start_button.clicked.connect(self.start_server)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.stop_button = QPushButton("Остановить сервер")
        self.stop_button.clicked.connect(self.stop_server)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        self.restart_button = QPushButton("Перезапустить")
        self.restart_button.clicked.connect(self.restart_server)
        self.restart_button.setEnabled(False)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.restart_button)
        control_layout.addStretch()
        
        layout.addWidget(control_group)
        
        # Индикатор статуса
        status_group = QGroupBox("Статус сервера")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Статус: Остановлен")
        self.status_label.setFont(QFont("Arial", 12))
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        
        layout.addWidget(status_group)
        
        # Лог сервера
        log_group = QGroupBox("Лог сервера")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setMaximumHeight(300)
        
        # Кнопки для лога
        log_buttons_layout = QHBoxLayout()
        self.clear_log_button = QPushButton("Очистить лог")
        self.clear_log_button.clicked.connect(self.clear_log)
        self.save_log_button = QPushButton("Сохранить лог")
        self.save_log_button.clicked.connect(self.save_log)
        
        log_buttons_layout.addWidget(self.clear_log_button)
        log_buttons_layout.addWidget(self.save_log_button)
        log_buttons_layout.addStretch()
        
        log_layout.addWidget(self.log_text)
        log_layout.addLayout(log_buttons_layout)
        
        layout.addWidget(log_group)
        
        self.tab_widget.addTab(server_widget, "Управление сервером")
        
    def create_instructions_tab(self):
        """Создание вкладки с инструкциями"""
        instructions_widget = QWidget()
        layout = QVBoxLayout(instructions_widget)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Инструкции по установке
        install_group = QGroupBox("Установка")
        install_layout = QVBoxLayout(install_group)
        
        install_text = """
        <h3>Установка зависимостей:</h3>
        <pre>pip install -r requirements.txt
pip install -e .</pre>
        
        <h3>Требования:</h3>
        <ul>
            <li>Windows 10/11</li>
            <li>Python 3.10+</li>
            <li>Microsoft Excel 2016+</li>
            <li>PyQt5 (для GUI)</li>
        </ul>
        """
        install_label = QLabel(install_text)
        install_label.setWordWrap(True)
        install_layout.addWidget(install_label)
        
        scroll_layout.addWidget(install_group)
        
        # Настройка Cursor
        cursor_group = QGroupBox("Настройка Cursor")
        cursor_layout = QVBoxLayout(cursor_group)
        
        cursor_text = """
        <h3>Создайте файл .cursorrules:</h3>
        <pre>{
  "mcpServers": {
    "excel": {
      "command": "python",
      "args": ["-m", "src.server"],
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}</pre>
        """
        cursor_label = QLabel(cursor_text)
        cursor_label.setWordWrap(True)
        cursor_layout.addWidget(cursor_label)
        
        scroll_layout.addWidget(cursor_group)
        
        # Доступные инструменты
        tools_group = QGroupBox("Доступные инструменты")
        tools_layout = QVBoxLayout(tools_group)
        
        tools_text = """
        <h3>Файлы:</h3>
        <ul>
            <li>open_excel_file - открыть файл Excel</li>
            <li>create_new_workbook - создать новую книгу</li>
            <li>save_workbook - сохранить книгу</li>
            <li>close_workbook - закрыть книгу</li>
        </ul>
        
        <h3>Данные:</h3>
        <ul>
            <li>read_cell - прочитать ячейку</li>
            <li>write_cell - записать в ячейку</li>
            <li>read_range - прочитать диапазон</li>
            <li>write_range - записать диапазон</li>
            <li>clear_range - очистить диапазон</li>
        </ul>
        
        <h3>Листы:</h3>
        <ul>
            <li>create_worksheet - создать лист</li>
            <li>delete_worksheet - удалить лист</li>
            <li>rename_worksheet - переименовать лист</li>
            <li>list_worksheets - список листов</li>
        </ul>
        
        <h3>Форматирование:</h3>
        <ul>
            <li>format_cells - форматировать ячейки</li>
            <li>set_font - установить шрифт</li>
            <li>set_borders - установить границы</li>
            <li>apply_conditional_formatting - условное форматирование</li>
        </ul>
        
        <h3>VBA:</h3>
        <ul>
            <li>run_vba_macro - запустить макрос VBA</li>
            <li>execute_vba_code - выполнить код VBA</li>
            <li>create_vba_module - создать модуль VBA</li>
            <li>list_vba_macros - список макросов</li>
        </ul>
        
        <h3>Диаграммы:</h3>
        <ul>
            <li>create_chart - создать диаграмму</li>
            <li>create_pivot_table - создать сводную таблицу</li>
            <li>apply_autofilter - применить автофильтр</li>
            <li>sort_data - сортировка данных</li>
        </ul>
        
        <h3>Утилиты:</h3>
        <ul>
            <li>get_excel_info - информация об Excel</li>
            <li>find_and_replace - найти и заменить</li>
            <li>protect_sheet - защитить лист</li>
        </ul>
        """
        tools_label = QLabel(tools_text)
        tools_label.setWordWrap(True)
        tools_layout.addWidget(tools_label)
        
        scroll_layout.addWidget(tools_group)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        self.tab_widget.addTab(instructions_widget, "Инструкции")
        
    def create_examples_tab(self):
        """Создание вкладки с примерами"""
        examples_widget = QWidget()
        layout = QVBoxLayout(examples_widget)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Примеры использования
        examples_text = """
        <h2>Примеры использования Excel MCP Server</h2>
        
        <h3>1. Создание новой книги и запись данных</h3>
        <pre>
# Создать новую книгу
create_new_workbook()

# Записать данные в ячейки
write_cell("A1", "Заголовок")
write_cell("A2", "Данные 1")
write_cell("A3", "Данные 2")

# Сохранить книгу
save_workbook("example.xlsx")
        </pre>
        
        <h3>2. Чтение данных из файла</h3>
        <pre>
# Открыть файл
open_excel_file("data.xlsx")

# Прочитать ячейку
value = read_cell("A1")

# Прочитать диапазон
data = read_range("A1:C10")

# Закрыть файл
close_workbook()
        </pre>
        
        <h3>3. Работа с листами</h3>
        <pre>
# Создать новый лист
create_worksheet("Новый лист")

# Переименовать лист
rename_worksheet("Лист1", "Данные")

# Получить список листов
sheets = list_worksheets()
        </pre>
        
        <h3>4. Форматирование</h3>
        <pre>
# Установить шрифт
set_font("A1:A10", bold=True, size=14)

# Установить границы
set_borders("A1:D10", border_style="thin")

# Применить условное форматирование
apply_conditional_formatting("A1:A100", "cell_value > 100")
        </pre>
        
        <h3>5. Создание диаграммы</h3>
        <pre>
# Создать диаграмму
create_chart(
    chart_type="line",
    data_range="A1:B10",
    title="График данных"
)
        </pre>
        
        <h3>6. Выполнение VBA кода</h3>
        <pre>
# Выполнить VBA код
execute_vba_code(\"\"\"
Sub HelloWorld()
    MsgBox \"Hello from MCP Server!\"
End Sub
\"\"\")

# Запустить макрос
run_vba_macro(\"HelloWorld\")
        </pre>
        """
        
        examples_label = QLabel(examples_text)
        examples_label.setWordWrap(True)
        scroll_layout.addWidget(examples_label)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        self.tab_widget.addTab(examples_widget, "Примеры")
        
    def create_settings_tab(self):
        """Создание вкладки настроек"""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        
        # Настройки Python
        python_group = QGroupBox("Настройки Python")
        python_layout = QVBoxLayout(python_group)
        
        python_path_layout = QHBoxLayout()
        python_path_layout.addWidget(QLabel("Путь к Python:"))
        self.python_path_edit = QLineEdit("python")
        python_path_layout.addWidget(self.python_path_edit)
        
        python_layout.addLayout(python_path_layout)
        layout.addWidget(python_group)
        
        # Настройки сервера
        server_group = QGroupBox("Настройки сервера")
        server_layout = QVBoxLayout(server_group)
        
        # Аргументы запуска
        args_layout = QHBoxLayout()
        args_layout.addWidget(QLabel("Аргументы запуска:"))
        self.args_edit = QLineEdit("-m src.server")
        args_layout.addWidget(self.args_edit)
        
        server_layout.addLayout(args_layout)
        
        # Автозапуск
        self.auto_start_checkbox = QCheckBox("Автоматически запускать сервер при старте приложения")
        server_layout.addWidget(self.auto_start_checkbox)
        
        # Автосохранение лога
        self.auto_save_log_checkbox = QCheckBox("Автоматически сохранять лог")
        server_layout.addWidget(self.auto_save_log_checkbox)
        
        layout.addWidget(server_group)
        
        # Кнопки настроек
        settings_buttons_layout = QHBoxLayout()
        
        self.save_settings_button = QPushButton("Сохранить настройки")
        self.save_settings_button.clicked.connect(self.save_settings)
        
        self.load_settings_button = QPushButton("Загрузить настройки")
        self.load_settings_button.clicked.connect(self.load_settings)
        
        self.reset_settings_button = QPushButton("Сбросить настройки")
        self.reset_settings_button.clicked.connect(self.reset_settings)
        
        self.install_deps_button = QPushButton("Установить зависимости")
        self.install_deps_button.clicked.connect(self.install_dependencies)
        
        settings_buttons_layout.addWidget(self.save_settings_button)
        settings_buttons_layout.addWidget(self.load_settings_button)
        settings_buttons_layout.addWidget(self.reset_settings_button)
        settings_buttons_layout.addWidget(self.install_deps_button)
        settings_buttons_layout.addStretch()
        
        layout.addLayout(settings_buttons_layout)
        layout.addStretch()
        
        self.tab_widget.addTab(settings_widget, "Настройки")
        
    def start_server(self):
        """Запуск MCP сервера"""
        if self.mcp_thread and self.mcp_thread.is_running:
            QMessageBox.warning(self, "Предупреждение", "Сервер уже запущен!")
            return
            
        self.log_text.append("Запуск MCP сервера...")
        self.status_label.setText("Статус: Запуск...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Бесконечный прогресс
        
        # Создание и запуск потока
        self.mcp_thread = MCPProcessThread()
        self.mcp_thread.output_received.connect(self.log_output)
        self.mcp_thread.error_received.connect(self.log_error)
        self.mcp_thread.process_started.connect(self.on_server_started)
        self.mcp_thread.process_stopped.connect(self.on_server_stopped)
        
        # Получение настроек
        python_path = self.python_path_edit.text()
        args = self.args_edit.text().split()
        
        # Запуск в отдельном потоке
        self.mcp_thread.start_server(python_path, args)
        
    def stop_server(self):
        """Остановка MCP сервера"""
        if not self.mcp_thread or not self.mcp_thread.is_running:
            QMessageBox.warning(self, "Предупреждение", "Сервер не запущен!")
            return
            
        self.log_text.append("Остановка MCP сервера...")
        self.mcp_thread.stop_server()
        
    def restart_server(self):
        """Перезапуск MCP сервера"""
        if self.mcp_thread and self.mcp_thread.is_running:
            self.stop_server()
            # Ждем немного перед перезапуском
            QTimer.singleShot(2000, self.start_server)
        else:
            self.start_server()
            
    def on_server_started(self):
        """Обработчик запуска сервера"""
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.restart_button.setEnabled(True)
        self.status_label.setText("Статус: Запущен")
        self.progress_bar.setVisible(False)
        self.log_text.append("✓ MCP сервер успешно запущен")
        
    def on_server_stopped(self):
        """Обработчик остановки сервера"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.restart_button.setEnabled(False)
        self.status_label.setText("Статус: Остановлен")
        self.progress_bar.setVisible(False)
        self.log_text.append("✓ MCP сервер остановлен")
        
    def log_output(self, text):
        """Логирование вывода сервера"""
        self.log_text.append(f"[OUT] {text}")
        self.log_text.moveCursor(QTextCursor.End)
        
    def log_error(self, text):
        """Логирование ошибок"""
        self.log_text.append(f"[ERROR] {text}")
        self.log_text.moveCursor(QTextCursor.End)
        
    def clear_log(self):
        """Очистка лога"""
        self.log_text.clear()
        
    def save_log(self):
        """Сохранение лога в файл"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить лог", "", "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                QMessageBox.information(self, "Успех", "Лог сохранен!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить лог: {str(e)}")
                
    def update_status(self):
        """Обновление статуса"""
        if self.mcp_thread and self.mcp_thread.is_running:
            if self.mcp_thread.process and self.mcp_thread.process.poll() is None:
                self.status_label.setText("Статус: Работает")
            else:
                self.status_label.setText("Статус: Ошибка")
                self.on_server_stopped()
                
    def save_settings(self):
        """Сохранение настроек"""
        settings = {
            "python_path": self.python_path_edit.text(),
            "args": self.args_edit.text(),
            "auto_start": self.auto_start_checkbox.isChecked(),
            "auto_save_log": self.auto_save_log_checkbox.isChecked()
        }
        
        try:
            with open("mcp_gui_settings.json", 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Успех", "Настройки сохранены!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки: {str(e)}")
            
    def load_settings(self):
        """Загрузка настроек"""
        try:
            with open("mcp_gui_settings.json", 'r', encoding='utf-8') as f:
                settings = json.load(f)
                
            self.python_path_edit.setText(settings.get("python_path", "python"))
            self.args_edit.setText(settings.get("args", "-m src.server"))
            self.auto_start_checkbox.setChecked(settings.get("auto_start", False))
            self.auto_save_log_checkbox.setChecked(settings.get("auto_save_log", False))
            
            QMessageBox.information(self, "Успех", "Настройки загружены!")
        except FileNotFoundError:
            QMessageBox.warning(self, "Предупреждение", "Файл настроек не найден!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить настройки: {str(e)}")
            
    def reset_settings(self):
        """Сброс настроек"""
        self.python_path_edit.setText("python")
        self.args_edit.setText("-m src.server")
        self.auto_start_checkbox.setChecked(False)
        self.auto_save_log_checkbox.setChecked(False)
        QMessageBox.information(self, "Успех", "Настройки сброшены!")
        
    def install_dependencies(self):
        """Установка зависимостей"""
        try:
            self.log_text.append("Установка зависимостей...")
            
            # Установка requirements.txt
            result = subprocess.run(
                [self.python_path_edit.text(), "-m", "pip", "install", "-r", "requirements.txt"],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            if result.returncode == 0:
                self.log_text.append("✓ Зависимости установлены")
                
                # Установка MCP сервера в режиме разработки
                result2 = subprocess.run(
                    [self.python_path_edit.text(), "-m", "pip", "install", "-e", "."],
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd()
                )
                
                if result2.returncode == 0:
                    self.log_text.append("✓ MCP сервер установлен")
                    QMessageBox.information(self, "Успех", "Все зависимости установлены!")
                else:
                    self.log_text.append(f"✗ Ошибка установки MCP сервера: {result2.stderr}")
                    QMessageBox.warning(self, "Предупреждение", "MCP сервер не установлен")
            else:
                self.log_text.append(f"✗ Ошибка установки зависимостей: {result.stderr}")
                QMessageBox.critical(self, "Ошибка", "Не удалось установить зависимости")
                
        except Exception as e:
            self.log_text.append(f"✗ Ошибка: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось установить зависимости: {str(e)}")
        
    def closeEvent(self, event):
        """Обработчик закрытия приложения"""
        if self.mcp_thread and self.mcp_thread.is_running:
            reply = QMessageBox.question(
                self, "Подтверждение",
                "Сервер запущен. Остановить его перед закрытием?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                self.stop_server()
                event.accept()
            elif reply == QMessageBox.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Главная функция"""
    app = QApplication(sys.argv)
    
    # Установка стиля
    app.setStyle('Fusion')
    
    # Создание и отображение главного окна
    window = ExcelMCPServerGUI()
    window.show()
    
    # Запуск приложения
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
