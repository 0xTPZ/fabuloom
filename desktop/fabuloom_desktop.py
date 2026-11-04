"""Fabuloom Studio Desktop shell over the shared EngineService.

This is intentionally a thin native shell. Projects, jobs, library queries
and API calls stay in ``fabuloom_core``; the shell does not implement a second
renderer or TTS pipeline. The existing browser Stage remains available as a
view of the same local product while the native editor surface grows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fabuloom_core.engine import EngineService
from fabuloom_core.api import EngineAPIServer
from fabuloom_core.paths import FabuloomPaths
from fabuloom_core.plugins import PluginRegistry


class FabuloomDesktop:
    def __init__(self, paths: FabuloomPaths, *, api_port: int = 8790, stage_port: int = 8765):
        self.paths = paths
        self.engine = EngineService(paths)
        self.api_port = api_port
        self.stage_port = stage_port
        self.root = tk.Tk()
        self.root.title("Fabuloom Studio")
        self.root.geometry("1120x720")
        self.root.minsize(900, 560)
        self.status_var = tk.StringVar(value="Motor pronto")
        self.project_tree: ttk.Treeview | None = None
        self.library_tree: ttk.Treeview | None = None
        self.job_tree: ttk.Treeview | None = None
        self.dashboard_text: tk.Text | None = None
        self.stage_process: subprocess.Popen[str] | None = None
        self.api_server = EngineAPIServer(("127.0.0.1", self.api_port), self.engine)
        self.api_thread = threading.Thread(target=self.api_server.serve_forever, name="fabuloom-api", daemon=True)
        self.api_thread.start()
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.root.configure(bg="#101827")
        header = tk.Frame(self.root, bg="#101827", padx=20, pady=16)
        header.pack(fill="x")
        tk.Label(header, text="FABULOOM STUDIO", fg="#f7d27a", bg="#101827", font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(header, textvariable=self.status_var, fg="#b7c5dc", bg="#101827", font=("Segoe UI", 10)).pack(side="right")
        body = tk.Frame(self.root, bg="#101827")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        sidebar = tk.Frame(body, bg="#182438", width=210, padx=12, pady=12)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="Workspace", fg="#f3f6fb", bg="#182438", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 12))
        for label, callback in (("Dashboard", self.refresh), ("Novo projeto", self.new_project), ("Abrir Stage", self.open_stage), ("Music Studio", self.open_music), ("Atualizar catálogo", self.catalog_scan)):
            ttk.Button(sidebar, text=label, command=callback).pack(fill="x", pady=4)
        ttk.Separator(sidebar).pack(fill="x", pady=16)
        tk.Label(sidebar, text="Motor compartilhado", fg="#f7d27a", bg="#182438", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(sidebar, text="Desktop · CLI · API local\nmesmos projetos e jobs", justify="left", fg="#b7c5dc", bg="#182438", font=("Segoe UI", 9)).pack(anchor="w", pady=8)
        notebook = ttk.Notebook(body)
        notebook.pack(side="left", fill="both", expand=True, padx=(14, 0))
        dashboard = ttk.Frame(notebook, padding=18)
        projects = ttk.Frame(notebook, padding=18)
        library = ttk.Frame(notebook, padding=18)
        jobs = ttk.Frame(notebook, padding=18)
        notebook.add(dashboard, text="Dashboard")
        notebook.add(projects, text="Projetos")
        notebook.add(library, text="Biblioteca")
        notebook.add(jobs, text="Jobs")
        self.dashboard_text = tk.Text(dashboard, height=20, state="disabled", wrap="word")
        self.dashboard_text.pack(fill="both", expand=True)
        self.project_tree = self._tree(projects, ("id", "name", "revision", "updated_at"), (180, 240, 80, 220))
        self.library_tree = self._tree(library, ("name", "kind", "relative_path", "size_bytes"), (220, 100, 500, 120))
        self.job_tree = self._tree(jobs, ("id", "kind", "state", "progress"), (260, 180, 130, 100))

    @staticmethod
    def _tree(parent: ttk.Frame, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=columns, show="headings")
        for column, width in zip(columns, widths):
            tree.heading(column, text=column)
            tree.column(column, width=width, anchor="w")
        tree.pack(fill="both", expand=True)
        return tree

    def refresh(self) -> None:
        status = self.engine.status()
        self.status_var.set(f"{status['projects']} projetos · {status['jobs']['running']} jobs em execução")
        if self.dashboard_text is not None:
            self.dashboard_text.configure(state="normal")
            self.dashboard_text.delete("1.0", "end")
            self.dashboard_text.insert("end", json.dumps(status, ensure_ascii=False, indent=2))
            self.dashboard_text.configure(state="disabled")
        self._replace(self.project_tree, self.engine.list_projects(), ("id", "name", "revision", "updated_at"))
        self._replace(self.library_tree, self.engine.search_library(), ("name", "kind", "relative_path", "size_bytes"))
        self._replace(self.job_tree, self.engine.list_jobs(), ("id", "kind", "state", "progress"))

    @staticmethod
    def _replace(tree: ttk.Treeview | None, values: list[dict[str, object]], columns: tuple[str, ...]) -> None:
        if tree is None:
            return
        for child in tree.get_children():
            tree.delete(child)
        for value in values:
            tree.insert("", "end", values=tuple(value.get(column, "") for column in columns))

    def new_project(self) -> None:
        name = simpledialog.askstring("Novo projeto", "Nome do projeto:", parent=self.root)
        if name:
            try:
                self.engine.create_project(name)
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Projeto", str(exc), parent=self.root)

    def catalog_scan(self) -> None:
        job = self.engine.create_job("catalog-scan")
        self.status_var.set(f"Catálogo iniciado: {job['id']}")
        self.root.after(500, self.refresh)

    def _start_stage_server(self) -> None:
        if self.stage_process and self.stage_process.poll() is None:
            return
        server = ROOT / "frontend" / "server.py"
        if not server.is_file():
            raise FileNotFoundError(server)
        import os

        environment = os.environ.copy()
        environment["FABULOOM_ROOT"] = str(self.paths.root)
        self.stage_process = subprocess.Popen([sys.executable, str(server), "--port", str(self.stage_port)], cwd=ROOT, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, text=True)

    def open_stage(self) -> None:
        try:
            self._start_stage_server()
            webbrowser.open(f"http://127.0.0.1:{self.stage_port}/studio.html")
        except Exception as exc:
            messagebox.showerror("Stage", str(exc), parent=self.root)

    def open_music(self) -> None:
        try:
            self._start_stage_server()
            webbrowser.open(f"http://127.0.0.1:{self.stage_port}/studio.html#music")
        except Exception as exc:
            messagebox.showerror("Music Studio", str(exc), parent=self.root)

    def close(self) -> None:
        self.api_server.shutdown()
        self.api_server.server_close()
        if self.stage_process and self.stage_process.poll() is None:
            self.stage_process.terminate()
        self.root.destroy()

    def run(self) -> int:
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.mainloop()
        return 0


def check(paths: FabuloomPaths) -> dict[str, object]:
    registry = PluginRegistry(ROOT / "plugins")
    return {"desktop": "tkinter-native-shell", "engine": "fabuloom_core.engine.EngineService", "api": "loopback-only", "paths": paths.as_dict(), "plugins": [manifest.as_dict() for manifest in registry.enabled()], "gui_available": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    parser.add_argument("--api-port", type=int, default=8790)
    parser.add_argument("--stage-port", type=int, default=8765)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    paths = FabuloomPaths.discover(product_root=ROOT, configured_root=args.root)
    if args.check:
        print(json.dumps(check(paths), ensure_ascii=False, indent=2))
        return 0
    return FabuloomDesktop(paths, api_port=args.api_port, stage_port=args.stage_port).run()


if __name__ == "__main__":
    raise SystemExit(main())
