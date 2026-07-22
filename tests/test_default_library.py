from __future__ import annotations

import unittest

from kicad_partstash.snippet_generators import generate_snippet
from kicad_partstash.snippet_validation import validate_snippet
from kicad_partstash.storage import PartStore


class DefaultLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parts = PartStore().load_default_parts()
        cls.by_id = {part.id: part for part in cls.parts}

    def test_default_ids_are_unique(self) -> None:
        self.assertEqual(len(self.parts), len(self.by_id))

    def test_verified_defaults_have_valid_snippets(self) -> None:
        for part in self.parts:
            if part.status != "verified":
                continue
            with self.subTest(part=part.id):
                self.assertTrue(part.snippet.strip())
                validation = validate_snippet(part.snippet)
                self.assertEqual(validation.warnings, [])
                self.assertEqual(validation.lib_id, part.symbol)
                self.assertEqual(validation.footprint, part.footprint)

    def test_generator_defaults_generate_valid_snippets(self) -> None:
        for part in self.parts:
            if part.status != "generator":
                continue
            with self.subTest(part=part.id):
                pins = part.default_template_values.get("pins", "")
                self.assertTrue(pins.isdigit())
                snippet = generate_snippet(part.generator, {"pins": pins})
                validation = validate_snippet(snippet)
                self.assertEqual(validation.warnings, [])
                self.assertTrue(validation.lib_id)
                self.assertTrue(validation.footprint)

    def test_crystal_3225_default_is_value_agnostic(self) -> None:
        part = self.by_id["crystal-smd-3225-4pin-handsolder"]
        validation = validate_snippet(part.snippet)

        self.assertEqual(part.name, "SMD Crystal 3225 4-Pin Hand Solder")
        self.assertEqual(part.symbol, "Device:Crystal_GND24")
        self.assertEqual(part.footprint, "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm_HandSoldering")
        self.assertEqual(validation.warnings, [])
        self.assertEqual(part.snippet.count("("), part.snippet.count(")"))
        self.assertNotIn("16MHz", part.searchable_text())
        self.assertNotIn("16 MHz", part.searchable_text())
        self.assertNotIn("16MHz", part.snippet)
        self.assertNotIn("16 MHz", part.snippet)

    def test_default_library_has_no_fixed_crystal_frequency(self) -> None:
        default_text = "\n".join(part.searchable_text() + "\n" + part.snippet for part in self.parts)
        self.assertNotIn("16mhz", default_text)
        self.assertNotIn("16 mhz", default_text)


if __name__ == "__main__":
    unittest.main()
