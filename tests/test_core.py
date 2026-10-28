import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fabuloom_core import (
    AnimationEvent,
    AudioManifest,
    AudioSegment,
    Book,
    Chapter,
    Character,
    Dialogue,
    Narrator,
    Project,
    Scene,
    SimulatedTTSProvider,
    SynthesisRequest,
    Timeline,
    TimelineValidationError,
    TTSError,
    deserialize_manifest,
    deserialize_project,
    make_stable_id,
    serialize_manifest,
    serialize_project,
    validate_timeline,
)


def demo_project() -> Project:
    character = Character(id="char-lia", name="Lia")
    narrator = Narrator(id="narrator-main", name="Narrador", voice_id="sim-narrator")
    scene = Scene(
        id="scene-001",
        title="Abertura",
        dialogues=[
            Dialogue(
                id="narration-001",
                text="A noite caiu.",
                kind="narration",
                narrator_id=narrator.id,
            ),
            Dialogue(
                id="dialogue-001",
                text="Quem está aí?",
                speaker_id=character.id,
            ),
        ],
    )
    return Project(
        id="project-demo",
        title="Demo",
        characters=[character],
        narrators=[narrator],
        books=[Book(id="book-demo", title="Livro", chapters=[Chapter(id="chapter-001", title="Capítulo", scenes=[scene])])],
    )


class ModelTests(unittest.TestCase):
    def test_stable_id_is_deterministic(self):
        self.assertEqual(make_stable_id("scene", "opening"), make_stable_id("scene", "opening"))
        self.assertNotEqual(make_stable_id("scene", "opening"), make_stable_id("scene", "ending"))

    def test_project_round_trip(self):
        original = demo_project()
        payload = serialize_project(original)
        restored = deserialize_project(payload)
        self.assertEqual(restored, original)

    def test_project_json_is_explicitly_versioned(self):
        payload = json.loads(serialize_project(demo_project()))
        self.assertEqual(payload["format_version"], "0.1.0")
        self.assertEqual(payload["books"][0]["chapters"][0]["scenes"][0]["dialogues"][0]["kind"], "narration")

    def test_unsupported_future_version_is_rejected(self):
        payload = json.loads(serialize_project(demo_project()))
        payload["format_version"] = "0.2.0"
        with self.assertRaises(ValueError):
            deserialize_project(payload)

    def test_duplicate_project_ids_are_rejected(self):
        project = demo_project()
        project.books[0].chapters[0].scenes[0].dialogues[0].id = project.characters[0].id
        with self.assertRaisesRegex(ValueError, "duplicate id"):
            project.validate()


class TimelineTests(unittest.TestCase):
    def segment(self, segment_id: str, start: int, end: int) -> AudioSegment:
        return AudioSegment(
            id=segment_id,
            dialogue_id="dialogue-001",
            provider_id="simulated",
            voice_id="sim-narrator",
            language="pt-BR",
            text="Texto",
            start_ms=start,
            end_ms=end,
            duration_ms=end - start,
        )

    def test_negative_times_are_rejected_at_model_boundary(self):
        with self.assertRaises(ValueError):
            self.segment("audio-001", -1, 100)

    def test_audio_overlap_is_rejected(self):
        timeline = Timeline(
            id="timeline-001",
            name="Timeline",
            duration_ms=1000,
            audio_segments=[self.segment("audio-001", 0, 600), self.segment("audio-002", 500, 900)],
        )
        with self.assertRaises(TimelineValidationError):
            validate_timeline(timeline)

    def test_animation_gesture_overlap_is_allowed(self):
        timeline = Timeline(
            id="timeline-001",
            name="Timeline",
            duration_ms=1000,
            animation_events=[
                AnimationEvent(id="event-001", kind="gesture", start_ms=0, end_ms=600),
                AnimationEvent(id="event-002", kind="expression", start_ms=500, end_ms=900),
            ],
        )
        validate_timeline(timeline)

    def test_structural_animation_overlap_is_rejected(self):
        timeline = Timeline(
            id="timeline-001",
            name="Timeline",
            duration_ms=1000,
            animation_events=[
                AnimationEvent(id="event-001", kind="page_change", start_ms=0, end_ms=600),
                AnimationEvent(id="event-002", kind="camera", start_ms=500, end_ms=900),
            ],
        )
        with self.assertRaises(TimelineValidationError):
            validate_timeline(timeline)

    def test_manifest_round_trip(self):
        manifest = AudioManifest(
            id="manifest-001",
            timeline_id="timeline-001",
            duration_ms=500,
            segments=[self.segment("audio-001", 0, 500)],
        )
        restored = deserialize_manifest(serialize_manifest(manifest))
        self.assertEqual(restored, manifest)


class TTSProviderTests(unittest.TestCase):
    def test_simulated_provider_is_deterministic_and_offline(self):
        provider = SimulatedTTSProvider()
        request = SynthesisRequest(
            id="request-001",
            text="Uma frase de teste.",
            voice_id="sim-narrator",
            language="pt-BR",
        )
        first = provider.synthesize(request)
        second = provider.synthesize(request)
        self.assertEqual(first, second)
        self.assertTrue(first.audio_uri.startswith("simulated://"))
        self.assertTrue(first.metadata["simulated"])
        self.assertEqual(len(first.word_timings), 4)
        self.assertEqual(first.phoneme_timings, [])

    def test_simulated_provider_rejects_unknown_voice(self):
        provider = SimulatedTTSProvider()
        request = SynthesisRequest(
            id="request-001",
            text="Texto",
            voice_id="unknown",
            language="pt-BR",
        )
        with self.assertRaises(TTSError) as error:
            provider.synthesize(request)
        self.assertEqual(error.exception.code, "UNSUPPORTED_VOICE")

    def test_simulated_provider_rejects_empty_text(self):
        request = SynthesisRequest(id="request-001", text="", voice_id="sim-narrator", language="pt-BR")
        with self.assertRaises(TTSError) as error:
            SimulatedTTSProvider().synthesize(request)
        self.assertEqual(error.exception.code, "EMPTY_TEXT")
