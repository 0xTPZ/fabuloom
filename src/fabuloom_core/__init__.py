"""Fabuloom Core V0.1 contracts.

The package is intentionally dependency-free. It defines serializable domain
models, timeline validation, and a deterministic simulated TTS provider.
"""

from .models import (
    MODEL_FORMAT_VERSION,
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
    make_stable_id,
)
from .serialization import deserialize_manifest, deserialize_project, serialize_manifest, serialize_project
from .sync import AudioManifest, TimelineValidationError, validate_timeline
from .tts import (
    SimulatedTTSProvider,
    SynthesisParameters,
    SynthesisRequest,
    SynthesisResult,
    TTSError,
    TTSProvider,
)

__all__ = [
    "MODEL_FORMAT_VERSION",
    "AnimationEvent",
    "AudioManifest",
    "AudioSegment",
    "Book",
    "Chapter",
    "Character",
    "Dialogue",
    "Narrator",
    "PhonemeTiming",
    "Project",
    "Scene",
    "SimulatedTTSProvider",
    "SynthesisParameters",
    "SynthesisRequest",
    "SynthesisResult",
    "TTSError",
    "TTSProvider",
    "Timeline",
    "TimelineValidationError",
    "VisemeTiming",
    "WordTiming",
    "deserialize_manifest",
    "deserialize_project",
    "make_stable_id",
    "serialize_manifest",
    "serialize_project",
    "validate_timeline",
]
