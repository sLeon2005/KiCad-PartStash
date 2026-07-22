from __future__ import annotations

import re

FIXED_REFERENCE_RE = re.compile(r'(\((?:property\s+"Reference"|reference)\s+")([A-Z]+)(\d+)(")')


def normalize_reference_designators(snippet: str) -> str:
    """Replace concrete schematic references like R7/C99 with R?/C?."""
    return FIXED_REFERENCE_RE.sub(lambda match: f"{match.group(1)}{match.group(2)}?{match.group(4)}", snippet)