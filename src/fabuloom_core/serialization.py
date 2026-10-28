"""JSON serialization for the V0.1 contracts."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
import json
from enum import Enum
from typing import Any, TypeVar

from .models import (
    AnimationEvent,
    AudioSegment,
    Book,
    Chapter,
    Character,
    Dialogue,
    Narrator,
    PhonemeTiming,
    Project,
    Scene,
    Timeline,
    VisemeTiming,
    WordTiming,
    validate_format_version,
)
from .sync import AudioManifest

T = TypeVar("T")


def to_primitive(value: Any) -> Any:
    if is_dataclass(value):
        return {field.name: to_primitive(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [to_primitive(item) for item in value]
    if isinstance(value, dict):
        return {key: to_primitive(item) for key, item in value.items()}
    return value


def serialize_project(project: Project, *, indent: int | None = 2) -> str:
    project.validate()
    return json.dumps(to_primitive(project), ensure_ascii=False, indent=indent, sort_keys=True)


def deserialize_project(payload: str | bytes | dict[str, Any]) -> Project:
    data = _as_dict(payload)
    validate_format_version(data.get("format_version"))
    project = Project(
        id=data["id"],
        title=data["title"],
        books=[_book(item) for item in data.get("books", [])],
        characters=[_character(item) for item in data.get("characters", [])],
        narrators=[_narrator(item) for item in data.get("narrators", [])],
        metadata=data.get("metadata", {}),
        format_version=data["format_version"],
    )
    project.validate()
    return project


def serialize_manifest(manifest: AudioManifest, *, indent: int | None = 2) -> str:
    manifest.validate()
    return json.dumps(to_primitive(manifest), ensure_ascii=False, indent=indent, sort_keys=True)


def deserialize_manifest(payload: str | bytes | dict[str, Any]) -> AudioManifest:
    data = _as_dict(payload)
    validate_format_version(data.get("format_version"))
    manifest = AudioManifest(
        id=data["id"],
        timeline_id=data["timeline_id"],
        duration_ms=data["duration_ms"],
        segments=[_audio_segment(item) for item in data.get("segments", [])],
        animation_events=[_animation_event(item) for item in data.get("animation_events", [])],
        metadata=data.get("metadata", {}),
        format_version=data["format_version"],
    )
    manifest.validate()
    return manifest


def _as_dict(payload: str | bytes | dict[str, Any]) -> dict[str, Any]:
    value = json.loads(payload) if isinstance(payload, (str, bytes)) else payload
    if not isinstance(value, dict):
        raise ValueError("serialized contract must be a JSON object")
    return value


def _character(data: dict[str, Any]) -> Character:
    return Character(**data)


def _narrator(data: dict[str, Any]) -> Narrator:
    return Narrator(**data)


def _dialogue(data: dict[str, Any]) -> Dialogue:
    return Dialogue(**data)


def _scene(data: dict[str, Any]) -> Scene:
    data = dict(data)
    data["dialogues"] = [_dialogue(item) for item in data.get("dialogues", [])]
    return Scene(**data)


def _chapter(data: dict[str, Any]) -> Chapter:
    data = dict(data)
    data["scenes"] = [_scene(item) for item in data.get("scenes", [])]
    return Chapter(**data)


def _book(data: dict[str, Any]) -> Book:
    data = dict(data)
    data["chapters"] = [_chapter(item) for item in data.get("chapters", [])]
    return Book(**data)


def _word_timing(data: dict[str, Any]) -> WordTiming:
    return WordTiming(**data)


def _phoneme_timing(data: dict[str, Any]) -> PhonemeTiming:
    return PhonemeTiming(**data)


def _viseme_timing(data: dict[str, Any]) -> VisemeTiming:
    return VisemeTiming(**data)


def _audio_segment(data: dict[str, Any]) -> AudioSegment:
    data = dict(data)
    data["word_timings"] = [_word_timing(item) for item in data.get("word_timings", [])]
    data["phoneme_timings"] = [_phoneme_timing(item) for item in data.get("phoneme_timings", [])]
    data["viseme_timings"] = [_viseme_timing(item) for item in data.get("viseme_timings", [])]
    return AudioSegment(**data)


def _animation_event(data: dict[str, Any]) -> AnimationEvent:
    return AnimationEvent(**data)
