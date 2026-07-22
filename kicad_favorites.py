from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import messagebox, ttk


APP_TITLE = "KiCad Favorite Parts"
DATA_FILE = Path(__file__).with_name("kicad_favorites.json")
TEMPLATE_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


@dataclass
class FavoritePart:
    id: str
    name: str
    category: str = ""
    tags: str = ""
    notes: str = ""
    snippet: str = ""

    @classmethod
    def blank(cls) -> "FavoritePart":
        return cls(id=str(uuid.uuid4()), name="Nuevo componente")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FavoritePart":
        return cls(
            id=str(data.get("id") or uuid.uuid4()),
            name=str(data.get("name") or "Sin nombre"),
            category=str(data.get("category") or ""),
            tags=str(data.get("tags") or ""),
            notes=str(data.get("notes") or ""),
            snippet=str(data.get("snippet") or ""),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "tags": self.tags,
            "notes": self.notes,
            "snippet": self.snippet,
        }

    def searchable_text(self) -> str:
        return " ".join([self.name, self.category, self.tags, self.notes]).lower()


class FavoritesStore:
    def __init__(self, path: Path = DATA_FILE) -> None:
        self.path = path

    def load(self) -> list[FavoritePart]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError("El archivo de favoritos debe contener una lista JSON.")
        return [FavoritePart.from_dict(item) for item in data if isinstance(item, dict)]

    def save(self, parts: list[FavoritePart]) -> None:
        payload = [part.to_dict() for part in sorted(parts, key=lambda p: (p.category.lower(), p.name.lower()))]
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")


class TemplateDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, variables: list[str]) -> None:
        super().__init__(parent)
        self.title("Completar variables")
        self.resizable(False, False)
        self.result: dict[str, str] | None = None
        self.entries: dict[str, ttk.Entry] = {}

        frame = ttk.Frame(self, padding=14)
        frame.grid(row=0, column=0, sticky="nsew")
        ttk.Label(frame, text="Este snippet tiene variables tipo {{valor}}.").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

        for row, variable in enumerate(variables, start=1):
            ttk.Label(frame, text=variable).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
            entry = ttk.Entry(frame, width=28)
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            self.entries[variable] = entry

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(variables) + 1, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancelar", command=self.destroy).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Copiar", command=self.submit).grid(row=0, column=1)

        self.transient(parent)
        self.grab_set()
        first = next(iter(self.entries.values()), None)
        if first is not None:
            first.focus_set()
        self.bind("<Return>", lambda _event: self.submit())
        self.bind("<Escape>", lambda _event: self.destroy())

    def submit(self) -> None:
        values = {name: entry.get().strip() for name, entry in self.entries.items()}
        missing = [name for name, value in values.items() if not value]
        if missing:
            messagebox.showwarning("Falta un valor", f"Completa: {', '.join(missing)}", parent=self)
            return
        self.result = values
        self.destroy()


