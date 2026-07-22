from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .snippet_validation import validate_snippet


@dataclass
class Part:
    id: str
    name: str
    category: str
    tags: list[str] = field(default_factory=list)
    symbol: str = ""
    footprint: str = ""
    description: str = ""
    snippet: str = ""
    template_fields: list[str] = field(default_factory=list)
    default_template_values: dict[str, str] = field(default_factory=dict)
    source: str = "default"
    verified_with: str = ""
    status: str = "needs_snippet"
    generator: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any], source: str = "default") -> "Part":
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

        template_fields = data.get("template_fields", [])
        if isinstance(template_fields, str):
            template_fields = [template_fields]

        default_template_values = data.get("default_template_values", {})
        if not isinstance(default_template_values, dict):
            default_template_values = {}

        return cls(
            id=str(data["id"]),
            name=str(data.get("name") or "Unnamed part"),
            category=str(data.get("category") or "Uncategorized"),
            tags=list(tags),
            symbol=str(data.get("symbol") or ""),
            footprint=str(data.get("footprint") or ""),
            description=str(data.get("description") or ""),
            snippet=str(data.get("snippet") or ""),
            template_fields=list(template_fields),
            default_template_values={str(key): str(value) for key, value in default_template_values.items()},
            source=str(data.get("source") or source),
            verified_with=str(data.get("verified_with") or ""),
            status=str(data.get("status") or "needs_snippet"),
            generator=str(data.get("generator") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "tags": self.tags,
            "symbol": self.symbol,
            "footprint": self.footprint,
            "description": self.description,
            "snippet": self.snippet,
            "template_fields": self.template_fields,
            "default_template_values": self.default_template_values,
            "source": self.source,
            "verified_with": self.verified_with,
            "status": self.status,
            "generator": self.generator,
        }

    def searchable_text(self) -> str:
        return " ".join(
            [
                self.name,
                self.category,
                " ".join(self.tags),
                self.symbol,
                self.footprint,
                self.description,
                self.status,
                self.generator,
            ]
        ).lower()

    def has_snippet(self) -> bool:
        return bool(self.snippet.strip()) or bool(self.generator.strip())

    def has_footprint_hint(self) -> bool:
        if self.footprint.strip():
            return True
        return validate_snippet(self.snippet).has_assigned_footprint
