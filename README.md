# Kicad-PartStash

A desktop stash for trusted KiCad component snippets.

Kicad-PartStash is a lightweight Windows utility for PCB designers who reuse the same KiCad parts across projects. It stores verified KiCad 9 clipboard snippets, lets you search your stash, and copies ready-to-paste components back to the clipboard.

## Status

Kicad-PartStash is an early usable MVP. The core app works, but the bundled default library is still being built from real KiCad 9 snippets.

Verified bundled snippets so far:

- Resistor 0805 Hand Solder
- Capacitor 0805 Hand Solder

## Features

- Search parts by name, category, tags, symbol, footprint, description, and status.
- Copy KiCad snippets with double-click, `Enter`, or the `Copy` button.
- Capture a KiCad clipboard snippet into the selected part.
- Edit user parts and user overrides for bundled defaults.
- Duplicate parts to create variants.
- Keep recent parts near the top.
- Warn when a captured snippet does not look like KiCad data or appears to lack an assigned footprint.
- Support simple header templates with a pin-count spinner.
- Import, export, and restore the user library.

## Development

Run from source:

```powershell
$env:PYTHONPATH = "src"
python -m kicad_partstash
```

If `python` is not available in your terminal, install Python 3.10+ or use the Python executable provided by your development environment.

## KiCad workflow

1. Open KiCad 9 and a schematic.
2. Place and configure a trusted component with its footprint assigned.
3. Copy that component in KiCad.
4. Select the matching part in Kicad-PartStash.
5. Click `Capture Clipboard`.
6. Copy it back from Kicad-PartStash.
7. Paste into a clean KiCad schematic and verify symbol and footprint.

Only snippets verified this way should be promoted into `data/default_parts.json`.

## Documentation

- [Roadmap](ROADMAP.md)
- [Clipboard format notes](docs/clipboard-format.md)
- [Header templates](docs/header-templates.md)
- [Library management](docs/library-management.md)
- [Snippet validation](docs/snippet-validation.md)
- [Manual test checklist](docs/manual-test-checklist.md)

## Product direction

- Lightweight Windows desktop app.
- Official KiCad library parts first.
- Components paste into the schematic with footprints already assigned.
- Mouse-first workflow, with keyboard shortcuts once the user gets comfortable.
- Missing footprints warn the user but do not block copying.
