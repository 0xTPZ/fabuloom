"""Loopback-only HTTP API for the shared Fabuloom engine."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .engine import EngineService
from .project_store import ProjectConflict, ProjectLocked, ProjectNotFound, ProjectStoreError


MAX_BODY = 256 * 1024


def _json_body(handler: BaseHTTPRequestHandler) -> dict[str, object]:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise ValueError("invalid Content-Length") from exc
    if length < 0 or length > MAX_BODY:
        raise ValueError("request body is too large")
    payload = json.loads(handler.rfile.read(length).decode("utf-8")) if length else {}
    if not isinstance(payload, dict):
        raise ValueError("request body must be an object")
    return payload


class EngineRequestHandler(BaseHTTPRequestHandler):
    server_version = "FabuloomEngine/0.1"

    @property
    def engine(self) -> EngineService:
        return self.server.engine  # type: ignore[attr-defined]

    def _send(self, payload: dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, message: str, status: int = 400) -> None:
        self._send({"error": message, "format": "fabuloom.api-error/0.1"}, status)

    def do_GET(self) -> None:  # noqa: N802
        path = unquote(urlsplit(self.path).path)
        try:
            if path == "/api/v1/status":
                self._send(self.engine.status())
            elif path == "/api/v1/projects":
                self._send({"format": "fabuloom.projects/0.1", "projects": self.engine.list_projects()})
            elif path.startswith("/api/v1/projects/"):
                self._send(self.engine.get_project(path.removeprefix("/api/v1/projects/")))
            elif path == "/api/v1/library":
                self._send({"format": "fabuloom.library-search/0.1", "assets": self.engine.search_library()})
            elif path == "/api/v1/jobs":
                self._send({"format": "fabuloom.jobs/0.1", "jobs": self.engine.list_jobs()})
            elif path.startswith("/api/v1/jobs/"):
                self._send(self.engine.get_job(path.removeprefix("/api/v1/jobs/")))
            else:
                self._error("endpoint not found", 404)
        except ProjectNotFound:
            self._error("project not found", 404)
        except FileNotFoundError:
            self._error("job not found", 404)
        except (ProjectStoreError, ValueError) as exc:
            self._error(str(exc), 409 if isinstance(exc, (ProjectConflict, ProjectLocked)) else 400)

    def do_POST(self) -> None:  # noqa: N802
        path = unquote(urlsplit(self.path).path)
        try:
            payload = _json_body(self)
            if path == "/api/v1/projects":
                project = self.engine.create_project(str(payload.get("name", "")), project_id=payload.get("id") if isinstance(payload.get("id"), str) else None, metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else None)
                self._send(project, 201)
            elif path == "/api/v1/jobs":
                job = self.engine.create_job(str(payload.get("kind", "")), payload.get("payload") if isinstance(payload.get("payload"), dict) else {})
                self._send(job, 202)
            elif path.startswith("/api/v1/jobs/") and path.endswith("/cancel"):
                job_id = path.removeprefix("/api/v1/jobs/").removesuffix("/cancel").strip("/")
                self._send(self.engine.cancel_job(job_id), 202)
            else:
                self._error("endpoint not found", 404)
        except FileNotFoundError:
            self._error("job not found", 404)
        except (ProjectConflict, ProjectLocked) as exc:
            self._error(str(exc), 409)
        except (ProjectStoreError, ValueError, TypeError) as exc:
            self._error(str(exc), 400)

    def do_PUT(self) -> None:  # noqa: N802
        path = unquote(urlsplit(self.path).path)
        if not path.startswith("/api/v1/projects/"):
            self._error("endpoint not found", 404)
            return
        try:
            payload = _json_body(self)
            expected_header = self.headers.get("If-Match")
            expected_revision = int(expected_header) if expected_header else payload.pop("expected_revision", None)
            if expected_revision is not None and not isinstance(expected_revision, int):
                raise ValueError("expected_revision must be an integer")
            project_id = path.removeprefix("/api/v1/projects/")
            self._send(self.engine.update_project(project_id, payload, expected_revision=expected_revision), 200)
        except ProjectNotFound:
            self._error("project not found", 404)
        except (ProjectConflict, ProjectLocked) as exc:
            self._error(str(exc), 409)
        except (ProjectStoreError, ValueError, TypeError) as exc:
            self._error(str(exc), 400)

    def log_message(self, format: str, *args: object) -> None:
        return


class EngineAPIServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], engine: EngineService):
        super().__init__(address, EngineRequestHandler)
        self.engine = engine


def serve(engine: EngineService, *, host: str = "127.0.0.1", port: int = 8790) -> None:
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("Fabuloom API only supports loopback binding")
    server = EngineAPIServer((host, port), engine)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


__all__ = ["EngineAPIServer", "EngineRequestHandler", "serve"]
