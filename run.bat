@echo off
setlocal enabledelayedexpansion

REM Use UTF-8 code page for readable logs
chcp 65001 >nul 2>&1

REM Optional: pass "debug" to see each command
if /i "%~1"=="debug" (
  echo [INFO] Debug mode enabled
  @echo on
)

REM Keep window open by default when double-clicked
set "PAUSE_ON_EXIT=1"
if /i "%~1"=="nopause" set "PAUSE_ON_EXIT=0"

REM Change to the directory of this script
cd /d "%~dp0"

set "VENV_DIR=.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"

REM Detect Python launcher or python.exe
where py >nul 2>&1 && set "PY_LAUNCHER=py -3"
if not defined PY_LAUNCHER (
  where python >nul 2>&1 && set "PY_LAUNCHER=python"
)
if not defined PY_LAUNCHER (
  echo [ERROR] Python 3 is not found in PATH. Install Python 3 and try again.
  set "EXITCODE=1"
  goto :finish
)

REM Create venv if it does not exist
if not exist "%PYTHON_EXE%" (
  echo [INFO] Creating virtual environment in %VENV_DIR%...
  %PY_LAUNCHER% -m venv "%VENV_DIR%"
  if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to create virtual environment. Ensure Python 3 and venv component are installed.
    echo        On Windows Store Python, install:  python -m pip install virtualenv
    set "EXITCODE=1"
    goto :finish
  )
)

REM Upgrade pip quietly
echo [INFO] Upgrading pip...
"%PYTHON_EXE%" -m pip install --upgrade pip --disable-pip-version-check >nul 2>&1

REM Install dependencies if requirements.txt present
if exist requirements.txt (
  echo [INFO] Installing dependencies from requirements.txt ...
  "%PIP_EXE%" install -r requirements.txt
  if %ERRORLEVEL% neq 0 (
    echo [ERROR] Dependency installation failed. See messages above.
    set "EXITCODE=1"
    goto :finish
  )
) else (
  echo [WARN] requirements.txt not found, skipping dependency installation.
)

set "PYTHONUNBUFFERED=1"

REM Prepare logging
set "LOG_DIR=logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%i"
set "LOG_FILE=%LOG_DIR%\run_%TS%.log"
echo [INFO] Logs will be written to: %LOG_FILE%

echo [INFO] Starting PC Control MCP Server...

REM Stream output to both console and log (if PowerShell is available)
where powershell >nul 2>&1
if %ERRORLEVEL%==0 (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Continue'; try { $PSNativeCommandUseErrorActionPreference=$false } catch {}; $log = '%LOG_FILE%'; $env:PYTHONUNBUFFERED='1'; $ProgressPreference='SilentlyContinue'; $utf8NoBom = New-Object System.Text.UTF8Encoding($false); $stream = New-Object System.IO.StreamWriter($log, $true, $utf8NoBom); try { & '%PYTHON_EXE%' -u 'main.py' 2>&1 | ForEach-Object { $_; $stream.WriteLine($_) } } finally { $stream.Flush(); $stream.Dispose() } ; exit $LASTEXITCODE"
) else (
  echo [WARN] PowerShell not found. Logging without live mirroring...
  "%PYTHON_EXE%" -u main.py 1>> "%LOG_FILE%" 2>&1
)

set "EXITCODE=%ERRORLEVEL%"

if %EXITCODE% neq 0 (
  echo [ERROR] Server exited with code %EXITCODE%.
) else (
  echo [INFO] Server stopped.
)

:finish
if "%PAUSE_ON_EXIT%"=="1" (
  echo.
  echo Press any key to close this window...
  pause >nul
)
exit /b %EXITCODE%


