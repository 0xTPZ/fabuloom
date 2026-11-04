from __future__ import annotations

from pathlib import Path
import tempfile
import time
import unittest

from fabuloom_core.cinematic import CINEMATIC_FORMAT, CinematicCompatibility, CinematicRequest
from fabuloom_core.engine import EngineService
from fabuloom_core.mcp import dispatch_tool, tool_definitions
from fabuloom_core.paths import FabuloomPaths


class CinematicCompatibilityTests(unittest.TestCase):
    def test_request_contract_requires_approved_voice_and_variants(self) -> None:
        request = CinematicRequest(11, "O eco que não morre", "workspace/inputs/book1/book.docx")
        request.validate()
        with self.assertRaises(ValueError):
            CinematicRequest(11, "title", "book.docx", voice_id="pf_dora").validate()
        with self.assertRaises(ValueError):
            CinematicRequest(11, "title", "book.docx", output_variants=("square",)).validate()

    def test_audit_is_read_only_and_distinguishes_reference_from_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = CinematicCompatibility(FabuloomPaths(root), product_root=Path(__file__).resolve().parents[1]).audit()
            self.assertEqual(report["format"], CINEMATIC_FORMAT)
            self.assertIn("legacy_pipeline", report)
            self.assertIn("reference_artifacts", report)
            self.assertFalse((root / "workspace" / "exports").exists())

    def test_shared_engine_exposes_cinematic_plan_and_mcp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = EngineService(FabuloomPaths(Path(directory)))
            plan = engine.cinematic.plan(CinematicRequest(11, "O eco que não morre", "workspace/inputs/book1/book.docx"))
            self.assertEqual(plan["format"], "fabuloom.cinematic-production-plan/0.1")
            job = engine.create_job("render-cinematic", {"mode": "plan", "chapter": 11, "chapter_title": "O eco que não morre"})
            deadline = time.monotonic() + 2
            current = engine.get_job(job["id"])
            while current["state"] in {"queued", "running"} and time.monotonic() < deadline:
                time.sleep(0.02)
                current = engine.get_job(job["id"])
            self.assertEqual(current["state"], "completed")
            self.assertIn("fabuloom_cinematic_diagnose", {tool["name"] for tool in tool_definitions()})
            self.assertEqual(dispatch_tool(engine, "fabuloom_cinematic_diagnose")["format"], CINEMATIC_FORMAT)


if __name__ == "__main__":
    unittest.main()
