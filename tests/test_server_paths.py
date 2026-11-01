import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import base64
import json


SERVER_PATH = Path(__file__).resolve().parents[1] / "frontend" / "server.py"
SPEC = importlib.util.spec_from_file_location("fabuloom_server_under_test", SERVER_PATH)
SERVER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SERVER)


class ServerPathTests(unittest.TestCase):
    def test_character_pack_installation_is_contained_and_rejects_active_svg(self):
        with TemporaryDirectory() as directory:
            previous = SERVER.PACKS_ROOT
            SERVER.PACKS_ROOT = Path(directory) / "packs"
            try:
                svg = base64.b64encode(b'<svg><script>alert(1)</script></svg>').decode()
                manifest = {"id": "demo", "version": "1.0", "pack": {"id": "demo", "layers": [{"asset": "face.svg"}]}}
                with self.assertRaises(ValueError):
                    SERVER._install_character_pack({"manifest": manifest, "files": [{"path": "face.svg", "mime": "image/svg+xml", "data": svg}]})
                safe = base64.b64encode(b'<svg viewBox="0 0 1 1"></svg>').decode()
                manifest["pack"]["license"] = "MIT"
                result = SERVER._install_character_pack({"manifest": manifest, "files": [{"path": "face.svg", "mime": "image/svg+xml", "data": safe}]})
                self.assertEqual(result["ref"], "demo@1.0")
                self.assertTrue((SERVER.PACKS_ROOT / "demo" / "1.0" / "face.svg").is_file())
                with self.assertRaises(ValueError):
                    SERVER._install_character_pack({"manifest": {"id": "demo2", "version": "1.0", "pack": {"id": "demo2"}}, "files": [{"path": "../escape.svg", "mime": "image/svg+xml", "data": safe}]})
            finally:
                SERVER.PACKS_ROOT = previous

    def test_project_character_pack_reference_survives_save_and_reload(self):
        with TemporaryDirectory() as directory:
            previous = SERVER.PROJECTS_ROOT
            SERVER.PROJECTS_ROOT = Path(directory) / "projects"
            try:
                project = {"id": "project-demo", "title": "Demo", "scenes": [], "character_pack": {"id": "community-demo-geometric-v1", "version": "1.0.0", "contract": "fabuloom.character/0.1", "character_id": "community-demo-geometric-v1", "expression": "smile", "asset_ref": "community-demo-geometric-v1@1.0.0"}}
                SERVER._save_project(project)
                restored = SERVER._load_project("project-demo")
                self.assertEqual(restored["character_pack"]["expression"], "smile")
                self.assertNotIn("C:", json.dumps(restored))
            finally:
                SERVER.PROJECTS_ROOT = previous

    def test_scene_validation_accepts_supported_camera_and_rejects_unknown(self):
        SERVER._validate_scenes([{"id": "scene-001", "duration_ms": 1000, "camera": "zoom", "transition": "cut", "image": "assets/a.png"}])
        with self.assertRaises(ValueError):
            SERVER._validate_scenes([{"id": "scene-001", "duration_ms": 1000, "camera": "orbit", "transition": "cut"}])

    def test_scene_validation_rejects_absolute_image_paths_and_duplicate_ids(self):
        with self.assertRaises(ValueError):
            SERVER._validate_scenes([{"id": "scene-001", "duration_ms": 1000, "image": "C:/private/image.png"}])
        with self.assertRaises(ValueError):
            SERVER._validate_scenes([{"id": "scene-001", "duration_ms": 1000}, {"id": "scene-001", "duration_ms": 1000}])

    def test_default_workspace_uses_checkout_when_no_umbrella_workspace_exists(self):
        with TemporaryDirectory() as directory:
            frontend_root = Path(directory) / "checkout" / "frontend"
            frontend_root.mkdir(parents=True)
            self.assertEqual(SERVER.workspace_root_for(frontend_root), frontend_root.parent.resolve())

    def test_default_workspace_keeps_existing_umbrella_layout(self):
        with TemporaryDirectory() as directory:
            umbrella = Path(directory) / "umbrella"
            frontend_root = umbrella / "studio" / "frontend"
            (umbrella / "workspace").mkdir(parents=True)
            frontend_root.mkdir(parents=True)
            self.assertEqual(SERVER.workspace_root_for(frontend_root), umbrella.resolve())

    def test_explicit_export_root_must_stay_inside_workspace(self):
        with TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            self.assertEqual(
                SERVER.export_root_for(workspace, str(workspace / "exports")),
                (workspace / "exports").resolve(),
            )
            with self.assertRaises(SystemExit):
                SERVER.export_root_for(workspace, str(Path(directory) / "outside"))

    def test_environment_health_exposes_guided_states_without_importing_kokoro_runtime(self):
        health = SERVER._environment_health()
        for key in ("python_state", "ffmpeg_state", "ffprobe_state", "kokoro_state", "model_state", "voice", "writable_state", "workspace"):
            self.assertIn(key, health)
        self.assertIn(health["python_state"], {"PRONTO", "ERRO"})
        self.assertIn(health["voice"], {"PRONTO", "CONFIGURAÇÃO NECESSÁRIA", "ERRO", "VERIFICAÇÃO NECESSÁRIA"})

    def test_environment_health_respects_isolated_huggingface_home(self):
        previous = os.environ.get("HF_HOME")
        try:
            os.environ["HF_HOME"] = str(Path(__file__).parent / "fixtures" / "empty-huggingface-cache")
            self.assertFalse(SERVER._environment_health()["model"])
        finally:
            if previous is None:
                os.environ.pop("HF_HOME", None)
            else:
                os.environ["HF_HOME"] = previous


if __name__ == "__main__":
    unittest.main()
