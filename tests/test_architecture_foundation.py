from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from fabuloom_core.asset_catalog import AssetCatalog
from fabuloom_core.engine import EngineService
from fabuloom_core.migration import LibraryMigration
from fabuloom_core.mcp import dispatch_tool, handle_message, tool_definitions
from fabuloom_core.paths import FabuloomPaths, PathConfigurationError
from fabuloom_core.production import ProductionError, ProductionService
from fabuloom_core.plugins import PluginRegistry
from fabuloom_core.project_store import ProjectConflict


class ArchitectureFoundationTests(unittest.TestCase):
    def test_paths_are_configurable_and_contained(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = FabuloomPaths(Path(directory))
            self.assertEqual(paths.resolve_workspace_path("projects/demo"), Path(directory).resolve() / "workspace" / "projects" / "demo")
            with self.assertRaises(PathConfigurationError):
                paths.resolve_workspace_path("../outside")

    def test_project_store_uses_revisions_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = EngineService(FabuloomPaths(Path(directory)))
            project = engine.create_project("Generic demo", project_id="generic-demo")
            updated = engine.update_project("generic-demo", {"name": "Generic demo", "metadata": {"kind": "redistributable"}}, expected_revision=project["revision"])
            self.assertEqual(updated["revision"], 2)
            self.assertGreaterEqual(len(updated["history"]), 2)
            with self.assertRaises(ProjectConflict):
                engine.update_project("generic-demo", {"name": "stale"}, expected_revision=1)

    def test_catalog_indexes_without_copying_assets_and_reports_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "library"
            root.mkdir()
            (root / "a.txt").write_text("same", encoding="utf-8")
            (root / "b.txt").write_text("same", encoding="utf-8")
            catalog = AssetCatalog(root, Path(directory) / "catalog.sqlite3")
            records = catalog.scan(category="test", origin="generated", rights_status="clear")
            self.assertEqual(len(records), 2)
            self.assertTrue(catalog.database_path.is_file())
            self.assertEqual(len(catalog.duplicate_groups()), 1)
            self.assertEqual(catalog.search("a")[0]["relative_path"], "a.txt")
            self.assertEqual(catalog.get(records[0].stable_id)["relative_path"], records[0].relative_path)

    def test_plugins_are_discovered_but_activation_is_explicit(self) -> None:
        root = Path(__file__).resolve().parents[1] / "plugins"
        registry = PluginRegistry(root)
        manifests = registry.enabled()
        self.assertEqual({manifest.id for manifest in manifests}, {"fabuloom.export.ffmpeg", "fabuloom.tts.simulated"})
        plan = registry.activation_plan("fabuloom.export.ffmpeg")
        self.assertEqual(plan["execution"], "explicit-only")
        self.assertTrue(plan["trusted"])

    def test_job_state_is_persistent_and_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = EngineService(FabuloomPaths(Path(directory)))
            project = engine.create_project("Job demo", project_id="job-demo")
            job = engine.create_job("validate-project", {"project_id": project["id"]})
            deadline = time.monotonic() + 2
            current = engine.get_job(job["id"])
            while current["state"] in {"queued", "running"} and time.monotonic() < deadline:
                time.sleep(0.02)
                current = engine.get_job(job["id"])
            self.assertEqual(current["state"], "completed")
            self.assertTrue(current["result"]["valid"])
            self.assertTrue((Path(directory) / "workspace" / "jobs" / f"{job['id']}.json").is_file())

    def test_mcp_adapter_delegates_to_shared_engine(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = EngineService(FabuloomPaths(Path(directory)))
            project = dispatch_tool(engine, "fabuloom_project_create", {"name": "MCP project", "project_id": "mcp-project"})
            self.assertEqual(project["id"], "mcp-project")
            response = handle_message(engine, {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "fabuloom_projects_list", "arguments": {}}})
            self.assertEqual(response["result"]["structuredContent"]["projects"][0]["id"], "mcp-project")
            self.assertIn("fabuloom_project_update", {tool["name"] for tool in tool_definitions()})
            self.assertIn("fabuloom_render_demo", {tool["name"] for tool in tool_definitions()})

    def test_capabilities_profiles_and_storage_doctor_are_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = EngineService(FabuloomPaths(Path(directory)))
            self.assertEqual(engine.capabilities()["format"], "fabuloom.capabilities/0.1")
            self.assertIn("render.demo", engine.capabilities()["operations"])
            self.assertIn("audio.mix", engine.capabilities()["operations"])
            self.assertEqual({item["id"] for item in engine.list_profiles()}, {"cinematic-chapter", "cinematic-short", "music-visualizer", "cinematic-trailer"})
            self.assertIn("storage", engine.doctor())
            self.assertEqual(ProductionService(FabuloomPaths(Path(directory))).dry_run()["format"], "fabuloom.render-plan/0.1")

    def test_export_modes_distinguish_economy_and_real_canvas_capture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = ProductionService(FabuloomPaths(Path(directory)))
            profile = service.profiles.get("cinematic-short")
            economy = service._export_settings(profile, {})
            real = service._export_settings(profile, {"capture_fps": 30, "output_fps": 30, "audio_sample_rate": 48000, "audio_channels": 2})
            self.assertEqual(economy["capture_quality"], "economy")
            self.assertEqual(economy["capture_fps"], 5)
            self.assertEqual(economy["audio_sample_rate"], 48000)
            self.assertEqual(real["capture_quality"], "real_canvas_capture")
            self.assertEqual(real["capture_fps"], 30)
            with self.assertRaises(ProductionError):
                service._export_settings(profile, {"capture_fps": True})

    def test_runtime_root_refuses_environment_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            active = Path(directory) / "active"
            configured = Path(directory) / "configured"
            paths = FabuloomPaths(active)
            with patch.dict(os.environ, {"FABULOOM_ROOT": str(configured)}):
                with self.assertRaises(PathConfigurationError):
                    paths.validate_runtime_root()
                doctor = EngineService(paths).doctor()
                self.assertEqual(doctor["status"], "blocked")
                self.assertIn("validation_error", doctor["storage"])

    def test_library_migration_is_checkpointed_reversible_and_preserves_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "legacy"; target = root / "private" / "library"; checkpoints = root / "workspace" / "migrations"
            source.mkdir(parents=True)
            original = source / "scene.txt"; original.write_text("approved", encoding="utf-8")
            migration = LibraryMigration(source, target, checkpoints)
            plan = migration.create_plan("test-migration")
            self.assertEqual(migration.simulate(plan)["files"], 1)
            result = migration.execute(plan)
            self.assertEqual(result["status"], "completed")
            self.assertEqual((target / "scene.txt").read_text(encoding="utf-8"), "approved")
            self.assertTrue(original.is_file())
            self.assertEqual(migration.rollback(plan)["removed"], 1)
            self.assertFalse((target / "scene.txt").exists())

    def test_catalog_rescan_preserves_editorial_and_rights_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "library"; root.mkdir()
            asset = root / "scene.txt"; asset.write_text("v1", encoding="utf-8")
            catalog = AssetCatalog(root, Path(directory) / "catalog.sqlite3")
            catalog.scan(category="environment", origin="owner", rights_status="confirmed", approval_status="APPROVED")
            connection = catalog.connect()
            try:
                connection.execute("UPDATE assets SET tags_json = ?, project_refs_json = ?", ('["hero"]', '["book-1"]'))
                connection.commit()
            finally:
                connection.close()
            catalog.scan(category="unclassified", origin="rescan", rights_status="review_required", approval_status="unreviewed")
            record = catalog.search("scene")[0]
            self.assertEqual(record["tags"], ["hero"])
            self.assertEqual(record["project_refs"], ["book-1"])
            self.assertEqual(record["approval_status"], "APPROVED")
            self.assertEqual(record["rights_status"], "confirmed")


if __name__ == "__main__":
    unittest.main()
