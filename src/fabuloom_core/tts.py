"""Provider-independent TTS contracts and a deterministic simulated provider."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Protocol

from .models import WordTiming, validate_nonempty


class TTSError(RuntimeError):
    """A provider-neutral synthesis failure with a stable error code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass
class SynthesisParameters:
    speed: float = 1.0
    pitch: float = 0.0
    volume: float = 1.0
    extras: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.speed, (int, float)) or self.speed <= 0:
            raise TTSError("INVALID_SPEED", "speed must be greater than zero")
        if not isinstance(self.volume, (int, float)) or self.volume <= 0:
            raise TTSError("INVALID_VOLUME", "volume must be greater than zero")


@dataclass
class SynthesisRequest:
    id: str
    text: str
    voice_id: str
    language: str
    parameters: SynthesisParameters = field(default_factory=SynthesisParameters)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        validate_nonempty(self.id, "request.id")
        if not isinstance(self.text, str) or not self.text.strip():
            raise TTSError("EMPTY_TEXT", "text must be non-empty")
        validate_nonempty(self.voice_id, "request.voice_id")
        validate_nonempty(self.language, "request.language")
        self.parameters.validate()


@dataclass
class SynthesisResult:
    request_id: str
    provider_id: str
    voice_id: str
    language: str
    audio_uri: str
    duration_ms: int
    word_timings: list[WordTiming] = field(default_factory=list)
    phoneme_timings: list[Any] = field(default_factory=list)
    viseme_timings: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class TTSProvider(Protocol):
    """Provider contract; implementations must not leak engine-specific APIs."""

    provider_id: str

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        ...


class SimulatedTTSProvider:
    """Deterministic provider for offline contract and integration tests.

    It creates no audio file and loads no model. The URI is a content-derived
    placeholder, and timing metadata is explicitly marked synthetic.
    """

    provider_id = "simulated"

    def __init__(self, voices: dict[str, set[str]] | None = None) -> None:
        self.voices = voices or {"pt-BR": {"sim-narrator", "sim-character"}}

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        request.validate()
        available = self.voices.get(request.language, set())
        if request.voice_id not in available:
            raise TTSError(
                "UNSUPPORTED_VOICE",
                f"voice {request.voice_id!r} is unavailable for {request.language}",
            )

        words = request.text.split()
        # This is a deterministic test duration, not an acoustic estimate.
        duration_ms = max(100, round(len(words) * 420 / request.parameters.speed))
        step = duration_ms // max(1, len(words))
        timings: list[WordTiming] = []
        for index, word in enumerate(words):
            start = index * step
            end = duration_ms if index == len(words) - 1 else (index + 1) * step
            timings.append(WordTiming(word=word, start_ms=start, end_ms=end))
        digest = hashlib.sha256(
            f"{request.text}|{request.voice_id}|{request.language}|{request.parameters.speed}".encode(
                "utf-8"
            )
        ).hexdigest()[:20]
        return SynthesisResult(
            request_id=request.id,
            provider_id=self.provider_id,
            voice_id=request.voice_id,
            language=request.language,
            audio_uri=f"simulated://audio/{digest}.wav",
            duration_ms=duration_ms,
            word_timings=timings,
            metadata={"simulated": True, "timing_source": "synthetic"},
        )
