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
from .kokoro import (
    KOKORO_MODEL_ID,
    KOKORO_MODEL_REVISION,
    PT_BR_VOICES,
    KokoroTTSProvider,
    WavInfo,
)
from .narration import (
    NarrationFailure,
    NarrationProvider,
    NarrationRun,
    NarrationSynthesisError,
    NarrationTextSegment,
    compose_narration_manifest,
    segment_text,
    synthesize_narration,
)
from .character_registry import (
    APPROVAL_STATES,
    CharacterIdentity,
    CharacterNotFound,
    CharacterRegistry,
    CharacterRegistryError,
)
from .tts import (
    SimulatedTTSProvider,
    SynthesisParameters,
    SynthesisRequest,
    SynthesisResult,
    TTSError,
    TTSProvider,
)
from .asset_catalog import AssetCatalog, AssetRecord, CATALOG_FORMAT
from .engine import EngineService
from .paths import FabuloomPaths, PathConfigurationError
from .project_store import PROJECT_FORMAT, ProjectConflict, ProjectLocked, ProjectNotFound, ProjectStore, ProjectStoreError
from .migration import LibraryMigration, MIGRATION_FORMAT
from .profiles import PROFILE_FORMAT, ProfileError, ProfileRegistry
from .production import DEMO_TEXT, DeterministicAudioProvider, ProductionError, ProductionService, PRODUCTION_FORMAT
from .cinematic import CINEMATIC_FORMAT, CINEMATIC_PROFILE_ID, SHORTS_PROFILE_ID, CinematicCompatibility, CinematicCompatibilityError, CinematicRequest

__all__ = [
    "MODEL_FORMAT_VERSION",
    "AnimationEvent",
    "AudioManifest",
    "AudioSegment",
    "Book",
    "Chapter",
    "Character",
    "KOKORO_MODEL_ID",
    "KOKORO_MODEL_REVISION",
    "KokoroTTSProvider",
    "NarrationFailure",
    "NarrationProvider",
    "NarrationRun",
    "NarrationSynthesisError",
    "NarrationTextSegment",
    "Dialogue",
    "Narrator",
    "PhonemeTiming",
    "Project",
    "PT_BR_VOICES",
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
    "WavInfo",
    "deserialize_manifest",
    "deserialize_project",
    "make_stable_id",
    "serialize_manifest",
    "serialize_project",
    "segment_text",
    "compose_narration_manifest",
    "synthesize_narration",
    "validate_timeline",
    "APPROVAL_STATES",
    "CharacterIdentity",
    "CharacterNotFound",
    "CharacterRegistry",
    "CharacterRegistryError",
    "AssetCatalog",
    "AssetRecord",
    "CATALOG_FORMAT",
    "EngineService",
    "FabuloomPaths",
    "PathConfigurationError",
    "PROJECT_FORMAT",
    "ProjectConflict",
    "ProjectLocked",
    "ProjectNotFound",
    "ProjectStore",
    "ProjectStoreError",
    "LibraryMigration",
    "MIGRATION_FORMAT",
    "PROFILE_FORMAT",
    "ProfileError",
    "ProfileRegistry",
    "DEMO_TEXT",
    "DeterministicAudioProvider",
    "ProductionError",
    "ProductionService",
    "PRODUCTION_FORMAT",
    "CINEMATIC_FORMAT",
    "CINEMATIC_PROFILE_ID",
    "SHORTS_PROFILE_ID",
    "CinematicCompatibility",
    "CinematicCompatibilityError",
    "CinematicRequest",
]
