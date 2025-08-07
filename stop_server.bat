@echo off
chcp 65001 >nul

echo ========================================
echo    PC Control MCP Server - Stop
echo ========================================
echo.

:: Ищем процессы Python, запущенные с pc_control_mcp.py
echo [INFO] Поиск запущенных процессов PC Control MCP Server...

:: Используем tasklist для поиска процессов
tasklist /FI "IMAGENAME eq python.exe" /FO CSV | findstr /I "pc_control_mcp" >nul
if errorlevel 1 (
    echo [INFO] Процессы PC Control MCP Server не найдены
) else (
    echo [INFO] Найдены процессы PC Control MCP Server
    echo [INFO] Завершение процессов...
    
    :: Завершаем процессы Python, которые запущены с pc_control_mcp.py
    for /f "tokens=2 delims=," %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV ^| findstr /I "pc_control_mcp"') do (
        echo Завершение процесса PID: %%i
        taskkill /PID %%i /F >nul 2>&1
    )
)

:: Альтернативный способ - завершить все процессы Python (осторожно!)
echo.
echo [ВНИМАНИЕ] Если сервер не остановился, можно завершить все процессы Python
echo [ВНИМАНИЕ] Это может повлиять на другие Python приложения!
echo.
set /p choice="Завершить все процессы Python? (y/N): "
if /i "%choice%"=="y" (
    echo [INFO] Завершение всех процессов Python...
    taskkill /IM python.exe /F >nul 2>&1
    echo [INFO] Все процессы Python завершены
) else (
    echo [INFO] Отменено
)

echo.
echo [INFO] Операция завершена
pause

