@echo off
setlocal

echo ========================================
echo PC Control MCP Server - Быстрый запуск
echo ========================================
echo.

:: Проверка наличия Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не найден. Пожалуйста, установите Python 3.8+
    echo Скачать можно с: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Проверка наличия виртуального окружения
if not exist "venv" (
    echo [INFO] Создание виртуального окружения...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ОШИБКА] Не удалось создать виртуальное окружение
        pause
        exit /b 1
    )
    echo [OK] Виртуальное окружение создано
)

:: Активация виртуального окружения
echo [INFO] Активация виртуального окружения...
call venv\Scripts\activate.bat

:: Проверка и установка зависимостей
echo [INFO] Проверка зависимостей...
pip show mcp >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Установка зависимостей...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ОШИБКА] Не удалось установить зависимости
        pause
        exit /b 1
    )
    echo [OK] Зависимости установлены
) else (
    echo [OK] Зависимости уже установлены
)

:: Проверка конфигурации
if not exist "config\local.yaml" (
    echo [INFO] Создание локальной конфигурации...
    if exist "config\default.yaml" (
        copy "config\default.yaml" "config\local.yaml" >nul
        echo [OK] Локальная конфигурация создана
    )
)

:: Проверка прав администратора
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ПРЕДУПРЕЖДЕНИЕ] Сервер запущен БЕЗ прав администратора
    echo Некоторые функции могут быть недоступны:
    echo - Управление службами
    echo - Некоторые системные операции
    echo - Операции с реестром
    echo.
    echo Для полного функционала запустите от имени администратора
    echo.
)

:: Запуск сервера
echo.
echo [INFO] Запуск PC Control MCP Server...
echo ========================================
echo.

:: Установка переменных окружения для отключения безопасности в dev режиме
set PC_CONTROL_SECURITY__ENABLED=false
set PC_CONTROL_LOGGING__LEVEL=INFO

:: Запуск
python main.py

:: Обработка завершения
if %errorlevel% neq 0 (
    echo.
    echo [ОШИБКА] Сервер завершился с ошибкой
    pause
)

deactivate
endlocal