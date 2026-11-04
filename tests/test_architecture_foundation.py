from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import unittest

from fabuloom_core.asset_catalog import AssetCatalog
from fabuloom_core.engine import EngineService
from fabuloom_core.mcp import dispatch_tool, handle_message, tool_definitions
from fabuloom_core.paths import FabuloomPaths, PathConfigurationError
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


if __name__ == "__main__":
    unittest.main()
