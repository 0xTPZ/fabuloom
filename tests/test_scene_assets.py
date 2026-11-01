import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fabuloom_core.scene_assets import SceneAssetError, SceneAssetNotFound, SceneAssetRegistry


class SceneAssetRegistryTests(unittest.TestCase):
    def test_loads_stable_id_and_verifies_hash(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            asset = root / "plate.png"
            asset.write_bytes(b"plate")
            import hashlib
            registry_path = root / "registry.json"
            registry_path.write_text(json.dumps({
                "format": "fabuloom.scene-asset-registry/0.1",
                "format_version": "0.1.0",
                "assets": [{
                    "id": "demo-plate",
                    "version": "1.0.0",
                    "relative_path": "plate.png",
                    "sha256": hashlib.sha256(b"plate").hexdigest(),
                }],
            }), encoding="utf-8")
            registry = SceneAssetRegistry.from_json(registry_path, workspace_root=root)
            self.assertEqual(registry.resolve("demo-plate"), asset.resolve())
            self.assertEqual(registry.ids(), ("demo-plate",))

    def test_missing_id_is_clear(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            registry_path = root / "registry.json"
            registry_path.write_text(json.dumps({
                "format": "fabuloom.scene-asset-registry/0.1",
                "format_version": "0.1.0",
                "assets": [],
            }), encoding="utf-8")
            registry = SceneAssetRegistry.from_json(registry_path, workspace_root=root)
            with self.assertRaisesRegex(SceneAssetNotFound, "not registered"):
                registry.resolve("demo-plate")

    def test_traversal_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(SceneAssetError):
                SceneAssetRegistry(root, (  # type: ignore[arg-type]
                    __import__("fabuloom_core.scene_assets", fromlist=["SceneAsset"]).SceneAsset(
                        id="demo-plate", version="1.0.0", relative_path="../outside.png", metadata={}
                    ),
                ))


if __name__ == "__main__":
    unittest.main()
