from __future__ import annotations

import unittest

from kicad_partstash.snippet_generators import generate_snippet, generator_template_fields
from kicad_partstash.snippet_validation import validate_snippet


class GeneratorTests(unittest.TestCase):
    def assert_generated_connector(
        self,
        generator: str,
        pins: int,
        expected_lib_id: str,
        expected_footprint: str,
    ) -> None:
        snippet = generate_snippet(generator, {"pins": str(pins)})
        validation = validate_snippet(snippet)

        self.assertEqual(validation.warnings, [])
        self.assertEqual(validation.lib_id, expected_lib_id)
        self.assertEqual(validation.footprint, expected_footprint)
        self.assertEqual(snippet.count("(pin passive line"), pins)
        self.assertEqual(snippet.count('\n\t(pin "'), pins)
        self.assertIn('(reference "J?")', snippet)
        self.assertNotIn('(reference "J")', snippet)

    def test_supported_generators_ask_for_pins(self) -> None:
        for generator in [
            "connector_1xn_pin_vertical",
            "connector_1xn_socket_vertical",
            "connector_jst_xh_vertical",
        ]:
            with self.subTest(generator=generator):
                self.assertEqual(generator_template_fields(generator), ["pins"])

    def test_vertical_pin_header_generator(self) -> None:
        self.assert_generated_connector(
            "connector_1xn_pin_vertical",
            7,
            "Connector:Conn_01x07_Pin",
            "Connector_PinHeader_2.54mm:PinHeader_1x07_P2.54mm_Vertical",
        )

    def test_vertical_pin_socket_generator(self) -> None:
        self.assert_generated_connector(
            "connector_1xn_socket_vertical",
            7,
            "Connector:Conn_01x07_Socket",
            "Connector_PinSocket_2.54mm:PinSocket_1x07_P2.54mm_Vertical",
        )

    def test_jst_xh_generator(self) -> None:
        for pins in [2, 3, 4, 10]:
            with self.subTest(pins=pins):
                self.assert_generated_connector(
                    "connector_jst_xh_vertical",
                    pins,
                    f"Connector:Conn_01x{pins:02d}_Pin",
                    f"Connector_JST:JST_XH_B{pins}B-XH-A_1x{pins:02d}_P2.50mm_Vertical",
                )

    def test_jst_xh_rejects_one_pin(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 2 pins"):
            generate_snippet("connector_jst_xh_vertical", {"pins": "1"})

    def test_unknown_generator_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported generator"):
            generate_snippet("unknown", {"pins": "4"})


if __name__ == "__main__":
    unittest.main()
