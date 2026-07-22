# Header Generators

Kicad-PartStash supports a deliberately small template/generator system for variable pin headers.

The first supported field is `pins`. It is entered through a small spinner when copying a generated part. Each generated part defines its own default, such as `4` for 2.54 mm headers and `2` for JST XH.

## Supported generated parts

- `Pin Header 1xN 2.54mm Vertical Male`
- `Pin Socket 1xN 2.54mm Vertical Female`
- `JST XH 1xN 2.50mm Vertical`

These are separate parts on purpose. Gender, pitch, direction, and orientation should stay encoded by the selected part; the copy-time prompt should only ask for pin count.

## Supported tokens

Metadata may use these tokens for display/search fields:

- `{{pins}}`: raw pin count, such as `4`
- `{{pins_2}}`: two-digit pin count, such as `04`

## KiCad 9 discovery

A copied 1x04 connector snippet does not only contain names such as `Conn_01x04_Pin` or `PinHeader_1x04_P2.54mm_Vertical`. It also embeds the generated library symbol geometry and explicit pin definitions for four pins.

Because of that, trusted `1xN` headers are produced by code that generates the full symbol body: graphics, pin positions, pin names, pin numbers, footprint property, and instance pin UUID blocks. It does not rely on only replacing `04` in a copied snippet.

## Manual verification

Before calling a generator fully verified, paste a few generated variants into KiCad 9. For 2.54 mm headers, test `1`, `4`, `7`, and a two-digit count such as `10`. For JST XH, test `2`, `3`, `4`, and `10`.
