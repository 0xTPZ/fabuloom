import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Chapter1V2ContractTests(unittest.TestCase):
    def test_capture_uses_persistent_story_medallion(self):
        source = (ROOT / "frontend" / "capture-topazio-book1-chapter1-v2.html").read_text(encoding="utf-8")
        self.assertIn('narrator_visibility: "all_scenes_medallion"', source)
        self.assertIn('const narratorMode = active?.scene ? (active.scene.kind === "host" ? "host" : "story") : "story";', source)
        self.assertNotIn('Boolean(active?.scene?.kind === "host")', source)
        self.assertIn("NarratorAvatarRenderer", source)

    def test_character_registry_has_unique_ids_and_explicit_approval(self):
        payload = json.loads((ROOT / "assets" / "character-registry.json").read_text(encoding="utf-8"))
        characters = payload["characters"]
        ids = [item["id"] for item in characters]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({item["approval_status"] for item in characters}, {"APPROVED", "DRAFT"})
        self.assertEqual([item["id"] for item in characters if item["approval_status"] == "APPROVED"], ["santa-v5-base"])
        self.assertTrue(all(item["sha256"] and len(item["sha256"]) == 64 for item in characters))

    def test_v2_runner_declares_thirty_six_story_shots(self):
        source = (ROOT / "examples" / "topazio_book1_chapter1_cronicas_v2_demo.py").read_text(encoding="utf-8")
        self.assertIn('PROJECT_ID = "topazio-book1-capitulo1-cronicas-v2"', source)
        self.assertIn('SHOT_SPECS = (', source)
        self.assertIn('"shot-036-story-to-library"', source)
        self.assertIn('"all_scenes_medallion"', source)


if __name__ == "__main__":
    unittest.main()
