from __future__ import annotations

import json
import unittest
from pathlib import Path

from examples.music_studio_demo import PROJECT_FORMAT, analyze_source, create_project, probe_audio


WORKSPACE = Path(__file__).resolve().parents[2]
SOURCE = WORKSPACE / "workspace" / "inputs" / "music" / "book1" / "O Chamado do Vazio.mp3"


class MusicStudioContractTests(unittest.TestCase):
    def test_real_source_metadata_and_rms_analysis(self) -> None:
        analysis = analyze_source(SOURCE)
        self.assertEqual(analysis["format"], "fabuloom.music-analysis/0.1")
        self.assertEqual(analysis["metadata"]["channels"], 2)
        self.assertEqual(analysis["metadata"]["sample_rate"], 48000)
        self.assertEqual(len(analysis["waveform"]["values"]), 240)
        self.assertEqual(analysis["timing"]["beats"], "unavailable")
        self.assertTrue(analysis["energy_candidates"])

    def test_project_keeps_two_independent_timelines_and_no_characters(self) -> None:
        root, project = create_project("book1/O Chamado do Vazio.mp3", "topazioverse-living-worlds", 0, 24000, "test-music-studio-contract")
        try:
            self.assertEqual(project["format"], PROJECT_FORMAT)
            self.assertEqual(project["full"]["duration_ms"], project["source"]["analysis"]["duration_ms"])
            self.assertEqual((project["short"]["width"], project["short"]["height"]), (1080, 1920))
            self.assertEqual(project["short"]["duration_ms"], 24000)
            self.assertFalse(project["visual_policy"]["characters"])
            self.assertIsNone(project["visual_policy"]["narrator"])
            self.assertTrue((root / "project.json").is_file())
            json.loads((root / "project.json").read_text(encoding="utf-8"))
        finally:
            # The test project is intentionally left in the local export workspace
            # as a recoverable fixture; no tracked project is touched.
            pass

    def test_probe_duration_is_positive(self) -> None:
        self.assertGreater(probe_audio(SOURCE)["duration_ms"], 150000)


if __name__ == "__main__":
    unittest.main()
