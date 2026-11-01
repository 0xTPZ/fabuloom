import tempfile
import unittest
from pathlib import Path

from fabuloom_core.narration import (
    NarrationSynthesisError,
    compose_narration_manifest,
    segment_text,
    synthesize_narration,
)
from fabuloom_core.tts import SynthesisRequest, SynthesisResult, TTSError


class FakeNarrationProvider:
    provider_id = "fake"

    def __init__(self, output_dir: Path, *, fail_ordinals=None, wrong_voice_ordinal=None) -> None:
        self.output_dir = output_dir
        self.fail_ordinals = set(fail_ordinals or ())
        self.wrong_voice_ordinal = wrong_voice_ordinal
        self.calls: list[tuple[str, str, Path]] = []

    def synthesize(self, request: SynthesisRequest, output_path=None) -> SynthesisResult:
        ordinal = int(request.metadata["ordinal"])
        if ordinal in self.fail_ordinals:
            raise TTSError("SYNTHESIS_FAILED", f"fake failure for ordinal {ordinal}")
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fake wav")
        voice_id = "pm_alex" if ordinal == self.wrong_voice_ordinal else request.voice_id
        self.calls.append((request.text, voice_id, target))
        return SynthesisResult(
            request_id=request.id,
            provider_id=self.provider_id,
            voice_id=voice_id,
            language=request.language,
            audio_uri=target.resolve().as_uri(),
            duration_ms=100 + ordinal * 25,
            metadata={"timing_available": False},
        )


class NarrationTests(unittest.TestCase):
    def test_sentence_paragraph_order_and_pause_policy(self) -> None:
        segments = segment_text("Primeira frase. Segunda pergunta?\n\nNovo parágrafo!")
        self.assertEqual([segment.ordinal for segment in segments], [0, 1, 2])
        self.assertEqual(
            [segment.text for segment in segments],
            ["Primeira frase.", "Segunda pergunta?", "Novo parágrafo!"],
        )
        self.assertEqual([segment.paragraph_index for segment in segments], [0, 0, 1])
        self.assertEqual([segment.pause_after_ms for segment in segments], [180, 350, 0])
        self.assertEqual(segments[0].pause_source, "punctuation")
        self.assertEqual(segments[1].pause_source, "paragraph_boundary")

    def test_long_text_is_split_without_exceeding_engine_budget(self) -> None:
        text = " ".join(["palavra"] * 30) + "."
        segments = segment_text(text, max_chars=40)
        self.assertGreater(len(segments), 1)
        self.assertTrue(all(len(segment.text) <= 40 for segment in segments))
        self.assertEqual([segment.ordinal for segment in segments], list(range(len(segments))))
        self.assertEqual(segments[-1].terminal_kind, "period")

    def test_common_abbreviation_does_not_break_sentence_order(self) -> None:
        segments = segment_text("A Dra. Lia chegou. Depois, a ponte brilhou.")
        self.assertEqual([segment.text for segment in segments], [
            "A Dra. Lia chegou.",
            "Depois, a ponte brilhou.",
        ])

    def test_manifest_uses_measured_durations_and_explicit_pauses(self) -> None:
        source = segment_text("A. B.")
        results = [
            SynthesisResult("request-a", "kokoro", "pf_dora", "pt-BR", "file:///a.wav", 100),
            SynthesisResult("request-b", "kokoro", "pf_dora", "pt-BR", "file:///b.wav", 200),
        ]
        manifest = compose_narration_manifest(
            source,
            results,
            manifest_id="manifest-test",
            timeline_id="timeline-test",
        )
        self.assertEqual([(item.start_ms, item.end_ms) for item in manifest.segments], [(0, 100), (280, 480)])
        self.assertEqual(manifest.duration_ms, 480)
        self.assertEqual(manifest.segments[0].metadata["temporal_source"], "measured_wav")
        self.assertEqual(manifest.segments[0].metadata["pause_after_ms"], 180)

    def test_synthesis_preserves_voice_order_and_output_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = FakeNarrationProvider(Path(directory))
            run = synthesize_narration(
                provider,
                "A. B. C.",
                narration_id="story-demo",
                voice_id="pf_dora",
            )
            self.assertEqual(run.status, "completed")
            self.assertEqual([call[1] for call in provider.calls], ["pf_dora"] * 3)
            self.assertEqual([call[2].name for call in provider.calls], [
                "story-demo-0000.wav",
                "story-demo-0001.wav",
                "story-demo-0002.wav",
            ])
            self.assertEqual([segment.start_ms for segment in run.manifest.segments], [0, 280, 585])

    def test_inconsistent_voice_is_reported_with_completed_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = FakeNarrationProvider(Path(directory), wrong_voice_ordinal=1)
            with self.assertRaises(NarrationSynthesisError) as context:
                synthesize_narration(
                    provider,
                    "A. B.",
                    narration_id="story-voice-check",
                    voice_id="pf_dora",
                )
            self.assertEqual(context.exception.failure.error_code, "INCONSISTENT_VOICE")
            self.assertEqual(len(context.exception.completed_results), 1)

    def test_continue_on_error_marks_partial_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = FakeNarrationProvider(Path(directory), fail_ordinals={1})
            run = synthesize_narration(
                provider,
                "A. B. C.",
                narration_id="story-partial",
                voice_id="pf_dora",
                continue_on_error=True,
            )
            self.assertEqual(run.status, "partial")
            self.assertEqual(len(run.failures), 1)
            self.assertEqual(run.manifest.metadata["failed_segment_ids"], [run.failures[0].segment_id])
            self.assertEqual(len(run.manifest.segments), 2)
