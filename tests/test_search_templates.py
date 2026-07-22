from __future__ import annotations

import unittest

from kicad_partstash.search import rank_parts
from kicad_partstash.storage import PartStore
from kicad_partstash.templates import (
    derived_values,
    find_template_tokens,
    render_template,
    required_template_fields,
    unsupported_template_fields,
)


class TemplateTests(unittest.TestCase):
    def test_pin_tokens_are_detected_and_rendered(self) -> None:
        snippet = "Conn_01x{{pins_2}} uses {{ pins }} pins"
        self.assertEqual(find_template_tokens(snippet), ["pins", "pins_2"])
        self.assertEqual(required_template_fields(snippet, []), ["pins"])
        self.assertEqual(unsupported_template_fields(["pins"]), [])
        self.assertEqual(derived_values({"pins": "4"})["pins_2"], "04")
        self.assertEqual(render_template(snippet, {"pins": "10"}), "Conn_01x10 uses 10 pins")

    def test_unknown_template_fields_are_reported(self) -> None:
        fields = required_template_fields("{{foo}} {{pins_2}}", [])
        self.assertEqual(fields, ["pins", "foo"])
        self.assertEqual(unsupported_template_fields(fields), ["foo"])


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parts = PartStore().load_default_parts()

    def assert_top_result(self, query: str, expected_name: str) -> None:
        ranked = rank_parts(self.parts, query, [])
        self.assertTrue(ranked, query)
        self.assertEqual(ranked[0].part.name, expected_name)

    def test_connector_searches_find_expected_generators(self) -> None:
        self.assert_top_result("male 1xn", "Pin Header 1xN 2.54mm Vertical Male")
        self.assert_top_result("female socket", "Pin Socket 1xN 2.54mm Vertical Female")
        self.assert_top_result("jst xh", "JST XH 1xN 2.50mm Vertical")

    def test_crystal_search_is_size_based_not_frequency_based(self) -> None:
        self.assert_top_result("crystal 3225", "SMD Crystal 3225 4-Pin Hand Solder")
        self.assertEqual(rank_parts(self.parts, "16mhz", []), [])


if __name__ == "__main__":
    unittest.main()
