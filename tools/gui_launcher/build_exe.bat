@echo off
setlocal
cd /d %~dp0\..\..

set PY_EXE=.venv\Scripts\python.exe
if not exist %PY_EXE% set PY_EXE=python

echo [INFO] Using Python: %PY_EXE%
%PY_EXE% -m pip install --upgrade pip pyinstaller || goto :eof

echo [INFO] Building GUI launcher...
%PY_EXE% -m PyInstaller --noconfirm --onefile --windowed tools/gui_launcher/pc_control_launcher.py || goto :eof

echo [INFO] Done. EXE at dist\pc_control_launcher.exe
endlocal

