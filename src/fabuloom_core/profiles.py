"""Versioned production profiles and capability metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROFILE_FORMAT = "fabuloom.production-profile/0.1"
REQUIRED_FIELDS = {
    "id",
    "version",
    "status",
    "duration_policy",
    "cut_rhythm",
    "narration",
    "safe_area",
    "voice",
    "music",
    "effects",
    "medallion",
    "transitions",
    "canonical_asset_sources",
    "review_criteria",
}
VALID_STATUSES = {"ready_for_technical_test", "incomplete", "review_required"}


class ProfileError(ValueError):
    """Raised when a production profile is malformed or unavailable."""


class ProfileRegistry:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    def _load(self, path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ProfileError(f"could not read profile {path}: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("format") != PROFILE_FORMAT:
            raise ProfileError(f"unsupported production profile format: {path}")
        missing = REQUIRED_FIELDS - set(payload)
        if missing:
            raise ProfileError(f"profile {path.name} is missing fields: {sorted(missing)}")
        if payload.get("status") not in VALID_STATUSES:
            raise ProfileError(f"profile {path.name} has an invalid status")
        if not isinstance(payload.get("id"), str) or not isinstance(payload.get("version"), str):
            raise ProfileError(f"profile {path.name} must define string id/version")
        return payload

    def list(self) -> list[dict[str, Any]]:
        if not self.root.is_dir():
            return []
        return [self._load(path) for path in sorted(self.root.glob("*.json"))]

    def get(self, profile_id: str) -> dict[str, Any]:
        for profile in self.list():
            if profile["id"] == profile_id:
                return profile
        raise ProfileError(f"production profile not found: {profile_id}")

    def capabilities(self) -> list[dict[str, object]]:
        return [
            {
                "id": profile["id"],
                "version": profile["version"],
                "status": profile["status"],
                "renderable": profile["status"] == "ready_for_technical_test",
            }
            for profile in self.list()
        ]


__all__ = ["PROFILE_FORMAT", "ProfileError", "ProfileRegistry"]
