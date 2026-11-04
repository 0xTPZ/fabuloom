"""Read-only FAB-ARCH-003 inventory and provenance report.

The command inventories only relevant Fabuloom directories. It never moves,
deletes, extracts or rewrites source media. Hashing is opt-in because approved
exports and video intermediates can be large.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable


MEDIA = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".mp4", ".mov", ".webm", ".png", ".jpg", ".jpeg", ".svg", ".docx"}
SKIP = {".git", ".pytest_cache", "__pycache__", "node_modules", ".venv", ".frames", "frames", "captures", "transitions", "generated", "fab-arch-003-audit"}
RELEVANT = (
    "private/library",
    "private/productions",
    "workspace/inputs",
    "workspace/projects",
    "workspace/exports",
    "workspace/renders",
    "workspace/staging",
    "workspace/cache",
    "worktrees",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def category(relative: str) -> str:
    lower = relative.lower().replace("\\", "/")
    if lower.startswith("workspace/inputs/"):
        return "original-input-or-private-library"
    if lower.startswith("private/library/"):
        return "private-library"
    if lower.startswith("private/productions/") or lower.startswith("workspace/exports/"):
        return "production-or-export"
    if lower.startswith("workspace/projects/"):
        return "editable-project"
    if lower.startswith(("workspace/cache/", "workspace/staging/")):
        return "rebuildable-cache-or-temporary"
    if lower.startswith("worktrees/"):
        return "development-worktree"
    return "other-relevant"


def iter_files(root: Path) -> Iterable[Path]:
    for relative_root in RELEVANT:
        directory = root / relative_root
        if not directory.is_dir():
            continue
        # Worktrees and render intermediates are preserved, but their internal
        # files are not part of the controlled library inventory. Enumerating
        # them would traverse millions of generated frames unnecessarily.
        if directory.name == "worktrees":
            continue
        for current, directories, filenames in __import__("os").walk(directory):
            current_path = Path(current)
            relative_parts = set(current_path.relative_to(root).parts)
            directories[:] = [name for name in directories if name not in SKIP and name not in {"worktrees"}]
            if relative_parts & SKIP:
                continue
            for filename in filenames:
                path = current_path / filename
                if path.is_file() and not any(part in SKIP for part in path.relative_to(root).parts):
                    yield path


def is_hash_source(relative: str) -> bool:
    lower = relative.lower().replace("\\", "/")
    return lower.startswith(("workspace/inputs/book1/", "workspace/inputs/music/book1/", "workspace/inputs/biblioteca videos e musicas/"))


def build_report(root: Path, *, hash_sources: bool) -> dict[str, object]:
    root = root.expanduser().resolve()
    files: list[dict[str, object]] = []
    totals: dict[str, dict[str, int]] = {}
    for path in iter_files(root):
        relative = path.relative_to(root).as_posix()
        kind = category(relative)
        size = path.stat().st_size
        files.append({
            "relative_path": relative,
            "name": path.name,
            "extension": path.suffix.lower(),
            "bytes": size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            "category": kind,
            "hash": sha256(path) if hash_sources and is_hash_source(relative) else None,
        })
        bucket = totals.setdefault(kind, {"files": 0, "bytes": 0})
        bucket["files"] += 1
        bucket["bytes"] += size
    files.sort(key=lambda item: str(item["relative_path"]))
    return {
        "format": "fabuloom.fab-arch-003-inventory/0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "read_only": True,
        "hash_sources": hash_sources,
        "scope": list(RELEVANT),
        "totals_by_category": totals,
        "files": files,
        "migration": {"mode": "dry-run", "performed": False, "sources_preserved": True, "rollback_available": "no migration was executed"},
        "cleanup": {"performed": False, "eligible_only": ["rebuildable caches and temporary files after active-process check"], "unknown_materials": "preserved"},
        "policies": {"approved_exports": "preserve", "worktrees": "preserve", "virtual_environments": "preserve", "private_library": "outside public product"},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=r"E:\Fabuloom")
    parser.add_argument("--output", default="workspace/exports/fab-arch-003-audit/inventory.json")
    parser.add_argument("--hash-sources", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    output = (root / args.output).resolve()
    output.relative_to(root)
    report = build_report(root, hash_sources=args.hash_sources)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = [
        "# FAB-ARCH-003 — inventário read-only",
        "",
        f"- Gerado em: `{report['generated_at']}`",
        f"- Arquivos catalogados: `{len(report['files'])}`",
        f"- Hashes dos inputs: `{args.hash_sources}`",
        "- Migração executada: `não`; fontes preservadas.",
        "",
        "| Categoria | Arquivos | Bytes |",
        "| --- | ---: | ---: |",
    ]
    for name, values in sorted(report["totals_by_category"].items()):
        markdown.append(f"| {name} | {values['files']} | {values['bytes']} |")
    markdown.extend([
        "",
        "Caches, temporários, frames e conteúdo interno de worktrees foram preservados e não foram removidos.",
        "A lista detalhada e os SHA-256 dos inputs selecionados estão em `inventory.json`.",
        "",
    ])
    output.with_suffix(".md").write_text("\n".join(markdown), encoding="utf-8")
    summary = {"output": str(output), "files": len(report["files"]), "totals_by_category": report["totals_by_category"], "hash_sources": args.hash_sources, "migration": report["migration"]}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
