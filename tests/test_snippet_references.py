from __future__ import annotations

import unittest

from kicad_partstash.snippet_generators import generate_snippet
from kicad_partstash.snippet_references import normalize_reference_designators
from kicad_partstash.storage import PartStore


class SnippetReferenceTests(unittest.TestCase):
    def test_normalizes_property_and_instance_references(self) -> None:
        snippet = '(property "Reference" "R7")\n(reference "R7")\n(property "Reference" "C99")'

        normalized = normalize_reference_designators(snippet)

        self.assertIn('(property "Reference" "R?")', normalized)
        self.assertIn('(reference "R?")', normalized)
        self.assertIn('(property "Reference" "C?")', normalized)
        self.assertNotIn('"R7"', normalized)
        self.assertNotIn('"C99"', normalized)

    def test_default_snippets_do_not_have_fixed_instance_references(self) -> None:
        for part in PartStore().load_default_parts():
            snippets = []
            if part.snippet:
                snippets.append(part.snippet)
            if part.generator:
                snippets.append(generate_snippet(part.generator, part.default_template_values))

            for snippet in snippets:
                with self.subTest(part=part.id):
                    self.assertEqual(snippet, normalize_reference_designators(snippet))


if __name__ == "__main__":
    unittest.main()