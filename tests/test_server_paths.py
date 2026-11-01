import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


SERVER_PATH = Path(__file__).resolve().parents[1] / "frontend" / "server.py"
SPEC = importlib.util.spec_from_file_location("fabuloom_server_under_test", SERVER_PATH)
SERVER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SERVER)


class ServerPathTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
