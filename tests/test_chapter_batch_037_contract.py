import hashlib
import unittest
from pathlib import Path

from topazio_book1_chapters_05_10_batch import (
    CHAPTER_PLANS,
    SOURCE_DOC,
    _host_texts,
    preflight_source,
)


class ChapterBatch037ContractTests(unittest.TestCase):
    def test_docx_has_exact_non_overlapping_boundaries_for_05_to_10(self):
        batch = preflight_source(SOURCE_DOC)
        self.assertEqual(set(batch["chapters"]), set(range(5, 11)))
        self.assertEqual(len(batch["source_doc_sha256"]), 64)
        previous_end = None
        for number in range(5, 11):
            chapter = batch["chapters"][number]
            self.assertGreater(chapter["paragraph_count"], 0)
            self.assertEqual(chapter["text_sha256"], hashlib.sha256(chapter["text"].encode("utf-8")).hexdigest())
            if previous_end is not None:
                self.assertGreaterEqual(chapter["heading_paragraph"], previous_end)
            previous_end = chapter["next_chapter_heading_paragraph"]

    def test_each_chapter_uses_twenty_environment_only_shots(self):
        self.assertEqual(set(CHAPTER_PLANS), set(range(5, 11)))
        for number, plan in CHAPTER_PLANS.items():
            with self.subTest(chapter=number):
                self.assertEqual(len(plan), 20)
                self.assertTrue(all(key.startswith(("c1:", "c1v2:", "c2:", "c3:", "c4:")) for key, _ in plan))

    def test_host_opening_and_closing_are_library_dialogue(self):
        intro, outro = _host_texts(5, "Capítulo 5 — O mapa sob a pele")
        self.assertIn("Saudações, Guardiões!", intro)
        self.assertIn("Capítulo 5", intro)
        self.assertIn("Guardiões", outro)
        self.assertIn("O mapa sob a pele", outro)


if __name__ == "__main__":
    unittest.main()
