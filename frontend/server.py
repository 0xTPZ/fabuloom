"""Loopback-only static server for the Fabuloom Studio."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlsplit


FRONTEND_ROOT = Path(__file__).resolve().parent
EXPORT_ROOT = Path(r"E:\Fabuloom\workspace\exports").resolve()
WORKSPACE_ROOT = Path(r"E:\Fabuloom").resolve()
CAPTURE_ROOT = None
MAX_CAPTURE_BYTES = 10 * 1024 * 1024
NARRATOR_JOB = None


class StageHandler(BaseHTTPRequestHandler):
    server_version = "FabuloomStudio/0.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = unquote(urlsplit(self.path).path)
        if path == "/narrator-mode/status":
            self._send_narrator_status()
            return
        if path.startswith("/exports/"):
            root = EXPORT_ROOT
            relative = path.removeprefix("/exports/")
        else:
            root = FRONTEND_ROOT
            relative = path.removeprefix("/") or "studio.html"
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            self.send_error(403, "path outside the local stage roots")
            return
        if not candidate.is_file():
            self.send_error(404, "resource not found")
            return
        content_type = "text/javascript" if candidate.suffix == ".ts" else mimetypes.guess_type(candidate.name)[0]
        content_type = content_type or "application/octet-stream"
        payload = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        """Receive one deterministic local capture frame or completion record."""
        if self.client_address[0] not in {"127.0.0.1", "::1"}:
            self.send_error(403, "capture accepts loopback requests only")
            return
        path = unquote(urlsplit(self.path).path)
        if path == "/narrator-mode/generate":
            self._start_narrator_job()
            return
        if CAPTURE_ROOT is None:
            self.send_error(404, "capture endpoint is disabled")
            return
        if not path.startswith("/capture/"):
            self.send_error(404, "unknown POST endpoint")
            return
        relative = path.removeprefix("/capture/")
        candidate = (CAPTURE_ROOT / relative).resolve()
        try:
            candidate.relative_to(CAPTURE_ROOT)
        except ValueError:
            self.send_error(403, "capture path outside the configured directory")
            return
        parts = Path(relative).parts
        if len(parts) != 2 or not parts[0] or parts[0] in {".", ".."}:
            self.send_error(400, "capture path must be /capture/<session>/<file>")
            return
        if candidate.suffix.lower() not in {".png", ".json"}:
            self.send_error(400, "capture accepts only PNG frames and JSON completion records")
            return
        raw_length = self.headers.get("Content-Length")
        try:
            content_length = int(raw_length or "-1")
        except ValueError:
            content_length = -1
        if content_length < 0 or content_length > MAX_CAPTURE_BYTES:
            self.send_error(413, "invalid or oversized capture payload")
            return
        payload = self.rfile.read(content_length)
        if len(payload) != content_length:
            self.send_error(400, "incomplete capture payload")
            return
        if candidate.suffix.lower() == ".json":
            try:
                json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.send_error(400, f"invalid completion JSON: {exc}")
                return
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_bytes(payload)
        self.close_connection = True
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_narrator_status(self) -> None:
        global NARRATOR_JOB
        job = NARRATOR_JOB
        if job is None:
            self._send_json({"state": "idle", "mode": "narrator-mode-v1"})
            return
        code = job.poll()
        state = "running" if code is None else ("completed" if code == 0 else "failed")
        self._send_json({"state": state, "mode": "narrator-mode-v1", "exit_code": code, "log": "/exports/videos/narrator-mode-ui.log", "video": "/exports/videos/fabuloom-narrator-mode-v1.mp4"})

    def _start_narrator_job(self) -> None:
        global NARRATOR_JOB
        if NARRATOR_JOB is not None and NARRATOR_JOB.poll() is None:
            self._send_json({"state": "running", "mode": "narrator-mode-v1"}, status=409)
            return
        raw_length = self.headers.get("Content-Length")
        try:
            content_length = int(raw_length or "0")
        except ValueError:
            content_length = -1
        if content_length < 0 or content_length > 32 * 1024:
            self.send_error(413, "invalid Narrator Mode request")
            return
        if content_length:
            payload = self.rfile.read(content_length)
            try:
                request = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.send_error(400, f"invalid Narrator Mode request JSON: {exc}")
                return
            if not isinstance(request, dict):
                self.send_error(400, "Narrator Mode request must be an object")
                return
            if request.get("voice") not in {None, "pm_santa"} or request.get("scene") not in {None, "topazio-storyteller-office"}:
                self.send_error(400, "Narrator Mode V1 accepts pm_santa and the original storyteller office scene")
                return
            requested_text = str(request.get("text") or "").strip()
            if len(requested_text) > 4000:
                self.send_error(413, "Narrator Mode text is too long")
                return
        else:
            requested_text = ""
        log_path = EXPORT_ROOT / "videos" / "narrator-mode-ui.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("w", encoding="utf-8")
        configured_python = WORKSPACE_ROOT / "workspace" / ".venv" / "Scripts" / "python.exe"
        python_executable = str(configured_python if configured_python.is_file() else Path(sys.executable))
        try:
            NARRATOR_JOB = subprocess.Popen(
                [python_executable, str(FRONTEND_ROOT.parent / "examples" / "narrator_mode_demo.py"), "--overwrite", "--text", requested_text],
                cwd=FRONTEND_ROOT.parent,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                env=os.environ.copy(),
            )
        finally:
            log_handle.close()
        self._send_json({"state": "running", "mode": "narrator-mode-v1"}, status=202)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[stage] {self.address_string()} {format % args}")


def main() -> int:
    global CAPTURE_ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    configured_capture = os.environ.get("FABULOOM_CAPTURE_DIR")
    if configured_capture:
        candidate = Path(configured_capture).resolve()
        try:
            candidate.relative_to(WORKSPACE_ROOT)
        except ValueError as exc:
            raise SystemExit("FABULOOM_CAPTURE_DIR must stay inside E:\\Fabuloom") from exc
        CAPTURE_ROOT = candidate
        CAPTURE_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), StageHandler)
    print(f"Fabuloom Studio: http://127.0.0.1:{args.port}/")
    print("Only loopback requests are accepted; exports are limited to the Fabuloom workspace.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStage server stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
