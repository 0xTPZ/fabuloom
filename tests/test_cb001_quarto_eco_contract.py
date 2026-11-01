from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import unittest


STUDIO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = STUDIO_ROOT / "examples" / "cronicas_breves_cb001_quarto_eco_demo.py"
PROJECT_ROOT = Path(r"E:\Fabuloom\workspace\exports\cronicas-breves\cb-001-o-quarto-eco")
EXPECTED_TEXT_SHA256 = "5fd0771e74fe34cc8214ef0e4ff2d65d3429b4b67b1968c80dd4c72c66f5f014"
EXPECTED_MUSIC_SHA256 = "89FD1D0630584A899991626AC2431C432012257851B7EFB4DA83DA8380CA8DC9"


class CB001ContractTests(unittest.TestCase):
    def test_script_contains_exact_editorial_text(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        match = re.search(r'STORY_TEXT = """(.*?)"""', source, re.DOTALL)
        self.assertIsNotNone(match)
        story_text = match.group(1).replace('\\"', '"').strip()
        self.assertEqual(hashlib.sha256(story_text.encode("utf-8")).hexdigest(), EXPECTED_TEXT_SHA256)
        self.assertIn("Então surgiu um quarto.", story_text)
        self.assertIn('"Eu nunca esqueci."', story_text)
        self.assertIn("Crônicas de Topázio no YouTube.", story_text)

    def test_public_script_declares_santa_and_environment_only_policy(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('VOICE_ID = "pm_santa"', source)
        self.assertIn('LANGUAGE = "pt-BR"', source)
        self.assertIn('"draft_character_rendering": "blocked"', source)
        self.assertIn('"story_visual_policy": "environment_only"', source)
        self.assertIn("santa-library-topazioverse-v1", source)

    def test_generated_artifact_contract_when_export_exists(self) -> None:
        report_path = PROJECT_ROOT / "reports" / "technical-report.json"
        if not report_path.is_file():
            self.skipTest("CB-001 media is generated outside a clean source checkout")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["duration_ms"], 59480)
        self.assertEqual(report["segments"], 18)
        self.assertEqual(report["probe"]["streams"][0]["width"], 1080)
        self.assertEqual(report["probe"]["streams"][0]["height"], 1920)
        self.assertEqual(report["probe"]["streams"][1]["codec_name"], "aac")
        self.assertEqual(report["probe"]["streams"][1]["channels"], 2)
        self.assertEqual(report["source_music"]["sha256"], EXPECTED_MUSIC_SHA256)
        self.assertTrue(report["validation"]["duration_coherent"])
        self.assertTrue(report["validation"]["ffmpeg_decode"])
        self.assertTrue(report["validation"]["blackdetect"]["passed"])
        self.assertTrue(report["validation"]["subtitle_sync"])
        self.assertEqual(report["validation"]["draft_characters"], "blocked")


if __name__ == "__main__":
    unittest.main()
