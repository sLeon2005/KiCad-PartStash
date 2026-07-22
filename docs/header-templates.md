# Header Templates

Kicad-PartStash supports a deliberately small template system for variable pin headers.

The first supported field is `pins`. It is entered through a small spinner when copying a part whose snippet or metadata requires it.

## Supported tokens

- `{{pins}}`: raw pin count, such as `4`
- `{{pins_2}}`: two-digit pin count, such as `04`

## Intended workflow

1. Capture a real KiCad 9 header snippet.
2. Verify it pastes correctly as a fixed header.
3. Replace the fixed pin count in the raw snippet with `{{pins_2}}` where KiCad symbol and footprint names need two digits.
4. Keep `template_fields` set to `["pins"]` in the part metadata.
5. Copy the part from the app and choose the pin count in the spinner.
6. Paste into KiCad and verify the generated header.

## Scope

Header direction, pitch, gender, and orientation should remain separate parts. The copy-time prompt should only ask for pin count.
