import tempfile
import unittest
import wave
from pathlib import Path

from fabuloom_core.kokoro import (
    PT_BR_VOICES,
    KokoroTTSProvider,
    WavInfo,
    _inspect_wav,
)
from fabuloom_core.tts import SynthesisParameters, SynthesisRequest, TTSError


class FakePipeline:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, float]] = []
        self.closed = False

    def __call__(self, text: str, *, voice: str, speed: float):
        self.calls.append((text, voice, speed))
        return [FakeResult([0.0, 0.1, -0.1])]

    def close(self) -> None:
        self.closed = True


class FakeResult:
    def __init__(self, audio) -> None:
        self.audio = audio


def write_fake_wav(path: Path, chunks) -> WavInfo:
    list(chunks)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24_000)
        output.writeframes(b"\x00\x00" * 2_400)
    return WavInfo(sample_rate=24_000, channels=1, sample_width=2, frames=2_400, duration_ms=100)


def make_request(**overrides) -> SynthesisRequest:
    values = {
        "id": "kokoro-test-001",
        "text": "Uma história curta.",
        "voice_id": "pf_dora",
        "language": "pt-BR",
    }
    values.update(overrides)
    return SynthesisRequest(**values)


class KokoroProviderTests(unittest.TestCase):
    def test_lists_pt_br_voices_and_rejects_other_languages(self) -> None:
        provider = KokoroTTSProvider()
        self.assertEqual(provider.list_voices(), PT_BR_VOICES)
        with self.assertRaises(TTSError) as context:
            provider.list_voices("en-US")
        self.assertEqual(context.exception.code, "UNSUPPORTED_LANGUAGE")

    def test_empty_text_is_rejected_before_model_initialization(self) -> None:
        factory_called = False

        def factory(**_kwargs):
            nonlocal factory_called
            factory_called = True
            return FakePipeline()

        provider = KokoroTTSProvider(pipeline_factory=factory, audio_writer=write_fake_wav)
        with self.assertRaises(TTSError) as context:
            provider.synthesize(make_request(text=""))
        self.assertEqual(context.exception.code, "EMPTY_TEXT")
        self.assertFalse(factory_called)

    def test_initialization_failure_has_stable_error_code(self) -> None:
        def factory(**_kwargs):
            raise RuntimeError("test-only initialization failure")

        provider = KokoroTTSProvider(pipeline_factory=factory)
        with self.assertRaises(TTSError) as context:
            provider.initialize()
        self.assertEqual(context.exception.code, "INITIALIZATION_FAILED")
        self.assertFalse(provider.initialized)

    def test_model_is_reused_and_result_contains_measured_wav_metadata(self) -> None:
        pipeline = FakePipeline()
        factory_calls = 0

        def factory(**kwargs):
            nonlocal factory_calls
            factory_calls += 1
            self.assertEqual(kwargs, {"lang_code": "p"})
            return pipeline

        with tempfile.TemporaryDirectory() as directory:
            provider = KokoroTTSProvider(
                output_dir=directory,
                pipeline_factory=factory,
                audio_writer=write_fake_wav,
            )
            first = provider.synthesize(make_request(), "first.wav")
            second = provider.synthesize(make_request(id="kokoro-test-002"), "second.wav")

            self.assertEqual(factory_calls, 1)
            self.assertEqual(provider.model_load_count, 1)
            self.assertEqual(len(pipeline.calls), 2)
            self.assertEqual(pipeline.calls[0][1:], ("pf_dora", 1.0))
            self.assertEqual(first.duration_ms, 100)
            self.assertEqual(second.metadata["sample_rate"], 24_000)
            self.assertFalse(second.metadata["timing_available"])
            self.assertEqual(second.word_timings, [])
            self.assertIsNotNone(second.metadata["model_load_seconds"])
            self.assertIsNotNone(second.metadata["synthesis_seconds"])

            with wave.open(str(Path(directory) / "first.wav"), "rb") as output:
                self.assertEqual(output.getframerate(), 24_000)
                self.assertEqual(output.getnframes(), 2_400)

            provider.close()
            self.assertTrue(pipeline.closed)
            self.assertFalse(provider.initialized)

    def test_unsupported_voice_and_provider_parameters_are_rejected(self) -> None:
        provider = KokoroTTSProvider()
        for request, code in (
            (make_request(voice_id="unknown"), "UNSUPPORTED_VOICE"),
            (make_request(parameters=SynthesisParameters(pitch=1.0)), "UNSUPPORTED_PARAMETER"),
            (make_request(parameters=SynthesisParameters(volume=0.5)), "UNSUPPORTED_PARAMETER"),
            (make_request(parameters=SynthesisParameters(extras={"seed": 1})), "UNSUPPORTED_PARAMETER"),
        ):
            with self.subTest(code=code):
                with self.assertRaises(TTSError) as context:
                    provider.synthesize(request)
                self.assertEqual(context.exception.code, code)

    def test_output_path_must_be_wav_inside_export_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = KokoroTTSProvider(output_dir=directory, pipeline_factory=lambda **_: FakePipeline())
            outside = str(Path(directory).parent / "outside.wav")
            for output_path in (outside, "invalid.mp3"):
                with self.subTest(output_path=output_path):
                    with self.assertRaises(TTSError) as context:
                        provider.synthesize(make_request(), output_path)
                    self.assertEqual(context.exception.code, "INVALID_OUTPUT_PATH")

    def test_invalid_wav_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.wav"
            path.write_bytes(b"not a wav")
            with self.assertRaises(TTSError) as context:
                _inspect_wav(path)
            self.assertEqual(context.exception.code, "INVALID_AUDIO")


if __name__ == "__main__":
    unittest.main()
