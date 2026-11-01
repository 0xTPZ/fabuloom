"""Create, validate, serialize, and round-trip a V0.1 Fabuloom project."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fabuloom_core import (  # noqa: E402
    AudioManifest,
    AudioSegment,
    Character,
    Dialogue,
    Narrator,
    Project,
    Scene,
    Chapter,
    Book,
    SimulatedTTSProvider,
    SynthesisRequest,
    Timeline,
    serialize_manifest,
    serialize_project,
    deserialize_project,
)


def main() -> None:
    character = Character(id="char-lia", name="Lia")
    narrator = Narrator(id="narrator-main", name="Narrador", voice_id="sim-narrator")
    dialogue = Dialogue(
        id="dialogue-001", text="A porta se abriu.", speaker_id=character.id
    )
    narration = Dialogue(
        id="narration-001",
        text="A noite caiu sobre a cidade.",
        kind="narration",
        narrator_id=narrator.id,
    )
    project = Project(
        id="project-demo",
        title="Fabuloom Demo",
        characters=[character],
        narrators=[narrator],
        books=[
            Book(
                id="book-demo",
                title="Demo",
                chapters=[
                    Chapter(
                        id="chapter-001",
                        title="Abertura",
                        scenes=[Scene(id="scene-001", title="A porta", dialogues=[narration, dialogue])],
                    )
                ],
            )
        ],
    )

    provider = SimulatedTTSProvider()
    result = provider.synthesize(
        SynthesisRequest(
            id="request-001",
            text=narration.text,
            voice_id=narrator.voice_id,
            language=narrator.language,
        )
    )
    segment = AudioSegment(
        id="audio-001",
        dialogue_id=narration.id,
        provider_id=result.provider_id,
        voice_id=result.voice_id,
        language=result.language,
        text=narration.text,
        start_ms=0,
        end_ms=result.duration_ms,
        duration_ms=result.duration_ms,
        audio_uri=result.audio_uri,
        word_timings=result.word_timings,
        metadata=result.metadata,
    )
    manifest = AudioManifest(
        id="manifest-demo",
        timeline_id="timeline-demo",
        duration_ms=result.duration_ms,
        segments=[segment],
    )
    manifest.validate()
    round_tripped = deserialize_project(serialize_project(project))
    print(f"project={round_tripped.id} format={round_tripped.format_version}")
    print(f"audio={segment.audio_uri} duration_ms={segment.duration_ms}")
    print(serialize_manifest(manifest, indent=2))


if __name__ == "__main__":
    main()
