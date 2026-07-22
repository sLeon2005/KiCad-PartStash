# Roadmap

Kicad-PartStash is a lightweight Windows desktop app for storing trusted KiCad 9 component snippets and copying them back into schematics.

Product principle: default parts must be copied and verified from KiCad 9. The app should warn about missing footprints, but it should not block the user.

## v0.0.1 - Research scaffold

Status: complete.

- Create the project structure.
- Define the part JSON model.
- Load bundled default parts and user overrides.
- Provide a minimal desktop UI.
- Capture selected snippets from the clipboard.
- Copy saved snippets back to the clipboard.
- Keep recent parts.
- Document the KiCad clipboard validation workflow.

## v0.1.0 - Usable MVP

Status: in progress.

- Verify the first real KiCad 9 snippets.
- Fill the initial default library with trusted resistor/capacitor parts.
- Improve search ranking.
- Add keyboard flow: search, enter to copy, escape to clear.
- Keep notifications subtle and non-blocking.
- Add snippet validation warnings.
- Add import/export and restore defaults.
- Add manual test checklist.

## v0.2.0 - Editable library

Status: partially complete.

- Add new user parts.
- Edit names, categories, tags, symbols, footprints, and raw snippets.
- Duplicate existing parts.
- Delete user parts.
- Keep bundled defaults recoverable.
- Add import and export.

## v0.3.0 - Header templates

Status: partially complete.

- Support 1xN vertical and horizontal headers.
- Ask only for pin count.
- Derive two-digit pin tokens such as `{{pins_2}}`.
- Verify multiple pin counts in KiCad 9.

## v0.4.0 - UX pass

Status: partially complete.

- Improve layout polish.
- Add better recent-part grouping.
- Add small status messages that clear automatically.
- Add light validation messages for missing footprints.

## v0.5.0 - Ready blocks

Status: planned.

- Add an ATmega328P minimal block.
- Include crystal, crystal capacitors, reset, ISP header, and useful net labels.
- Verify block paste behavior in a clean KiCad 9 project.

## v1.0.0 - Portfolio release

Status: planned.

- Complete README.
- Include verified default library.
- Include examples.
- Package a Windows executable.
- Publish the first GitHub release.
