"""Persistent, metadata-first catalog for the private library boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Iterable

from .models import make_stable_id


CATALOG_FORMAT = "fabuloom.asset-catalog/0.1"
SKIP_DIRECTORIES = {".git", ".venv", "node_modules", ".pytest_cache", ".frames", "cache"}
MEDIA_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".mp4", ".mov", ".webm",
    ".wav", ".mp3", ".flac", ".m4a", ".ogg", ".docx", ".json", ".md", ".txt",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".mp3", ".wav", ".flac", ".m4a", ".ogg"}:
        return "audio"
    if suffix in {".mp4", ".mov", ".webm"}:
        return "video"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}:
        return "image"
    if suffix == ".docx":
        return "document"
    if suffix in {".json", ".md", ".txt"}:
        return "metadata"
    return "file"


def _probe_media(path: Path) -> dict[str, object]:
    if path.suffix.lower() not in {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".mp4", ".mov", ".webm"}:
        return {}
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration,format_name:stream=width,height,codec_name,sample_rate,channels", "-of", "json", str(path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        payload = json.loads(result.stdout)
        stream = next((item for item in payload.get("streams", []) if item.get("codec_name")), {})
        metadata: dict[str, object] = {"format": payload.get("format", {}).get("format_name"), "codec": stream.get("codec_name")}
        if payload.get("format", {}).get("duration"):
            metadata["duration_ms"] = round(float(payload["format"]["duration"]) * 1000)
        if stream.get("width"):
            metadata["width"] = int(stream["width"])
        if stream.get("height"):
            metadata["height"] = int(stream["height"])
        if stream.get("sample_rate"):
            metadata["sample_rate"] = int(stream["sample_rate"])
        if stream.get("channels"):
            metadata["channels"] = int(stream["channels"])
        return metadata
    except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError):
        return {"metadata_error": True}


@dataclass(frozen=True)
class AssetRecord:
    stable_id: str
    name: str
    relative_path: str
    kind: str
    category: str
    size_bytes: int
    modified_at: str
    sha256: str
    metadata: dict[str, object]
    tags: list[str]
    project_refs: list[str]
    approval_status: str
    origin: str
    rights_status: str
    imported_at: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class AssetCatalog:
    """SQLite index that stores references, never copies the indexed media."""

    def __init__(self, library_root: Path, database_path: Path):
        self.library_root = library_root.expanduser().resolve()
        self.database_path = database_path.expanduser().resolve()

    def connect(self, *, initialize: bool = True) -> sqlite3.Connection:
        if initialize:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        if not initialize:
            return connection
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS catalog_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS assets (
                stable_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                relative_path TEXT NOT NULL UNIQUE,
                kind TEXT NOT NULL,
                category TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                modified_at TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                project_refs_json TEXT NOT NULL,
                approval_status TEXT NOT NULL,
                origin TEXT NOT NULL,
                rights_status TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                missing INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_assets_kind ON assets(kind);
            CREATE INDEX IF NOT EXISTS idx_assets_sha256 ON assets(sha256);
            CREATE INDEX IF NOT EXISTS idx_assets_missing ON assets(missing);
            """
        )
        connection.execute("INSERT OR REPLACE INTO catalog_meta(key, value) VALUES ('format', ?)", (CATALOG_FORMAT,))
        return connection

    def record_for(self, path: Path, *, category: str = "unclassified", origin: str = "owner_library", rights_status: str = "review_required", approval_status: str = "unreviewed") -> AssetRecord:
        resolved = path.expanduser().resolve()
        try:
            relative = resolved.relative_to(self.library_root).as_posix()
        except ValueError as exc:
            raise ValueError(f"asset must stay inside catalog root: {resolved}") from exc
        stat = resolved.stat()
        return AssetRecord(
            stable_id=make_stable_id("asset", relative),
            name=resolved.name,
            relative_path=relative,
            kind=_kind(resolved),
            category=category,
            size_bytes=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            sha256=_sha256(resolved),
            metadata=_probe_media(resolved),
            tags=[],
            project_refs=[],
            approval_status=approval_status,
            origin=origin,
            rights_status=rights_status,
            imported_at=_utc_now(),
        )

    def scan(self, *, category: str = "unclassified", origin: str = "owner_library", rights_status: str = "review_required", approval_status: str = "unreviewed", dry_run: bool = False) -> list[AssetRecord]:
        if not self.library_root.is_dir():
            raise FileNotFoundError(self.library_root)
        records: list[AssetRecord] = []
        for path in sorted(self.library_root.rglob("*")):
            if not path.is_file() or any(part in SKIP_DIRECTORIES for part in path.relative_to(self.library_root).parts):
                continue
            if path.suffix.lower() not in MEDIA_EXTENSIONS:
                continue
            records.append(self.record_for(path, category=category, origin=origin, rights_status=rights_status, approval_status=approval_status))
        if not dry_run:
            connection = self.connect()
            try:
                existing_rows = {
                    row["stable_id"]: row
                    for row in connection.execute(
                        "SELECT stable_id, category, tags_json, project_refs_json, approval_status, origin, rights_status FROM assets"
                    ).fetchall()
                }
                connection.execute("UPDATE assets SET missing = 1")
                for record in records:
                    existing = existing_rows.get(record.stable_id)
                    if existing is not None:
                        # A rescan refreshes physical facts only. Editorial
                        # tags, project links, approval and licensing state
                        # are preserved until an explicit editorial operation
                        # changes them.
                        record = replace(
                            record,
                            category=existing["category"],
                            tags=json.loads(existing["tags_json"]),
                            project_refs=json.loads(existing["project_refs_json"]),
                            approval_status=existing["approval_status"],
                            origin=existing["origin"],
                            rights_status=existing["rights_status"],
                        )
                    connection.execute(
                        """INSERT INTO assets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                           ON CONFLICT(stable_id) DO UPDATE SET name=excluded.name, relative_path=excluded.relative_path,
                           kind=excluded.kind, category=excluded.category, size_bytes=excluded.size_bytes,
                           modified_at=excluded.modified_at, sha256=excluded.sha256, metadata_json=excluded.metadata_json,
                           tags_json=excluded.tags_json, project_refs_json=excluded.project_refs_json,
                           approval_status=excluded.approval_status, origin=excluded.origin,
                           rights_status=excluded.rights_status, imported_at=excluded.imported_at, missing=0""",
                        (record.stable_id, record.name, record.relative_path, record.kind, record.category, record.size_bytes, record.modified_at, record.sha256, json.dumps(record.metadata), json.dumps(record.tags), json.dumps(record.project_refs), record.approval_status, record.origin, record.rights_status, record.imported_at),
                    )
                connection.commit()
            finally:
                connection.close()
        return records

    def search(self, query: str = "", *, kind: str | None = None, missing: bool | None = None) -> list[dict[str, object]]:
        clauses: list[str] = []
        args: list[object] = []
        if query:
            clauses.append("(name LIKE ? OR relative_path LIKE ? OR tags_json LIKE ?)")
            pattern = f"%{query}%"
            args.extend([pattern, pattern, pattern])
        if kind:
            clauses.append("kind = ?")
            args.append(kind)
        if missing is not None:
            clauses.append("missing = ?")
            args.append(int(missing))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        connection = self.connect(initialize=False)
        try:
            rows = connection.execute(f"SELECT * FROM assets {where} ORDER BY relative_path", args).fetchall()
        finally:
            connection.close()
        return [self._row_to_dict(row) for row in rows]

    def get(self, stable_id: str) -> dict[str, object] | None:
        """Return one catalog record by stable ID without touching its media."""

        connection = self.connect(initialize=False)
        try:
            row = connection.execute("SELECT * FROM assets WHERE stable_id = ?", (stable_id,)).fetchone()
        finally:
            connection.close()
        return self._row_to_dict(row) if row is not None else None

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
        value = dict(row)
        for key in ("metadata_json", "tags_json", "project_refs_json"):
            value[key.removesuffix("_json")] = json.loads(value.pop(key))
        value["missing"] = bool(value["missing"])
        return value

    def duplicate_groups(self) -> list[list[dict[str, object]]]:
        connection = self.connect(initialize=False)
        try:
            hashes = connection.execute("SELECT sha256 FROM assets GROUP BY sha256 HAVING COUNT(*) > 1").fetchall()
        finally:
            connection.close()
        return [self.search_by_hash(row[0]) for row in hashes]

    def search_by_hash(self, digest: str) -> list[dict[str, object]]:
        connection = self.connect(initialize=False)
        try:
            rows = connection.execute("SELECT * FROM assets WHERE sha256 = ? ORDER BY relative_path", (digest,)).fetchall()
        finally:
            connection.close()
        return [self._row_to_dict(row) for row in rows]


__all__ = ["AssetCatalog", "AssetRecord", "CATALOG_FORMAT"]
