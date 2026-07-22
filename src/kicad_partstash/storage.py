from __future__ import annotations

import json
import os
from pathlib import Path

from .models import Part


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PARTS_PATH = PROJECT_ROOT / "data" / "default_parts.json"
APP_DATA_DIR = Path(os.getenv("APPDATA", PROJECT_ROOT)) / "Kicad-PartStash"
USER_PARTS_PATH = APP_DATA_DIR / "user_parts.json"
PREFERENCES_PATH = APP_DATA_DIR / "preferences.json"


class PartStore:
    def __init__(
        self,
        default_parts_path: Path = DEFAULT_PARTS_PATH,
        user_parts_path: Path = USER_PARTS_PATH,
        preferences_path: Path = PREFERENCES_PATH,
    ) -> None:
        self.default_parts_path = default_parts_path
        self.user_parts_path = user_parts_path
        self.preferences_path = preferences_path

    def load_parts(self) -> list[Part]:
        defaults = self.load_default_parts()
        user_parts = self.load_user_parts()
        by_id = {part.id: part for part in defaults}
        for part in user_parts:
            by_id[part.id] = part
        return list(by_id.values())

    def load_default_parts(self) -> list[Part]:
        return self._load_part_file(self.default_parts_path, source="default")

    def load_user_parts(self) -> list[Part]:
        return self._load_part_file(self.user_parts_path, source="user")

    def default_ids(self) -> set[str]:
        return {part.id for part in self.load_default_parts()}

    def save_user_part(self, part: Part) -> None:
        part.source = "user"
        user_parts = {item.id: item for item in self.load_user_parts()}
        user_parts[part.id] = part
        self._write_user_parts(user_parts.values())

    def delete_user_part(self, part_id: str) -> None:
        user_parts = {item.id: item for item in self.load_user_parts()}
        user_parts.pop(part_id, None)
        self._write_user_parts(user_parts.values())

    def export_user_parts(self, path: Path) -> int:
        user_parts = self.load_user_parts()
        self._write_json(path, [part.to_dict() for part in user_parts])
        return len(user_parts)

    def import_user_parts(self, path: Path) -> int:
        imported_parts = self._load_part_file(path, source="user")
        user_parts = {part.id: part for part in self.load_user_parts()}
        for part in imported_parts:
            part.source = "user"
            user_parts[part.id] = part
        self._write_user_parts(user_parts.values())
        return len(imported_parts)

    def restore_default_overrides(self) -> int:
        default_ids = self.default_ids()
        user_parts = self.load_user_parts()
        kept_parts = [part for part in user_parts if part.id not in default_ids]
        removed_count = len(user_parts) - len(kept_parts)
        self._write_user_parts(kept_parts)
        return removed_count

    def load_recent_ids(self) -> list[str]:
        data = self._read_json(self.preferences_path, default={})
        recent_ids = data.get("recent_ids", []) if isinstance(data, dict) else []
        return [str(item) for item in recent_ids][:10]

    def save_recent_ids(self, recent_ids: list[str]) -> None:
        self._write_json(self.preferences_path, {"recent_ids": recent_ids[:10]})

    def _write_user_parts(self, parts: object) -> None:
        sorted_parts = sorted(parts, key=lambda part: (part.category.lower(), part.name.lower(), part.id))
        self._write_json(self.user_parts_path, [part.to_dict() for part in sorted_parts])

    def _load_part_file(self, path: Path, source: str) -> list[Part]:
        data = self._read_json(path, default=[])
        if not isinstance(data, list):
            raise ValueError(f"{path} must contain a JSON list.")
        return [Part.from_dict(item, source=source) for item in data if isinstance(item, dict)]

    def _read_json(self, path: Path, default: object) -> object:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
