import importlib.util
from pathlib import Path
import tempfile
import unittest
import wave

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

    def test_ambiguous_duplicate_texts_do_not_redistribute_assets(self):
        existing = [
            {"id": "scene-a", "text": "igual", "image": "assets/a.png"},
            {"id": "scene-b", "text": "igual", "image": "assets/b.png"},
        ]
        result = SERVER._reconcile_scenes(existing, [Segment("novo A", 500), Segment("novo B", 500)])
        self.assertEqual([scene["id"] for scene in result], ["scene-001", "scene-002"])
        self.assertEqual([scene["image"] for scene in result], [None, None])

    def test_full_replacement_does_not_inherit_manual_configuration(self):
        existing = [
            {"id": "scene-a", "text": "antigo A", "image": "assets/a.png", "camera": "zoom"},
            {"id": "scene-b", "text": "antigo B", "image": "assets/b.png", "camera": "pan-horizontal"},
        ]
        result = SERVER._reconcile_scenes(existing, [Segment("novo A", 500), Segment("novo B", 500)])
        self.assertEqual([scene["id"] for scene in result], ["scene-001", "scene-002"])
        self.assertEqual([scene["image"] for scene in result], [None, None])
        self.assertEqual([scene["camera"] for scene in result], ["static", "static"])

    def test_timeline_audio_preserves_manifest_gap_and_tail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wav_files = []
            for index in range(2):
                path = root / f"{index}.wav"
                with wave.open(str(path), "wb") as wav:
                    wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000)
                    wav.writeframes((b"\x01\x00" if index == 0 else b"\x02\x00") * 2400)
                wav_files.append(path)
            output = root / "timeline.wav"
            duration = SERVER._build_timeline_audio(root, wav_files, {"duration_ms": 300, "segments": [
                {"start_ms": 0, "end_ms": 100}, {"start_ms": 200, "end_ms": 300}
            ]}, output)
            with wave.open(str(output), "rb") as wav:
                self.assertEqual(duration, 300)
                self.assertEqual(wav.getnframes(), 7200)
                wav.readframes(2400)
                self.assertEqual(wav.readframes(2400), b"\x00" * 4800)


if __name__ == "__main__":
    unittest.main()
