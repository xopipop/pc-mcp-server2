@echo off
chcp 65001 >nul

echo ========================================
echo    PC Control MCP Server - Quick Start
echo ========================================
echo.

:: Проверяем наличие основного файла сервера
if not exist "pc_control_mcp.py" (
    echo [ОШИБКА] Файл pc_control_mcp.py не найден!
    pause
    exit /b 1
)

:: Активируем виртуальное окружение, если оно есть
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Активация виртуального окружения...
    call venv\Scripts\activate.bat
)

:: Настраиваем переменные окружения
set PYTHONPATH=.
set PC_CONTROL_MCP_LOG_LEVEL=INFO

echo.
echo [ПРЕДУПРЕЖДЕНИЕ] Этот сервер предоставляет ПОЛНЫЙ ДОСТУП к системе!
echo [ПРЕДУПРЕЖДЕНИЕ] Используйте только в изолированной среде!
echo.
echo [INFO] Запуск сервера...
echo [INFO] Для остановки нажмите Ctrl+C
echo.

:: Запускаем сервер
python pc_control_mcp.py

echo.
echo [INFO] Сервер завершен
pause

