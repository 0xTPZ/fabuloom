"""Capture the three-narrator five-state facial recovery board."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

STUDIO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports")


def _edge_path() -> Path:
    for root in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES")):
        if root:
            candidate = Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if candidate.is_file(): return candidate
    raise FileNotFoundError("Microsoft Edge is required")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--export-dir", type=Path, default=EXPORT_ROOT); parser.add_argument("--overwrite", action="store_true"); parser.add_argument("--port", type=int, default=8802); parser.add_argument("--timeout", type=float, default=120); args = parser.parse_args()
    output_root = args.export_dir.resolve() / "videos" / "facial-system-recovery-v1"; output_root.mkdir(parents=True, exist_ok=True)
    session = output_root / ".facial-recovery-board-capture"
    if session.exists():
        if not args.overwrite: raise FileExistsError(session)
        shutil.rmtree(session)
    session.mkdir()
    env = os.environ.copy(); env["FABULOOM_CAPTURE_DIR"] = str(output_root)
    server = subprocess.Popen([sys.executable, str(STUDIO_ROOT / "frontend" / "server.py"), "--port", str(args.port)], cwd=STUDIO_ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    edge = None; profile = None
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                with urlopen(f"http://127.0.0.1:{args.port}/facial-recovery-state-board.html", timeout=1): break
            except Exception: time.sleep(.2)
        else: raise TimeoutError("facial board server did not start")
        profile = Path(tempfile.mkdtemp(prefix=".facial-board-edge-", dir=output_root)); url = f"http://127.0.0.1:{args.port}/facial-recovery-state-board.html?session={session.name}"
        edge = subprocess.Popen([str(_edge_path()), "--headless=new", "--disable-gpu", "--disable-extensions", "--no-first-run", "--no-default-browser-check", f"--user-data-dir={profile}", "--window-size=1900,1350", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        complete = session / "complete.json"; deadline = time.monotonic() + args.timeout
        while not complete.is_file():
            if time.monotonic() >= deadline: raise TimeoutError("facial board capture timed out")
            if edge.poll() is not None:
                error = session / "error.json"; raise RuntimeError(error.read_text(encoding="utf-8") if error.is_file() else "Edge exited")
            time.sleep(.2)
        report = output_root / "facial-recovery-state-board-report.json"
        payload = json.loads(complete.read_text(encoding="utf-8")); payload["board"] = str(session / "board.png"); report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        target = output_root / "facial-recovery-state-board.png"
        if target.exists() and not args.overwrite: raise FileExistsError(target)
        shutil.copy2(session / "board.png", target)
        print(f"board={target}"); print(f"report={report}"); print("state=completed"); return 0
    finally:
        if edge is not None and edge.poll() is None:
            edge.terminate()
            try: edge.wait(timeout=5)
            except subprocess.TimeoutExpired: subprocess.run(["taskkill", "/PID", str(edge.pid), "/T", "/F"], check=False, capture_output=True)
        if profile is not None: shutil.rmtree(profile, ignore_errors=True)
        if server.poll() is None:
            server.terminate()
            try: server.wait(timeout=5)
            except subprocess.TimeoutExpired: server.kill()


if __name__ == "__main__": raise SystemExit(main())
