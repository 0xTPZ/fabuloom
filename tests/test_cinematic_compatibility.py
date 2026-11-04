from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager
import shutil
import time
import unittest
import json
import uuid

from fabuloom_core.cinematic import CINEMATIC_FORMAT, CinematicCompatibility, CinematicCompatibilityError, CinematicRequest
from fabuloom_core.engine import EngineService
from fabuloom_core.mcp import dispatch_tool, tool_definitions
from fabuloom_core.paths import FabuloomPaths


@contextmanager
def _isolated_directory():
    root = Path(__file__).resolve().parents[1] / ".test-runtime-r1" / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class CinematicCompatibilityTests(unittest.TestCase):
    def test_request_contract_requires_approved_voice_and_variants(self) -> None:
        request = CinematicRequest(11, "O eco que não morre", "workspace/inputs/book1/book.docx")
        request.validate()
        with self.assertRaises(ValueError):
            CinematicRequest(11, "title", "book.docx", voice_id="pf_dora").validate()
        with self.assertRaises(ValueError):
            CinematicRequest(11, "title", "book.docx", output_variants=("square",)).validate()
        with self.assertRaises(ValueError):
            CinematicRequest(11, "title", "book.docx", output_root="   ").validate()

    def test_execute_contract_requires_storyboard_and_host_contract(self) -> None:
        request = CinematicRequest(12, "A floresta que escolhe", "book.docx", mode="execute")
        with self.assertRaisesRegex(ValueError, "scene_asset_ids"):
            request.validate()
        request = CinematicRequest(
            12,
            "A floresta que escolhe",
            "book.docx",
            mode="execute",
            scene_asset_ids=("scene-chapter4-circular-scar",),
            storyboard=({"asset_id": "scene-chapter4-circular-scar", "story_segment_start": 0, "story_segment_end": 1},),
            host_intro="Abertura do capítulo 12.",
            host_outro="Até o próximo capítulo.",
        )
        request.validate()

    def test_chapter_12_and_13_plans_are_isolated_and_parameterized(self) -> None:
        with _isolated_directory() as root:
            compatibility = CinematicCompatibility(FabuloomPaths(root), product_root=Path(__file__).resolve().parents[1])
            common = {
                "source_document": "workspace/inputs/book1/Topazio-O-Despertar-dos-Cristais.docx",
                "scene_asset_ids": ("scene-chapter4-circular-scar",),
                "storyboard": ({"asset_id": "scene-chapter4-circular-scar", "story_segment_start": 0, "story_segment_end": 1},),
                "host_intro": "Abertura parametrizada.",
                "host_outro": "Despedida parametrizada.",
            }
            chapter12 = compatibility.plan(CinematicRequest(12, "A floresta que escolhe", mode="plan", output_root=str(root / "workspace" / "exports" / "cap12"), **common))
            chapter13 = compatibility.plan(CinematicRequest(13, "O eco seguinte", mode="plan", output_root=str(root / "workspace" / "exports" / "cap13"), **common))
            self.assertEqual(chapter12["request"]["chapter"], 12)
            self.assertEqual(chapter13["request"]["chapter"], 13)
            self.assertEqual(chapter12["request"]["output_root"].split("cap")[-1], "12")
            self.assertEqual(chapter13["request"]["output_root"].split("cap")[-1], "13")
            serialized_13 = json.dumps(chapter13, ensure_ascii=False)
            self.assertNotIn("cap12", serialized_13)
            self.assertNotIn("A FLORESTA QUE ESCOLHE", serialized_13)

    def test_runner_has_no_chapter_12_fixed_literals(self) -> None:
        runner = (Path(__file__).resolve().parents[1] / "examples" / "cronicas_cinematic_production.py").read_text(encoding="utf-8")
        self.assertNotIn("chapter12", runner)
        self.assertNotIn("A FLORESTA", runner)

    def test_registered_runner_is_hash_pinned_and_request_bound(self) -> None:
        product_root = Path(__file__).resolve().parents[1]
        compatibility = CinematicCompatibility(FabuloomPaths(product_root / "test-runtime"), product_root=product_root)
        runner = compatibility._registered_runner("cronicas.chapter")
        self.assertEqual(runner["id"], "cronicas.chapter")
        self.assertEqual(len(str(runner["sha256"])), 64)
        self.assertIn("--request", json.loads((product_root / "profiles" / "registries" / "cinematic-runners.json").read_text(encoding="utf-8"))["runners"][0]["contract"])

    def test_output_root_must_be_child_of_exports(self) -> None:
        with _isolated_directory() as root:
            compatibility = CinematicCompatibility(FabuloomPaths(root), product_root=Path(__file__).resolve().parents[1])
            request = CinematicRequest(12, "A floresta que escolhe", "book.docx", mode="execute", output_root=str(root / "workspace" / "exports"))
            with self.assertRaisesRegex(CinematicCompatibilityError, "child of workspace/exports"):
                compatibility._choose_output_root(request)

    def test_audit_is_read_only_and_distinguishes_reference_from_execution(self) -> None:
        with _isolated_directory() as root:
            report = CinematicCompatibility(FabuloomPaths(root), product_root=Path(__file__).resolve().parents[1]).audit()
            self.assertEqual(report["format"], CINEMATIC_FORMAT)
            self.assertIn("legacy_pipeline", report)
            self.assertIn("reference_artifacts", report)
            self.assertFalse((root / "workspace" / "exports").exists())

    def test_shared_engine_exposes_cinematic_plan_and_mcp(self) -> None:
        with _isolated_directory() as root:
            engine = EngineService(FabuloomPaths(root))
            plan = engine.cinematic.plan(CinematicRequest(11, "O eco que não morre", "workspace/inputs/book1/book.docx"))
            self.assertEqual(plan["format"], "fabuloom.cinematic-production-plan/0.1")
            self.assertEqual(plan["request"]["runner"], "cronicas.chapter")
            self.assertIn("render.cinematic.execute", engine.capabilities()["operations"])
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
