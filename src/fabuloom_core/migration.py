"""Checkpointed, reversible library migration primitives.

The migration boundary copies only explicitly selected library files. Sources
are never removed, metadata is carried in the checkpoint, and rollback only
removes a destination file when its hash still matches the copy made by this
operation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Callable
import uuid

from .asset_catalog import MEDIA_EXTENSIONS, SKIP_DIRECTORIES
from .models import make_stable_id


MIGRATION_FORMAT = "fabuloom.library-migration/0.1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inside(path: Path, root: Path) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(root.expanduser().resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes migration root: {resolved}") from exc
    return resolved


class LibraryMigration:
    def __init__(self, source_root: str | Path, target_root: str | Path, checkpoint_root: str | Path):
        self.source_root = Path(source_root).expanduser().resolve()
        self.target_root = Path(target_root).expanduser().resolve()
        self.checkpoint_root = Path(checkpoint_root).expanduser().resolve()

    def inventory(self) -> list[dict[str, object]]:
        if not self.source_root.is_dir():
            raise FileNotFoundError(self.source_root)
        entries: list[dict[str, object]] = []
        for path in sorted(self.source_root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(self.source_root)
            if any(part in SKIP_DIRECTORIES for part in relative.parts):
                continue
            if path.suffix.lower() not in MEDIA_EXTENSIONS:
                continue
            entries.append({
                "asset_id": make_stable_id("asset", f"legacy:{relative.as_posix()}"),
                "relative_path": relative.as_posix(),
                "source": str(path),
                "target": str(self.target_root / relative),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "rights_status": "review_required",
                "editorial_metadata_policy": "preserve_existing_and_sidecars",
                "status": "planned",
            })
        return entries

    def create_plan(self, migration_id: str | None = None) -> Path:
        identifier = migration_id or f"migration-{uuid.uuid4().hex[:12]}"
        if not identifier or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for character in identifier):
            raise ValueError("migration_id contains unsafe characters")
        directory = self.checkpoint_root / identifier
        directory.mkdir(parents=True, exist_ok=True)
        plan = {
            "format": MIGRATION_FORMAT,
            "id": identifier,
            "created_at": _now(),
            "source_root": str(self.source_root),
            "target_root": str(self.target_root),
            "preserve_sources": True,
            "status": "planned",
            "entries": self.inventory(),
        }
        path = directory / "checkpoint.json"
        self._write(path, plan)
        return path

    def simulate(self, plan_path: str | Path) -> dict[str, object]:
        plan = self._read(plan_path)
        entries = list(plan.get("entries") or [])
        return {
            "format": MIGRATION_FORMAT,
            "migration_id": plan.get("id"),
            "mode": "dry-run",
            "source_root": plan.get("source_root"),
            "target_root": plan.get("target_root"),
            "files": len(entries),
            "bytes": sum(int(entry.get("size_bytes", 0)) for entry in entries),
            "preserve_sources": True,
            "rights_status": "review_required",
            "checkpoint": str(Path(plan_path).resolve()),
        }

    def execute(self, plan_path: str | Path, *, progress: Callable[[int, int], None] | None = None) -> dict[str, object]:
        path = Path(plan_path).expanduser().resolve()
        plan = self._read(path)
        entries = list(plan.get("entries") or [])
        self.target_root.mkdir(parents=True, exist_ok=True)
        copied = 0
        for index, entry in enumerate(entries, start=1):
            source = _inside(Path(str(entry["source"])), self.source_root)
            target = _inside(Path(str(entry["target"])), self.target_root)
            if not source.is_file():
                raise FileNotFoundError(source)
            expected = str(entry["sha256"])
            if target.is_file():
                if sha256(target) != expected:
                    raise RuntimeError(f"migration target conflict: {target}")
                entry["status"] = "verified"
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}-", suffix=".part", dir=target.parent)
                os.close(descriptor)
                temporary = Path(temporary_name)
                try:
                    shutil.copy2(source, temporary)
                    os.replace(temporary, target)
                finally:
                    temporary.unlink(missing_ok=True)
                if sha256(target) != expected:
                    raise RuntimeError(f"migration hash verification failed: {target}")
                entry["status"] = "verified"
                copied += 1
            entry["completed_at"] = _now()
            plan["status"] = "running"
            plan["updated_at"] = _now()
            self._write(path, plan)
            if progress:
                progress(index, len(entries))
        plan["status"] = "completed"
        plan["completed_at"] = _now()
        self._write(path, plan)
        return {"migration_id": plan["id"], "status": plan["status"], "files": len(entries), "copied": copied, "checkpoint": str(path)}

    def rollback(self, plan_path: str | Path) -> dict[str, object]:
        path = Path(plan_path).expanduser().resolve()
        plan = self._read(path)
        removed = 0
        for entry in plan.get("entries", []):
            if entry.get("status") not in {"verified", "copied"}:
                continue
            target = _inside(Path(str(entry["target"])), self.target_root)
            if not target.exists():
                entry["status"] = "rolled_back"
                continue
            if sha256(target) != str(entry["sha256"]):
                raise RuntimeError(f"refusing rollback because target changed: {target}")
            target.unlink()
            removed += 1
            entry["status"] = "rolled_back"
        plan["status"] = "rolled_back"
        plan["rolled_back_at"] = _now()
        self._write(path, plan)
        return {"migration_id": plan["id"], "status": plan["status"], "removed": removed, "checkpoint": str(path)}

    @staticmethod
    def _read(path: Path) -> dict[str, object]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("format") != MIGRATION_FORMAT:
            raise ValueError("unsupported migration checkpoint")
        return payload

    @staticmethod
    def _write(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}-", suffix=".tmp", dir=path.parent, text=True)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


__all__ = ["LibraryMigration", "MIGRATION_FORMAT", "sha256"]