class App(tk.Tk):
    def __init__(self, store: FavoritesStore) -> None:
        super().__init__()
        self.store = store
        self.parts: list[FavoritePart] = []
        self.filtered_ids: list[str] = []
        self.current_id: str | None = None
        self.dirty = False

        self.title(APP_TITLE)
        self.minsize(980, 620)
        self.configure(padx=12, pady=12)

        self.name_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.tags_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Listo.")

        self._build_ui()
        self._bind_events()
        self._load_parts()

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        left.rowconfigure(2, weight=1)

        ttk.Label(left, text="Buscar").grid(row=0, column=0, sticky="w")
        search = ttk.Entry(left, textvariable=self.search_var, width=34)
        search.grid(row=1, column=0, sticky="ew", pady=(4, 8))

        self.listbox = tk.Listbox(left, width=38, activestyle="dotbox", exportselection=False)
        self.listbox.grid(row=2, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(left, orient="vertical", command=self.listbox.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        left_buttons = ttk.Frame(left)
        left_buttons.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(left_buttons, text="Nuevo", command=self.new_part).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(left_buttons, text="Duplicar", command=self.duplicate_part).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(left_buttons, text="Eliminar", command=self.delete_part).grid(row=0, column=2, sticky="ew")
        left_buttons.columnconfigure((0, 1, 2), weight=1)

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(1, weight=1)
        right.rowconfigure(5, weight=1)

        ttk.Label(right, text="Nombre").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(right, textvariable=self.name_var).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(right, text="Categoria").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(right, textvariable=self.category_var).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(right, text="Tags").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(right, textvariable=self.tags_var).grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(right, text="Notas").grid(row=3, column=0, sticky="nw", pady=4)
        self.notes_text = tk.Text(right, height=4, wrap="word")
        self.notes_text.grid(row=3, column=1, sticky="ew", pady=4)

        helper = (
            "Pega aqui el texto que KiCad pone en el portapapeles al copiar un simbolo. "
            "Tambien puedes usar variables como {{pins}} y se pediran al copiar."
        )
        ttk.Label(right, text=helper, wraplength=650).grid(row=4, column=1, sticky="w", pady=(8, 4))

        self.snippet_text = tk.Text(right, height=18, wrap="none", undo=True)
        self.snippet_text.grid(row=5, column=1, sticky="nsew")
        yscroll = ttk.Scrollbar(right, orient="vertical", command=self.snippet_text.yview)
        yscroll.grid(row=5, column=2, sticky="ns")
        xscroll = ttk.Scrollbar(right, orient="horizontal", command=self.snippet_text.xview)
        xscroll.grid(row=6, column=1, sticky="ew")
        self.snippet_text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        actions = ttk.Frame(right)
        actions.grid(row=7, column=1, sticky="e", pady=(12, 0))
        ttk.Button(actions, text="Capturar portapapeles", command=self.capture_clipboard).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(actions, text="Guardar", command=self.save_current).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(actions, text="Copiar para KiCad", command=self.copy_current).grid(row=0, column=2)

        ttk.Label(self, textvariable=self.status_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _bind_events(self) -> None:
        self.search_var.trace_add("write", lambda *_args: self.refresh_list())
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        for var in (self.name_var, self.category_var, self.tags_var):
            var.trace_add("write", lambda *_args: self.mark_dirty())
        self.notes_text.bind("<<Modified>>", self.on_text_modified)
        self.snippet_text.bind("<<Modified>>", self.on_text_modified)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _load_parts(self) -> None:
        try:
            self.parts = self.store.load()
        except Exception as exc:
            messagebox.showerror("No se pudo cargar", str(exc), parent=self)
            self.parts = []
        self.refresh_list()
        if self.parts:
            self.select_part(self.parts[0].id)
        else:
            self.new_part()

    def refresh_list(self) -> None:
        query = self.search_var.get().strip().lower()
        selected = self.current_id
        self.listbox.delete(0, tk.END)
        self.filtered_ids = []

        for part in sorted(self.parts, key=lambda p: (p.category.lower(), p.name.lower())):
            if query and query not in part.searchable_text():
                continue
            label = f"{part.category} / {part.name}" if part.category else part.name
            self.filtered_ids.append(part.id)
            self.listbox.insert(tk.END, label)

        if selected in self.filtered_ids:
            index = self.filtered_ids.index(selected)
            self.listbox.selection_set(index)
            self.listbox.see(index)

    def on_select(self, _event: tk.Event) -> None:
        if self.dirty and not self.confirm_discard_changes():
            self.restore_selection()
            return
        selection = self.listbox.curselection()
        if not selection:
            return
        self.select_part(self.filtered_ids[selection[0]])

    def restore_selection(self) -> None:
        self.listbox.selection_clear(0, tk.END)
        if self.current_id in self.filtered_ids:
            self.listbox.selection_set(self.filtered_ids.index(self.current_id))

    def select_part(self, part_id: str) -> None:
        part = self.find_part(part_id)
        if part is None:
            return
        self.current_id = part.id
        self.name_var.set(part.name)
        self.category_var.set(part.category)
        self.tags_var.set(part.tags)
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert("1.0", part.notes)
        self.snippet_text.delete("1.0", tk.END)
        self.snippet_text.insert("1.0", part.snippet)
        self.reset_modified_flags()
        self.dirty = False
        self.status_var.set(f"Seleccionado: {part.name}")

    def find_part(self, part_id: str | None) -> FavoritePart | None:
        return next((part for part in self.parts if part.id == part_id), None)

    def new_part(self) -> None:
        if self.dirty and not self.confirm_discard_changes():
            return
        part = FavoritePart.blank()
        self.parts.append(part)
        self.current_id = part.id
        self.refresh_list()
        self.select_part(part.id)
        self.status_var.set("Nuevo favorito creado. Pega o captura el snippet de KiCad.")

    def duplicate_part(self) -> None:
        source = self.find_part(self.current_id)
        if source is None:
            return
        if self.dirty and not self.confirm_discard_changes():
            return
        clone = FavoritePart(
            id=str(uuid.uuid4()),
            name=f"{source.name} copia",
            category=source.category,
            tags=source.tags,
            notes=source.notes,
            snippet=source.snippet,
        )
        self.parts.append(clone)
        self.refresh_list()
        self.select_part(clone.id)
        self.save_all()

    def delete_part(self) -> None:
        part = self.find_part(self.current_id)
        if part is None:
            return
        if not messagebox.askyesno("Eliminar favorito", f"Eliminar '{part.name}'?", parent=self):
            return
        self.parts = [item for item in self.parts if item.id != part.id]
        self.current_id = None
        self.save_all()
        self.refresh_list()
        if self.parts:
            self.select_part(self.parts[0].id)
        else:
            self.new_part()

    def capture_clipboard(self) -> None:
        try:
            text = self.clipboard_get()
        except tk.TclError:
            messagebox.showwarning("Portapapeles vacio", "No hay texto para capturar.", parent=self)
            return
        if not text.strip():
            messagebox.showwarning("Portapapeles vacio", "No hay texto para capturar.", parent=self)
            return
        self.snippet_text.delete("1.0", tk.END)
        self.snippet_text.insert("1.0", text)
        self.mark_dirty()
        self.status_var.set("Snippet capturado desde el portapapeles.")

    def save_current(self) -> None:
        part = self.find_part(self.current_id)
        if part is None:
            return
        part.name = self.name_var.get().strip() or "Sin nombre"
        part.category = self.category_var.get().strip()
        part.tags = self.tags_var.get().strip()
        part.notes = self.notes_text.get("1.0", "end-1c").strip()
        part.snippet = self.snippet_text.get("1.0", "end-1c")
        self.save_all()
        self.refresh_list()
        self.dirty = False
        self.reset_modified_flags()
        self.status_var.set(f"Guardado: {part.name}")

    def save_all(self) -> None:
        try:
            self.store.save(self.parts)
        except Exception as exc:
            messagebox.showerror("No se pudo guardar", str(exc), parent=self)

    def copy_current(self) -> None:
        self.save_current()
        part = self.find_part(self.current_id)
        if part is None:
            return
        snippet = part.snippet
        if not snippet.strip():
            messagebox.showwarning("Snippet vacio", "Este favorito no tiene texto para copiar.", parent=self)
            return

        variables = sorted(set(TEMPLATE_RE.findall(snippet)))
        if variables:
            dialog = TemplateDialog(self, variables)
            self.wait_window(dialog)
            if dialog.result is None:
                return
            for name, value in dialog.result.items():
                snippet = re.sub(r"\{\{\s*" + re.escape(name) + r"\s*\}\}", value, snippet)

        self.clipboard_clear()
        self.clipboard_append(snippet)
        self.update()
        self.status_var.set(f"Copiado para KiCad: {part.name}")

    def on_text_modified(self, event: tk.Event) -> None:
        widget = event.widget
        if widget.edit_modified():
            self.mark_dirty()
            widget.edit_modified(False)

    def mark_dirty(self) -> None:
        if self.current_id is not None:
            self.dirty = True

    def reset_modified_flags(self) -> None:
        self.notes_text.edit_modified(False)
        self.snippet_text.edit_modified(False)

    def confirm_discard_changes(self) -> bool:
        result = messagebox.askyesnocancel(
            "Cambios sin guardar",
            "Quieres guardar los cambios antes de cambiar de favorito?",
            parent=self,
        )
        if result is None:
            return False
        if result:
            self.save_current()
        else:
            self.dirty = False
        return True

    def on_close(self) -> None:
        if self.dirty and not self.confirm_discard_changes():
            return
        self.destroy()


def main() -> None:
    app = App(FavoritesStore())
    app.mainloop()


if __name__ == "__main__":
    main()
