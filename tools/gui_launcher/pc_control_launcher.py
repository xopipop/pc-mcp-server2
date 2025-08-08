import subprocess
import threading
import queue
import sys
import os
from pathlib import Path
import shutil

import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class ServerProcess:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.proc: subprocess.Popen | None = None
        self.out_q: queue.Queue[str] = queue.Queue()
        self._reader_thread: threading.Thread | None = None

    def _resolve_python_cmd(self) -> list[str] | None:
        """Resolve a Python interpreter command that is NOT this launcher.

        Preference order:
        1) Project venv: .venv/Scripts/python.exe
        2) Windows Python Launcher: py -3
        3) python from PATH
        """
        # Prefer project venv
        venv_py = self.project_root / '.venv' / 'Scripts' / 'python.exe'
        if venv_py.exists():
            return [str(venv_py)]

        # Try Windows Python Launcher
        if shutil.which('py'):
            return ['py', '-3']

        # Try python from PATH
        if shutil.which('python'):
            return ['python']

        return None

    def start(self) -> None:
        if self.proc and self.proc.poll() is None:
            return
        cmd_base = self._resolve_python_cmd()
        if not cmd_base:
            messagebox.showerror('Python not found', 'Не найден интерпретатор Python (ни .venv, ни py, ни python в PATH).')
            return
        cmd = [*cmd_base, '-u', 'main.py', '--test-log']
        self.proc = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        )
        self._reader_thread = threading.Thread(target=self._pump_output, daemon=True)
        self._reader_thread.start()

    def _pump_output(self) -> None:
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            self.out_q.put(line.rstrip('\n'))
        self.out_q.put("[process-exited]")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass

    def read_lines(self) -> list[str]:
        lines: list[str] = []
        try:
            while True:
                lines.append(self.out_q.get_nowait())
        except queue.Empty:
            pass
        return lines


class LauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('PC Control MCP — Launcher')
        self.geometry('1000x650')
        self.minsize(800, 480)
        self.project_root = self._detect_project_root()
        self.server = ServerProcess(self.project_root)
        self.status = tk.StringVar(value='Idle')
        self._apply_theme()
        self._build_ui()
        self.after(200, self._poll_output)

    def _detect_project_root(self) -> Path:
        """Detect project root robustly for source and frozen builds.

        - Source run: use repo structure (two parents up).
        - Frozen (PyInstaller): prefer folder with main.py; if running from dist/, go up one.
        """
        try:
            if getattr(sys, 'frozen', False):  # running as bundled exe
                exe_dir = Path(sys.executable).resolve().parent
                # If exe is in project root
                if (exe_dir / 'main.py').exists() or (exe_dir / 'config').exists():
                    return exe_dir
                # If exe is in dist/ under project root
                if exe_dir.name.lower() == 'dist' and (exe_dir.parent / 'main.py').exists():
                    return exe_dir.parent
                return exe_dir
            # Source run
            return Path(__file__).resolve().parents[2]
        except Exception:
            return Path.cwd()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style='Surface.TFrame')
        root.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(root, style='Header.TFrame')
        header.pack(fill=tk.X)
        ttk.Label(header, text='PC Control MCP', style='Title.TLabel').pack(side=tk.LEFT, padx=(16, 8), pady=12)
        ttk.Label(header, text='GUI Launcher', style='Subtitle.TLabel').pack(side=tk.LEFT, pady=12)

        toolbar = ttk.Frame(root, style='Toolbar.TFrame')
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text='Start', style='Accent.TButton', command=self.start_server).pack(side=tk.LEFT, padx=(16, 8), pady=10)
        ttk.Button(toolbar, text='Stop', style='Danger.TButton', command=self.stop_server).pack(side=tk.LEFT, padx=(0, 16), pady=10)
        ttk.Button(toolbar, text='Save Log…', command=self.save_log).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text='Open Logs', command=self.open_logs).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text='Clear', command=self.clear_output).pack(side=tk.LEFT)

        body = ttk.Frame(root, style='Surface.TFrame')
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.output = tk.Text(body, wrap=tk.NONE, state=tk.NORMAL, relief=tk.FLAT, borderwidth=0)
        self.output.configure(bg=self.colors['surface'], fg=self.colors['text'], insertbackground=self.colors['accent'])
        self.output.tag_configure('INFO', foreground=self.colors['info'])
        self.output.tag_configure('WARN', foreground=self.colors['warn'])
        self.output.tag_configure('ERROR', foreground=self.colors['error'])
        self.output.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        xscroll = ttk.Scrollbar(self.output, orient=tk.HORIZONTAL, command=self.output.xview, style='Thin.Horizontal.TScrollbar')
        yscroll = ttk.Scrollbar(self.output, orient=tk.VERTICAL, command=self.output.yview, style='Thin.Vertical.TScrollbar')
        self.output.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)

        statusbar = ttk.Frame(root, style='Status.TFrame')
        statusbar.pack(fill=tk.X)
        ttk.Label(statusbar, textvariable=self.status, style='Status.TLabel').pack(side=tk.LEFT, padx=12, pady=6)

    def start_server(self) -> None:
        self.append('Starting server…', tag='INFO')
        self.server.start()
        self.status.set('Running')

    def stop_server(self) -> None:
        self.append('Stopping server…', tag='WARN')
        self.server.stop()
        self.status.set('Stopped')

    def clear_output(self) -> None:
        self.output.delete('1.0', tk.END)

    def append(self, line: str, tag: str | None = None) -> None:
        use_tag = tag
        upper = line.upper()
        if not use_tag:
            if 'ERROR' in upper or 'TRACEBACK' in upper:
                use_tag = 'ERROR'
            elif 'WARN' in upper or 'WARNING' in upper:
                use_tag = 'WARN'
            elif 'INFO' in upper or 'DEBUG' in upper:
                use_tag = 'INFO'
        if use_tag:
            self.output.insert(tk.END, line + '\n', use_tag)
        else:
            self.output.insert(tk.END, line + '\n')
        self.output.see(tk.END)

    def save_log(self) -> None:
        default_name = f'gui_log_{Path.cwd().name}.txt'
        path = filedialog.asksaveasfilename(defaultextension='.txt', initialfile=default_name)
        if not path:
            return
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.output.get('1.0', tk.END))
        messagebox.showinfo('Saved', f'Saved to {path}')

    def open_logs(self) -> None:
        logs_dir = self.project_root / 'logs'
        logs_dir.mkdir(exist_ok=True)
        os.startfile(str(logs_dir))

    def _poll_output(self) -> None:
        for line in self.server.read_lines():
            if line == '[process-exited]':
                self.append('Server exited', tag='WARN')
                self.status.set('Exited')
            else:
                self.append(line)
        self.after(200, self._poll_output)

    def _apply_theme(self) -> None:
        self.colors = {
            'bg': '#0f1115',
            'surface': '#151922',
            'toolbar': '#10131a',
            'border': '#232838',
            'text': '#e5e7eb',
            'muted': '#a1a7b5',
            'accent': '#3b82f6',
            'accent_fg': '#ffffff',
            'danger': '#ef4444',
            'error': '#ef4444',
            'warn': '#f59e0b',
            'info': '#60a5fa',
        }
        self.configure(bg=self.colors['bg'])
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('Surface.TFrame', background=self.colors['surface'])
        style.configure('Header.TFrame', background=self.colors['toolbar'])
        style.configure('Toolbar.TFrame', background=self.colors['toolbar'])
        style.configure('Status.TFrame', background=self.colors['toolbar'])
        style.configure('Title.TLabel', background=self.colors['toolbar'], foreground=self.colors['text'], font=('Segoe UI', 18, 'bold'))
        style.configure('Subtitle.TLabel', background=self.colors['toolbar'], foreground=self.colors['muted'], font=('Segoe UI', 12))
        style.configure('Status.TLabel', background=self.colors['toolbar'], foreground=self.colors['muted'], font=('Segoe UI', 10))
        style.configure('TLabel', background=self.colors['surface'], foreground=self.colors['text'])
        style.configure('TButton', background=self.colors['surface'], foreground=self.colors['text'], borderwidth=0, padding=(14, 8))
        style.map('TButton', background=[('active', self.colors['border'])])
        style.configure('Accent.TButton', background=self.colors['accent'], foreground=self.colors['accent_fg'])
        style.map('Accent.TButton', background=[('active', '#2563eb')])
        style.configure('Danger.TButton', background=self.colors['danger'], foreground=self.colors['accent_fg'])
        style.map('Danger.TButton', background=[('active', '#dc2626')])
        style.configure('Thin.Horizontal.TScrollbar', troughcolor=self.colors['surface'], background=self.colors['border'])
        style.configure('Thin.Vertical.TScrollbar', troughcolor=self.colors['surface'], background=self.colors['border'])


if __name__ == '__main__':
    app = LauncherApp()
    app.mainloop()


