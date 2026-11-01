"""Persistent visual identity registry for reusable Fabuloom characters."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .models import validate_format_version, validate_id, validate_nonempty


REGISTRY_FORMAT_VERSION = "0.1.0"
REGISTRY_FORMAT = "fabuloom.character-registry/0.1"
APPROVAL_STATES = frozenset({"DRAFT", "APPROVED", "SUPERSEDED"})


class CharacterRegistryError(ValueError):
    """Base error for invalid or unavailable character identities."""


class CharacterNotFound(CharacterRegistryError):
    """Raised when a requested character identity is not registered."""


@dataclass(frozen=True)
class CharacterIdentity:
    id: str
    canonical_name: str
    version: str
    base_image: str
    visual_description: str
    palette: tuple[str, ...]
    physical_characteristics: tuple[str, ...]
    facial_structure: str
    costume: str
    proportions: str
    sha256: str | None
    origin: str
    approval_status: str
    variations: tuple[dict[str, Any], ...]

    def __post_init__(self) -> None:
        validate_id(self.id)
        validate_nonempty(self.canonical_name, "canonical_name")
        validate_nonempty(self.version, "version")
        validate_nonempty(self.base_image, "base_image")
        validate_nonempty(self.visual_description, "visual_description")
        validate_nonempty(self.facial_structure, "facial_structure")
        validate_nonempty(self.costume, "costume")
        validate_nonempty(self.proportions, "proportions")
        validate_nonempty(self.origin, "origin")
        if self.approval_status not in APPROVAL_STATES:
            raise CharacterRegistryError(f"unsupported approval status: {self.approval_status!r}")
        path = Path(self.base_image)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise CharacterRegistryError("character base_image must be workspace-relative")
        if not self.palette or not self.physical_characteristics:
            raise CharacterRegistryError("character palette and physical characteristics are required")


class CharacterRegistry:
    """Load and resolve persistent character identities against a workspace."""

    def __init__(self, workspace_root: str | Path, identities: tuple[CharacterIdentity, ...]) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self._identities = {identity.id: identity for identity in identities}
        if len(self._identities) != len(identities):
            raise CharacterRegistryError("character IDs must be unique")

    @classmethod
    def from_json(cls, path: str | Path, *, workspace_root: str | Path) -> "CharacterRegistry":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("format") != REGISTRY_FORMAT:
            raise CharacterRegistryError(f"unsupported character registry format: {payload.get('format')!r}")
        validate_format_version(payload.get("format_version", REGISTRY_FORMAT_VERSION))
        raw_characters = payload.get("characters")
        if not isinstance(raw_characters, list):
            raise CharacterRegistryError("character registry must contain a characters list")
        identities = tuple(
            CharacterIdentity(
                id=item["id"],
                canonical_name=item["canonical_name"],
                version=item["version"],
                base_image=item["base_image"],
                visual_description=item["visual_description"],
                palette=tuple(item["palette"]),
                physical_characteristics=tuple(item["physical_characteristics"]),
                facial_structure=item["facial_structure"],
                costume=item["costume"],
                proportions=item["proportions"],
                sha256=item.get("sha256"),
                origin=item["origin"],
                approval_status=item["approval_status"],
                variations=tuple(item.get("variations", ())),
            )
            for item in raw_characters
        )
        return cls(workspace_root, identities)

    def get(self, character_id: str) -> CharacterIdentity:
        validate_id(character_id, "character_id")
        try:
            return self._identities[character_id]
        except KeyError as exc:
            raise CharacterNotFound(f"character ID is not registered: {character_id}") from exc

    def resolve(self, character_id: str, *, verify_hash: bool = True) -> Path:
        identity = self.get(character_id)
        candidate = (self.workspace_root / identity.base_image).resolve()
        try:
            candidate.relative_to(self.workspace_root)
        except ValueError as exc:
            raise CharacterRegistryError(f"character image escapes workspace root: {character_id}") from exc
        if not candidate.is_file():
            raise CharacterNotFound(f"registered character image is missing: {character_id}")
        if verify_hash and identity.sha256:
            actual = _sha256(candidate)
            if actual.lower() != identity.sha256.lower():
                raise CharacterRegistryError(f"character image hash mismatch for {character_id}")
        return candidate

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._identities))

    def approved_ids(self) -> tuple[str, ...]:
        return tuple(sorted(identity.id for identity in self._identities.values() if identity.approval_status == "APPROVED"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
