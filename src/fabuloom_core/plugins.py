"""Explicit, versioned plugin discovery without executing unknown code."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re


PLUGIN_FORMAT = "fabuloom.plugin/0.1"
_PLUGIN_ID = re.compile(r"^[a-z][a-z0-9._-]{2,63}$")


class PluginValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PluginManifest:
    id: str
    name: str
    version: str
    api_version: str
    capabilities: tuple[str, ...]
    entry_point: str | None
    source: str
    enabled: bool = False

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "PluginManifest":
        if payload.get("format") != PLUGIN_FORMAT:
            raise PluginValidationError("unsupported plugin manifest format")
        plugin_id = str(payload.get("id", ""))
        if not _PLUGIN_ID.fullmatch(plugin_id):
            raise PluginValidationError("plugin id is invalid")
        capabilities = payload.get("capabilities")
        if not isinstance(capabilities, list) or not all(isinstance(value, str) and value for value in capabilities):
            raise PluginValidationError("capabilities must be a list of non-empty strings")
        source = str(payload.get("source", ""))
        if source not in {"builtin", "local", "external"}:
            raise PluginValidationError("plugin source must be builtin, local or external")
        entry = payload.get("entry_point")
        if entry is not None and not isinstance(entry, str):
            raise PluginValidationError("entry_point must be a string or null")
        return cls(id=plugin_id, name=str(payload.get("name", "")), version=str(payload.get("version", "")), api_version=str(payload.get("api_version", "")), capabilities=tuple(capabilities), entry_point=entry, source=source, enabled=bool(payload.get("enabled", False)))

    def as_dict(self) -> dict[str, object]:
        return {"format": PLUGIN_FORMAT, "id": self.id, "name": self.name, "version": self.version, "api_version": self.api_version, "capabilities": list(self.capabilities), "entry_point": self.entry_point, "source": self.source, "enabled": self.enabled}


class PluginRegistry:
    """Discover manifests; activation is explicit and never imports code."""

    def __init__(self, manifest_root: Path):
        self.manifest_root = manifest_root.expanduser().resolve()

    def discover(self) -> list[PluginManifest]:
        manifests: list[PluginManifest] = []
        if not self.manifest_root.is_dir():
            return manifests
        for path in sorted(self.manifest_root.rglob("plugin.json")):
            try:
                path.resolve().relative_to(self.manifest_root)
                payload = json.loads(path.read_text(encoding="utf-8"))
                manifest = PluginManifest.from_dict(payload)
                manifests.append(manifest)
            except (OSError, ValueError, json.JSONDecodeError, PluginValidationError):
                continue
        return manifests

    def enabled(self) -> list[PluginManifest]:
        return [manifest for manifest in self.discover() if manifest.enabled]

    def activation_plan(self, plugin_id: str) -> dict[str, object]:
        match = next((manifest for manifest in self.discover() if manifest.id == plugin_id), None)
        if match is None:
            raise PluginValidationError(f"plugin not found: {plugin_id}")
        return {"plugin": match.as_dict(), "execution": "explicit-only", "trusted": match.source == "builtin", "requires_review": match.source != "builtin"}


__all__ = ["PLUGIN_FORMAT", "PluginManifest", "PluginRegistry", "PluginValidationError"]
