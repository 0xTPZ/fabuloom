import importlib.util
from pathlib import Path
import unittest

SERVER_PATH = Path(__file__).resolve().parents[1] / "frontend" / "server.py"
SPEC = importlib.util.spec_from_file_location("fabuloom_server_reconcile", SERVER_PATH)
SERVER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SERVER)


class Segment:
    def __init__(self, text, end_ms, start_ms=0):
        self.text = text
        self.start_ms = start_ms
        self.end_ms = end_ms


class SceneReconciliationTests(unittest.TestCase):
    def test_regeneration_preserves_identity_assets_and_manual_camera(self):
        existing = [{"id": "scene-001", "title": "Estrela", "text": "antigo", "image": "assets/star.png", "duration_ms": 4100, "camera": "zoom", "transition": "cut"}]
        result = SERVER._reconcile_scenes(existing, [Segment("novo", 900)])
        self.assertEqual(result[0]["id"], "scene-001")
        self.assertEqual(result[0]["image"], "assets/star.png")
        self.assertEqual(result[0]["duration_ms"], 4100)
        self.assertEqual(result[0]["camera"], "zoom")
        self.assertEqual(result[0]["text"], "novo")

    def test_new_segments_get_stable_scene_ids_without_using_manifest_ids(self):
        result = SERVER._reconcile_scenes([], [Segment("um", 500), Segment("dois", 1000)])
        self.assertEqual([scene["id"] for scene in result], ["scene-001", "scene-002"])


if __name__ == "__main__":
    unittest.main()
