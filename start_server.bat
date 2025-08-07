@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo    PC Control MCP Server Launcher
echo ========================================
echo.

:: Проверяем, установлен ли Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден в системе!
    echo Пожалуйста, установите Python 3.8+ с https://python.org
    echo.
    pause
    exit /b 1
)

echo [INFO] Python найден
python --version

:: Проверяем, установлен ли pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] pip не найден!
    echo Пожалуйста, переустановите Python с включенным pip
    echo.
    pause
    exit /b 1
)

echo [INFO] pip найден
pip --version

:: Создаем виртуальное окружение, если его нет
if not exist "venv" (
    echo [INFO] Создание виртуального окружения...
    python -m venv venv
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось создать виртуальное окружение!
        pause
        exit /b 1
    )
    echo [INFO] Виртуальное окружение создано
)

:: Активируем виртуальное окружение
echo [INFO] Активация виртуального окружения...
call venv\Scripts\activate.bat

:: Обновляем pip
echo [INFO] Обновление pip...
python -m pip install --upgrade pip

:: Устанавливаем зависимости
echo [INFO] Установка зависимостей...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости!
    echo Попробуйте запустить: pip install -r requirements.txt
    pause
    exit /b 1
)

:: Устанавливаем GUI зависимости, если нужно
if exist "install_gui_dependencies.py" (
    echo [INFO] Установка GUI зависимостей...
    python install_gui_dependencies.py
)

:: Настраиваем переменные окружения
echo [INFO] Настройка переменных окружения...
set PYTHONPATH=.
set PC_CONTROL_MCP_LOG_LEVEL=INFO

:: Проверяем наличие основного файла сервера
if not exist "pc_control_mcp.py" (
    echo [ОШИБКА] Файл pc_control_mcp.py не найден!
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Запуск PC Control MCP Server
echo ========================================
echo.
echo [ПРЕДУПРЕЖДЕНИЕ] Этот сервер предоставляет ПОЛНЫЙ ДОСТУП к системе!
echo [ПРЕДУПРЕЖДЕНИЕ] Используйте только в изолированной среде!
echo.
echo [INFO] Сервер запускается...
echo [INFO] Для остановки нажмите Ctrl+C
echo.

:: Запускаем сервер
python pc_control_mcp.py

:: Если сервер завершился с ошибкой
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Сервер завершился с ошибкой!
    echo Проверьте логи в папке: %USERPROFILE%\.pc_control_mcp\logs\
    echo.
    pause
    exit /b 1
)

echo.
echo [INFO] Сервер завершен
pause

