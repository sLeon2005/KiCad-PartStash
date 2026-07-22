from __future__ import annotations

import re
from dataclasses import dataclass, field


LIB_ID_RE = re.compile(r'\(lib_id\s+"([^"]+)"\)')
FOOTPRINT_RE = re.compile(r'\(property\s+"Footprint"\s+"([^"]*)"')
AUTO_STATUSES = {
    "",
    "draft",
    "needs_snippet",
    "captured",
    "captured_missing_footprint_warning",
    "captured_needs_review",
}


@dataclass(frozen=True)
class SnippetValidation:
    snippet: str
    looks_like_kicad: bool
    has_lib_symbols: bool
    has_symbol_instance: bool
    lib_id: str = ""
    footprint: str = ""
    footprint_properties: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_assigned_footprint(self) -> bool:
        return bool(self.footprint)

    @property
    def is_usable(self) -> bool:
        return bool(self.snippet.strip()) and self.looks_like_kicad and self.has_symbol_instance

    def suggested_status(self, current_status: str = "") -> str:
        if current_status and current_status not in AUTO_STATUSES:
            return current_status
        if not self.snippet.strip():
            return "needs_snippet"
        if not self.looks_like_kicad or not self.has_symbol_instance:
            return "captured_needs_review"
        if not self.has_assigned_footprint:
            return "captured_missing_footprint_warning"
        return "captured"

    def summary(self) -> str:
        if not self.snippet.strip():
            return "No snippet captured."
        if self.warnings:
            return "; ".join(self.warnings)
        bits = ["KiCad snippet looks valid"]
        if self.lib_id:
            bits.append(f"symbol: {self.lib_id}")
        if self.footprint:
            bits.append(f"footprint: {self.footprint}")
        return "; ".join(bits)


def validate_snippet(snippet: str) -> SnippetValidation:
    text = snippet.strip()
    if not text:
        return SnippetValidation(
            snippet=snippet,
            looks_like_kicad=False,
            has_lib_symbols=False,
            has_symbol_instance=False,
            warnings=["Snippet is empty"],
        )

    lib_ids = LIB_ID_RE.findall(snippet)
    footprint_properties = FOOTPRINT_RE.findall(snippet)
    assigned_footprints = [value for value in footprint_properties if value.strip()]
    has_lib_symbols = "(lib_symbols" in snippet
    has_symbol_instance = bool(lib_ids) and "(symbol" in snippet
    looks_like_kicad = "(symbol" in snippet or has_lib_symbols

    warnings: list[str] = []
    if not looks_like_kicad:
        warnings.append("Snippet does not look like KiCad clipboard text")
    if not has_lib_symbols:
        warnings.append("Missing lib_symbols block")
    if not has_symbol_instance:
        warnings.append("Missing symbol instance or lib_id")
    if not footprint_properties:
        warnings.append("Missing Footprint property")
    elif not assigned_footprints:
        warnings.append("Footprint is unassigned")

    return SnippetValidation(
        snippet=snippet,
        looks_like_kicad=looks_like_kicad,
        has_lib_symbols=has_lib_symbols,
        has_symbol_instance=has_symbol_instance,
        lib_id=lib_ids[-1] if lib_ids else "",
        footprint=assigned_footprints[-1] if assigned_footprints else "",
        footprint_properties=footprint_properties,
        warnings=warnings,
    )
