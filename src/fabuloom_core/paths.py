"""Configurable, product/private-safe Fabuloom paths.

The public product never assumes that the owner's library is present.  A
runtime root can be supplied with ``FABULOOM_ROOT`` or explicitly by callers;
the remaining paths are derived from that root and can be inspected before
anything is created.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil


class PathConfigurationError(ValueError):
    """Raised when a configured Fabuloom path escapes its owning root."""


def _inside(child: Path, parent: Path) -> Path:
    child = child.expanduser().resolve()
    parent = parent.expanduser().resolve()
    try:
        child.relative_to(parent)
    except ValueError as exc:
        raise PathConfigurationError(f"path {child} must stay inside {parent}") from exc
    return child


@dataclass(frozen=True)
class FabuloomPaths:
    """The single path contract shared by CLI, API and Desktop."""

    root: Path

    @property
    def product(self) -> Path:
        return self.root / "product"

    @property
    def private(self) -> Path:
        return self.root / "private"

    @property
    def workspace(self) -> Path:
        return self.root / "workspace"

    @property
    def library(self) -> Path:
        return self.private / "library"

    @property
    def legacy_inputs(self) -> Path:
        """Legacy owner library used for read-only inventory before migration."""

        return self.workspace / "inputs"

    @property
    def library_source(self) -> Path:
        """Select the mounted library without falling back to a system folder."""

        if self.library.is_dir():
            return self.library
        if self.legacy_inputs.is_dir():
            return self.legacy_inputs
        return self.library

    @property
    def productions(self) -> Path:
        return self.private / "productions"

    @property
    def projects(self) -> Path:
        return self.workspace / "projects"

    @property
    def jobs(self) -> Path:
        return self.workspace / "jobs"

    @property
    def staging(self) -> Path:
        return self.workspace / "staging"

    @property
    def cache(self) -> Path:
        return self.workspace / "cache"

    @property
    def renders(self) -> Path:
        return self.workspace / "renders"

    @property
    def exports(self) -> Path:
        return self.workspace / "exports"

    @property
    def operations(self) -> Path:
        return self.root / "operations"

    @property
    def catalog_db(self) -> Path:
        return self.workspace / "catalog" / "library.sqlite3"

    def all_managed_roots(self) -> dict[str, Path]:
        return {
            "product": self.product,
            "private": self.private,
            "workspace": self.workspace,
            "library": self.library,
            "legacy_inputs": self.legacy_inputs,
            "library_source": self.library_source,
            "projects": self.projects,
            "jobs": self.jobs,
            "staging": self.staging,
            "cache": self.cache,
            "renders": self.renders,
            "exports": self.exports,
            "operations": self.operations,
        }

    def resolve_workspace_path(self, relative: str | os.PathLike[str]) -> Path:
        """Resolve a workspace-relative path and reject traversal."""

        return _inside(self.workspace / Path(relative), self.workspace)

    def ensure_runtime_directories(self) -> None:
        """Create only empty operational directories; never copy private media."""

        for path in (self.projects, self.jobs, self.staging, self.cache, self.renders, self.exports, self.operations):
            path.mkdir(parents=True, exist_ok=True)

    def as_dict(self) -> dict[str, str]:
        return {name: str(path) for name, path in self.all_managed_roots().items()}

    def storage_report(self) -> dict[str, object]:
        """Return drive/path capacity without creating large temporary files."""

        configured_root = self.root.expanduser().resolve()
        root = configured_root if configured_root.exists() else configured_root.parent
        usage = shutil.disk_usage(root)
        violations: list[dict[str, str]] = []
        for name, managed_path in self.all_managed_roots().items():
            try:
                managed_path.expanduser().resolve().relative_to(configured_root)
            except ValueError:
                violations.append({"name": name, "path": str(managed_path)})
        drives: dict[str, dict[str, int | str]] = {}
        for candidate in (Path("C:/"), Path("E:/")):
            if candidate.exists():
                candidate_usage = shutil.disk_usage(candidate)
                drives[str(candidate.drive or candidate)] = {
                    "total_bytes": candidate_usage.total,
                    "used_bytes": candidate_usage.used,
                    "free_bytes": candidate_usage.free,
                }
        return {
            "configured_root": str(self.root),
            "configured_root_exists": configured_root.exists(),
            "configured_drive": root.drive or str(root.anchor),
            "configured_free_bytes": usage.free,
            "configured_total_bytes": usage.total,
            "drives": drives,
            "fallback_to_system_temp": False,
            "managed_paths_contained": not violations,
            "path_violations": violations,
            "temporary_and_staging_root": str(self.staging),
            "large_file_policy": "staging/cache/renders/exports remain under configured_root; system temp is not a production target",
        }

    def validate_runtime_root(self) -> dict[str, object]:
        """Fail explicitly if the configured runtime would escape its root."""

        raw_root = self.root.expanduser()
        if not raw_root.is_absolute():
            raise PathConfigurationError("Fabuloom runtime root must be absolute")
        configured_root = raw_root.resolve()
        configured_env = os.environ.get("FABULOOM_ROOT")
        if configured_env:
            env_root = Path(configured_env).expanduser().resolve()
            if env_root != configured_root:
                raise PathConfigurationError(
                    f"FABULOOM_ROOT points to {env_root}, but the active engine root is {configured_root}; refusing a silent fallback"
                )
        report = self.storage_report()
        if not bool(report["managed_paths_contained"]):
            raise PathConfigurationError(f"managed Fabuloom paths escape configured root: {report['path_violations']}")
        return report

    def require_free_space(self, minimum_bytes: int, *, operation: str = "operation") -> dict[str, object]:
        if isinstance(minimum_bytes, bool) or not isinstance(minimum_bytes, int) or minimum_bytes < 0:
            raise ValueError("minimum_bytes must be a non-negative integer")
        report = self.storage_report()
        free_bytes = int(report["configured_free_bytes"])
        if free_bytes < minimum_bytes:
            raise RuntimeError(
                f"insufficient space for {operation}: {free_bytes} bytes available on {report['configured_drive']}, "
                f"{minimum_bytes} required; no system-drive fallback is allowed"
            )
        return report

    @classmethod
    def discover(cls, product_root: Path | None = None, configured_root: str | None = None) -> "FabuloomPaths":
        if configured_root:
            root = Path(configured_root).expanduser().resolve()
        elif os.environ.get("FABULOOM_ROOT"):
            root = Path(os.environ["FABULOOM_ROOT"]).expanduser().resolve()
        elif product_root is not None:
            candidates = (product_root.resolve(), *product_root.resolve().parents)
            # A worktree may have its own generated ``workspace`` directory.
            # Prefer the Fabuloom umbrella that owns both the public checkout
            # and the shared workspace, then fall back to a standalone local
            # root when no such umbrella exists.
            umbrella = next((candidate for candidate in candidates if (candidate / "workspace").is_dir() and (candidate / "studio").is_dir()), None)
            if umbrella is None:
                umbrella = next((candidate for candidate in candidates if (candidate / "workspace").is_dir()), None)
            if umbrella is not None:
                root = umbrella
            elif product_root.resolve().name == "product":
                root = product_root.resolve().parent
            elif product_root.resolve().drive.upper() == "E:":
                root = Path("E:/Fabuloom").resolve()
            else:
                root = (Path.home() / "Fabuloom").resolve()
        else:
            windows_root = Path("E:/Fabuloom")
            root = windows_root.resolve() if windows_root.is_dir() else (Path.home() / "Fabuloom").resolve()
        return cls(root=root)


__all__ = ["FabuloomPaths", "PathConfigurationError"]
