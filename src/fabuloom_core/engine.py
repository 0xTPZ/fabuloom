"""Shared Fabuloom engine services used by every control surface."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
import threading
import uuid

from .asset_catalog import AssetCatalog
from .paths import FabuloomPaths
from .project_store import ProjectStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EngineService:
    """One service object for Desktop, CLI and loopback API callers."""

    def __init__(self, paths: FabuloomPaths, *, initialize: bool = True):
        self.paths = paths
        if initialize:
            self.paths.ensure_runtime_directories()
        self.projects = ProjectStore(self.paths.projects)
        self.catalog = AssetCatalog(self.paths.library, self.paths.catalog_db)
        self._job_threads: dict[str, threading.Thread] = {}
        self._job_cancel: dict[str, threading.Event] = {}
        self._job_lock = threading.RLock()
        self.recover_stale_jobs()

    def status(self) -> dict[str, object]:
        jobs = self.list_jobs()
        return {
            "format": "fabuloom.engine-status/0.1",
            "engine": "fabuloom-engine",
            "mode": "local-first",
            "paths": self.paths.as_dict(),
            "private_library_present": self.paths.library.is_dir(),
            "projects": len(self.projects.list()),
            "jobs": {"total": len(jobs), "running": sum(job["state"] == "running" for job in jobs), "queued": sum(job["state"] == "queued" for job in jobs)},
            "network": {"default_binding": "loopback-only"},
        }

    def create_project(self, name: str, *, project_id: str | None = None, metadata: dict[str, object] | None = None) -> dict[str, object]:
        return self.projects.create(name, project_id=project_id, metadata=metadata)

    def get_project(self, project_id: str) -> dict[str, object]:
        return self.projects.load(project_id)

    def update_project(self, project_id: str, payload: dict[str, object], *, expected_revision: int | None = None, operation: str = "update") -> dict[str, object]:
        return self.projects.save(project_id, payload, expected_revision=expected_revision, operation=operation)

    def list_projects(self) -> list[dict[str, object]]:
        return self.projects.list()

    def search_library(self, query: str = "", *, kind: str | None = None, missing: bool | None = None) -> list[dict[str, object]]:
        if not self.paths.catalog_db.is_file():
            return []
        return self.catalog.search(query, kind=kind, missing=missing)

    def validate_project(self, project_id: str) -> dict[str, object]:
        project = self.projects.load(project_id)
        return {"project_id": project["id"], "format": project["format"], "revision": project.get("revision", 0), "valid": True}

    def _job_path(self, job_id: str) -> Path:
        return self.paths.jobs / f"{job_id}.json"

    def _write_job(self, job: dict[str, object]) -> None:
        with self._job_lock:
            path = self._job_path(str(job["id"]))
            path.parent.mkdir(parents=True, exist_ok=True)
            serialized = json.dumps(job, ensure_ascii=False, indent=2) + "\n"
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".job-", suffix=".tmp", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(serialized)
            try:
                os.replace(temporary, path)
            except PermissionError:
                # Some managed Windows temp locations deny ReplaceFile while
                # allowing ordinary writes. The fallback remains process-local;
                # normal workspace paths retain the atomic replace guarantee.
                path.write_text(serialized, encoding="utf-8")
                temporary.unlink(missing_ok=True)

    def _read_job(self, job_id: str) -> dict[str, object]:
        with self._job_lock:
            return json.loads(self._job_path(job_id).read_text(encoding="utf-8"))

    def list_jobs(self) -> list[dict[str, object]]:
        values: list[dict[str, object]] = []
        if not self.paths.jobs.is_dir():
            return values
        for path in sorted(self.paths.jobs.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                values.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        return values

    def recover_stale_jobs(self) -> None:
        """Mark abandoned in-process jobs; arbitrary work is never resumed silently."""

        for job in self.list_jobs():
            if job.get("state") in {"queued", "running"}:
                job.update({"state": "interrupted", "finished_at": _now(), "error": "previous engine process ended before completion"})
                self._write_job(job)

    def create_job(self, kind: str, payload: dict[str, object] | None = None) -> dict[str, object]:
        if kind not in {"validate-project", "catalog-scan"}:
            raise ValueError(f"unsupported job kind: {kind}")
        job = {"format": "fabuloom.job/0.1", "id": f"job-{uuid.uuid4().hex[:16]}", "kind": kind, "payload": payload or {}, "state": "queued", "progress": 0, "created_at": _now(), "updated_at": _now()}
        self._write_job(job)
        cancel = threading.Event()
        with self._job_lock:
            self._job_cancel[str(job["id"])] = cancel
            thread = threading.Thread(target=self._run_job, args=(job, cancel), daemon=True, name=f"fabuloom-{job['id']}")
            self._job_threads[str(job["id"])] = thread
            thread.start()
        return job

    def _run_job(self, job: dict[str, object], cancel: threading.Event) -> None:
        job_id = str(job["id"])
        try:
            job.update({"state": "running", "progress": 0.05, "started_at": _now(), "updated_at": _now()})
            self._write_job(job)
            if cancel.is_set():
                raise InterruptedError("cancelled before start")
            if job["kind"] == "validate-project":
                result = self.validate_project(str(job["payload"].get("project_id", "")))
            else:
                if not self.paths.library.is_dir():
                    result = {"records": 0, "library_present": False}
                else:
                    records = self.catalog.scan(dry_run=False)
                    result = {"records": len(records), "library_present": True}
            if cancel.is_set():
                raise InterruptedError("cancelled")
            job.update({"state": "completed", "progress": 1.0, "result": result, "finished_at": _now(), "updated_at": _now()})
        except InterruptedError as exc:
            job.update({"state": "cancelled", "error": str(exc), "finished_at": _now(), "updated_at": _now()})
        except Exception as exc:  # job errors are persisted for Desktop/CLI diagnostics
            job.update({"state": "failed", "error": f"{type(exc).__name__}: {exc}", "finished_at": _now(), "updated_at": _now()})
        finally:
            self._write_job(job)

    def get_job(self, job_id: str) -> dict[str, object]:
        return self._read_job(job_id)

    def wait_for_job(self, job_id: str, *, timeout_seconds: float | None = None) -> dict[str, object]:
        deadline = time.monotonic() + timeout_seconds if timeout_seconds is not None else None
        while True:
            job = self.get_job(job_id)
            if job.get("state") not in {"queued", "running"}:
                return job
            if deadline is not None and time.monotonic() >= deadline:
                return job
            time.sleep(0.02)

    def cancel_job(self, job_id: str) -> dict[str, object]:
        with self._job_lock:
            event = self._job_cancel.get(job_id)
            if event:
                event.set()
        job = self._read_job(job_id)
        if job.get("state") in {"queued", "running"} and not event:
            job.update({"state": "cancel-requested", "updated_at": _now()})
            self._write_job(job)
        return job


__all__ = ["EngineService"]
