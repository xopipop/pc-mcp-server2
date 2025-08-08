import subprocess
import threading
import queue
import sys
import os
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class ServerProcess:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.proc: subprocess.Popen | None = None
        self.out_q: queue.Queue[str] = queue.Queue()
        self._reader_thread: threading.Thread | None = None

    def start(self) -> None:
        if self.proc and self.proc.poll() is None:
            return
        python_exe = Path('.venv/Scripts/python.exe')
        if not python_exe.exists():
            python_exe = sys.executable
        cmd = [str(python_exe), '-u', 'main.py', '--test-log']
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
        self.title('PC Control MCP - Launcher')
        self.geometry('900x600')
        self.minsize(700, 400)
        self.project_root = Path(__file__).resolve().parents[2]
        self.server = ServerProcess(self.project_root)
        self._build_ui()
        self.after(200, self._poll_output)

    def _build_ui(self) -> None:
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(btns, text='Start Server', command=self.start_server).pack(side=tk.LEFT)
        ttk.Button(btns, text='Stop Server', command=self.stop_server).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text='Save Log…', command=self.save_log).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text='Open Logs Folder', command=self.open_logs).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text='Clear', command=self.clear_output).pack(side=tk.LEFT, padx=(8, 0))

        self.output = tk.Text(frm, wrap=tk.NONE, state=tk.NORMAL)
        self.output.pack(fill=tk.BOTH, expand=True)

        xscroll = ttk.Scrollbar(self.output, orient=tk.HORIZONTAL, command=self.output.xview)
        yscroll = ttk.Scrollbar(self.output, orient=tk.VERTICAL, command=self.output.yview)
        self.output.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)

    def start_server(self) -> None:
        self.append('Starting server…')
        self.server.start()

    def stop_server(self) -> None:
        self.append('Stopping server…')
        self.server.stop()

    def clear_output(self) -> None:
        self.output.delete('1.0', tk.END)

    def append(self, line: str) -> None:
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
                self.append('Server exited')
            else:
                self.append(line)
        self.after(200, self._poll_output)


if __name__ == '__main__':
    app = LauncherApp()
    app.mainloop()


