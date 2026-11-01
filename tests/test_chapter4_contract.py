import hashlib
import json
from pathlib import Path
import unittest
import wave

from fabuloom_core.character_registry import CharacterRegistry, CharacterRegistryError
from topazio_book1_chapter4_cronicas_demo import SOURCE_DOC, load_chapter4


PROJECT_ROOT = Path(r"E:\Fabuloom\workspace\exports\topazio-book1-capitulo4-cronicas")
REGISTRY = Path(__file__).resolve().parents[1] / "assets" / "character-registry.json"


class Chapter4ContractTests(unittest.TestCase):
    def test_docx_boundaries_are_chapter_four_only(self):
        paragraphs, text, metadata = load_chapter4(SOURCE_DOC)
        self.assertEqual(metadata["title"], "Capítulo 4 — O círculo dos ausentes")
        self.assertEqual(metadata["heading_paragraph"], 107)
        self.assertEqual(metadata["first_narrative_paragraph"], 108)
        self.assertEqual(metadata["last_narrative_paragraph"], 178)
        self.assertEqual(metadata["end_separator_paragraph"], 179)
        self.assertEqual(metadata["next_chapter_heading_paragraph"], 180)
        self.assertEqual(metadata["raw_paragraph_count"], 72)
        self.assertEqual(metadata["paragraph_count"], 71)
        self.assertEqual(metadata["word_count"], 1026)
        self.assertEqual(metadata["text_characters"], 5913)
        self.assertEqual(metadata["text_sha256"], hashlib.sha256(text.encode("utf-8")).hexdigest())
        self.assertEqual(len(paragraphs), 71)

    def test_only_approved_santa_can_be_production_selected(self):
        registry = CharacterRegistry.from_json(REGISTRY, workspace_root=Path(r"E:\Fabuloom"))
        self.assertEqual(registry.require_approved("santa-v5-base").approval_status, "APPROVED")
        for character_id in registry.ids():
            if character_id != "santa-v5-base":
                with self.subTest(character_id=character_id):
                    with self.assertRaises(CharacterRegistryError):
                        registry.require_approved(character_id)

    def test_completed_timeline_blocks_unapproved_assets(self):
        timeline_path = PROJECT_ROOT / "timeline" / "topazio-book1-capitulo4-cronicas.json"
        manifest_path = PROJECT_ROOT / "manifest.json"
        if not timeline_path.is_file() or not manifest_path.is_file():
            self.skipTest("Mission 029 export is not present")
        timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(timeline["source_paragraphs"], list(range(108, 179)))
        self.assertEqual(timeline["source_paragraph_end_separator"], 179)
        self.assertEqual(timeline["next_chapter_heading_paragraph"], 180)
        self.assertEqual(timeline["voice_id"], "pm_santa")
        self.assertTrue(timeline["character_policy"]["approved_only"])
        self.assertEqual(timeline["character_policy"]["draft_rendering"], "blocked")
        for scene in timeline["scenes"]:
            self.assertEqual(scene["character_registry_id"], "santa-v5-base")
            if scene["kind"] == "story":
                self.assertTrue(scene["environment_only"])
                self.assertNotIn("draft", scene["image"].lower())
        self.assertEqual(manifest["duration_ms"], timeline["duration_ms"])
        self.assertEqual(manifest["metadata"]["source_paragraphs"], list(range(108, 179)))
        self.assertTrue((PROJECT_ROOT / "timeline" / "topazio-book1-capitulo4-cronicas.srt").is_file())
        self.assertTrue((PROJECT_ROOT / "metadata" / "youtube-metadata.json").is_file())

    def test_measured_wavs_match_manifest_when_export_exists(self):
        manifest_path = PROJECT_ROOT / "manifest.json"
        if not manifest_path.is_file():
            self.skipTest("Mission 029 manifest is not present")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for segment in manifest["segments"]:
            uri = segment["audio_uri"]
            self.assertTrue(uri.startswith("file:///"))
            wav_path = Path(uri.removeprefix("file:///"))
            with wave.open(str(wav_path), "rb") as wav:
                measured = round(wav.getnframes() * 1000 / wav.getframerate())
            self.assertAlmostEqual(measured, segment["duration_ms"], delta=1)


if __name__ == "__main__":
    unittest.main()
