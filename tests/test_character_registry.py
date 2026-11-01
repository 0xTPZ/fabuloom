import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fabuloom_core.character_registry import CharacterNotFound, CharacterRegistry, CharacterRegistryError


def _payload(*, base_image: str = "character.png", sha256: str | None = None) -> dict:
    return {
        "format": "fabuloom.character-registry/0.1",
        "format_version": "0.1.0",
        "characters": [{
            "id": "demo-character-v1-base",
            "canonical_name": "Demo",
            "version": "1.0.0",
            "base_image": base_image,
            "visual_description": "original draft identity",
            "palette": ["navy", "gold"],
            "physical_characteristics": ["silver hair"],
            "facial_structure": "front-facing stylized face",
            "costume": "blue and gold uniform",
            "proportions": "head slightly larger for readability",
            "sha256": sha256,
            "origin": "local concept",
            "approval_status": "DRAFT",
            "variations": [{"id": "demo-character-v1-smile", "status": "DRAFT"}],
        }],
    }


class CharacterRegistryTests(unittest.TestCase):
    def test_resolves_hash_and_reports_approval(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "character.png"
            image.write_bytes(b"character")
            registry_path = root / "registry.json"
            registry_path.write_text(json.dumps(_payload(sha256=hashlib.sha256(b"character").hexdigest())), encoding="utf-8")
            registry = CharacterRegistry.from_json(registry_path, workspace_root=root)
            self.assertEqual(registry.resolve("demo-character-v1-base"), image.resolve())
            self.assertEqual(registry.ids(), ("demo-character-v1-base",))
            self.assertEqual(registry.approved_ids(), ())

    def test_missing_id_and_missing_file_are_distinct(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            registry_path = root / "registry.json"
            registry_path.write_text(json.dumps(_payload()), encoding="utf-8")
            registry = CharacterRegistry.from_json(registry_path, workspace_root=root)
            with self.assertRaises(CharacterNotFound):
                registry.get("unknown-character-v1-base")
            with self.assertRaises(CharacterNotFound):
                registry.resolve("demo-character-v1-base")

    def test_traversal_and_hash_mismatch_are_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "character.png"
            image.write_bytes(b"character")
            missing_registry = root / "missing.json"
            with self.assertRaises(FileNotFoundError):
                CharacterRegistry.from_json(missing_registry, workspace_root=root)
            traversal_path = root / "traversal.json"
            traversal_path.write_text(json.dumps(_payload(base_image="../character.png")), encoding="utf-8")
            with self.assertRaises(CharacterRegistryError):
                CharacterRegistry.from_json(traversal_path, workspace_root=root)
            mismatch_path = root / "mismatch.json"
            mismatch_path.write_text(json.dumps(_payload(sha256="00" * 32)), encoding="utf-8")
            registry = CharacterRegistry.from_json(mismatch_path, workspace_root=root)
            with self.assertRaisesRegex(CharacterRegistryError, "hash mismatch"):
                registry.resolve("demo-character-v1-base")


if __name__ == "__main__":
    unittest.main()
