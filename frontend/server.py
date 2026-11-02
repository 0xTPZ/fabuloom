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
import threading
import time
import uuid
from urllib.parse import parse_qs, unquote, urlsplit


FRONTEND_ROOT = Path(__file__).resolve().parent


def workspace_root_for(frontend_root: Path, configured: str | None = None) -> Path:
    """Resolve the local workspace without requiring the developer's drive layout."""
    if configured:
        return Path(configured).expanduser().resolve()
    project_root = frontend_root.parent
    umbrella_root = project_root.parent
    if (umbrella_root / "workspace").is_dir():
        return umbrella_root.resolve()
    return project_root.resolve()


def export_root_for(workspace_root: Path, configured: str | None = None) -> Path:
    """Resolve an export directory that remains contained by the local workspace."""
    candidate = Path(configured).expanduser() if configured else workspace_root / "workspace" / "exports"
    resolved = candidate.resolve()
    try:
        resolved.relative_to(workspace_root)
    except ValueError as exc:
        raise SystemExit("FABULOOM_EXPORT_ROOT must stay inside FABULOOM_WORKSPACE_ROOT") from exc
    return resolved


WORKSPACE_ROOT = workspace_root_for(FRONTEND_ROOT, os.environ.get("FABULOOM_WORKSPACE_ROOT"))
EXPORT_ROOT = export_root_for(WORKSPACE_ROOT, os.environ.get("FABULOOM_EXPORT_ROOT"))
CAPTURE_ROOT = None
MAX_CAPTURE_BYTES = 10 * 1024 * 1024
NARRATOR_JOB = None
MUSIC_JOBS: dict[str, dict] = {}
MUSIC_LOCK = threading.Lock()
MUSIC_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}


def _music_root() -> Path:
    return (WORKSPACE_ROOT / "workspace" / "inputs" / "music").resolve()


def _safe_music_asset(value: str) -> Path:
    raw = str(value).replace("\\", "/").strip().lstrip("/")
    candidate = (_music_root() / raw).resolve()
    try:
        candidate.relative_to(_music_root())
    except ValueError as exc:
        raise ValueError("asset must stay inside workspace/inputs/music") from exc
    if candidate.suffix.lower() not in MUSIC_EXTENSIONS or not candidate.is_file():
        raise ValueError("music asset not found or unsupported")
    return candidate


def _read_request(handler: BaseHTTPRequestHandler, max_bytes: int = 64 * 1024) -> dict:
    raw_length = handler.headers.get("Content-Length")
    try:
        content_length = int(raw_length or "0")
    except ValueError as exc:
        raise ValueError("invalid request length") from exc
    if content_length < 0 or content_length > max_bytes:
        raise ValueError("request is too large")
    payload = handler.rfile.read(content_length)
    if len(payload) != content_length:
        raise ValueError("incomplete request body")
    data = json.loads(payload.decode("utf-8")) if payload else {}
    if not isinstance(data, dict):
        raise ValueError("request must be an object")
    return data


def _music_runner() -> Path:
    return FRONTEND_ROOT.parent / "examples" / "music_studio_demo.py"


def _music_python() -> str:
    configured = WORKSPACE_ROOT / "workspace" / ".venv" / "Scripts" / "python.exe"
    return str(configured if configured.is_file() else Path(sys.executable))


def _music_catalog() -> list[dict]:
    catalog = []
    for source in sorted(_music_root().rglob("*")):
        if not source.is_file() or source.suffix.lower() not in MUSIC_EXTENSIONS:
            continue
        relative = source.relative_to(_music_root()).as_posix()
        try:
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,format_name,size:stream=codec_name,sample_rate,channels", "-of", "json", str(source)], check=True, text=True, capture_output=True)
            data = json.loads(probe.stdout)
            stream = next((item for item in data.get("streams", []) if item.get("codec_name")), {})
            catalog.append({"asset": relative, "filename": source.name, "duration_ms": int(round(float(data.get("format", {}).get("duration") or 0) * 1000)), "format": data.get("format", {}).get("format_name"), "codec": stream.get("codec_name"), "sample_rate": int(stream.get("sample_rate") or 0), "channels": int(stream.get("channels") or 0), "size_bytes": int(data.get("format", {}).get("size") or source.stat().st_size)})
        except (OSError, subprocess.CalledProcessError, ValueError, json.JSONDecodeError):
            catalog.append({"asset": relative, "filename": source.name, "metadata_error": True, "size_bytes": source.stat().st_size})
    return catalog


def _music_project_path(project_id: str) -> Path:
    safe = "".join(character if character.isalnum() or character in "-_" else "-" for character in str(project_id)).strip("-")
    candidate = (EXPORT_ROOT / "music-studio" / safe / "project.json").resolve()
    candidate.relative_to(EXPORT_ROOT.resolve())
    return candidate


