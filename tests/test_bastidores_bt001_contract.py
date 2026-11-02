import sys
import unittest
from pathlib import Path


STUDIO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO_ROOT / "examples"))
sys.path.insert(0, str(STUDIO_ROOT / "src"))

from bastidores_bt001_demo import (  # noqa: E402
    BLOCK_RANGES,
    LANGUAGE,
    PROJECT_ID,
    SCENE_SPECS,
    SCRIPT_TEXT,
    VOICE_ID,
    build_timeline,
)


class BastidoresBt001ContractTests(unittest.TestCase):
    def _manifest(self):
        segments = []
        start = 0
        for paragraph_index in range(16):
            end = start + 1000
            segments.append(
                {
                    "id": f"bt-001-{paragraph_index:04d}",
                    "text": f"paragraph {paragraph_index}",
                    "start_ms": start,
                    "end_ms": end,
                    "audio_uri": f"E:/Fabuloom/workspace/exports/{PROJECT_ID}/audio/segments/bt-001-{paragraph_index:04d}.wav",
                    "metadata": {"paragraph_index": paragraph_index},
                }
            )
            start = end
        return {"duration_ms": start, "segments": segments}

    def test_editorial_contract_keeps_voice_and_language(self):
        self.assertEqual(VOICE_ID, "pm_santa")
        self.assertEqual(LANGUAGE, "pt-BR")
        self.assertIn("Guardião, você já se perguntou", SCRIPT_TEXT)
        self.assertIn("atlasliterario.duckdns.org", SCRIPT_TEXT)

    def test_timeline_covers_measured_narration_and_cta_tail(self):
        manifest = self._manifest()
        timeline = build_timeline(manifest)
        self.assertEqual(set(timeline["blocks"][-1]["paragraphs"]), set(BLOCK_RANGES["INVITATION"]))
        self.assertEqual(timeline["duration_ms"], manifest["duration_ms"])
        self.assertEqual(timeline["program_duration_ms"], manifest["duration_ms"] + 7000)
        self.assertEqual(timeline["scenes"][-1]["end_ms"], timeline["program_duration_ms"])
        self.assertEqual(len(timeline["scenes"]), len(SCENE_SPECS))
        self.assertEqual(timeline["portal"]["capture_status"], "verified_live_capture")

    def test_timeline_does_not_claim_word_or_phoneme_timing(self):
        timeline = build_timeline(self._manifest())
        self.assertEqual(timeline["word_phoneme_viseme_timing"], "unavailable")
        self.assertEqual(timeline["soundtrack"]["rights"], "commercial publication confirmation pending")


if __name__ == "__main__":
    unittest.main()
