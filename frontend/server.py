"""Loopback-only static server for the Fabuloom Studio."""

from __future__ import annotations

import argparse
import base64
import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import uuid
from urllib.parse import unquote, urlsplit
import wave


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
PROJECTS_ROOT = WORKSPACE_ROOT / "workspace" / "projects"
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
MAX_EXPORT_JOBS = 1
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_ASSET_BYTES = 25 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
ALLOWED_AUDIO_TYPES = {"audio/wav": ".wav", "audio/x-wav": ".wav", "audio/mpeg": ".mp3", "audio/ogg": ".ogg"}
ALLOWED_CAMERAS = {"static", "zoom", "pan-horizontal", "pan-vertical"}
ALLOWED_TRANSITIONS = {"cut"}


def _project_dir(project_id: str) -> Path:
    if not project_id or any(part in {".", ".."} for part in Path(project_id).parts) or not project_id.replace("-", "").isalnum():
        raise ValueError("invalid project id")
    candidate = (PROJECTS_ROOT / project_id).resolve()
    candidate.relative_to(PROJECTS_ROOT.resolve())
    return candidate


def _project_file(project_id: str) -> Path:
    return _project_dir(project_id) / "project.json"


def _read_json_body(handler: BaseHTTPRequestHandler, limit: int = MAX_JSON_BYTES) -> dict:
    try:
        length = int(handler.headers.get("Content-Length", "-1"))
    except ValueError as exc:
        raise ValueError("invalid Content-Length") from exc
    if length < 0 or length > limit:
        raise ValueError("request is missing or exceeds the local size limit")
    payload = handler.rfile.read(length)
    value = json.loads(payload.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("request body must be a JSON object")
    return value


def _save_project(data: dict) -> dict:
    project_id = str(data.get("id") or "")
    directory = _project_dir(project_id)
    directory.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (directory / "project.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def _load_project(project_id: str) -> dict:
    path = _project_file(project_id)
    if not path.is_file():
        raise FileNotFoundError(project_id)
    return json.loads(path.read_text(encoding="utf-8"))


def _project_summary(data: dict) -> dict:
    return {key: data.get(key) for key in ("id", "title", "description", "format", "created_at", "updated_at", "scenes", "narrator", "audio", "exports")}


def _validate_scenes(scenes: object) -> None:
    if not isinstance(scenes, list):
        raise ValueError("scenes must be a list")
    ids: set[str] = set()
    for scene in scenes:
        if not isinstance(scene, dict):
            raise ValueError("each scene must be an object")
        scene_id = str(scene.get("id") or "")
        if not scene_id or scene_id in ids or any(part in {".", ".."} for part in Path(scene_id).parts):
            raise ValueError("scene ids must be unique and safe")
        ids.add(scene_id)
        if int(scene.get("duration_ms") or 0) <= 0:
            raise ValueError("scene duration must be positive")
        if scene.get("camera", "static") not in ALLOWED_CAMERAS:
            raise ValueError("unsupported camera movement")
        if scene.get("transition", "cut") not in ALLOWED_TRANSITIONS:
            raise ValueError("unsupported scene transition")
        image = scene.get("image")
        if image is not None and (not isinstance(image, str) or Path(image).is_absolute() or any(part in {".", ".."} for part in Path(image).parts)):
            raise ValueError("scene image path must be workspace-relative")


def _reconcile_scenes(existing: list[dict], segments: object) -> list[dict]:
    """Map measured narration segments onto stable project scene identities."""
    reconciled = []
    for index, segment in enumerate(segments):
        previous = existing[index] if index < len(existing) else {}
        scene_id = str(previous.get("id") or f"scene-{index + 1:03d}")
        reconciled.append({
            "id": scene_id,
            "title": previous.get("title") or f"Cena {index + 1}",
            "text": segment.text,
            "image": previous.get("image"),
            "duration_ms": int(previous.get("duration_ms") or (segment.end_ms - segment.start_ms)),
            "camera": previous.get("camera", "static"),
            "transition": previous.get("transition", "cut"),
        })
    _validate_scenes(reconciled)
    return reconciled


def _environment_health() -> dict:
    python_ok = sys.version_info >= (3, 11)
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    kokoro_package = importlib.util.find_spec("kokoro") is not None
    hf_home = Path(os.environ.get("HF_HOME", str(Path.home() / ".cache" / "huggingface"))).expanduser()
    model_cache = hf_home / "hub" / "models--hexgrad--Kokoro-82M"
    model_ready = model_cache.exists()
    writable = os.access(WORKSPACE_ROOT, os.W_OK)
    return {
        "python": sys.version.split()[0],
        "python_state": "PRONTO" if python_ok else "ERRO",
        "ffmpeg": bool(ffmpeg_path),
        "ffmpeg_state": "PRONTO" if ffmpeg_path else "NÃO INSTALADO",
        "ffprobe": bool(ffprobe_path),
        "ffprobe_state": "PRONTO" if ffprobe_path else "NÃO INSTALADO",
        "kokoro": kokoro_package,
        "kokoro_state": "PRONTO" if kokoro_package else "NÃO INSTALADO",
        "model": model_ready,
        "model_state": "PRONTO" if model_ready else ("CONFIGURAÇÃO NECESSÁRIA" if kokoro_package else "AGUARDANDO KOKORO"),
        "voice": "CONFIGURAÇÃO NECESSÁRIA" if not (kokoro_package and model_ready) else "VERIFICAÇÃO NECESSÁRIA",
        "writable": writable,
        "writable_state": "PRONTO" if writable else "ERRO",
        "workspace": str(WORKSPACE_ROOT),
    }


class StageHandler(BaseHTTPRequestHandler):
    server_version = "FabuloomStudio/0.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = unquote(urlsplit(self.path).path)
        if path == "/api/health":
            health = _environment_health()
            health["port"] = self.server.server_port
            self._send_json(health)
            return
        if path == "/api/projects":
            PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
            projects = []
            for project_file in sorted(PROJECTS_ROOT.glob("*/project.json")):
                try:
                    projects.append(_project_summary(json.loads(project_file.read_text(encoding="utf-8"))))
                except (OSError, json.JSONDecodeError):
                    continue
            self._send_json({"projects": projects})
            return
        if path.startswith("/api/projects/"):
            project_id = path.removeprefix("/api/projects/").strip("/").split("/")
            if len(project_id) == 3 and project_id[1] == "export" and project_id[2] == "status":
                with JOBS_LOCK:
                    job = JOBS.get(project_id[0])
                if not job:
                    self.send_error(404, "export job not found")
                else:
                    self._send_json(job)
                return
            if len(project_id) >= 3 and project_id[1] == "asset":
                try:
                    root = _project_dir(project_id[0]).resolve()
                    candidate = (root / Path("/".join(project_id[2:]))).resolve()
                    candidate.relative_to(root)
                    if not candidate.is_file():
                        raise FileNotFoundError
                    payload = candidate.read_bytes()
                    self.send_response(200); self.send_header("Content-Type", mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)
                except (ValueError, FileNotFoundError):
                    self.send_error(404, "asset not found")
                return
            if len(project_id) >= 3 and project_id[1] == "audio":
                try:
                    root = _project_dir(project_id[0]).resolve()
                    relative_audio_request = Path("/".join(project_id[2:]))
                    if relative_audio_request.as_posix() == "manifest.json":
                        relative_audio_request = Path("audio") / relative_audio_request
                    candidate = (root / relative_audio_request).resolve()
                    candidate.relative_to(root)
                    if not candidate.is_file():
                        raise FileNotFoundError
                    payload = candidate.read_bytes()
                    content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
                    if candidate.name == "manifest.json":
                        manifest = json.loads(payload.decode("utf-8"))
                        for segment in manifest.get("segments", []):
                            audio_uri = str(segment.get("audio_uri") or "")
                            audio_path = Path(audio_uri.replace("file:///", "").replace("file://", ""))
                            relative_audio = audio_path.resolve().relative_to(root)
                            segment["audio_uri"] = f"/api/projects/{project_id[0]}/audio/{relative_audio.as_posix()}"
                        payload = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
                        content_type = "application/json"
                    self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(payload))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(payload)
                except (ValueError, FileNotFoundError, json.JSONDecodeError):
                    self.send_error(404, "audio not found")
                return
            if len(project_id) == 1 and project_id[0]:
                try:
                    self._send_json(_load_project(project_id[0]))
                except (ValueError, FileNotFoundError):
                    self.send_error(404, "project not found")
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
        if path == "/api/projects":
            try:
                body = _read_json_body(self)
                title = str(body.get("title") or "").strip()
                if not title or len(title) > 120:
                    raise ValueError("project title is required and must be 120 characters or fewer")
                project_id = f"project-{uuid.uuid4().hex[:12]}"
                now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                project = {"id": project_id, "title": title, "description": str(body.get("description") or "").strip(), "format": body.get("format") or "horizontal-1080p", "created_at": now, "updated_at": now, "narrator": {"id": "santa", "name": "Santa V5", "voice_id": "pm_santa", "language": "pt-BR"}, "scenes": [], "audio": {}, "exports": []}
                self._send_json(_save_project(project), status=201)
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json({"error": str(exc)}, status=400)
            return
        if path.startswith("/api/projects/"):
            parts = path.removeprefix("/api/projects/").strip("/").split("/")
            if len(parts) == 2 and parts[1] in {"save", "assets", "narration", "export"}:
                try:
                    project = _load_project(parts[0])
                    body = _read_json_body(self, MAX_ASSET_BYTES if parts[1] == "assets" else MAX_JSON_BYTES)
                    if parts[1] == "save":
                        if "scenes" in body:
                            _validate_scenes(body["scenes"])
                        for field in ("title", "description", "format", "script", "scenes", "narrator", "audio"):
                            if field in body:
                                project[field] = body[field]
                        self._send_json(_save_project(project))
                        return
                    if parts[1] == "assets":
                        self._handle_asset_upload(project, body)
                        return
                    if parts[1] == "narration":
                        self._handle_narration(project, body)
                        return
                    if parts[1] == "export":
                        self._handle_export(project, body)
                        return
                except FileNotFoundError:
                    self.send_error(404, "project not found")
                except (ValueError, json.JSONDecodeError) as exc:
                    self._send_json({"error": str(exc)}, status=400)
                except Exception as exc:  # surfaced as a user-facing operation error
                    self._send_json({"error": str(exc)}, status=500)
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

    def do_DELETE(self) -> None:  # noqa: N802 - stdlib handler API
        path = unquote(urlsplit(self.path).path)
        if not path.startswith("/api/projects/"):
            self.send_error(404, "unknown DELETE endpoint")
            return
        project_id = path.removeprefix("/api/projects/").strip("/")
        export_parts = project_id.split("/")
        if len(export_parts) == 3 and export_parts[1] == "export":
            with JOBS_LOCK:
                job = JOBS.get(export_parts[0])
                if job and job.get("job_id") == export_parts[2] and job.get("state") in {"queued", "running"}:
                    job["cancel_requested"] = True
                    job["state"] = "cancelled"
                    self._send_json(job)
                    return
            self.send_error(404, "export job not found")
            return
        try:
            directory = _project_dir(project_id)
            if not directory.is_dir():
                raise FileNotFoundError(project_id)
            shutil.rmtree(directory)
            self._send_json({"deleted": project_id})
        except (ValueError, FileNotFoundError):
            self.send_error(404, "project not found")

    @staticmethod
    def _kokoro_available() -> bool:
        return importlib.util.find_spec("kokoro") is not None

    def _handle_asset_upload(self, project: dict, body: dict) -> None:
        kind = str(body.get("kind") or "image")
        mime = str(body.get("mime") or "")
        extension = ALLOWED_IMAGE_TYPES.get(mime) if kind == "image" else ALLOWED_AUDIO_TYPES.get(mime)
        if not extension:
            raise ValueError("unsupported asset type; use PNG, JPEG, WebP, WAV, MP3 or OGG")
        encoded = str(body.get("data") or "")
        raw = base64.b64decode(encoded, validate=True)
        if not raw or len(raw) > MAX_ASSET_BYTES:
            raise ValueError("asset is empty or exceeds the 25 MB limit")
        safe_name = Path(str(body.get("filename") or f"asset{extension}")).name
        asset_id = f"asset-{uuid.uuid4().hex[:10]}"
        relative = Path("assets") / f"{asset_id}{extension}"
        target = _project_dir(project["id"]) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        record = {"id": asset_id, "filename": safe_name, "kind": kind, "mime": mime, "path": str(relative).replace("\\", "/"), "size": len(raw)}
        if kind == "image":
            scene_id = str(body.get("scene_id") or "")
            for scene in project.setdefault("scenes", []):
                if scene.get("id") == scene_id:
                    scene["image"] = record["path"]
        elif kind == "music":
            project.setdefault("audio", {})["music"] = record
        elif kind == "voice":
            project.setdefault("audio", {}).setdefault("wav_files", []).append(record["path"])
        else:
            raise ValueError("unsupported asset kind")
        _save_project(project)
        self._send_json({"asset": record, "project": project}, status=201)

    def _handle_narration(self, project: dict, body: dict) -> None:
        text = str(body.get("text") or "").strip()
        if not text:
            raise ValueError("roteiro vazio: escreva um texto antes de gerar a narração")
        if str(body.get("voice_id") or "pm_santa") != "pm_santa":
            raise ValueError("esta Alpha suporta somente Santa V5 / pm_santa")
        sys.path.insert(0, str(FRONTEND_ROOT.parent / "src"))
        from fabuloom_core.kokoro import KokoroTTSProvider
        from fabuloom_core.narration import synthesize_narration
        from fabuloom_core.serialization import serialize_manifest
        output_dir = _project_dir(project["id"]) / "audio"
        provider = KokoroTTSProvider(output_dir=output_dir, allow_overwrite=True)
        try:
            run = synthesize_narration(provider, text, narration_id=f"{project['id']}-santa", voice_id="pm_santa", output_dir=output_dir)
        finally:
            provider.close()
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(serialize_manifest(run.manifest), encoding="utf-8")
        project["audio"]["manifest"] = str(manifest_path.relative_to(_project_dir(project["id"]))).replace("\\", "/")
        project["audio"]["voice"] = "pm_santa"
        project["audio"]["duration_ms"] = run.manifest.duration_ms
        project["audio"]["wav_files"] = [str(path.relative_to(_project_dir(project["id"]))).replace("\\", "/") for path in sorted(output_dir.glob("*.wav"))]
        project["scenes"] = _reconcile_scenes(project.get("scenes", []), run.manifest.segments)
        _save_project(project)
        self._send_json({"project": project, "manifest": json.loads(manifest_path.read_text(encoding="utf-8"))}, status=201)

    def _handle_export(self, project: dict, body: dict) -> None:
        with JOBS_LOCK:
            if any(item.get("state") in {"queued", "running"} for item in JOBS.values()):
                self._send_json({"error": "já existe uma exportação em andamento"}, status=409)
                return
            job_id = f"export-{uuid.uuid4().hex[:10]}"
            job = {"job_id": job_id, "project_id": project["id"], "state": "queued", "progress": 0, "message": "Aguardando FFmpeg", "cancel_requested": False}
            JOBS[project["id"]] = job
        thread = threading.Thread(target=self._run_export_job, args=(project, body, job), daemon=True)
        thread.start()
        self._send_json({"job": job}, status=202)

    def _run_export_job(self, project: dict, body: dict, job: dict) -> None:
        try:
            with JOBS_LOCK:
                job["state"] = "running"; job["message"] = "Preparando cenas"
            export = self._perform_export(project, body, job)
            with JOBS_LOCK:
                if job.get("state") == "cancelled": return
                job.update({"state": "completed", "progress": 100, "message": "MP4 concluído", "export": export})
        except Exception as exc:
            with JOBS_LOCK:
                if job.get("state") != "cancelled": job.update({"state": "failed", "message": str(exc), "error": str(exc)})

    def _perform_export(self, project: dict, body: dict, job: dict) -> dict:
        audio = project.get("audio", {})
        wav_files = [(_project_dir(project["id"]) / item).resolve() for item in audio.get("wav_files", [])]
        if not wav_files or not all(path.is_file() for path in wav_files):
            raise ValueError("gere a narração Santa V5 antes de exportar o vídeo")
        scenes = project.get("scenes", [])
        if not scenes or not all(scene.get("image") and (_project_dir(project["id"]) / scene["image"]).is_file() for scene in scenes):
            raise ValueError("adicione uma imagem válida a cada cena antes de exportar")
        output_dir = (EXPORT_ROOT / "projects" / project["id"]).resolve()
        output_dir.relative_to(EXPORT_ROOT.resolve())
        output_dir.mkdir(parents=True, exist_ok=True)
        scene_dir = output_dir / "scenes"; scene_dir.mkdir(exist_ok=True)
        scene_paths = []
        for index, scene in enumerate(scenes):
            with JOBS_LOCK:
                if job.get("cancel_requested"): raise RuntimeError("exportação cancelada")
                job["progress"] = int(index / max(1, len(scenes)) * 60); job["message"] = f"Renderizando cena {index + 1} de {len(scenes)}"
            image = (_project_dir(project["id"]) / scene["image"]).resolve(); image.relative_to(_project_dir(project["id"]).resolve())
            duration = max(0.1, float(scene.get("duration_ms", 1000)) / 1000)
            camera = scene.get("camera", "static")
            if camera == "zoom":
                vf = "scale=2304:1296:force_original_aspect_ratio=increase,crop=2304:1296,zoompan=z='min(zoom+0.0015,1.12)':d=1:s=1920x1080:fps=30"
            elif camera == "pan-horizontal":
                vf = "scale=2304:1296:force_original_aspect_ratio=increase,crop=2304:1296,zoompan=z='1.08':x='(iw-iw/zoom)*on/(30*20)':y='(ih-ih/zoom)/2':d=1:s=1920x1080:fps=30"
            elif camera == "pan-vertical":
                vf = "scale=2304:1296:force_original_aspect_ratio=increase,crop=2304:1296,zoompan=z='1.08':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)*on/(30*20)':d=1:s=1920x1080:fps=30"
            else:
                vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
            target = scene_dir / f"scene-{index:03d}.mp4"
            subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(image), "-t", f"{duration:.3f}", "-vf", vf, "-r", "30", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(target)], check=True, capture_output=True, text=True)
            scene_paths.append(target)
        list_path = output_dir / "scenes.txt"
        list_path.write_text("\n".join(f"file '{path.as_posix()}'" for path in scene_paths) + "\n", encoding="utf-8")
        video_path = output_dir / "video-only.mp4"
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(video_path)], check=True, capture_output=True, text=True)
        voice_list = output_dir / "voice.txt"
        voice_list.write_text("\n".join(f"file '{path.as_posix()}'" for path in wav_files) + "\n", encoding="utf-8")
        voice_path = output_dir / "voice.wav"
        if len(wav_files) == 1:
            shutil.copyfile(wav_files[0], voice_path)
        else:
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(voice_list), "-c", "copy", str(voice_path)], check=True, capture_output=True, text=True)
        output = output_dir / f"{project['id']}-1080p.mp4"
        command = ["ffmpeg", "-y", "-i", str(video_path), "-i", str(voice_path)]
        music = project.get("audio", {}).get("music", {}).get("path")
        if music and (_project_dir(project["id"]) / music).is_file():
            command += ["-stream_loop", "-1", "-i", str((_project_dir(project["id"]) / music).resolve()), "-filter_complex", "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,asplit=2[voice_main][voice_side];[2:a]loudnorm=I=-26:TP=-2:LRA=12[bed];[bed][voice_side]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[ducked];[ducked]volume=0.35[music];[voice_main][music]amix=inputs=2:duration=first:dropout_transition=2,alimiter=limit=0.95[aout]", "-map", "0:v", "-map", "[aout]"]
        else:
            command += ["-map", "0:v", "-map", "1:a", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.95"]
        command += ["-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(output)]
        with JOBS_LOCK: job["progress"] = 85; job["message"] = "Finalizando MP4"
        subprocess.run(command, check=True, capture_output=True, text=True)
        export = {"path": str(output.relative_to(WORKSPACE_ROOT)).replace("\\", "/"), "format": "1920x1080 H.264/AAC MP4", "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        project.setdefault("exports", []).append(export)
        _save_project(project)
        return export

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
