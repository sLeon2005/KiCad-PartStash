# Kicad-PartStash

A desktop stash for trusted KiCad component snippets.

Kicad-PartStash is a lightweight Windows utility for PCB designers who reuse the same KiCad parts across projects. It stores verified KiCad 9 clipboard snippets, lets you search your stash, and copies ready-to-paste components back to the clipboard.

## Current status

This project is in the `v0.0.1` research scaffold stage. The app structure exists, but the bundled default library still needs real KiCad 9 snippets captured and verified.

## Development

Run from source:

```powershell
$env:PYTHONPATH = "src"
python -m kicad_partstash
```

## Product direction

- Lightweight Windows desktop app.
- Official KiCad library parts first.
- Components paste into the schematic with footprints already assigned.
- Double-click copies a component.
- Header templates ask only for pin count.
- Missing footprints warn the user but do not block copying.

See [ROADMAP.md](ROADMAP.md) for the planned versions.
