"""Shared project storage with optimistic revisions and cooperative locks."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
import uuid

from .models import make_stable_id


PROJECT_FORMAT = "fabuloom.project/0.1"


class ProjectStoreError(RuntimeError):
    """Base error for project persistence."""


class ProjectNotFound(ProjectStoreError):
    pass


class ProjectConflict(ProjectStoreError):
    pass


class ProjectLocked(ProjectStoreError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectStore:
    """The persistence boundary used by Desktop, CLI and the local API."""

    def __init__(self, projects_root: Path, *, lock_timeout_seconds: float = 5.0):
        self.projects_root = projects_root.expanduser().resolve()
        self.lock_timeout_seconds = lock_timeout_seconds

    def _safe_id(self, project_id: str) -> str:
        safe = str(project_id).strip()
        if not safe or safe in {".", ".."} or any(part in {".", ".."} for part in Path(safe).parts) or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in safe):
            raise ValueError("project_id must be a simple stable identifier")
        return safe

    def project_dir(self, project_id: str) -> Path:
        return self.projects_root / self._safe_id(project_id)

    def project_path(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "project.json"

    @contextmanager
    def _lock(self, project_id: str):
        directory = self.project_dir(project_id)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / ".project.lock"
        deadline = time.monotonic() + self.lock_timeout_seconds
        acquired = False
        while time.monotonic() < deadline:
            try:
                handle = path.open("x", encoding="utf-8")
                handle.write(json.dumps({"pid": os.getpid(), "token": uuid.uuid4().hex, "created_at": _now()}))
                handle.close()
                acquired = True
                break
            except FileExistsError:
                time.sleep(0.05)
        if not acquired:
            raise ProjectLocked(f"project is locked: {project_id}")
        try:
            yield
        finally:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _atomic_write(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".project-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)

    def load(self, project_id: str) -> dict[str, object]:
        path = self.project_path(project_id)
        if not path.is_file():
            raise ProjectNotFound(project_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("format") != PROJECT_FORMAT:
            raise ProjectStoreError(f"unsupported project format: {path}")
        return payload

    def list(self) -> list[dict[str, object]]:
        if not self.projects_root.is_dir():
            return []
        values = []
        for path in sorted(self.projects_root.glob("*/project.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            values.append({"id": payload.get("id"), "name": payload.get("name"), "revision": payload.get("revision", 0), "updated_at": payload.get("updated_at"), "path": path.as_posix()})
        return values

    def create(self, name: str, *, project_id: str | None = None, metadata: dict[str, object] | None = None) -> dict[str, object]:
        clean_name = str(name).strip()
        if not clean_name:
            raise ValueError("project name must not be empty")
        identifier = self._safe_id(project_id or make_stable_id("project", clean_name))
        if self.project_path(identifier).exists():
            raise ProjectConflict(f"project already exists: {identifier}")
        payload = {"format": PROJECT_FORMAT, "id": identifier, "name": clean_name, "revision": 1, "created_at": _now(), "updated_at": _now(), "metadata": metadata or {}, "books": [], "history": [{"operation": "create", "at": _now(), "revision": 1}]}
        with self._lock(identifier):
            self._atomic_write(self.project_path(identifier), payload)
        return payload

    def save(self, project_id: str, payload: dict[str, object], *, expected_revision: int | None = None, operation: str = "update") -> dict[str, object]:
        identifier = self._safe_id(project_id)
        with self._lock(identifier):
            current = self.load(identifier)
            current_revision = int(current.get("revision", 0))
            if expected_revision is not None and current_revision != expected_revision:
                raise ProjectConflict(f"revision mismatch: expected {expected_revision}, current {current_revision}")
            updated = dict(payload)
            updated.update({"format": PROJECT_FORMAT, "id": identifier, "revision": current_revision + 1, "updated_at": _now()})
            history = list(current.get("history") or [])
            history.append({"operation": operation, "at": _now(), "revision": updated["revision"]})
            updated["history"] = history[-100:]
            self._atomic_write(self.project_path(identifier), updated)
        return updated

    def append_operation(self, project_id: str, operation: str, details: dict[str, object] | None = None) -> dict[str, object]:
        identifier = self._safe_id(project_id)
        with self._lock(identifier):
            current = self.load(identifier)
            history = list(current.get("history") or [])
            history.append({"operation": operation, "details": details or {}, "at": _now(), "revision": current.get("revision", 0)})
            current["history"] = history[-100:]
            self._atomic_write(self.project_path(identifier), current)
            return current


__all__ = ["PROJECT_FORMAT", "ProjectConflict", "ProjectLocked", "ProjectNotFound", "ProjectStore", "ProjectStoreError"]
