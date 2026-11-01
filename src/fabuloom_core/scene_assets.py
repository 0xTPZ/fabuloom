"""Stable, workspace-relative scene asset registration.

The registry is intentionally small: it identifies reusable visual plates by a
stable ID, keeps binary media outside Git, and resolves only paths contained by
the configured Fabuloom workspace.  It is suitable for local renderers and
does not expose machine-specific absolute paths in public manifests.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .models import ModelValidationError, validate_format_version, validate_id, validate_nonempty


REGISTRY_FORMAT_VERSION = "0.1.0"
REGISTRY_FORMAT = "fabuloom.scene-asset-registry/0.1"


class SceneAssetError(ValueError):
    """Base error for invalid or unavailable scene assets."""


class SceneAssetNotFound(SceneAssetError):
    """Raised when a registered asset ID is not present or its file is absent."""


@dataclass(frozen=True)
class SceneAsset:
    id: str
    version: str
    relative_path: str
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        validate_id(self.id)
        validate_nonempty(self.version, "version")
        validate_nonempty(self.relative_path, "relative_path")
        if Path(self.relative_path).is_absolute():
            raise SceneAssetError("scene asset paths must be workspace-relative")
        if any(part in {"", ".", ".."} for part in Path(self.relative_path).parts):
            raise SceneAssetError("scene asset paths cannot contain traversal components")


class SceneAssetRegistry:
    """Load and resolve a JSON registry against a trusted workspace root."""

    def __init__(self, workspace_root: str | Path, assets: tuple[SceneAsset, ...]) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self._assets = {asset.id: asset for asset in assets}
        if len(self._assets) != len(assets):
            raise SceneAssetError("scene asset IDs must be unique")

    @classmethod
    def from_json(cls, path: str | Path, *, workspace_root: str | Path) -> "SceneAssetRegistry":
        registry_path = Path(path)
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        if payload.get("format") != REGISTRY_FORMAT:
            raise SceneAssetError(f"unsupported scene asset registry format: {payload.get('format')!r}")
        validate_format_version(payload.get("format_version", REGISTRY_FORMAT_VERSION))
        raw_assets = payload.get("assets")
        if not isinstance(raw_assets, list):
            raise SceneAssetError("scene asset registry must contain an assets list")
        assets = tuple(
            SceneAsset(
                id=item["id"],
                version=item["version"],
                relative_path=item["relative_path"],
                metadata={key: value for key, value in item.items() if key not in {"id", "version", "relative_path"}},
            )
            for item in raw_assets
        )
        return cls(workspace_root, assets)

    def get(self, asset_id: str) -> SceneAsset:
        validate_id(asset_id, "asset_id")
        try:
            return self._assets[asset_id]
        except KeyError as exc:
            raise SceneAssetNotFound(f"scene asset ID is not registered: {asset_id}") from exc

    def resolve(self, asset_id: str, *, verify_hash: bool = True) -> Path:
        asset = self.get(asset_id)
        candidate = (self.workspace_root / asset.relative_path).resolve()
        try:
            candidate.relative_to(self.workspace_root)
        except ValueError as exc:
            raise SceneAssetError(f"scene asset escapes workspace root: {asset_id}") from exc
        if not candidate.is_file():
            raise SceneAssetNotFound(f"registered scene asset file is missing: {asset_id}")
        expected = asset.metadata.get("sha256")
        if verify_hash and expected:
            actual = _sha256(candidate)
            if actual.lower() != str(expected).lower():
                raise SceneAssetError(f"scene asset hash mismatch for {asset_id}")
        return candidate

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._assets))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

