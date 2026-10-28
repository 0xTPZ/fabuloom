"""Versioned Fabuloom domain models.

The models use stable caller-provided IDs. ``make_stable_id`` is provided for
deterministic IDs derived from an external namespace/key pair; it does not use
randomness or machine-local state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Any

MODEL_FORMAT_VERSION = "0.1.0"
_SUPPORTED_VERSION = re.compile(r"^0\.1\.\d+$")
_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")


class ModelValidationError(ValueError):
    """Raised when a model violates a structural invariant."""


def validate_format_version(value: str) -> str:
    if not isinstance(value, str) or not _SUPPORTED_VERSION.fullmatch(value):
        raise ModelValidationError(
            f"Unsupported format_version {value!r}; supported family is 0.1.x"
        )
    return value


def validate_id(value: str, field_name: str = "id") -> str:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise ModelValidationError(
            f"{field_name} must match {_ID_PATTERN.pattern}: {value!r}"
        )
    return value


def validate_nonempty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelValidationError(f"{field_name} must be a non-empty string")
    return value


def validate_nonnegative(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ModelValidationError(f"{field_name} must be a non-negative integer")
    return value


def make_stable_id(namespace: str, key: str) -> str:
    """Return a deterministic, project-safe ID for a namespace and natural key."""

    validate_nonempty(namespace, "namespace")
    validate_nonempty(key, "key")
    prefix = re.sub(r"[^a-z0-9]+", "-", namespace.lower()).strip("-") or "item"
    digest = hashlib.sha256(f"{namespace}:{key}".encode("utf-8")).hexdigest()[:16]
    return validate_id(f"{prefix[:40]}-{digest}")


@dataclass
class Character:
    id: str
    name: str
    language: str = "pt-BR"
    default_voice_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    format_version: str = MODEL_FORMAT_VERSION

    def __post_init__(self) -> None:
        validate_id(self.id)
        validate_nonempty(self.name, "name")
        validate_format_version(self.format_version)


@dataclass
class Narrator:
    id: str
    name: str
    voice_id: str
    language: str = "pt-BR"
    metadata: dict[str, Any] = field(default_factory=dict)
    format_version: str = MODEL_FORMAT_VERSION

    def __post_init__(self) -> None:
        validate_id(self.id)
        validate_nonempty(self.name, "name")
        validate_nonempty(self.voice_id, "voice_id")
        validate_format_version(self.format_version)


@dataclass
class Dialogue:
    id: str
    text: str
    kind: str = "dialogue"
    speaker_id: str | None = None
    narrator_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    format_version: str = MODEL_FORMAT_VERSION

    def __post_init__(self) -> None:
        validate_id(self.id)
        validate_nonempty(self.text, "text")
        if self.kind not in {"dialogue", "narration"}:
            raise ModelValidationError("kind must be 'dialogue' or 'narration'")
        if self.kind == "dialogue" and not self.speaker_id:
            raise ModelValidationError("dialogue requires speaker_id")
        if self.kind == "narration" and not self.narrator_id:
            raise ModelValidationError("narration requires narrator_id")
        validate_format_version(self.format_version)


@dataclass
class Scene:
    id: str
    title: str
    dialogues: list[Dialogue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    format_version: str = MODEL_FORMAT_VERSION

    def __post_init__(self) -> None:
        validate_id(self.id)
        validate_nonempty(self.title, "title")
        validate_format_version(self.format_version)


@dataclass
class Chapter:
    id: str
    title: str
    scenes: list[Scene] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    format_version: str = MODEL_FORMAT_VERSION

    def __post_init__(self) -> None:
        validate_id(self.id)
        validate_nonempty(self.title, "title")
        validate_format_version(self.format_version)


@dataclass
class Book:
    id: str
    title: str
    chapters: list[Chapter] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    format_version: str = MODEL_FORMAT_VERSION

    def __post_init__(self) -> None:
        validate_id(self.id)
        validate_nonempty(self.title, "title")
        validate_format_version(self.format_version)


@dataclass
class Project:
    id: str
    title: str
    books: list[Book] = field(default_factory=list)
    characters: list[Character] = field(default_factory=list)
    narrators: list[Narrator] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    format_version: str = MODEL_FORMAT_VERSION

    def __post_init__(self) -> None:
        validate_id(self.id)
        validate_nonempty(self.title, "title")
        validate_format_version(self.format_version)

    def validate(self) -> None:
        """Validate IDs, references, and duplicate entity IDs across the project."""

        entities: list[tuple[str, str]] = [("project", self.id)]
        entities.extend(("character", item.id) for item in self.characters)
        entities.extend(("narrator", item.id) for item in self.narrators)
        for book in self.books:
            entities.append(("book", book.id))
            for chapter in book.chapters:
                entities.append(("chapter", chapter.id))
                for scene in chapter.scenes:
                    entities.append(("scene", scene.id))
                    for dialogue in scene.dialogues:
                        entities.append(("dialogue", dialogue.id))
                        if dialogue.speaker_id and not any(
                            item.id == dialogue.speaker_id for item in self.characters
                        ):
                            raise ModelValidationError(
                                f"dialogue {dialogue.id} references unknown speaker_id {dialogue.speaker_id}"
                            )
                        if dialogue.narrator_id and not any(
                            item.id == dialogue.narrator_id for item in self.narrators
                        ):
                            raise ModelValidationError(
                                f"dialogue {dialogue.id} references unknown narrator_id {dialogue.narrator_id}"
                            )
        seen: dict[str, str] = {}
        for entity_type, entity_id in entities:
            if entity_id in seen:
                raise ModelValidationError(
                    f"duplicate id {entity_id!r}: {seen[entity_id]} and {entity_type}"
                )
            seen[entity_id] = entity_type


@dataclass
class WordTiming:
    word: str
    start_ms: int
    end_ms: int

    def __post_init__(self) -> None:
        validate_nonempty(self.word, "word")
        _validate_range(self.start_ms, self.end_ms, "word timing")


@dataclass
class PhonemeTiming:
    phoneme: str
    start_ms: int
    end_ms: int

    def __post_init__(self) -> None:
        validate_nonempty(self.phoneme, "phoneme")
        _validate_range(self.start_ms, self.end_ms, "phoneme timing")


@dataclass
class VisemeTiming:
    viseme: str
    start_ms: int
    end_ms: int

    def __post_init__(self) -> None:
        validate_nonempty(self.viseme, "viseme")
        _validate_range(self.start_ms, self.end_ms, "viseme timing")


def _validate_range(start_ms: int, end_ms: int, label: str) -> None:
    validate_nonnegative(start_ms, f"{label}.start_ms")
    validate_nonnegative(end_ms, f"{label}.end_ms")
    if end_ms < start_ms:
        raise ModelValidationError(f"{label}.end_ms cannot be before start_ms")


@dataclass
class AudioSegment:
    id: str
    dialogue_id: str
    provider_id: str
    voice_id: str
    language: str
    text: str
    start_ms: int
    end_ms: int
    duration_ms: int
    audio_uri: str | None = None
    track_id: str = "voice"
    word_timings: list[WordTiming] = field(default_factory=list)
    phoneme_timings: list[PhonemeTiming] = field(default_factory=list)
    viseme_timings: list[VisemeTiming] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    format_version: str = MODEL_FORMAT_VERSION

    def __post_init__(self) -> None:
        validate_id(self.id)
        validate_id(self.dialogue_id, "dialogue_id")
        validate_nonempty(self.provider_id, "provider_id")
        validate_nonempty(self.voice_id, "voice_id")
        validate_nonempty(self.language, "language")
        validate_nonempty(self.text, "text")
        _validate_range(self.start_ms, self.end_ms, "audio segment")
        validate_nonnegative(self.duration_ms, "duration_ms")
        if self.end_ms - self.start_ms != self.duration_ms:
            raise ModelValidationError(
                "duration_ms must equal end_ms - start_ms for an AudioSegment"
            )
        validate_nonempty(self.track_id, "track_id")
        validate_format_version(self.format_version)


@dataclass
class AnimationEvent:
    id: str
    kind: str
    start_ms: int
    end_ms: int
    target_id: str | None = None
    track_id: str = "animation"
    payload: dict[str, Any] = field(default_factory=dict)
    format_version: str = MODEL_FORMAT_VERSION

    def __post_init__(self) -> None:
        validate_id(self.id)
        validate_nonempty(self.kind, "kind")
        _validate_range(self.start_ms, self.end_ms, "animation event")
        validate_nonempty(self.track_id, "track_id")
        if self.target_id:
            validate_id(self.target_id, "target_id")
        validate_format_version(self.format_version)


@dataclass
class Timeline:
    id: str
    name: str
    duration_ms: int
    audio_segments: list[AudioSegment] = field(default_factory=list)
    animation_events: list[AnimationEvent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    format_version: str = MODEL_FORMAT_VERSION

    def __post_init__(self) -> None:
        validate_id(self.id)
        validate_nonempty(self.name, "name")
        validate_nonnegative(self.duration_ms, "duration_ms")
        validate_format_version(self.format_version)
