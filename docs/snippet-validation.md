# Snippet Validation

Kicad-PartStash performs lightweight validation when a snippet is captured, saved, or copied.

The validation is advisory. It should warn the user, not block their workflow.

## Checks

- The snippet is not empty.
- The text looks like KiCad clipboard data.
- A `lib_symbols` block is present.
- A pasted symbol instance has a `lib_id`.
- At least one `Footprint` property is present.
- At least one `Footprint` property has an assigned value.

KiCad snippets may contain an empty footprint inside the library symbol definition and an assigned footprint inside the actual symbol instance. Kicad-PartStash treats the non-empty instance footprint as the assigned footprint.

## Suggested statuses

- `needs_snippet`: no snippet is present.
- `captured`: snippet looks like KiCad data and has an assigned footprint.
- `captured_missing_footprint_warning`: snippet looks like KiCad data but the footprint appears unassigned.
- `captured_needs_review`: snippet does not look like normal KiCad clipboard data.

Users can still copy snippets with warnings.
