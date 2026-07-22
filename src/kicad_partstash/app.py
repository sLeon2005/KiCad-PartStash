from __future__ import annotations

import copy
import tkinter as tk
import uuid
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .models import Part
from .search import rank_parts
from .snippet_validation import validate_snippet
from .storage import PartStore
from .templates import render_template, required_template_fields, unsupported_template_fields


APP_TITLE = "Kicad-PartStash"
DEFAULT_STATUS = "Ready."
PIN_MIN = 1
PIN_MAX = 64


class PinDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, default_pins: str = "4") -> None:
        super().__init__(parent)
        self.title("Pins")
        self.resizable(False, False)
        self.result: dict[str, str] | None = None
        self.pins_var = tk.StringVar(value=default_pins)

        frame = ttk.Frame(self, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        ttk.Label(frame, text="Number of pins").grid(row=0, column=0, sticky="w", padx=(0, 10))
        spinbox = ttk.Spinbox(frame, from_=PIN_MIN, to=PIN_MAX, textvariable=self.pins_var, width=6)
        spinbox.grid(row=0, column=1, sticky="w")

        buttons = ttk.Frame(frame)
        buttons.grid(row=1, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Copy", command=self.submit).grid(row=0, column=1)

        self.transient(parent)
        self.grab_set()
        spinbox.focus_set()
        spinbox.selection_range(0, tk.END)
        self.bind("<Return>", lambda _event: self.submit())
        self.bind("<Escape>", lambda _event: self.destroy())

    def submit(self) -> None:
        value = self.pins_var.get().strip()
        if not value.isdigit() or not PIN_MIN <= int(value) <= PIN_MAX:
            messagebox.showwarning("Invalid value", f"Pins must be between {PIN_MIN} and {PIN_MAX}.", parent=self)
            return
        self.result = {"pins": str(int(value))}
        self.destroy()


class App(tk.Tk):
    def __init__(self, store: PartStore | None = None) -> None:
        super().__init__()
        self.store = store or PartStore()
        self.parts: list[Part] = []
        self.default_ids: set[str] = set()
        self.recent_ids: list[str] = []
        self.filtered_ids: list[str] = []
        self.selected_id: str | None = None
        self.status_after_id: str | None = None
        self.dirty = False
        self.loading_fields = False
        self.edit_entries: list[ttk.Entry] = []

        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value=DEFAULT_STATUS)
        self.validation_var = tk.StringVar(value="Snippet: no snippet selected.")
        self.field_vars = {
            "name": tk.StringVar(),
            "category": tk.StringVar(),
            "symbol": tk.StringVar(),
            "footprint": tk.StringVar(),
            "tags": tk.StringVar(),
            "status": tk.StringVar(),
            "source": tk.StringVar(),
        }

        self.title(APP_TITLE)
        self.minsize(1040, 640)
        self._build_menu()
        self._build_ui()
        self._bind_events()
        self.load_data()

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Import User Library...", command=self.import_library)
        file_menu.add_command(label="Export User Library...", command=self.export_library)
        file_menu.add_separator()
        file_menu.add_command(label="Restore Bundled Defaults", command=self.restore_defaults)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menu.add_cascade(label="File", menu=file_menu)

        part_menu = tk.Menu(menu, tearoff=False)
        part_menu.add_command(label="New Part", command=self.new_part)
        part_menu.add_command(label="Duplicate Part", command=self.duplicate_selected)
        part_menu.add_command(label="Delete Part", command=self.delete_selected)
        part_menu.add_separator()
        part_menu.add_command(label="Capture Clipboard", command=self.capture_clipboard_for_selected)
        part_menu.add_command(label="Save", command=self.save_current, accelerator="Ctrl+S")
        part_menu.add_command(label="Copy", command=self.copy_selected, accelerator="Enter")
        menu.add_cascade(label="Part", menu=part_menu)

        self.config(menu=menu)

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self, padding=(12, 12, 6, 8))
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.rowconfigure(2, weight=1)
        sidebar.columnconfigure(0, weight=1)

        ttk.Label(sidebar, text="Search").grid(row=0, column=0, sticky="w")
        self.search_entry = ttk.Entry(sidebar, textvariable=self.search_var, width=34)
        self.search_entry.grid(row=1, column=0, sticky="ew", pady=(4, 10))

        self.listbox = tk.Listbox(sidebar, width=38, exportselection=False, activestyle="dotbox")
        self.listbox.grid(row=2, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(sidebar, orient="vertical", command=self.listbox.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        library_actions = ttk.Frame(sidebar)
        library_actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        for column in range(3):
            library_actions.columnconfigure(column, weight=1)
        ttk.Button(library_actions, text="New", command=self.new_part).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(library_actions, text="Duplicate", command=self.duplicate_selected).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(library_actions, text="Delete", command=self.delete_selected).grid(row=0, column=2, sticky="ew")

        main = ttk.Frame(self, padding=(10, 12, 12, 8))
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(1, weight=1)
        main.rowconfigure(9, weight=1)

        rows = [
            ("Name", "name"),
            ("Category", "category"),
            ("Symbol", "symbol"),
            ("Footprint", "footprint"),
            ("Tags", "tags"),
            ("Status", "status"),
            ("Source", "source"),
        ]
        for row, (label, key) in enumerate(rows):
            ttk.Label(main, text=label).grid(row=row, column=0, sticky="w", pady=3, padx=(0, 10))
            entry = ttk.Entry(main, textvariable=self.field_vars[key])
            if key == "source":
                entry.configure(state="readonly")
            entry.grid(row=row, column=1, sticky="ew", pady=3)
            self.edit_entries.append(entry)

        ttk.Label(main, text="Description").grid(row=7, column=0, sticky="nw", pady=(10, 3), padx=(0, 10))
        self.description_text = tk.Text(main, height=4, wrap="word", undo=True)
        self.description_text.grid(row=7, column=1, sticky="ew", pady=(10, 3))

        ttk.Label(main, text="Raw KiCad snippet").grid(row=8, column=0, sticky="nw", pady=(10, 3), padx=(0, 10))
        self.snippet_text = tk.Text(main, height=14, wrap="none", undo=True)
        self.snippet_text.grid(row=9, column=1, sticky="nsew")
        snippet_scroll = ttk.Scrollbar(main, orient="vertical", command=self.snippet_text.yview)
        snippet_scroll.grid(row=9, column=2, sticky="ns")
        self.snippet_text.configure(yscrollcommand=snippet_scroll.set)

        ttk.Label(main, textvariable=self.validation_var, wraplength=720).grid(row=10, column=1, sticky="w", pady=(8, 0))

        actions = ttk.Frame(main)
        actions.grid(row=11, column=1, sticky="e", pady=(12, 0))
        ttk.Button(actions, text="Capture Clipboard", command=self.capture_clipboard_for_selected).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(actions, text="Save", command=self.save_current).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(actions, text="Copy", command=self.copy_selected).grid(row=0, column=2)

        ttk.Label(self, textvariable=self.status_var).grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 8))
        self.search_entry.focus_set()

    def _bind_events(self) -> None:
        self.search_var.trace_add("write", lambda *_args: self.refresh_list())
        for var in self.field_vars.values():
            var.trace_add("write", lambda *_args: self.mark_dirty())
        self.description_text.bind("<<Modified>>", self.on_text_modified)
        self.snippet_text.bind("<<Modified>>", self.on_text_modified)
        self.search_entry.bind("<Down>", self.focus_listbox)
        self.search_entry.bind("<Up>", self.focus_listbox)
        self.search_entry.bind("<Return>", self.on_return_key)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        self.listbox.bind("<Double-Button-1>", lambda _event: self.copy_selected())
        self.listbox.bind("<Return>", self.on_return_key)
        self.listbox.bind("<Escape>", self.on_escape_key)
        self.bind("<Return>", self.on_return_key)
        self.bind("<Control-f>", lambda _event: self.focus_search())
        self.bind("<Control-s>", self.on_save_key)
        self.bind("<Escape>", self.on_escape_key)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_data(self) -> None:
        try:
            self.parts = self.store.load_parts()
            self.default_ids = self.store.default_ids()
            self.recent_ids = self.store.load_recent_ids()
        except Exception as exc:
            messagebox.showerror("Could not load data", str(exc), parent=self)
            self.parts = []
            self.default_ids = set()
            self.recent_ids = []
        self.refresh_list()
        if self.filtered_ids:
            self.select_part(self.filtered_ids[0])

    def refresh_list(self) -> None:
        query = self.search_var.get().strip()
        current = self.selected_id
        ranked_parts = rank_parts(self.parts, query, self.recent_ids)

        self.listbox.delete(0, tk.END)
        self.filtered_ids = []
        for ranked in ranked_parts:
            part = ranked.part
            prefix = "Recent" if part.id in self.recent_ids else part.category
            marker = "*" if part.source == "user" else ""
            label = f"{prefix} / {part.name}{marker}"
            self.filtered_ids.append(part.id)
            self.listbox.insert(tk.END, label)

        if current in self.filtered_ids:
            index = self.filtered_ids.index(current)
            self.listbox.selection_set(index)
            self.listbox.see(index)
        elif self.filtered_ids:
            self.listbox.selection_set(0)
            if not self.dirty:
                self.select_part(self.filtered_ids[0])
        elif not self.dirty:
            self.clear_details()

    def clear_details(self) -> None:
        self.loading_fields = True
        self.selected_id = None
        for var in self.field_vars.values():
            var.set("")
        self.set_text(self.description_text, "")
        self.set_text(self.snippet_text, "")
        self.validation_var.set("Snippet: no snippet selected.")
        self.description_text.edit_modified(False)
        self.snippet_text.edit_modified(False)
        self.loading_fields = False

    def on_select(self, _event: tk.Event) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        if self.dirty and not self.confirm_unsaved_changes():
            self.restore_selection()
            return
        self.select_part(self.filtered_ids[selection[0]])

    def restore_selection(self) -> None:
        self.listbox.selection_clear(0, tk.END)
        if self.selected_id in self.filtered_ids:
            self.listbox.selection_set(self.filtered_ids.index(self.selected_id))

    def select_part(self, part_id: str) -> None:
        part = self.find_part(part_id)
        if part is None:
            return
        self.loading_fields = True
        self.selected_id = part.id
        self.field_vars["name"].set(part.name)
        self.field_vars["category"].set(part.category)
        self.field_vars["symbol"].set(part.symbol)
        self.field_vars["footprint"].set(part.footprint)
        self.field_vars["tags"].set(", ".join(part.tags))
        self.field_vars["status"].set(part.status)
        self.field_vars["source"].set(part.source)
        self.set_text(self.description_text, part.description)
        self.set_text(self.snippet_text, part.snippet)
        self.update_validation_summary(part.snippet)
        self.description_text.edit_modified(False)
        self.snippet_text.edit_modified(False)
        self.dirty = False
        self.loading_fields = False

    def find_part(self, part_id: str | None) -> Part | None:
        return next((part for part in self.parts if part.id == part_id), None)

    def new_part(self) -> None:
        if self.dirty and not self.confirm_unsaved_changes():
            return
        part = Part(
            id=f"user-{uuid.uuid4()}",
            name="New Part",
            category="Uncategorized",
            source="user",
            status="draft",
        )
        self.parts.append(part)
        self.selected_id = part.id
        self.refresh_list()
        self.select_part(part.id)
        self.field_vars["name"].set("")
        self.field_vars["name"].set("New Part")
        self.set_status("Created a new user part.")

    def duplicate_selected(self) -> None:
        part = self.find_part(self.selected_id)
        if part is None:
            return
        if self.dirty and not self.confirm_unsaved_changes():
            return
        clone = copy.deepcopy(part)
        clone.id = f"user-{uuid.uuid4()}"
        clone.name = f"{part.name} Copy"
        clone.source = "user"
        clone.status = "draft"
        self.parts.append(clone)
        self.refresh_list()
        self.select_part(clone.id)
        self.save_current()
        self.set_status(f"Duplicated: {part.name}")

    def delete_selected(self) -> None:
        part = self.find_part(self.selected_id)
        if part is None:
            return
        if part.source != "user":
            self.set_status("Bundled defaults cannot be deleted. Duplicate or edit to create a user part.")
            return

        default_backing_exists = part.id in self.default_ids
        action = "Remove user override" if default_backing_exists else "Delete user part"
        if not messagebox.askyesno(action, f"{action}: {part.name}?", parent=self):
            return

        self.store.delete_user_part(part.id)
        self.recent_ids = [item for item in self.recent_ids if item != part.id]
        self.store.save_recent_ids(self.recent_ids)
        self.reload_after_mutation(select_id=part.id if default_backing_exists else None)
        self.set_status(f"{action} complete.")

    def import_library(self) -> None:
        if self.dirty and not self.confirm_unsaved_changes():
            return
        path = filedialog.askopenfilename(
            parent=self,
            title="Import user library",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            count = self.store.import_user_parts(Path(path))
        except Exception as exc:
            messagebox.showerror("Import failed", str(exc), parent=self)
            return
        self.reload_after_mutation()
        self.set_status(f"Imported {count} user part(s).")

    def export_library(self) -> None:
        if self.dirty and not self.confirm_unsaved_changes():
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export user library",
            defaultextension=".json",
            initialfile="kicad_partstash_user_parts.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            count = self.store.export_user_parts(Path(path))
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc), parent=self)
            return
        self.set_status(f"Exported {count} user part(s).")

    def restore_defaults(self) -> None:
        if self.dirty and not self.confirm_unsaved_changes():
            return
        if not messagebox.askyesno(
            "Restore defaults",
            "Remove user edits to bundled defaults? Custom user parts will stay.",
            parent=self,
        ):
            return
        try:
            count = self.store.restore_default_overrides()
        except Exception as exc:
            messagebox.showerror("Restore failed", str(exc), parent=self)
            return
        self.reload_after_mutation()
        self.set_status(f"Restored {count} default override(s).")

    def save_current(self) -> None:
        part = self.find_part(self.selected_id)
        if part is None:
            return
        updated = copy.deepcopy(part)
        updated.name = self.field_vars["name"].get().strip() or "Unnamed Part"
        updated.category = self.field_vars["category"].get().strip() or "Uncategorized"
        updated.symbol = self.field_vars["symbol"].get().strip()
        updated.footprint = self.field_vars["footprint"].get().strip()
        updated.tags = [tag.strip() for tag in self.field_vars["tags"].get().split(",") if tag.strip()]
        requested_status = self.field_vars["status"].get().strip() or "draft"
        updated.description = self.description_text.get("1.0", "end-1c").strip()
        updated.snippet = self.snippet_text.get("1.0", "end-1c")
        updated.source = "user"

        validation = validate_snippet(updated.snippet)
        updated.status = validation.suggested_status(requested_status)
        if validation.lib_id and not updated.symbol:
            updated.symbol = validation.lib_id
        if validation.footprint and not updated.footprint:
            updated.footprint = validation.footprint

        self.store.save_user_part(updated)
        self.parts = [updated if item.id == updated.id else item for item in self.parts]
        self.select_part(updated.id)
        self.refresh_list()
        self.update_validation_summary(updated.snippet)
        self.set_status(f"Saved: {updated.name}")

    def copy_selected(self) -> None:
        if self.dirty and not self.confirm_unsaved_changes():
            return
        part = self.find_part(self.selected_id)
        if part is None:
            return
        if not part.has_snippet():
            self.set_status(f"No snippet captured yet: {part.name}")
            return

        snippet = part.snippet
        fields = required_template_fields(snippet, part.template_fields)
        unsupported_fields = unsupported_template_fields(fields)
        if unsupported_fields:
            self.set_status(f"Unsupported template fields: {', '.join(unsupported_fields)}")
            return
        if "pins" in fields:
            default_pins = part.default_template_values.get("pins", "4")
            dialog = PinDialog(self, default_pins=default_pins)
            self.wait_window(dialog)
            if dialog.result is None:
                return
            snippet = render_template(snippet, dialog.result)
        else:
            snippet = render_template(snippet, {})

        self.clipboard_clear()
        self.clipboard_append(snippet)
        self.update()
        self.add_recent(part.id)

        validation = validate_snippet(snippet)
        if validation.warnings:
            self.set_status(f"Copied with warning: {validation.summary()}")
        else:
            self.set_status(f"Copied: {part.name}")

    def capture_clipboard_for_selected(self) -> None:
        part = self.find_part(self.selected_id)
        if part is None:
            return
        try:
            snippet = self.clipboard_get()
        except tk.TclError:
            self.set_status("Clipboard has no text.")
            return
        if not snippet.strip():
            self.set_status("Clipboard has no text.")
            return

        validation = validate_snippet(snippet)
        self.set_text(self.snippet_text, snippet)
        self.update_validation_summary(snippet)
        self.field_vars["status"].set(validation.suggested_status(self.field_vars["status"].get()))
        if validation.lib_id and not self.field_vars["symbol"].get().strip():
            self.field_vars["symbol"].set(validation.lib_id)
        if validation.footprint and not self.field_vars["footprint"].get().strip():
            self.field_vars["footprint"].set(validation.footprint)
        self.mark_dirty()
        self.save_current()
        self.set_status(f"Captured: {validation.summary()}")

    def reload_after_mutation(self, select_id: str | None = None) -> None:
        self.parts = self.store.load_parts()
        self.refresh_list()
        if select_id in {part.id for part in self.parts}:
            self.select_part(select_id)  # type: ignore[arg-type]
        elif self.filtered_ids:
            self.select_part(self.filtered_ids[0])
        else:
            self.selected_id = None

    def add_recent(self, part_id: str) -> None:
        self.recent_ids = [part_id] + [item for item in self.recent_ids if item != part_id]
        self.recent_ids = self.recent_ids[:10]
        self.store.save_recent_ids(self.recent_ids)
        self.refresh_list()

    def confirm_unsaved_changes(self) -> bool:
        result = messagebox.askyesnocancel(
            "Unsaved changes",
            "Save changes before continuing?",
            parent=self,
        )
        if result is None:
            return False
        if result:
            self.save_current()
        else:
            self.dirty = False
        return True

    def mark_dirty(self) -> None:
        if not self.loading_fields and self.selected_id is not None:
            self.dirty = True

    def on_text_modified(self, event: tk.Event) -> None:
        widget = event.widget
        if widget.edit_modified():
            self.mark_dirty()
            if widget is self.snippet_text:
                self.update_validation_summary(self.snippet_text.get("1.0", "end-1c"))
            widget.edit_modified(False)

    def update_validation_summary(self, snippet: str) -> None:
        validation = validate_snippet(snippet)
        if not snippet.strip():
            self.validation_var.set("Snippet: empty.")
        elif validation.warnings:
            self.validation_var.set(f"Snippet: needs review - {validation.summary()}")
        else:
            self.validation_var.set(f"Snippet: OK - {validation.lib_id} / {validation.footprint}")

    def on_return_key(self, event: tk.Event) -> str | None:
        focus = self.focus_get()
        if focus in (self.description_text, self.snippet_text):
            return None
        if focus in self.edit_entries and focus is not self.search_entry:
            return None
        self.copy_selected()
        return "break"

    def on_save_key(self, _event: tk.Event) -> str:
        self.save_current()
        return "break"

    def on_escape_key(self, event: tk.Event) -> str | None:
        focus = self.focus_get()
        if focus in (self.description_text, self.snippet_text):
            return None
        self.clear_search()
        self.focus_search()
        return "break"

    def focus_listbox(self, event: tk.Event) -> str:
        if not self.filtered_ids:
            return "break"
        if not self.listbox.curselection():
            index = len(self.filtered_ids) - 1 if event.keysym == "Up" else 0
            self.listbox.selection_set(index)
            self.listbox.see(index)
        self.listbox.focus_set()
        return "break"

    def focus_search(self) -> None:
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, tk.END)

    def clear_search(self) -> None:
        self.search_var.set("")

    def set_text(self, widget: tk.Text, value: str) -> None:
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)

    def set_status(self, message: str) -> None:
        self.status_var.set(message)
        if self.status_after_id is not None:
            self.after_cancel(self.status_after_id)
        self.status_after_id = self.after(3000, lambda: self.status_var.set(DEFAULT_STATUS))

    def on_close(self) -> None:
        if self.dirty and not self.confirm_unsaved_changes():
            return
        self.destroy()


def main() -> None:
    app = App()
    app.mainloop()
