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
from .cinematic import CinematicCompatibility, CinematicRequest
from .migration import LibraryMigration
from .paths import FabuloomPaths, PathConfigurationError
from .profiles import ProfileRegistry
from .production import ProductionService
from .project_store import ProjectNotFound, ProjectStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EngineService:
    """One service object for Desktop, CLI and loopback API callers."""

    def __init__(self, paths: FabuloomPaths, *, initialize: bool = True, recover_stale: bool = True):
        self.paths = paths
        if initialize:
            self.paths.ensure_runtime_directories()
        self.projects = ProjectStore(self.paths.projects)
        self.catalog = AssetCatalog(self.paths.library_source, self.paths.catalog_db)
        self.production = ProductionService(paths, product_root=Path(__file__).resolve().parents[2])
        self.cinematic = CinematicCompatibility(paths, product_root=Path(__file__).resolve().parents[2])
        self.profiles = ProfileRegistry(Path(__file__).resolve().parents[2] / "profiles")
        self._job_threads: dict[str, threading.Thread] = {}
        self._job_cancel: dict[str, threading.Event] = {}
        self._job_lock = threading.RLock()
        if recover_stale:
            self.recover_stale_jobs()

    def status(self) -> dict[str, object]:
        jobs = self.list_jobs()
        return {
            "format": "fabuloom.engine-status/0.1",
            "engine": "fabuloom-engine",
            "mode": "local-first",
            "paths": self.paths.as_dict(),
            "storage": self.paths.storage_report(),
            "private_library_present": self.paths.library_source.is_dir(),
            "projects": len(self.projects.list()),
            "jobs": {"total": len(jobs), "running": sum(job["state"] == "running" for job in jobs), "queued": sum(job["state"] == "queued" for job in jobs)},
            "network": {"default_binding": "loopback-only"},
            "cinematic": {"profile": "cronicas-cinematic-production", "diagnostic": "available through doctor"},
        }

    def cinematic_diagnostics(self) -> dict[str, object]:
        """Read-only status for the real cinematic line, separate from demo QA."""

        return self.cinematic.audit()

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

    def capabilities(self) -> dict[str, object]:
        """Return machine-readable operations, dependencies and limits."""

        return {
            "format": "fabuloom.capabilities/0.1",
            "engine": "fabuloom-engine",
            "version": "0.1.0",
            "interfaces": ["desktop", "cli", "http-loopback", "mcp-stdio"],
            "operations": {
                "doctor": {"status": "implemented", "parameters": {"root": "optional string"}},
                "profiles.list": {"status": "implemented", "parameters": {}},
                "assets.search": {"status": "implemented", "parameters": {"query": "string", "kind": "optional string", "missing": "optional boolean"}},
                "projects.list": {"status": "implemented", "parameters": {}},
                "render.dry_run": {"status": "implemented", "parameters": {"profile": "optional string", "provider": "optional string"}},
                "render.demo": {"status": "implemented", "parameters": {"profile": "string", "provider": "simulated-audio|kokoro", "voice_id": "string", "text": "string", "capture_fps": "5 economy or 24/30 real Canvas", "output_fps": "24|30", "audio_sample_rate": "integer; 48000 recommended", "audio_channels": "1|2"}},
                "render.cinematic.plan": {"status": "implemented", "parameters": {"chapter": "positive integer", "chapter_title": "string", "source_document": "workspace-relative string", "voice_id": "pm_santa", "language": "pt-BR", "output_variants": "horizontal|vertical"}},
                "render.cinematic.validate_reference": {"status": "implemented", "parameters": {"decode": "boolean"}},
                "audio.mix": {"status": "implemented", "parameters": {"music_path": "optional configured-root audio path", "music_asset_id": "optional catalog stable ID", "ducking": "voice-priority sidechain"}},
                "library.migration": {"status": "implemented", "parameters": {"dry_run": "boolean", "checkpoint": "optional path"}},
                "mcp.adapter": {"status": "implemented", "parameters": {"transport": "stdio"}},
                "word_phoneme_viseme_alignment": {"status": "not_implemented", "parameters": {}},
            },
            "dependencies": self.production._dependency_report(),
            "mounted_library": {"source": str(self.paths.library_source), "private_target": str(self.paths.library), "present": self.paths.library_source.is_dir()},
            "jobs": sorted({"validate-project", "catalog-scan", "render-demo", "library-migration", "cinematic-audit", "render-cinematic"}),
            "limits": ["render-demo uses the existing Music Studio Canvas renderer", "cinematic production uses a guarded adapter over the approved legacy runner until isolated output parameters are available", "capture_fps=5 is economical and repeats frames during encoding; 24/30 captures real Canvas frames", "generic acceptance audio is synthetic unless provider=kokoro", "technical QA never implies artistic approval"],
        }

    def doctor(self) -> dict[str, object]:
        dependencies = self.production._dependency_report()
        profiles = self.profiles.capabilities()
        try:
            storage = self.paths.validate_runtime_root()
            storage_valid = True
        except PathConfigurationError as exc:
            storage = self.paths.storage_report()
            storage["validation_error"] = str(exc)
            storage_valid = False
        try:
            cinematic = self.cinematic_diagnostics()
        except PathConfigurationError as exc:
            cinematic = {
                "format": "fabuloom.cronicas-cinematic-production/0.1",
                "status": "blocked",
                "blocking_issues": [f"runtime root validation failed: {exc}"],
            }
        return {
            "format": "fabuloom.doctor/0.1",
            "status": "ready" if storage_valid and dependencies["ffmpeg"] and dependencies["ffprobe"] and storage["configured_free_bytes"] > 64 * 1024 * 1024 else "blocked",
            "dependencies": dependencies,
            "storage": storage,
            "profiles": profiles,
            "library_source": str(self.paths.library_source),
            "library_target": str(self.paths.library),
            "no_c_fallback": str(self.paths.root).upper().startswith("E:") or not os.name == "nt",
            "cinematic": cinematic,
        }

    def list_profiles(self) -> list[dict[str, object]]:
        return self.profiles.capabilities()

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
        if kind not in {"validate-project", "catalog-scan", "render-demo", "library-migration", "cinematic-audit", "render-cinematic"}:
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
        def progress(stage: str, value: float, extra: dict[str, object] | None = None) -> None:
            job.update({"stage": stage, "progress": value, "updated_at": _now()})
            if extra:
                job["stage_details"] = extra
            self._write_job(job)
        try:
            job.update({"state": "running", "progress": 0.05, "started_at": _now(), "updated_at": _now()})
            self._write_job(job)
            if cancel.is_set():
                raise InterruptedError("cancelled before start")
            if job["kind"] == "validate-project":
                result = self.validate_project(str(job["payload"].get("project_id", "")))
            elif job["kind"] == "catalog-scan":
                if not self.paths.library_source.is_dir():
                    result = {"records": 0, "library_present": False}
                else:
                    records = self.catalog.scan(dry_run=False)
                    result = {"records": len(records), "library_present": True}
            elif job["kind"] == "render-demo":
                payload = dict(job["payload"])
                project_id = str(payload.get("project_id") or payload.get("output_id") or "")
                if project_id:
                    try:
                        project = self.get_project(project_id)
                    except ProjectNotFound:
                        project = self.create_project(
                            str(payload.get("title") or "Fabuloom production"),
                            project_id=project_id,
                            metadata={"production_profile": str(payload.get("profile") or "cinematic-short"), "private_assets_used": False},
                        )
                    payload["project_id"] = project_id
                music_asset_id = payload.get("music_asset_id")
                if music_asset_id:
                    record = self.catalog.get(str(music_asset_id))
                    if record is None or bool(record.get("missing")):
                        raise ValueError(f"music asset is not available in the catalog: {music_asset_id}")
                    if str(record.get("approval_status")) in {"draft", "rejected"}:
                        raise ValueError("draft or rejected assets cannot be used for production")
                    payload["music_path"] = str(self.paths.library_source / str(record["relative_path"]))
                result = self.production.render_demo(payload, progress=progress)
                if project_id:
                    current = self.get_project(project_id)
                    metadata = dict(current.get("metadata") or {})
                    metadata["last_render"] = {
                        "profile": result.get("profile"),
                        "status": "technical_qa_complete",
                        "review_status": result.get("artistic_qa", {}).get("status"),
                        "artifact_root": str(Path(str(result["project"])).parent.relative_to(self.paths.exports)),
                    }
                    self.update_project(project_id, {"name": current["name"], "metadata": metadata, "books": current.get("books", [])}, expected_revision=int(current.get("revision", 0)), operation="render-complete")
            elif job["kind"] == "cinematic-audit":
                result = self.cinematic_diagnostics()
            elif job["kind"] == "render-cinematic":
                payload = dict(job["payload"])
                variants = payload.get("output_variants", ["horizontal", "vertical"])
                if isinstance(variants, str):
                    variants = [variants]
                request = CinematicRequest(
                    chapter=int(payload.get("chapter", 11)),
                    chapter_title=str(payload.get("chapter_title", "")),
                    source_document=str(payload.get("source_document", "workspace/inputs/book1/Topazio-O-Despertar-dos-Cristais.docx")),
                    voice_id=str(payload.get("voice_id", "pm_santa")),
                    language=str(payload.get("language", "pt-BR")),
                    music_asset_id=str(payload["music_asset_id"]) if payload.get("music_asset_id") else None,
                    scene_asset_ids=tuple(str(value) for value in payload.get("scene_asset_ids", []) if isinstance(value, str)),
                    output_variants=tuple(str(value) for value in variants),
                    mode=str(payload.get("mode", "plan")),
                    runner=str(payload["runner"]) if payload.get("runner") else None,
                )
                if request.mode == "plan":
                    result = self.cinematic.plan(request)
                elif request.mode == "validate-reference":
                    result = self.cinematic.validate_reference(decode=bool(payload.get("decode", False)), progress=lambda stage: progress("cinematic-qa", 0.5, {"stage": stage}))
                else:
                    result = self.cinematic.execute(request)
            else:
                payload = job["payload"]
                source_root = Path(str(payload.get("source_root") or self.paths.legacy_inputs)).resolve()
                target_root = Path(str(payload.get("target_root") or self.paths.library)).resolve()
                source_root.relative_to(self.paths.root.resolve())
                target_root.relative_to(self.paths.root.resolve())
                migration = LibraryMigration(source_root, target_root, self.paths.workspace / "migrations")
                checkpoint = Path(str(payload.get("checkpoint") or migration.create_plan(payload.get("migration_id") if isinstance(payload.get("migration_id"), str) else None)))
                checkpoint.relative_to((self.paths.workspace / "migrations").resolve())
                if bool(payload.get("dry_run", True)):
                    result = migration.simulate(checkpoint)
                elif bool(payload.get("rollback", False)):
                    result = migration.rollback(checkpoint)
                else:
                    plan = json.loads(checkpoint.read_text(encoding="utf-8"))
                    required_bytes = sum(int(entry.get("size_bytes", 0)) for entry in plan.get("entries", []))
                    self.paths.require_free_space(required_bytes, operation="library migration")
                    result = migration.execute(checkpoint, progress=lambda current, total: progress("library-migration", current / max(1, total), {"current": current, "total": total}))
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
