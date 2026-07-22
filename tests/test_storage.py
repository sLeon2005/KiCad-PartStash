from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kicad_partstash.models import Part
from kicad_partstash.storage import PartStore


class StorageTests(unittest.TestCase):
    def make_store(self, directory: Path) -> PartStore:
        directory.mkdir(parents=True, exist_ok=True)
        default_parts_path = directory / "default_parts.json"
        default_parts_path.write_text(
            json.dumps(
                [
                    {
                        "id": "default-resistor",
                        "name": "Default Resistor",
                        "category": "Passives",
                        "symbol": "Device:R",
                    }
                ]
            ),
            encoding="utf-8",
        )
        return PartStore(
            default_parts_path=default_parts_path,
            user_parts_path=directory / "user_parts.json",
            preferences_path=directory / "preferences.json",
        )

    def test_user_part_overrides_default_with_same_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(Path(tmp))
            store.save_user_part(
                Part(
                    id="default-resistor",
                    name="User Resistor",
                    category="Passives",
                    symbol="Device:R_Small_US",
                )
            )

            parts = store.load_parts()
            self.assertEqual(len(parts), 1)
            self.assertEqual(parts[0].name, "User Resistor")
            self.assertEqual(parts[0].source, "user")

    def test_recent_ids_are_limited_to_ten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(Path(tmp))
            store.save_recent_ids([f"part-{index}" for index in range(20)])
            self.assertEqual(store.load_recent_ids(), [f"part-{index}" for index in range(10)])

    def test_export_import_and_restore_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_store(root / "source")
            exported = root / "parts.json"
            source.save_user_part(Part(id="custom-led", name="Custom LED", category="Passives"))
            self.assertEqual(source.export_user_parts(exported), 1)

            target = self.make_store(root / "target")
            self.assertEqual(target.import_user_parts(exported), 1)
            self.assertIn("custom-led", {part.id for part in target.load_user_parts()})

            target.save_user_part(Part(id="default-resistor", name="Override", category="Passives"))
            self.assertEqual(target.restore_default_overrides(), 1)
            self.assertEqual({part.id for part in target.load_user_parts()}, {"custom-led"})


if __name__ == "__main__":
    unittest.main()
