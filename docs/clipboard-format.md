# KiCad Clipboard Format Notes

Kicad-PartStash is built around one strict rule: default snippets should come from real KiCad 9 clipboard data, not from guessed text.

## Research workflow

1. Open KiCad 9.
2. Create a temporary schematic.
3. Place one component.
4. Assign the intended footprint.
5. Copy the component from the schematic.
6. Paste it into Kicad-PartStash with `Capture Clipboard`.
7. Paste it back into a clean schematic and verify it still works.
8. Move the verified snippet into `data/default_parts.json` or `examples/`.

## What to verify

- The symbol is the intended official KiCad symbol.
- The footprint is assigned.
- Pasting into another schematic works.
- Repeated paste operations do not create KiCad errors.
- Variable snippets, such as 1xN headers, only ask for the pin count.

## Open questions

- Whether KiCad 9 tolerates repeated UUIDs in pasted clipboard snippets.
- Which exact official footprints should be used for terminal blocks, USB-B, push buttons, and the ATmega328P package.
- Whether ready blocks need any position normalization before saving.