def _start_music_export(project_path: Path, formats: str, overwrite: bool) -> str:
    job_id = uuid.uuid4().hex[:12]
    project_root = project_path.parent
    log_path = project_root / "reports" / f"export-{job_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [_music_python(), str(_music_runner()), "--project", str(project_path), "--formats", formats, "--port", str(8800 + int(job_id[:3], 16) % 500), "--capture-timeout", "1800"]
    if overwrite:
        command.append("--overwrite")
    handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(command, cwd=str(FRONTEND_ROOT.parent), stdout=handle, stderr=subprocess.STDOUT, env=os.environ.copy())
    with MUSIC_LOCK:
        MUSIC_JOBS[job_id] = {"id": job_id, "state": "running", "process": process, "log": log_path, "project": project_path}
    def monitor() -> None:
        code = process.wait()
        handle.close()
        with MUSIC_LOCK:
            job = MUSIC_JOBS.get(job_id)
            if job:
                job["state"] = "completed" if code == 0 else "failed"
                job["exit_code"] = code
    threading.Thread(target=monitor, daemon=True).start()
    return job_id


class StageHandler(BaseHTTPRequestHandler):
    server_version = "FabuloomStudio/0.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = unquote(urlsplit(self.path).path)
        query = parse_qs(urlsplit(self.path).query)
        if path == "/api/music/catalog":
            self._send_json({"format": "fabuloom.music-catalog/0.1", "assets": _music_catalog()})
            return
        if path == "/api/music/analyze":
            try:
                asset = (query.get("asset") or [""])[0]
                source = _safe_music_asset(asset)
                result = subprocess.run([_music_python(), str(_music_runner()), "--analyze-only", "--asset", source.relative_to(_music_root()).as_posix()], cwd=str(FRONTEND_ROOT.parent), check=True, text=True, capture_output=True, env=os.environ.copy())
                self._send_json(json.loads(result.stdout))
            except (ValueError, FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
                self._send_json({"error": str(exc)}, status=400)
            return
        if path == "/api/music/projects":
            projects_root = EXPORT_ROOT / "music-studio"
            projects = []
            if projects_root.is_dir():
                for project_path in sorted(projects_root.glob("*/project.json"), key=lambda item: item.stat().st_mtime, reverse=True):
                    try:
                        project = json.loads(project_path.read_text(encoding="utf-8"))
                        projects.append({"id": project.get("id"), "title": project.get("title"), "format": project.get("format"), "source": project.get("source", {}).get("filename"), "path": project_path.relative_to(EXPORT_ROOT).as_posix(), "updated_at": project_path.stat().st_mtime})
                    except (OSError, ValueError, json.JSONDecodeError):
                        continue
            self._send_json({"format": "fabuloom.music-projects/0.1", "projects": projects})
            return
        if path == "/api/music/project":
            try:
                project_path = _music_project_path((query.get("id") or [""])[0])
                self._send_json(json.loads(project_path.read_text(encoding="utf-8")))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                self._send_json({"error": str(exc)}, status=404)
            return
        if path.startswith("/api/music/jobs/"):
            job_id = path.removeprefix("/api/music/jobs/")
            with MUSIC_LOCK:
                job = dict(MUSIC_JOBS.get(job_id) or {})
            if not job:
                self._send_json({"error": "job not found"}, status=404)
                return
            process = job.pop("process", None)
            log_path = job.get("log")
            progress_path = Path(job["project"]).parent / "reports" / "progress.json"
            job["log"] = "/exports/" + log_path.relative_to(EXPORT_ROOT).as_posix() if log_path else None
            job["progress"] = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.is_file() else {"stage": job["state"], "progress": 0}
            job["project"] = Path(job["project"]).relative_to(EXPORT_ROOT).as_posix()
            self._send_json(job)
            return
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
        if path == "/api/music/project":
            try:
                request = _read_request(self)
                asset = str(request.get("asset") or "")
                _safe_music_asset(asset)
                command = [_music_python(), str(_music_runner()), "--create-project", "--asset", asset, "--style", str(request.get("style_id") or "topazioverse-living-worlds"), "--name", str(request.get("name") or "music-project")]
                if request.get("short_start_ms") is not None:
                    command.extend(["--short-start-ms", str(int(request["short_start_ms"]))])
                if request.get("short_end_ms") is not None:
                    command.extend(["--short-end-ms", str(int(request["short_end_ms"]))])
                result = subprocess.run(command, cwd=str(FRONTEND_ROOT.parent), check=True, text=True, capture_output=True, env=os.environ.copy())
                response = json.loads(result.stdout)
                project = json.loads(Path(response["project"]).read_text(encoding="utf-8"))
                self._send_json({"project": project}, status=201)
            except (ValueError, FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
                self._send_json({"error": str(exc)}, status=400)
            return
        if path == "/api/music/export":
            try:
                request = _read_request(self)
                project_path = _music_project_path(str(request.get("project_id") or ""))
                if not project_path.is_file():
                    raise FileNotFoundError(project_path)
                formats = str(request.get("formats") or "both")
                if formats not in {"full", "short", "both"}:
                    raise ValueError("formats must be full, short, or both")
                job_id = _start_music_export(project_path, formats, bool(request.get("overwrite", False)))
                self._send_json({"job_id": job_id, "state": "running"}, status=202)
            except (ValueError, FileNotFoundError) as exc:
                self._send_json({"error": str(exc)}, status=400)
            return
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
        if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg", ".json"}:
            self.send_error(400, "capture accepts only PNG/JPEG frames and JSON completion records")
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
    parser.add_argument("--capture-dir", help="local loopback capture directory; must stay inside the workspace")
    args = parser.parse_args()
    configured_capture = args.capture_dir or os.environ.get("FABULOOM_CAPTURE_DIR")
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
