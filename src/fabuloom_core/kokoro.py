"""Optional Kokoro TTS integration.

The module keeps Kokoro and audio dependencies lazy so the core package and
its unit tests remain usable without models, GPU, or network access.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
import time
from typing import Any, Callable, Iterable
import wave

from .tts import SynthesisRequest, SynthesisResult, TTSError


KOKORO_MODEL_ID = "hexgrad/Kokoro-82M"
KOKORO_MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
PT_BR_LANGUAGE = "pt-BR"
KOKORO_LANGUAGE_CODE = "p"
PT_BR_VOICES = ("pf_dora", "pm_alex", "pm_santa")
DEFAULT_SAMPLE_RATE = 24_000


@dataclass(frozen=True)
class WavInfo:
    """Measured properties of an output WAV file."""

    sample_rate: int
    channels: int
    sample_width: int
    frames: int
    duration_ms: int

    def __post_init__(self) -> None:
        if self.sample_rate <= 0 or self.channels <= 0 or self.sample_width <= 0:
            raise ValueError("WAV format properties must be positive")
        if self.frames <= 0 or self.duration_ms <= 0:
            raise ValueError("WAV must contain audio frames")


AudioWriter = Callable[[Path, Iterable[Any]], WavInfo]
PipelineFactory = Callable[..., Any]


class KokoroTTSProvider:
    """Kokoro implementation of the provider-neutral TTS contract.

    The model is initialized lazily and reused for subsequent requests. The
    adapter supports Kokoro's Portuguese language code and voice selection,
    plus the generic ``speed`` parameter. Pitch, volume, and arbitrary extras
    are intentionally rejected because this integration does not implement
    them. Word, phoneme, and viseme timings are reported as unavailable.
    """

    provider_id = "kokoro"
    model_id = KOKORO_MODEL_ID
    model_revision = KOKORO_MODEL_REVISION
    sample_rate = DEFAULT_SAMPLE_RATE

    def __init__(
        self,
        output_dir: str | Path | None = None,
        *,
        pipeline_factory: PipelineFactory | None = None,
        audio_writer: AudioWriter | None = None,
    ) -> None:
        self.output_dir = (
            Path(output_dir)
            if output_dir is not None
            else Path(__file__).resolve().parents[3] / "workspace" / "exports"
        )
        self._pipeline_factory = pipeline_factory
        self._audio_writer = audio_writer or _write_wav
        self._pipeline: Any | None = None
        self._lock = threading.RLock()
        self._model_load_count = 0
        self._last_model_load_seconds: float | None = None
        self._last_synthesis_seconds: float | None = None

    @property
    def initialized(self) -> bool:
        return self._pipeline is not None

    @property
    def model_load_count(self) -> int:
        return self._model_load_count

    @property
    def last_model_load_seconds(self) -> float | None:
        return self._last_model_load_seconds

    @property
    def last_synthesis_seconds(self) -> float | None:
        return self._last_synthesis_seconds

    def list_voices(self, language: str = PT_BR_LANGUAGE) -> tuple[str, ...]:
        if language != PT_BR_LANGUAGE:
            raise TTSError("UNSUPPORTED_LANGUAGE", f"Kokoro PT-BR adapter does not support {language!r}")
        return PT_BR_VOICES

    def initialize(self) -> "KokoroTTSProvider":
        """Load the pipeline once, reporting missing dependencies clearly."""

        with self._lock:
            if self._pipeline is not None:
                return self
            factory = self._pipeline_factory
            if factory is None:
                try:
                    from kokoro import KPipeline
                except ImportError as exc:
                    raise TTSError(
                        "MISSING_DEPENDENCY",
                        "Kokoro is not installed in the active Python environment",
                    ) from exc
                factory = KPipeline
            started = time.perf_counter()
            try:
                self._pipeline = factory(lang_code=KOKORO_LANGUAGE_CODE)
            except Exception as exc:
                self._pipeline = None
                raise TTSError("INITIALIZATION_FAILED", f"Kokoro pipeline could not initialize: {exc}") from exc
            self._last_model_load_seconds = time.perf_counter() - started
            self._model_load_count += 1
            return self

    def synthesize(
        self,
        request: SynthesisRequest,
        output_path: str | Path | None = None,
    ) -> SynthesisResult:
        request.validate()
        self._validate_request(request)
        target = self._resolve_output_path(request, output_path)

        with self._lock:
            pipeline = self.initialize()._pipeline
            started = time.perf_counter()
            try:
                chunks = list(
                    pipeline(
                        request.text,
                        voice=request.voice_id,
                        speed=float(request.parameters.speed),
                    )
                )
            except Exception as exc:
                raise TTSError("SYNTHESIS_FAILED", f"Kokoro failed to synthesize the request: {exc}") from exc
            if not chunks:
                raise TTSError("EMPTY_AUDIO", "Kokoro returned no audio chunks")
            try:
                wav_info = self._audio_writer(target, chunks)
            except TTSError:
                raise
            except Exception as exc:
                raise TTSError("AUDIO_WRITE_FAILED", f"Could not write WAV output: {exc}") from exc
            self._last_synthesis_seconds = time.perf_counter() - started

        return SynthesisResult(
            request_id=request.id,
            provider_id=self.provider_id,
            voice_id=request.voice_id,
            language=request.language,
            audio_uri=target.resolve().as_uri(),
            duration_ms=wav_info.duration_ms,
            metadata={
                "model_id": self.model_id,
                "model_revision": self.model_revision,
                "language_code": KOKORO_LANGUAGE_CODE,
                "sample_rate": wav_info.sample_rate,
                "channels": wav_info.channels,
                "frames": wav_info.frames,
                "timing_available": False,
                "word_timing_available": False,
                "phoneme_timing_available": False,
                "viseme_timing_available": False,
                "timing_source": "audio_duration_only",
                "model_load_seconds": self.last_model_load_seconds,
                "synthesis_seconds": self.last_synthesis_seconds,
            },
        )

    def close(self) -> None:
        """Release the provider reference and call an optional pipeline closer."""

        with self._lock:
            pipeline, self._pipeline = self._pipeline, None
            if pipeline is None:
                return
            close = getattr(pipeline, "close", None)
            if callable(close):
                try:
                    close()
                except Exception as exc:
                    raise TTSError("CLOSE_FAILED", f"Kokoro pipeline close failed: {exc}") from exc

    def _validate_request(self, request: SynthesisRequest) -> None:
        if request.language != PT_BR_LANGUAGE:
            raise TTSError("UNSUPPORTED_LANGUAGE", f"Kokoro supports only {PT_BR_LANGUAGE}")
        if request.voice_id not in PT_BR_VOICES:
            raise TTSError("UNSUPPORTED_VOICE", f"unsupported Kokoro voice {request.voice_id!r}")
        if request.parameters.pitch != 0:
            raise TTSError("UNSUPPORTED_PARAMETER", "Kokoro adapter does not implement pitch")
        if request.parameters.volume != 1:
            raise TTSError("UNSUPPORTED_PARAMETER", "Kokoro adapter does not implement volume")
        if request.parameters.extras:
            raise TTSError("UNSUPPORTED_PARAMETER", "Kokoro adapter does not implement extra parameters")

    def _resolve_output_path(
        self,
        request: SynthesisRequest,
        output_path: str | Path | None,
    ) -> Path:
        root = self.output_dir.resolve()
        candidate = Path(output_path) if output_path is not None else root / f"{request.id}.wav"
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise TTSError("INVALID_OUTPUT_PATH", "WAV output must stay inside the Fabuloom workspace exports directory") from exc
        if candidate.suffix.lower() != ".wav":
            raise TTSError("INVALID_OUTPUT_PATH", "Kokoro output must use the .wav extension")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate


def _write_wav(path: Path, chunks: Iterable[Any]) -> WavInfo:
    try:
        import numpy as np
    except ImportError as exc:
        raise TTSError("MISSING_DEPENDENCY", "numpy is required to assemble Kokoro audio") from exc
    try:
        import soundfile as sf
    except ImportError as exc:
        raise TTSError("MISSING_DEPENDENCY", "soundfile is required to write Kokoro WAV output") from exc

    pieces = []
    for chunk in chunks:
        if hasattr(chunk, "audio"):
            # Kokoro 0.9.x yields KPipeline.Result objects. The Result also
            # supports tuple-like iteration, so checking the explicit audio
            # property first avoids converting the whole result to an array.
            audio = chunk.audio
        else:
            audio = chunk[2] if isinstance(chunk, (tuple, list)) and len(chunk) >= 3 else chunk
        if audio is None:
            continue
        if hasattr(audio, "detach"):
            audio = audio.detach()
        if hasattr(audio, "cpu"):
            audio = audio.cpu()
        if hasattr(audio, "numpy"):
            audio = audio.numpy()
        array = np.asarray(audio)
        if array.size:
            pieces.append(array.reshape(-1))
    if not pieces:
        raise TTSError("EMPTY_AUDIO", "Kokoro returned only empty audio chunks")
    audio = np.concatenate(pieces)
    try:
        sf.write(str(path), audio, DEFAULT_SAMPLE_RATE, format="WAV", subtype="PCM_16")
    except Exception as exc:
        raise TTSError("AUDIO_WRITE_FAILED", f"soundfile could not write WAV: {exc}") from exc
    return _inspect_wav(path)


def _inspect_wav(path: Path) -> WavInfo:
    try:
        with wave.open(str(path), "rb") as wav:
            info = WavInfo(
                sample_rate=wav.getframerate(),
                channels=wav.getnchannels(),
                sample_width=wav.getsampwidth(),
                frames=wav.getnframes(),
                duration_ms=round(wav.getnframes() * 1000 / wav.getframerate()),
            )
    except (OSError, EOFError, wave.Error, ValueError) as exc:
        raise TTSError("INVALID_AUDIO", f"output is not a valid non-empty WAV: {exc}") from exc
    return info
