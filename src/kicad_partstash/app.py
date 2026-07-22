from __future__ import annotations

import copy
import tkinter as tk
import uuid
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk

from .models import Part
from .search import rank_parts
from .snippet_generators import generate_snippet, generator_template_fields
from .snippet_references import normalize_reference_designators
from .snippet_validation import validate_snippet
from .storage import PartStore
from .templates import render_template, required_template_fields, unsupported_template_fields


APP_TITLE = "Kicad-PartStash"
DEFAULT_STATUS = "Ready."
PIN_MIN = 1
PIN_MAX = 64

PREFERRED_FONTS = ("Aptos", "Segoe UI Variable Text", "Segoe UI")
PREFERRED_MONO_FONTS = ("Cascadia Mono", "Consolas", "Courier New")
FONT_FAMILY = "Segoe UI"
MONO_FONT_FAMILY = "Consolas"
COLOR_APP_BG = "#eef2f7"
COLOR_PANEL = "#ffffff"
COLOR_SIDEBAR = "#f7f9fc"
COLOR_BORDER = "#d9e1ec"
COLOR_TEXT = "#1f2937"
COLOR_MUTED = "#64748b"
COLOR_ACCENT = "#2563eb"
COLOR_ACCENT_DARK = "#1d4ed8"
COLOR_DANGER = "#b91c1c"
COLOR_SUCCESS = "#15803d"
COLOR_INPUT_BG = "#ffffff"
COLOR_FIELD_BG = "#fbfdff"
COLOR_FILTER_ACTIVE_BG = "#dbeafe"
COLOR_FILTER_ACTIVE_TEXT = "#1e40af"


def choose_font(families: tuple[str, ...], fallback: str) -> str:
    available = set(tkfont.families())
    for family in families:
        if family in available:
            return family
    return fallback


