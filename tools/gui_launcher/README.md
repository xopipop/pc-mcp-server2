PC Control MCP GUI Launcher
===========================

Windows GUI-приложение для запуска сервера, просмотра и сохранения логов.

Возможности:
- Запуск/остановка `main.py` в подпроцессе (`python -u main.py --test-log`).
- Отображение stdout/stderr в окне.
- Кнопки: Сохранить лог, Открыть папку логов, Очистить вывод.

Сборка EXE:
1) Активировать venv (`.venv`).
2) Установить:
   pip install pyinstaller
3) Сборка:
   pyinstaller --noconfirm --onefile --windowed tools/gui_launcher/pc_control_launcher.py
   Готовый `pc_control_launcher.exe` появится в `dist/`.

Запуск из исходников:
python tools/gui_launcher/pc_control_launcher.py


