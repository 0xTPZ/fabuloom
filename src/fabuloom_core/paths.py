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
            else:
                root = (Path.home() / "Fabuloom").resolve()
        else:
            root = (Path.home() / "Fabuloom").resolve()
        return cls(root=root)


__all__ = ["FabuloomPaths", "PathConfigurationError"]
