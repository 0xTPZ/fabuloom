"""Audio manifest and timeline synchronization rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import (
    MODEL_FORMAT_VERSION,
    AnimationEvent,
    AudioSegment,
    Timeline,
    validate_format_version,
)


class TimelineValidationError(ValueError):
    """Raised when a timeline or manifest violates temporal rules."""


# Gestures and expressions may overlap on the same animation track. Structural
# events such as page changes and camera cuts must not overlap on that track.
OVERLAP_ALLOWED_EVENT_KINDS = frozenset({"gesture", "expression", "viseme"})


@dataclass
class AudioManifest:
    id: str
    timeline_id: str
    duration_ms: int
    segments: list[AudioSegment] = field(default_factory=list)
    animation_events: list[AnimationEvent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    format_version: str = MODEL_FORMAT_VERSION

    def __post_init__(self) -> None:
        validate_format_version(self.format_version)

    def validate(self) -> None:
        timeline = Timeline(
            id=self.timeline_id,
            name=self.timeline_id,
            duration_ms=self.duration_ms,
            audio_segments=self.segments,
            animation_events=self.animation_events,
            format_version=self.format_version,
        )
        validate_timeline(timeline)


def validate_timeline(timeline: Timeline) -> None:
    """Validate ranges, IDs, bounds, and overlap policy.

    Audio segments cannot overlap on the same track. Animation events may
    overlap on different tracks, or on the same track when both events are
    explicitly overlap-safe kinds (gesture, expression, or viseme).
    """

    identifiers: set[str] = set()
    for item in [*timeline.audio_segments, *timeline.animation_events]:
        if item.id in identifiers:
            raise TimelineValidationError(f"duplicate timeline id {item.id!r}")
        identifiers.add(item.id)
        if item.start_ms < 0 or item.end_ms < item.start_ms:
            raise TimelineValidationError(f"invalid time range for {item.id}")
        if item.end_ms > timeline.duration_ms:
            raise TimelineValidationError(
                f"{item.id} ends at {item.end_ms} ms beyond timeline duration {timeline.duration_ms} ms"
            )

    _reject_overlaps(timeline.audio_segments, "audio segments", always_forbid=True)
    grouped_events: dict[str, list[AnimationEvent]] = {}
    for event in timeline.animation_events:
        grouped_events.setdefault(event.track_id, []).append(event)
    for track_id, events in grouped_events.items():
        _reject_overlaps(
            events,
            f"animation events on track {track_id!r}",
            always_forbid=False,
        )

    for segment in timeline.audio_segments:
        segment_duration = segment.duration_ms
        for timing in [
            *segment.word_timings,
            *segment.phoneme_timings,
            *segment.viseme_timings,
        ]:
            if timing.end_ms > segment_duration:
                raise TimelineValidationError(
                    f"timing in segment {segment.id} exceeds segment duration"
                )


def _reject_overlaps(items: list[Any], label: str, always_forbid: bool) -> None:
    ordered = sorted(items, key=lambda item: (item.start_ms, item.end_ms, item.id))
    for previous, current in zip(ordered, ordered[1:]):
        if current.start_ms >= previous.end_ms:
            continue
        if not always_forbid:
            allowed = (
                previous.kind in OVERLAP_ALLOWED_EVENT_KINDS
                and current.kind in OVERLAP_ALLOWED_EVENT_KINDS
            )
            if allowed:
                continue
        raise TimelineValidationError(
            f"overlap forbidden in {label}: {previous.id} and {current.id}"
        )
