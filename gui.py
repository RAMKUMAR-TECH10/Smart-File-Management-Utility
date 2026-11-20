"""Explorer-style CustomTkinter interface for the Smart File Manager."""

from __future__ import annotations

from pathlib import Path
from tkinter import Canvas, Menu, messagebox, simpledialog, ttk

import customtkinter as ctk

from duplicate_finder import delete_duplicates, find_duplicates
from file_explorer import FileEntry, get_quick_locations, list_directory, navigate_parent, open_path
from file_metadata import CATEGORIES, format_size, get_metadata
from file_operations import (
    copy_file,
    create_folder,
    delete_file,
    move_file,
    rename_file,
)
from file_organizer import apply_organization_plan, build_organization_plan
from file_search import SearchFilters, search_files
from history_manager import HistoryManager
from logger import get_logger
from storage_analyzer import analyze_folder
from validation import validate_folder

LOG = get_logger()
MODES = ("Explorer", "Organizer", "Duplicates", "Storage", "History")


class FileManagerApp(ctk.CTk):
    """Main application window with a file-browser workspace and tool modes."""

    def __init__(self) -> None:
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        super().__init__()
        self.title("Smart File Manager")
        self.geometry("1320x780")
        self.minsize(1080, 660)

        self.history = HistoryManager()
        self.current_path = Path.home()
        self.back_stack: list[Path] = []
        self.forward_stack: list[Path] = []
        self.mode = "Explorer"
        self.entries: list[FileEntry] = []
        self.plan_items: list = []
        self.duplicate_groups: dict[str, int] = {}
        self.chart_data: dict[str, int] = {}
        self.category_vars: dict[str, ctk.BooleanVar] = {}

        self._build_ui()
        self.navigate(self.current_path, track=False)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self, height=58, corner_radius=0)
        header.grid(row=0, column=0, columnspan=3, sticky="ew")
        ctk.CTkLabel(header, text="SMART FILE MANAGER", font=ctk.CTkFont(size=17, weight="bold"))\
            .pack(side="left", padx=18)
        self.mode_selector = ctk.CTkSegmentedButton(header, values=MODES, command=self.change_mode)
        self.mode_selector.set("Explorer")
        self.mode_selector.pack(side="left", padx=14, pady=10)
        self.theme_button = ctk.CTkButton(
            header, text="Light mode", width=100, command=self.toggle_theme
        )
        self.theme_button.pack(side="right", padx=14)

        self.nav_bar = ctk.CTkFrame(self, height=42, corner_radius=0)
        self.nav_bar.grid(row=1, column=0, columnspan=3, sticky="ew")
        for text, command, width in (
            ("←", self.go_back, 30),
            ("→", self.go_forward, 30),
            ("↑", self.go_up, 30),
            ("⟳", self.refresh, 30),
        ):
            ctk.CTkButton(self.nav_bar, text=text, width=width, command=command).pack(
                side="left", padx=(12 if text == "←" else 3), pady=5
            )
        self.path_entry = ctk.CTkEntry(self.nav_bar, height=30)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=10, pady=5)
        self.path_entry.bind("<Return>", lambda _: self.navigate(self.path_entry.get()))
        self.search_entry = ctk.CTkEntry(
            self.nav_bar, placeholder_text="Search files and folders...", width=270, height=30
        )
        self.search_entry.pack(side="left", padx=(4, 6), pady=5)
        self.search_entry.bind("<Return>", lambda _: self.run_search())
        ctk.CTkButton(self.nav_bar, text="Search", width=80, command=self.run_search).pack(
            side="left", padx=(0, 12), pady=5
        )

        self.action_bar = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color=("gray88", "gray20"))
        self.action_bar.grid(row=2, column=0, columnspan=3, sticky="ew")

        sidebar = ctk.CTkFrame(self, width=220, corner_radius=6)
        sidebar.grid(row=3, column=0, sticky="nsew", padx=(10, 6), pady=(8, 6))
        sidebar.grid_propagate(False)
        ctk.CTkLabel(sidebar, text="QUICK ACCESS", font=ctk.CTkFont(size=12, weight="bold"))\
            .grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))
        for index, (label, path) in enumerate(get_quick_locations(), start=1):
            ctk.CTkButton(
                sidebar, text=f"  {label}", anchor="w", height=30,
                command=lambda target=path: self.navigate(target),
            ).grid(row=index, column=0, sticky="ew", padx=8, pady=2)
        row = len(get_quick_locations()) + 1
        ctk.CTkLabel(sidebar, text="TOOLS", font=ctk.CTkFont(size=12, weight="bold"))\
            .grid(row=row, column=0, sticky="w", padx=14, pady=(16, 8))
        for offset, mode in enumerate(MODES[1:], start=1):
            ctk.CTkButton(
                sidebar, text=f"  {mode}", anchor="w", height=30,
                command=lambda selected=mode: self.change_mode(selected),
            ).grid(row=row + offset, column=0, sticky="ew", padx=8, pady=2)
        ctk.CTkButton(
            sidebar,
            text="  Recovery folder",
            anchor="w",
            height=30,
            command=lambda: self.navigate(Path.home() / ".smart_file_manager" / "recycle_bin"),
        ).grid(row=row + len(MODES), column=0, sticky="ew", padx=8, pady=2)

        main = ctk.CTkFrame(self, corner_radius=6)
        main.grid(row=3, column=1, sticky="nsew", padx=6, pady=(8, 6))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        self.tool_panel = ctk.CTkFrame(main, height=140, corner_radius=6)
        self.tool_panel.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

        table_frame = ctk.CTkFrame(main, corner_radius=6)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=4)
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            table_frame,
            columns=("name", "type", "size", "modified"),
            show="headings",
            selectmode="extended",
            height=18,
        )
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=6)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=6, padx=(0, 6))
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.tag_configure("folder", foreground="#4da3ff")
        self.tree.tag_configure("conflict", foreground="#ff8a65")
        self.tree.tag_configure("duplicate", foreground="#f4b942")
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Button-3>", self.on_right_click)

        self.chart_frame = ctk.CTkFrame(main, height=210, corner_radius=6)
        self.chart_frame.grid(row=3, column=0, sticky="ew", padx=8, pady=(4, 8))
        self.chart = Canvas(self.chart_frame, highlightthickness=0, height=190)
        self.chart.pack(fill="x", expand=True, padx=8, pady=8)
        self.chart.bind("<Configure>", lambda _: self.draw_chart())
        self.chart_frame.grid_remove()

        details = ctk.CTkFrame(self, width=280, corner_radius=6)
        details.grid(row=3, column=2, sticky="nsew", padx=(6, 10), pady=(8, 6))
        details.grid_propagate(False)
        ctk.CTkLabel(details, text="PROPERTIES", font=ctk.CTkFont(size=12, weight="bold"))\
            .pack(anchor="w", padx=14, pady=(14, 6))
        self.details_box = ctk.CTkTextbox(details, wrap="word", font=ctk.CTkFont(size=12))
        self.details_box.pack(fill="both", expand=True, padx=12, pady=4)
        self.details_box.configure(state="disabled")

        status = ctk.CTkFrame(self, height=32, corner_radius=0)
        status.grid(row=4, column=0, columnspan=3, sticky="ew")
        self.status_label = ctk.CTkLabel(status, text="Ready", anchor="w")
        self.status_label.pack(side="left", padx=16, pady=4)
        self.summary_label = ctk.CTkLabel(status, text="", anchor="e")
        self.summary_label.pack(side="right", padx=16, pady=4)
        self.progress = ctk.CTkProgressBar(status, mode="indeterminate", width=110)
        self.busy = False

        self.bind("<F2>", lambda _: self.rename_selected())
        self.bind("<Delete>", lambda _: self.delete_selected())
        self.bind("<Control-n>", lambda _: self.new_folder())
        self.bind("<Control-r>", lambda _: self.refresh())
        self.bind("<BackSpace>", lambda _: self.go_up())

    def _set_status(self, text: str, summary: str = "") -> None:
        self.status_label.configure(text=text)
        if summary:
            self.summary_label.configure(text=summary)

    def _busy_start(self, text: str = "Working...") -> None:
        self._set_status(text)
        self.progress.pack(side="right", padx=(0, 8), pady=4)
        self.progress.start()
        self.busy = True
        self.update_idletasks()

    def _busy_stop(self) -> None:
        if self.busy:
            self.progress.stop()
            self.progress.pack_forget()
            self.busy = False

    def _clear_action_bar(self) -> None:
        for widget in self.action_bar.winfo_children():
            widget.destroy()

    def _action(self, text: str, command: object, width: int = 118) -> None:
        ctk.CTkButton(self.action_bar, text=text, width=width, height=28, command=command)\
            .pack(side="left", padx=(10, 0), pady=5)

    def _clear_tool_panel(self) -> None:
        for widget in self.tool_panel.winfo_children():
            widget.destroy()

    def _set_columns(self, columns: list[tuple[str, str, int]]) -> None:
        self.tree.delete(*self.tree.get_children())
        keys = [column[0] for column in columns]
        self.tree.configure(columns=keys)
        for key, heading, width in columns:
            self.tree.heading(key, text=heading)
            self.tree.column(key, width=width, stretch=(key == keys[0]))

    def _rows(self, rows: list[tuple[str, tuple, str]]) -> None:
        self.tree.delete(*self.tree.get_children())
        for iid, values, tag in rows:
            self.tree.insert("", "end", iid=iid, values=values, tags=(tag,) if tag else ())

    def _selected_paths(self) -> list[Path]:
        if self.mode == "History":
            return []
        return [Path(iid) for iid in self.tree.selection() if iid]

    def change_mode(self, mode: str) -> None:
        if mode not in MODES:
            return
        self.mode = mode
        self.mode_selector.set(mode)
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, str(self.current_path))
        self.search_entry.delete(0, "end")
        self.tree.delete(*self.tree.get_children())
        self.details_box.configure(state="normal")
        self.details_box.delete("1.0", "end")
        self.details_box.configure(state="disabled")
        self._clear_action_bar()
        self._clear_tool_panel()
        self.chart_frame.grid_remove()

        if mode == "Explorer":
            self._action("New folder", self.new_folder)
            self._action("Rename", self.rename_selected, 90)
            self._action("Copy to...", self.copy_selected, 100)
            self._action("Move to...", self.move_selected, 100)
            self._action("Delete", self.delete_selected, 90)
            self._action("Open", self.open_selected, 80)
            self._set_status("Explorer mode - double-click a folder to open it")
            self.refresh()
        elif mode == "Organizer":
            self._action("Refresh", self.refresh, 90)
            self._build_organizer_panel()
        elif mode == "Duplicates":
            self._action("Refresh", self.refresh, 90)
            self._build_duplicate_panel()
        elif mode == "Storage":
            self._action("Refresh", self.refresh, 90)
            self._build_storage_panel()
        else:
            self._action("Refresh", self.refresh, 90)
            self._action("Clear history", self.clear_history, 120)
            self.show_history()

    def navigate(self, path: str | Path, track: bool = True) -> None:
        if not validate_folder(path):
            messagebox.showerror("Invalid folder", "The selected folder does not exist.", parent=self)
            return
        target = Path(path).expanduser().resolve()
        if track and target != self.current_path:
            self.back_stack.append(self.current_path)
            self.forward_stack.clear()
        self.current_path = target
        if self.mode != "Explorer":
            self.change_mode("Explorer")
        else:
            self.refresh()

    def go_back(self) -> None:
        if not self.back_stack:
            return
        self.forward_stack.append(self.current_path)
        self.current_path = self.back_stack.pop()
        self.refresh()

    def go_forward(self) -> None:
        if not self.forward_stack:
            return
        self.back_stack.append(self.current_path)
        self.current_path = self.forward_stack.pop()
        self.refresh()

    def go_up(self) -> None:
        self.navigate(navigate_parent(self.current_path))

    def refresh(self) -> None:
        if self.mode in ("Explorer", "Search"):
            self.refresh_explorer()
        elif self.mode == "Organizer":
            self.preview_organization()
        elif self.mode == "Duplicates":
            self.scan_duplicates()
        elif self.mode == "Storage":
            self.analyze_storage()
        else:
            self.show_history()

    def refresh_explorer(self) -> None:
        self.entries = list_directory(self.current_path)
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, str(self.current_path))
        self._set_columns([
            ("name", "Name", 430), ("type", "Type", 180),
            ("size", "Size", 110), ("modified", "Modified", 165),
        ])
        rows = [
            (
                str(entry.path),
                (entry.name, entry.type_label, entry.size_text, entry.modified_text),
                "folder" if entry.is_dir else "",
            )
            for entry in self.entries
        ]
        self._rows(rows)
        folders = sum(item.is_dir for item in self.entries)
        size = sum(item.size for item in self.entries)
        self._set_status(
            "Ready",
            f"{len(self.entries)} items | {folders} folders | {len(self.entries) - folders} files | "
            f"{format_size(size)}",
        )

    def on_select(self, _event: object = None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        if self.mode in ("History", "Storage") and ":" in item and not Path(item).exists():
            return
        path = Path(item)
        if not path.exists():
            return
        info = get_metadata(path)
        text = "\n".join(f"{key}: {value}" for key, value in info.items())
        self.details_box.configure(state="normal")
        self.details_box.delete("1.0", "end")
        self.details_box.insert("1.0", text)
        self.details_box.configure(state="disabled")
        count = len(selected)
        self._set_status(f"Selected {count} item{'s' if count != 1 else ''}: {path.name}")

    def on_double_click(self, _event: object = None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        if self.mode == "Storage" and item.startswith("folder:"):
            self.navigate(Path(item.removeprefix("folder:")))
            return
        path = Path(item)
        if self.mode in ("Explorer", "Search", "Duplicates", "Storage") and path.is_dir():
            self.navigate(path)
        elif path.exists():
            result = open_path(path)
            if not result.success:
                messagebox.showerror("Cannot open", str(result), parent=self)

    def on_right_click(self, event: object) -> None:
        row = self.tree.identify_row(event.y)
        if row and row not in self.tree.selection():
            self.tree.selection_set(row)
        if not self.tree.selection():
            return
        menu = Menu(self, tearoff=0)
        menu.add_command(label="Open", command=self.open_selected)
        if self.mode in ("Explorer", "Search"):
            menu.add_command(label="Rename (F2)", command=self.rename_selected)
            menu.add_command(label="Copy to...", command=self.copy_selected)
            menu.add_command(label="Move to...", command=self.move_selected)
            menu.add_separator()
            menu.add_command(label="Delete (safe)", command=self.delete_selected)
        menu.add_separator()
        menu.add_command(label="Properties", command=self.on_select)
        menu.tk_popup(event.x_root, event.y_root)

    def open_selected(self) -> None:
        for path in self._selected_paths():
            result = open_path(path)
            if not result.success:
                messagebox.showerror("Cannot open", str(result), parent=self)

    def new_folder(self) -> None:
        name = simpledialog.askstring("New folder", "Folder name:", parent=self)
        if not name:
            return
        result = create_folder(self.current_path, name, self.history)
        self._notify(result)
        if self.mode == "Explorer":
            self.refresh_explorer()

    def rename_selected(self) -> None:
        selected = self._selected_paths()
        if len(selected) != 1:
            messagebox.showinfo("Rename", "Select exactly one item.", parent=self)
            return
        source = selected[0]
        name = simpledialog.askstring(
            "Rename", "New name:", initialvalue=source.name, parent=self
        )
        if not name:
            return
        result = rename_file(source, name, self.history)
        self._notify(result)
        self.refresh_explorer()

    def _ask_destination(self) -> str | None:
        return simpledialog.askstring(
            "Destination", "Destination folder:", initialvalue=str(self.current_path), parent=self
        )

    def _confirm_overwrite(self, targets: list[Path]) -> bool | None:
        existing = [target for target in targets if target.exists()]
        if not existing:
            return False
        return messagebox.askyesno(
            "Overwrite files",
            f"{len(existing)} destination file(s) already exist. Overwrite them?",
            parent=self,
        )

    def copy_selected(self) -> None:
        selected = [path for path in self._selected_paths() if path.is_file()]
        if not selected:
            messagebox.showinfo("Copy", "Select one or more files.", parent=self)
            return
        destination = self._ask_destination()
        if not destination:
            return
        targets = [
            Path(destination) / path.name if Path(destination).is_dir() else Path(destination)
            for path in selected
        ]
        overwrite = self._confirm_overwrite(targets)
        if overwrite is None:
            return
        for path in selected:
            self._notify(copy_file(path, destination, overwrite=bool(overwrite), history=self.history))

    def move_selected(self) -> None:
        selected = self._selected_paths()
        if not selected:
            return
        destination = self._ask_destination()
        if not destination:
            return
        targets = [
            Path(destination) / path.name if Path(destination).is_dir() else Path(destination)
            for path in selected
        ]
        overwrite = self._confirm_overwrite(targets)
        if overwrite is None:
            return
        for path in selected:
            self._notify(move_file(path, destination, overwrite=bool(overwrite), history=self.history))
        self.refresh_explorer()

    def delete_selected(self) -> None:
        selected = self._selected_paths()
        if not selected:
            return
        listing = "\n".join(f"  - {path.name}" for path in selected[:8])
        if len(selected) > 8:
            listing += f"\n  ... and {len(selected) - 8} more"
        if not messagebox.askyesno(
            "Confirm deletion",
            f"Move these {len(selected)} item(s) to the recovery folder?\n\n{listing}",
            parent=self,
        ):
            self._set_status("Deletion cancelled")
            return
        for path in selected:
            self._notify(delete_file(path, confirmed=True, history=self.history))
        self.refresh()

    def run_search(self) -> None:
        filters = SearchFilters(keyword=self.search_entry.get(), recursive=True)
        valid, message = filters.validate()
        if not valid:
            messagebox.showwarning("Search", message, parent=self)
            return
        self._busy_start("Searching...")
        results = search_files(self.current_path, filters)
        self._busy_stop()
        self.mode = "Search"
        self._set_columns([
            ("name", "Name", 430), ("type", "Type", 180),
            ("size", "Size", 110), ("modified", "Modified", 165),
        ])
        self._rows([
            (
                str(entry.path),
                (entry.name, entry.type_label, entry.size_text, entry.modified_text),
                "",
            )
            for entry in results
        ])
        self._set_status(
            f"Search results for '{filters.keyword}' in {self.current_path.name}",
            f"{len(results)} file(s) found",
        )

    def _notify(self, result: object) -> None:
        text = str(result)
        if getattr(result, "success", True):
            self._set_status(text)
        else:
            LOG.warning(text)
            messagebox.showerror("Operation failed", text, parent=self)

    # Organizer mode

    def _build_organizer_panel(self) -> None:
        self._clear_tool_panel()
        ctk.CTkLabel(
            self.tool_panel, text="Select categories:", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=(10, 6), pady=(8, 2))
        self.category_vars = {
            name: ctk.BooleanVar(value=True) for name in CATEGORIES
        }
        for index, (name, variable) in enumerate(self.category_vars.items()):
            ctk.CTkCheckBox(
                self.tool_panel, text=name, variable=variable, width=120, height=22
            ).grid(row=index // 5 + 1, column=index % 5, sticky="w", padx=8, pady=2)
        ctk.CTkButton(
            self.tool_panel, text="Preview changes", width=140, command=self.preview_organization
        ).grid(row=3, column=0, sticky="w", padx=10, pady=(6, 8))
        ctk.CTkButton(
            self.tool_panel, text="Apply approved plan", width=170,
            command=self.apply_organization,
        ).grid(row=3, column=1, sticky="w", padx=(8, 0), pady=(6, 8))
        self._set_columns([
            ("name", "File", 300), ("type", "Category", 150),
            ("size", "Destination", 420), ("modified", "Status", 130),
        ])
        self._set_status("Organizer mode - select categories and preview the changes")

    def preview_organization(self) -> None:
        if self.mode != "Organizer":
            return
        selected = [name for name, variable in self.category_vars.items() if variable.get()]
        self._busy_start("Building organization preview...")
        self.plan_items, warnings = build_organization_plan(self.current_path, selected)
        self._busy_stop()
        self._rows([
            (
                str(item.source),
                (
                    item.source.name,
                    item.category,
                    str(item.destination.relative_to(item.source.parent)),
                    "CONFLICT" if item.conflict else "Ready",
                ),
                "conflict" if item.conflict else "",
            )
            for item in self.plan_items
        ])
        self._set_status(
            f"Preview: {len(self.plan_items)} file(s) would be moved"
            + (f", {len(warnings)} conflict(s)" if warnings else ""),
            f"Folder: {self.current_path.name}",
        )
        if warnings:
            LOG.info("Organizer warnings: %s", "; ".join(warnings))

    def apply_organization(self) -> None:
        if not self.plan_items:
            messagebox.showinfo(
                "Organizer", "Preview the changes first, then apply the approved plan.", parent=self
            )
            return
        conflicts = sum(item.conflict for item in self.plan_items)
        approved = messagebox.askyesno(
            "Confirm organization",
            f"Move {len(self.plan_items)} file(s) into category folders?\n"
            f"{conflicts} conflicting file(s) will be skipped.\n\n"
            "No file will be moved without this confirmation.",
            parent=self,
        )
        if not approved:
            self._set_status("Organization cancelled")
            return
        self._busy_start("Organizing files...")
        summary = apply_organization_plan(
            self.plan_items, history=self.history, overwrite=False, confirmed=True
        )
        self._busy_stop()
        self.plan_items = []
        self._set_status(
            f"Organized {len(summary.applied)} file(s)",
            f"{len(summary.failed)} failed | {len(summary.skipped)} skipped",
        )
        if summary.failed:
            messagebox.showwarning(
                "Organization issues", "\n".join(summary.failed[:10]), parent=self
            )
        self.tree.delete(*self.tree.get_children())

    # Duplicate mode

    def _build_duplicate_panel(self) -> None:
        self._clear_tool_panel()
        ctk.CTkLabel(self.tool_panel, text="Minimum size (MB):", font=ctk.CTkFont(size=12))\
            .grid(row=0, column=0, sticky="w", padx=(10, 4), pady=(14, 8))
        self.min_size_entry = ctk.CTkEntry(self.tool_panel, width=90)
        self.min_size_entry.insert(0, "0")
        self.min_size_entry.grid(row=0, column=1, sticky="w", pady=(14, 8))
        ctk.CTkButton(self.tool_panel, text="Scan for duplicates", width=160,
                      command=self.scan_duplicates).grid(row=0, column=2, padx=10, pady=(14, 8))
        ctk.CTkButton(self.tool_panel, text="Delete selected copies", width=180,
                      command=self.delete_duplicate_selection).grid(row=0, column=3, padx=6, pady=(14, 8))
        self._set_columns([
            ("name", "File", 320), ("type", "Size", 110),
            ("size", "SHA-256 (first 16)", 210), ("modified", "Location", 400),
        ])
        self._set_status("Duplicate mode - scan, review, then manually choose copies to delete")

    def scan_duplicates(self) -> None:
        if self.mode != "Duplicates":
            return
        try:
            minimum = max(0, int(float(self.min_size_entry.get() or 0)))
        except ValueError:
            messagebox.showwarning("Duplicates", "Minimum size must be a number.", parent=self)
            return
        self._busy_start("Scanning for duplicate files...")
        report = find_duplicates(self.current_path, min_size=minimum * 1024 * 1024)
        self._busy_stop()
        self.duplicate_groups = {}
        rows: list[tuple[str, tuple, str]] = []
        for group_index, group in enumerate(report.groups, start=1):
            for path in group.paths:
                self.duplicate_groups[str(path)] = group_index
                rows.append((
                    str(path),
                    (
                        path.name,
                        format_size(group.size),
                        group.file_hash[:16],
                        str(path.parent),
                    ),
                    "duplicate",
                ))
        self._rows(rows)
        self._set_status(
            f"Scanned {report.files_scanned} file(s) - review before deleting",
            f"{report.duplicate_count} duplicates | {format_size(report.total_wasted_bytes)} recoverable",
        )
        if report.errors:
            LOG.warning("Duplicate scan warnings: %s", "; ".join(report.errors[:10]))

    def delete_duplicate_selection(self) -> None:
        selected = self._selected_paths()
        if not selected:
            messagebox.showinfo("Duplicates", "Select the copies you want to remove.", parent=self)
            return
        listing = "\n".join(f"  - {path}" for path in selected[:8])
        if not messagebox.askyesno(
            "Confirm deletion",
            f"Move these {len(selected)} selected copy/copies to the recovery folder?\n\n{listing}",
            parent=self,
        ):
            return
        self._busy_start("Removing selected copies...")
        results = delete_duplicates(selected, confirmed=True, history=self.history)
        self._busy_stop()
        failed = [str(result) for result in results if not result.success]
        self._set_status(
            f"Removed {len(results) - len(failed)} duplicate copy/copies",
            f"{len(failed)} failed",
        )
        if failed:
            messagebox.showwarning("Deletion issues", "\n".join(failed[:10]), parent=self)
        self.scan_duplicates()

    # Storage mode

    def _build_storage_panel(self) -> None:
        self._clear_tool_panel()
        ctk.CTkButton(
            self.tool_panel, text="Analyze this folder", width=160, command=self.analyze_storage
        ).grid(row=0, column=0, padx=10, pady=(22, 10))
        ctk.CTkLabel(
            self.tool_panel,
            text="Scans subfolders (symbolic links are skipped) and draws the category distribution.",
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=1, sticky="w", padx=8, pady=(22, 10))
        self.chart_frame.grid()
        self.chart_data = {}
        self.draw_chart()
        self._set_columns([
            ("name", "Category / Folder / File", 420), ("type", "Kind", 130),
            ("size", "Size", 120), ("modified", "Details", 260),
        ])
        self._set_status("Storage mode - click analyze to build a storage report")

    def analyze_storage(self) -> None:
        if self.mode != "Storage":
            return
        self._busy_start("Analyzing storage usage...")
        report = analyze_folder(self.current_path)
        self._busy_stop()
        rows: list[tuple[str, tuple, str]] = []
        for category, size in sorted(report.by_category.items(), key=lambda item: -item[1]):
            rows.append((
                f"category:{category}", (category, "Category", format_size(size), ""), "folder"
            ))
        for name, size in report.largest_folders:
            rows.append((
                f"folder:{self.current_path / name}",
                (name, "Folder", format_size(size), str(self.current_path / name)),
                "folder",
            ))
        for entry in report.largest_files:
            rows.append((
                str(entry.path),
                (entry.name, "File", entry.size_text, str(entry.path.parent)),
                "",
            ))
        self._rows(rows)
        self.chart_data = report.by_category
        self.draw_chart()
        self._set_status(
            f"Analyzed {self.current_path}",
            f"{report.file_count} files | {report.folder_count} folders | "
            f"{format_size(report.total_size)} total | {report.skipped} skipped",
        )

    def draw_chart(self) -> None:
        self.chart.delete("all")
        if not self.chart_data:
            self.chart.create_text(
                20, 20, anchor="nw", text="Category storage chart will appear after analysis.",
                fill="#9aa0a6",
            )
            return
        width = max(self.chart.winfo_width(), 400)
        colors = ["#4da3ff", "#66c2a5", "#f4b942", "#ff8a65", "#b39ddb", "#4dd0e1", "#aed581", "#d7ccc8"]
        entries = sorted(self.chart_data.items(), key=lambda item: -item[1])[:8]
        maximum = max(size for _, size in entries) or 1
        bar_left, bar_width, top = 130, max(width - 330, 120), 18
        palette = ctk.get_appearance_mode().lower()
        text_color = "#e8eaed" if palette == "dark" else "#202124"
        for index, (name, size) in enumerate(entries):
            y = top + index * 22
            bar = max(4, int(bar_width * size / maximum))
            self.chart.create_text(
                10, y + 6, anchor="nw", text=name, fill=text_color, font=("Segoe UI", 10)
            )
            self.chart.create_rectangle(
                bar_left, y, bar_left + bar, y + 14, fill=colors[index % len(colors)], outline=""
            )
            self.chart.create_text(
                bar_left + bar + 8, y + 2, anchor="nw",
                text=format_size(size), fill=text_color, font=("Segoe UI", 9),
            )

    # History mode

    def show_history(self) -> None:
        records = self.history.get_all(500)
        self._set_columns([
            ("name", "Operation", 150), ("type", "Date & time", 175),
            ("size", "File / folder", 430), ("modified", "Status", 100),
        ])
        self._rows([
            (
                str(record["id"]),
                (
                    record["operation"], record["timestamp"],
                    record["path"], record["status"],
                ),
                "",
            )
            for record in records
        ])
        self._set_status("Operation history", f"{len(records)} recorded action(s)")

    def clear_history(self) -> None:
        if not messagebox.askyesno(
            "Clear history", "Delete all recorded operations from the database?", parent=self
        ):
            return
        self.history.clear()
        self.show_history()

    def toggle_theme(self) -> None:
        current = ctk.get_appearance_mode().lower()
        target = "Light" if current == "dark" else "Dark"
        ctk.set_appearance_mode(target)
        self.theme_button.configure(text="Dark mode" if target == "Light" else "Light mode")
        self.tree.tag_configure("folder", foreground="#0066cc" if target == "Light" else "#4da3ff")
        self.draw_chart()

    def on_close(self) -> None:
        self.history.close()
        self.destroy()
