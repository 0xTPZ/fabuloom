import os
from pathlib import Path
import unittest
import wave

from fabuloom_core.kokoro import KokoroTTSProvider
from fabuloom_core.tts import SynthesisRequest


@unittest.skipUnless(
    os.environ.get("FABULOOM_RUN_KOKORO_REAL") == "1",
    "set FABULOOM_RUN_KOKORO_REAL=1 to run the local Kokoro integration test",
)
class RealKokoroIntegrationTests(unittest.TestCase):
    def test_pt_br_voice_produces_a_valid_wav(self) -> None:
        output_dir = Path(r"E:\Fabuloom\workspace\exports")
        output_path = output_dir / "kokoro-integration-test.wav"
        provider = KokoroTTSProvider(output_dir=output_dir)
        try:
            result = provider.synthesize(
                SynthesisRequest(
                    id="kokoro-real-integration",
                    text="Esta é uma verificação local do provedor Kokoro.",
                    voice_id="pf_dora",
                    language="pt-BR",
                ),
                output_path,
            )
            self.assertTrue(output_path.is_file())
            self.assertGreater(result.duration_ms, 0)
            with wave.open(str(output_path), "rb") as output:
                self.assertEqual(output.getframerate(), 24_000)
                self.assertGreater(output.getnframes(), 0)
        finally:
            provider.close()