def normalize_padding(padding: int | tuple[int, int] | tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    if isinstance(padding, int):
        return (padding, padding, padding, padding)
    if len(padding) == 2:
        horizontal, vertical = padding
        return (horizontal, vertical, horizontal, vertical)
    return padding


class RoundedFrame(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        fill: str,
        *,
        radius: int = 12,
        padding: int | tuple[int, int] | tuple[int, int, int, int] = 0,
        outline: str = "",
        background: str = COLOR_APP_BG,
        width: int = 1,
        height: int = 1,
    ) -> None:
        super().__init__(parent, bg=background, highlightthickness=0, borderwidth=0)
        self.fill = fill
        self.outline = outline or fill
        self.radius = radius
        self.padding = normalize_padding(padding)
        self.canvas = tk.Canvas(self, bg=background, highlightthickness=0, borderwidth=0, width=width, height=height)
        self.canvas.pack(fill="both", expand=True)
        self.content = tk.Frame(self.canvas, bg=fill, highlightthickness=0, borderwidth=0)
        left, top, _, _ = self.padding
        self.background_id = self.canvas.create_polygon(0, 0, fill=fill, outline=self.outline, smooth=True)
        self.window_id = self.canvas.create_window(left, top, anchor="nw", window=self.content)
        self.canvas.bind("<Configure>", self._draw)

    def _draw(self, event: tk.Event) -> None:
        width = max(event.width, 2)
        height = max(event.height, 2)
        left, top, right, bottom = self.padding
        self.canvas.coords(self.background_id, *rounded_rectangle_points(1, 1, width - 1, height - 1, self.radius))
        self.canvas.itemconfigure(self.background_id, fill=self.fill, outline=self.outline)
        self.canvas.coords(self.window_id, left, top)
        self.canvas.itemconfigure(self.window_id, width=max(1, width - left - right), height=max(1, height - top - bottom))


def rounded_rectangle_points(x1: int, y1: int, x2: int, y2: int, radius: int) -> list[int]:
    radius = max(0, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    return [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]


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
        self.category_filter = ""
        self.filter_buttons: dict[str, ttk.Button] = {}
        self.more_filter_button: ttk.Button | None = None

        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value=DEFAULT_STATUS)
        self.validation_var = tk.StringVar(value="Snippet: no snippet selected.")
        self.detail_title_var = tk.StringVar(value="No part selected")
        self.detail_subtitle_var = tk.StringVar(value="Search or create a part to start.")
        self.result_count_var = tk.StringVar(value="0 parts")
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
        self.minsize(1080, 680)
        self.configure(bg=COLOR_APP_BG)
        self.ui_font = choose_font(PREFERRED_FONTS, FONT_FAMILY)
        self.mono_font = choose_font(PREFERRED_MONO_FONTS, MONO_FONT_FAMILY)
        self._configure_style()
        self._build_menu()
        self._build_ui()
        self._bind_events()
        self.load_data()
        self.after(0, self.maximize_window)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.option_add("*Font", (self.ui_font, 10))
        self.option_add("*Menu.Font", (self.ui_font, 10))

        style.configure(".", font=(self.ui_font, 10), foreground=COLOR_TEXT)
        style.configure("App.TFrame", background=COLOR_APP_BG)
        style.configure("Panel.TFrame", background=COLOR_PANEL)
        style.configure("Sidebar.TFrame", background=COLOR_SIDEBAR)
        style.configure("Toolbar.TFrame", background=COLOR_PANEL)
        style.configure("Status.TFrame", background=COLOR_APP_BG)

        style.configure("TLabel", background=COLOR_PANEL, foreground=COLOR_TEXT)
        style.configure("Sidebar.TLabel", background=COLOR_SIDEBAR, foreground=COLOR_TEXT)
        style.configure("Title.TLabel", background=COLOR_PANEL, foreground=COLOR_TEXT, font=(self.ui_font, 18, "bold"))
        style.configure("AppTitle.TLabel", background=COLOR_SIDEBAR, foreground=COLOR_TEXT, font=(self.ui_font, 17, "bold"))
        style.configure("Section.TLabel", background=COLOR_PANEL, foreground=COLOR_TEXT, font=(self.ui_font, 11, "bold"))
        style.configure("Field.TLabel", background=COLOR_PANEL, foreground=COLOR_MUTED, font=(self.ui_font, 9, "bold"))
        style.configure("Muted.TLabel", background=COLOR_PANEL, foreground=COLOR_MUTED)
        style.configure("SidebarMuted.TLabel", background=COLOR_SIDEBAR, foreground=COLOR_MUTED)
        style.configure("Status.TLabel", background=COLOR_APP_BG, foreground=COLOR_MUTED)
        style.configure("StatusSuccess.TLabel", background=COLOR_APP_BG, foreground=COLOR_SUCCESS)
        style.configure("Validation.TLabel", background=COLOR_PANEL, foreground=COLOR_MUTED)

        style.configure("TEntry", fieldbackground=COLOR_INPUT_BG, bordercolor=COLOR_BORDER, lightcolor=COLOR_BORDER, darkcolor=COLOR_BORDER, padding=5)
        style.configure("TSpinbox", fieldbackground=COLOR_INPUT_BG, bordercolor=COLOR_BORDER, arrowsize=13, padding=4)

        style.configure("TButton", padding=(10, 6), background="#edf2f7", bordercolor=COLOR_BORDER, focusthickness=1)
        style.map("TButton", background=[("active", "#e2e8f0")])
        style.configure("Accent.TButton", foreground="#ffffff", background=COLOR_ACCENT, bordercolor=COLOR_ACCENT_DARK, padding=(12, 7))
        style.map("Accent.TButton", background=[("active", COLOR_ACCENT_DARK), ("pressed", COLOR_ACCENT_DARK)])
        style.configure("Ghost.TButton", background=COLOR_SIDEBAR, bordercolor=COLOR_BORDER, padding=(8, 5))
        style.map("Ghost.TButton", background=[("active", "#e8eef6")])
        style.configure("Filter.TButton", background=COLOR_SIDEBAR, foreground=COLOR_MUTED, bordercolor=COLOR_BORDER, padding=(3, 2), font=(self.ui_font, 8))
        style.map("Filter.TButton", background=[("active", "#e8eef6")])
        style.configure("FilterActive.TButton", background=COLOR_FILTER_ACTIVE_BG, foreground=COLOR_FILTER_ACTIVE_TEXT, bordercolor="#bfdbfe", padding=(3, 2), font=(self.ui_font, 8, "bold"))
        style.map("FilterActive.TButton", background=[("active", "#bfdbfe")])
        style.configure("Danger.TButton", foreground=COLOR_DANGER, background="#fff5f5", bordercolor="#fecaca")
        style.map("Danger.TButton", background=[("active", "#fee2e2")])

        style.configure("Vertical.TScrollbar", background="#e2e8f0", troughcolor=COLOR_PANEL, bordercolor=COLOR_PANEL, arrowcolor=COLOR_MUTED)

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

        sidebar_panel = RoundedFrame(self, fill=COLOR_SIDEBAR, radius=16, padding=(18, 16, 12, 12), outline=COLOR_BORDER, width=360)
        sidebar_panel.grid(row=0, column=0, sticky="nsew", padx=(12, 10), pady=(12, 0))
        sidebar = sidebar_panel.content
        sidebar.rowconfigure(5, weight=1)
        sidebar.columnconfigure(0, weight=1)

        ttk.Label(sidebar, text="Kicad-PartStash", style="AppTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            sidebar,
            text="Trusted KiCad parts, ready to paste",
            style="SidebarMuted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 18))

        ttk.Label(sidebar, text="Search", style="Sidebar.TLabel").grid(row=2, column=0, sticky="w")
        search_frame = ttk.Frame(sidebar, style="Sidebar.TFrame")
        search_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 8))
        search_frame.columnconfigure(0, weight=1)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=34)
        self.search_entry.grid(row=0, column=0, sticky="ew")
        ttk.Button(search_frame, text="x", width=3, command=self.clear_search_and_focus, style="Ghost.TButton").grid(
            row=0, column=1, padx=(6, 0)
        )

        filter_frame = ttk.Frame(sidebar, style="Sidebar.TFrame")
        filter_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 8))
        for label, category, width in [
            ("All", "", 4),
            ("Pass", "Passives", 5),
            ("Conn", "Connectors", 5),
            ("ICs", "ICs", 4),
            ("Sw", "Switches", 3),
            ("Ready", "Ready Blocks", 6),
        ]:
            button = ttk.Button(
                filter_frame,
                text=label,
                width=width,
                style="Filter.TButton",
                command=lambda selected=category: self.set_category_filter(selected),
            )
            button.pack(side="left", padx=(0, 3))
            self.filter_buttons[category] = button
        self.more_filter_button = ttk.Button(
            filter_frame,
            text="More v",
            width=6,
            style="Filter.TButton",
            command=self.show_category_menu,
        )
        self.more_filter_button.pack(side="left")

        list_panel = RoundedFrame(sidebar, fill=COLOR_PANEL, radius=10, padding=1, outline=COLOR_BORDER, background=COLOR_SIDEBAR)
        list_panel.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(6, 0))
        list_frame = list_panel.content
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.listbox = tk.Listbox(
            list_frame,
            width=40,
            exportselection=False,
            activestyle="none",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            highlightcolor=COLOR_ACCENT,
            background=COLOR_PANEL,
            foreground=COLOR_TEXT,
            selectbackground=COLOR_ACCENT,
            selectforeground="#ffffff",
            font=(self.ui_font, 10),
            relief="flat",
        )
        self.listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        ttk.Label(sidebar, textvariable=self.result_count_var, style="SidebarMuted.TLabel").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        library_actions = ttk.Frame(sidebar, style="Sidebar.TFrame")
        library_actions.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        for column in range(3):
            library_actions.columnconfigure(column, weight=1)
        ttk.Button(library_actions, text="New", command=self.new_part, style="Ghost.TButton").grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(library_actions, text="Duplicate", command=self.duplicate_selected, style="Ghost.TButton").grid(
            row=0, column=1, sticky="ew", padx=(0, 6)
        )
        ttk.Button(library_actions, text="Delete", command=self.delete_selected, style="Danger.TButton").grid(
            row=0, column=2, sticky="ew"
        )

        main_panel = RoundedFrame(self, fill=COLOR_PANEL, radius=16, padding=(18, 16, 18, 12), outline=COLOR_BORDER, width=700)
        main_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=(12, 0))
        main = main_panel.content
        main.columnconfigure(1, weight=1)
        main.rowconfigure(11, weight=1)

        header = ttk.Frame(main, style="Panel.TFrame")
        header.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, textvariable=self.detail_title_var, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.detail_subtitle_var, style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 0))

        rows = [
            ("Name", "name"),
            ("Category", "category"),
            ("Symbol", "symbol"),
            ("Footprint", "footprint"),
            ("Tags", "tags"),
            ("Status", "status"),
            ("Source", "source"),
        ]
        for offset, (label, key) in enumerate(rows, start=1):
            ttk.Label(main, text=label, style="Field.TLabel").grid(row=offset, column=0, sticky="w", pady=4, padx=(0, 12))
            entry = ttk.Entry(main, textvariable=self.field_vars[key])
            if key == "source":
                entry.configure(state="readonly")
            entry.grid(row=offset, column=1, columnspan=2, sticky="ew", pady=4)
            self.edit_entries.append(entry)

        ttk.Label(main, text="Description", style="Section.TLabel").grid(
            row=8, column=0, columnspan=3, sticky="w", pady=(16, 5)
        )
        description_panel = RoundedFrame(main, fill=COLOR_INPUT_BG, radius=10, padding=1, outline=COLOR_BORDER, background=COLOR_PANEL)
        description_panel.grid(row=9, column=0, columnspan=3, sticky="ew")
        self.description_text = tk.Text(
            description_panel.content,
            height=3,
            wrap="word",
            undo=True,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            background=COLOR_INPUT_BG,
            foreground=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            font=(self.ui_font, 10),
            padx=8,
            pady=7,
        )
        self.description_text.pack(fill="both", expand=True)

        ttk.Label(main, text="Raw KiCad snippet", style="Section.TLabel").grid(
            row=10, column=0, columnspan=3, sticky="w", pady=(16, 5)
        )
        snippet_panel = RoundedFrame(main, fill=COLOR_FIELD_BG, radius=10, padding=1, outline=COLOR_BORDER, background=COLOR_PANEL)
        snippet_panel.grid(row=11, column=0, columnspan=2, sticky="nsew")
        self.snippet_text = tk.Text(
            snippet_panel.content,
            height=10,
            wrap="none",
            undo=True,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            background=COLOR_FIELD_BG,
            foreground=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            font=(self.mono_font, 9),
            padx=8,
            pady=7,
        )
        self.snippet_text.pack(fill="both", expand=True)
        snippet_scroll = ttk.Scrollbar(main, orient="vertical", command=self.snippet_text.yview)
        snippet_scroll.grid(row=11, column=2, sticky="ns")
        self.snippet_text.configure(yscrollcommand=snippet_scroll.set)

        ttk.Label(main, textvariable=self.validation_var, wraplength=760, style="Validation.TLabel").grid(
            row=12, column=0, columnspan=3, sticky="w", pady=(9, 0)
        )

        actions = ttk.Frame(main, style="Toolbar.TFrame")
        actions.grid(row=13, column=0, columnspan=3, sticky="e", pady=(14, 0))
        ttk.Button(actions, text="Capture Clipboard", command=self.capture_clipboard_for_selected).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(actions, text="Save", command=self.save_current).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(actions, text="Copy", command=self.copy_selected, style="Accent.TButton").grid(row=0, column=2)

        status_bar = ttk.Frame(self, padding=(14, 8, 14, 8), style="Status.TFrame")
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.status_label = ttk.Label(status_bar, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.grid(row=0, column=0, sticky="w")
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

    def refresh_list(self, preserve_order: bool = False) -> None:
        query = self.search_var.get().strip()
        current = self.selected_id
        if preserve_order and self.filtered_ids:
            parts_by_id = {part.id: part for part in self.parts}
            ordered_parts = [parts_by_id[part_id] for part_id in self.filtered_ids if part_id in parts_by_id]
        else:
            ordered_parts = [ranked.part for ranked in rank_parts(self.parts, query, self.recent_ids)]
        if self.category_filter:
            ordered_parts = [part for part in ordered_parts if part.category == self.category_filter]

        self.listbox.delete(0, tk.END)
        self.filtered_ids = []
        for part in ordered_parts:
            prefix = "Recent" if part.id in self.recent_ids else part.category
            marker = "*" if part.source == "user" else ""
            label = f"{prefix} / {part.name}{marker}"
            self.filtered_ids.append(part.id)
            self.listbox.insert(tk.END, label)

        self.update_result_count(query)
        self.update_filter_buttons()

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
        self.detail_title_var.set("No part selected")
        self.detail_subtitle_var.set("Search or create a part to start.")
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
        self.detail_title_var.set(part.name)
        self.detail_subtitle_var.set(self.part_subtitle(part))
        self.set_text(self.description_text, part.description)
        self.set_text(self.snippet_text, part.snippet)
        self.update_validation_summary(part)
        self.description_text.edit_modified(False)
        self.snippet_text.edit_modified(False)
        self.dirty = False
        self.loading_fields = False

    def part_subtitle(self, part: Part) -> str:
        bits = [part.category or "Uncategorized"]
        if part.status:
            bits.append(part.status.replace("_", " "))
        if part.generator:
            bits.append("generated")
        if part.source == "user":
            bits.append("user library")
        return " - ".join(bits)

    def update_result_count(self, query: str) -> None:
        count = len(self.filtered_ids)
        noun = "part" if count == 1 else "parts"
        scope = f" in {self.category_filter}" if self.category_filter else ""
        if query:
            self.result_count_var.set(f"{count} {noun} found{scope}")
        else:
            self.result_count_var.set(f"{count} {noun}{scope}")

    def category_options(self) -> list[str]:
        return sorted({part.category for part in self.parts if part.category})

    def set_category_filter(self, category: str) -> None:
        self.category_filter = category
        self.refresh_list()

    def show_category_menu(self) -> None:
        if self.more_filter_button is None:
            return
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label="All", command=lambda: self.set_category_filter(""))
        categories = self.category_options()
        if categories:
            menu.add_separator()
        for category in categories:
            label = category
            if category == self.category_filter:
                label = f"{category} *"
            menu.add_command(label=label, command=lambda selected=category: self.set_category_filter(selected))
        x = self.more_filter_button.winfo_rootx()
        y = self.more_filter_button.winfo_rooty() + self.more_filter_button.winfo_height()
        menu.tk_popup(x, y)

    def update_filter_buttons(self) -> None:
        for category, button in self.filter_buttons.items():
            style = "FilterActive.TButton" if category == self.category_filter else "Filter.TButton"
            button.configure(style=style)
        if self.more_filter_button is not None:
            quick_categories = set(self.filter_buttons)
            more_active = bool(self.category_filter and self.category_filter not in quick_categories)
            self.more_filter_button.configure(style="FilterActive.TButton" if more_active else "Filter.TButton")

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

        if updated.generator and not updated.snippet.strip():
            updated.status = requested_status if requested_status != "needs_snippet" else "generator"
        else:
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
        self.update_validation_summary(updated)
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

        try:
            snippet = self.build_snippet_for_copy(part)
        except ValueError as exc:
            self.set_status(str(exc))
            return
        if snippet is None:
            return

        self.clipboard_clear()
        self.clipboard_append(snippet)
        self.update()
        self.add_recent(part.id)

        validation = validate_snippet(snippet)
        if validation.warnings:
            self.set_status(f"Copied with warning: {validation.summary()}")
        else:
            self.set_status(f"Copied: {part.name}", kind="success")

    def build_snippet_for_copy(self, part: Part) -> str | None:
        if part.generator:
            fields = generator_template_fields(part.generator)
            values = self.ask_for_template_values(fields, part.default_template_values)
            if values is None:
                return None
            return normalize_reference_designators(generate_snippet(part.generator, values))

        snippet = part.snippet
        fields = required_template_fields(snippet, part.template_fields)
        unsupported_fields = unsupported_template_fields(fields)
        if unsupported_fields:
            raise ValueError(f"Unsupported template fields: {', '.join(unsupported_fields)}")
        values = self.ask_for_template_values(fields, part.default_template_values)
        if values is None:
            return None
        return normalize_reference_designators(render_template(snippet, values))

    def ask_for_template_values(
        self, fields: list[str], default_template_values: dict[str, str]
    ) -> dict[str, str] | None:
        if "pins" not in fields:
            return {}
        default_pins = default_template_values.get("pins", "4")
        dialog = PinDialog(self, default_pins=default_pins)
        self.wait_window(dialog)
        return dialog.result

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

        snippet = normalize_reference_designators(snippet)
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
        self.refresh_list(preserve_order=True)

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

    def update_validation_summary(self, part_or_snippet: Part | str) -> None:
        if isinstance(part_or_snippet, Part):
            part = part_or_snippet
            snippet = part.snippet
            if part.generator and not snippet.strip():
                default_pins = part.default_template_values.get("pins", "4")
                self.validation_var.set(f"Generator: asks for pin count. Default: {default_pins}.")
                return
        else:
            snippet = part_or_snippet

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

    def clear_search_and_focus(self) -> None:
        self.clear_search()
        self.focus_search()

    def set_text(self, widget: tk.Text, value: str) -> None:
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)

    def set_status(self, message: str, kind: str = "normal") -> None:
        self.status_var.set(message)
        self.status_label.configure(style="StatusSuccess.TLabel" if kind == "success" else "Status.TLabel")
        if self.status_after_id is not None:
            self.after_cancel(self.status_after_id)
        if kind == "success":
            self.status_after_id = self.after(3000, self.normalize_status_color)
        else:
            self.status_after_id = self.after(3000, self.reset_status)

    def normalize_status_color(self) -> None:
        self.status_label.configure(style="Status.TLabel")
        self.status_after_id = None

    def reset_status(self) -> None:
        self.status_var.set(DEFAULT_STATUS)
        self.status_label.configure(style="Status.TLabel")
        self.status_after_id = None

    def maximize_window(self) -> None:
        try:
            self.state("zoomed")
        except tk.TclError:
            width = self.winfo_screenwidth()
            height = self.winfo_screenheight()
            self.geometry(f"{width}x{height}+0+0")

    def on_close(self) -> None:
        if self.dirty and not self.confirm_unsaved_changes():
            return
        self.destroy()


def main() -> None:
    app = App()
    app.mainloop()
