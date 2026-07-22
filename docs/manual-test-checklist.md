# Manual Test Checklist

Use this checklist before tagging a usable MVP release or promoting new default snippets.

## App startup

- Run `python -m kicad_partstash` from the repo with `PYTHONPATH=src`.
- Confirm the app opens without errors.
- Confirm the search box is focused on startup.
- Confirm bundled parts appear in the list.

## Search and copy

- Search `res 0805` and confirm `Resistor 0805 Hand Solder` is selected.
- Press `Enter` and confirm the status line says the part was copied.
- Search `cap hand` and confirm only the capacitor is the best match.
- Double-click a part and confirm it copies.
- Confirm copied resistor/capacitor snippets paste into KiCad 9.

## Editing

- Duplicate a bundled default.
- Edit the duplicated part name, tags, and description.
- Press `Ctrl+S` and confirm it saves as a user part.
- Delete the user part and confirm bundled defaults remain.

## Capture

- Copy a configured part from KiCad 9.
- Select its matching part in Kicad-PartStash.
- Click `Capture Clipboard`.
- Confirm symbol and footprint fields are filled when detectable.
- Confirm the snippet validation line shows OK or a useful warning.

## Header templates

- Use a header snippet containing `{{pins_2}}`.
- Copy the part and confirm the pin-count spinner appears.
- Enter `4` and confirm the rendered snippet contains `04` where expected.
- Enter `10` and confirm the rendered snippet contains `10` where expected.
- Paste generated headers into KiCad 9 and verify symbol/footprint.

## Library management

- Export the user library to JSON.
- Import that JSON into a clean/local test library.
- Edit a bundled default, then use Restore Bundled Defaults.
- Confirm custom user parts remain after restore.
- Confirm user overrides for bundled defaults are removed after restore.

## Snippet validation

- Capture valid KiCad clipboard text and confirm the validation line says OK.
- Capture plain text such as `lol?` and confirm it is marked for review.
- Capture a KiCad snippet without an assigned footprint and confirm a footprint warning appears.
