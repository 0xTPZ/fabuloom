"""Deterministic narration segmentation and measured temporal composition."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import time
from pathlib import Path
from typing import Any, Protocol, Sequence

from .models import AudioSegment, make_stable_id, validate_id, validate_nonempty, validate_nonnegative
from .sync import AudioManifest
from .tts import SynthesisRequest, SynthesisResult, TTSError


_TERMINAL_CHARS = frozenset(".!?…")
_CLOSING_CHARS = frozenset('"\'”’»)]}）')
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")
_COMMON_ABBREVIATIONS = frozenset({"sr", "sra", "srta", "dr", "dra", "prof", "profa", "etc", "p.ex"})


class NarrationProvider(Protocol):
    """Minimal provider surface required by ``synthesize_narration``."""

    provider_id: str
    output_dir: Path

    def synthesize(
        self,
        request: SynthesisRequest,
        output_path: str | Path | None = None,
    ) -> SynthesisResult:
        ...


@dataclass(frozen=True)
class NarrationTextSegment:
    """One ordered source-text unit before synthesis.

    ``pause_after_ms`` is an intentional composition gap, not audio duration.
    It is derived only from paragraph boundaries or terminal punctuation.
    """

    id: str
    text: str
    ordinal: int
    paragraph_index: int
    sentence_index: int
    fragment_index: int = 0
    terminal_kind: str = "none"
    pause_after_ms: int = 0
    pause_source: str = "none"

    def __post_init__(self) -> None:
        validate_id(self.id)
        validate_nonempty(self.text, "text")
        validate_nonnegative(self.ordinal, "ordinal")
        validate_nonnegative(self.paragraph_index, "paragraph_index")
        validate_nonnegative(self.sentence_index, "sentence_index")
        validate_nonnegative(self.fragment_index, "fragment_index")
        validate_nonnegative(self.pause_after_ms, "pause_after_ms")
        if self.terminal_kind not in {"none", "period", "question", "exclamation", "ellipsis"}:
            raise ValueError(f"unsupported terminal_kind {self.terminal_kind!r}")
        if self.pause_source not in {"none", "punctuation", "paragraph_boundary"}:
            raise ValueError(f"unsupported pause_source {self.pause_source!r}")


@dataclass(frozen=True)
class NarrationFailure:
    segment_id: str
    error_code: str
    message: str


class NarrationSynthesisError(TTSError):
    """Fail-fast narration error with completed and failed segment details."""

    def __init__(
        self,
        failure: NarrationFailure,
        completed_results: Sequence[SynthesisResult],
    ) -> None:
        self.failure = failure
        self.completed_results = tuple(completed_results)
        super().__init__("NARRATION_FAILED", f"segment {failure.segment_id} failed: {failure.message}")


@dataclass(frozen=True)
class NarrationRun:
    """Result of composing a narration sequence."""

    manifest: AudioManifest
    source_segments: tuple[NarrationTextSegment, ...]
    results: tuple[SynthesisResult, ...]
    processing_seconds: float
    failures: tuple[NarrationFailure, ...] = field(default_factory=tuple)

    @property
    def status(self) -> str:
        return "partial" if self.failures else "completed"


def segment_text(
    text: str,
    *,
    segment_namespace: str = "narration",
    max_chars: int = 400,
    sentence_pause_ms: int = 180,
    question_pause_ms: int = 240,
    paragraph_pause_ms: int = 350,
) -> tuple[NarrationTextSegment, ...]:
    """Split text by paragraphs and sentence punctuation while preserving order.

    A sentence longer than ``max_chars`` is split only at whitespace, with a
    final hard split only for an individual token that exceeds the limit. No
    audio or word timing is inferred by this function.
    """

    validate_nonempty(text, "text")
    validate_nonempty(segment_namespace, "segment_namespace")
    for value, name in (
        (max_chars, "max_chars"),
        (sentence_pause_ms, "sentence_pause_ms"),
        (question_pause_ms, "question_pause_ms"),
        (paragraph_pause_ms, "paragraph_pause_ms"),
    ):
        validate_nonnegative(value, name)
    if max_chars == 0:
        raise ValueError("max_chars must be greater than zero")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [part.strip() for part in _PARAGRAPH_SPLIT.split(normalized) if part.strip()]
    if not paragraphs:
        raise ValueError("text must contain a non-empty paragraph")

    sentence_groups: list[tuple[int, list[tuple[str, str]]]] = []
    for paragraph_index, paragraph in enumerate(paragraphs):
        sentences = _split_sentences(paragraph)
        if sentences:
            sentence_groups.append((paragraph_index, sentences))

    output: list[NarrationTextSegment] = []
    ordinal = 0
    for paragraph_position, (paragraph_index, sentences) in enumerate(sentence_groups):
        is_last_paragraph = paragraph_position == len(sentence_groups) - 1
        for sentence_index, (sentence, terminal_kind) in enumerate(sentences):
            fragments = _split_long_text(sentence, max_chars)
            is_last_sentence = sentence_index == len(sentences) - 1
            for fragment_index, fragment in enumerate(fragments):
                is_last_fragment = fragment_index == len(fragments) - 1
                pause_after_ms = 0
                pause_source = "none"
                if is_last_fragment:
                    if is_last_sentence and not is_last_paragraph:
                        pause_after_ms = paragraph_pause_ms
                        pause_source = "paragraph_boundary"
                    elif not (is_last_sentence and is_last_paragraph):
                        pause_after_ms = _pause_for_terminal(
                            terminal_kind,
                            sentence_pause_ms=sentence_pause_ms,
                            question_pause_ms=question_pause_ms,
                        )
                        pause_source = "punctuation" if pause_after_ms else "none"

                segment_id = make_stable_id(
                    "narration-segment",
                    f"{segment_namespace}:{ordinal}:{fragment}",
                )
                output.append(
                    NarrationTextSegment(
                        id=segment_id,
                        text=fragment,
                        ordinal=ordinal,
                        paragraph_index=paragraph_index,
                        sentence_index=sentence_index,
                        fragment_index=fragment_index,
                        terminal_kind=terminal_kind if is_last_fragment else "none",
                        pause_after_ms=pause_after_ms,
                        pause_source=pause_source,
                    )
                )
                ordinal += 1
    return tuple(output)


def compose_narration_manifest(
    source_segments: Sequence[NarrationTextSegment],
    results: Sequence[SynthesisResult],
    *,
    manifest_id: str,
    timeline_id: str,
    track_id: str = "voice",
    metadata: dict[str, Any] | None = None,
) -> AudioManifest:
    """Compose ordered audio segments using measured result durations only."""

    validate_id(manifest_id, "manifest_id")
    validate_id(timeline_id, "timeline_id")
    validate_nonempty(track_id, "track_id")
    if len(source_segments) != len(results):
        raise ValueError("source_segments and results must have the same length")

    audio_segments: list[AudioSegment] = []
    cursor_ms = 0
    for source, result in zip(source_segments, results):
        duration_ms = result.duration_ms
        start_ms = cursor_ms
        end_ms = start_ms + duration_ms
        segment_metadata = {
            **result.metadata,
            "source_segment_id": source.id,
            "paragraph_index": source.paragraph_index,
            "sentence_index": source.sentence_index,
            "fragment_index": source.fragment_index,
            "pause_after_ms": source.pause_after_ms,
            "pause_source": source.pause_source,
            "temporal_source": "measured_wav",
        }
        audio_segments.append(
            AudioSegment(
                id=source.id,
                dialogue_id=source.id,
                provider_id=result.provider_id,
                voice_id=result.voice_id,
                language=result.language,
                text=source.text,
                start_ms=start_ms,
                end_ms=end_ms,
                duration_ms=duration_ms,
                audio_uri=result.audio_uri,
                track_id=track_id,
                word_timings=list(result.word_timings),
                phoneme_timings=list(result.phoneme_timings),
                viseme_timings=list(result.viseme_timings),
                metadata=segment_metadata,
            )
        )
        cursor_ms = end_ms + source.pause_after_ms

    manifest_metadata = {
        "temporal_source": "measured_wav",
        "sequence_order": "source_segment_order",
        "segment_count": len(audio_segments),
        **(metadata or {}),
    }
    manifest = AudioManifest(
        id=manifest_id,
        timeline_id=timeline_id,
        duration_ms=cursor_ms,
        segments=audio_segments,
        metadata=manifest_metadata,
    )
    manifest.validate()
    return manifest


def synthesize_narration(
    provider: NarrationProvider,
    text: str,
    *,
    narration_id: str,
    voice_id: str,
    language: str = "pt-BR",
    manifest_id: str | None = None,
    timeline_id: str | None = None,
    output_dir: str | Path | None = None,
    track_id: str = "voice",
    continue_on_error: bool = False,
    **segmentation_options: int | str,
) -> NarrationRun:
    """Synthesize ordered text segments and compose their measured timeline."""

    validate_id(narration_id, "narration_id")
    validate_nonempty(voice_id, "voice_id")
    validate_nonempty(language, "language")
    segmentation = dict(segmentation_options)
    segmentation["segment_namespace"] = narration_id
    source_segments = segment_text(text, **segmentation)
    root = Path(output_dir) if output_dir is not None else Path(provider.output_dir)
    results: list[SynthesisResult] = []
    completed_segments: list[NarrationTextSegment] = []
    failures: list[NarrationFailure] = []
    started = time.perf_counter()

    for source in source_segments:
        request = SynthesisRequest(
            id=source.id,
            text=source.text,
            voice_id=voice_id,
            language=language,
            metadata={
                "narration_id": narration_id,
                "source_segment_id": source.id,
                "ordinal": source.ordinal,
            },
        )
        output_path = root / f"{narration_id}-{source.ordinal:04d}.wav"
        try:
            result = provider.synthesize(request, output_path)
            _validate_result_consistency(result, provider_id=provider.provider_id, voice_id=voice_id, language=language)
        except TTSError as exc:
            failure = NarrationFailure(source.id, exc.code, str(exc))
            failures.append(failure)
            if not continue_on_error:
                raise NarrationSynthesisError(failure, results) from exc
            continue
        except Exception as exc:
            failure = NarrationFailure(source.id, "PROVIDER_FAILURE", str(exc))
            failures.append(failure)
            if not continue_on_error:
                raise NarrationSynthesisError(failure, results) from exc
            continue
        completed_segments.append(source)
        results.append(result)

    if not results:
        failure = failures[0] if failures else NarrationFailure("none", "EMPTY_NARRATION", "no source segments were synthesized")
        raise NarrationSynthesisError(failure, results)

    manifest = compose_narration_manifest(
        completed_segments,
        results,
        manifest_id=manifest_id or narration_id,
        timeline_id=timeline_id or make_stable_id("narration-timeline", narration_id),
        track_id=track_id,
        metadata={
            "narration_id": narration_id,
            "voice_id": voice_id,
            "language": language,
            "status": "partial" if failures else "completed",
            "failed_segment_ids": [failure.segment_id for failure in failures],
        },
    )
    return NarrationRun(
        manifest=manifest,
        source_segments=tuple(completed_segments),
        results=tuple(results),
        processing_seconds=time.perf_counter() - started,
        failures=tuple(failures),
    )


def _validate_result_consistency(
    result: SynthesisResult,
    *,
    provider_id: str,
    voice_id: str,
    language: str,
) -> None:
    if result.provider_id != provider_id:
        raise TTSError("INCONSISTENT_PROVIDER", "narration result provider differs from requested provider")
    if result.voice_id != voice_id:
        raise TTSError("INCONSISTENT_VOICE", "narration result voice differs from requested voice")
    if result.language != language:
        raise TTSError("INCONSISTENT_LANGUAGE", "narration result language differs from requested language")


def _split_sentences(paragraph: str) -> list[tuple[str, str]]:
    sentences: list[tuple[str, str]] = []
    start = 0
    index = 0
    while index < len(paragraph):
        if paragraph[index] not in _TERMINAL_CHARS:
            index += 1
            continue
        punctuation_start = index
        while index + 1 < len(paragraph) and paragraph[index + 1] in _TERMINAL_CHARS:
            index += 1
        punctuation_end = index + 1
        while punctuation_end < len(paragraph) and paragraph[punctuation_end] in _CLOSING_CHARS:
            punctuation_end += 1
        preceding_word = paragraph[start:punctuation_start].strip().split()[-1].lower().strip('"\'“‘«(') if paragraph[start:punctuation_start].strip() else ""
        abbreviation = preceding_word in _COMMON_ABBREVIATIONS and paragraph[punctuation_start] == "."
        if abbreviation and punctuation_end < len(paragraph):
            index = punctuation_end
            continue
        if punctuation_end < len(paragraph) and not paragraph[punctuation_end].isspace():
            index = punctuation_end
            continue
        candidate = paragraph[start:punctuation_end].strip()
        if candidate:
            terminal = paragraph[punctuation_start : index + 1]
            sentences.append((candidate, _terminal_kind(terminal)))
        start = punctuation_end
        index = punctuation_end
    tail = paragraph[start:].strip()
    if tail:
        sentences.append((tail, "none"))
    return sentences


def _split_long_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    pieces: list[str] = []
    current = ""
    for token_match in re.finditer(r"\S+(?:\s+|$)", text):
        token = token_match.group(0)
        if len(token.rstrip()) > max_chars:
            if current.strip():
                pieces.append(current.strip())
                current = ""
            raw = token.rstrip()
            for start in range(0, len(raw), max_chars):
                pieces.append(raw[start : start + max_chars])
            continue
        if current and len(current) + len(token) > max_chars:
            pieces.append(current.strip())
            current = ""
        current += token
    if current.strip():
        pieces.append(current.strip())
    return pieces or [text[:max_chars]]


def _terminal_kind(punctuation: str) -> str:
    if "?" in punctuation:
        return "question"
    if "!" in punctuation:
        return "exclamation"
    if "…" in punctuation or punctuation.count(".") >= 3:
        return "ellipsis"
    return "period"


def _pause_for_terminal(terminal_kind: str, *, sentence_pause_ms: int, question_pause_ms: int) -> int:
    if terminal_kind in {"question", "exclamation", "ellipsis"}:
        return question_pause_ms
    if terminal_kind == "period":
        return sentence_pause_ms
    return 0
