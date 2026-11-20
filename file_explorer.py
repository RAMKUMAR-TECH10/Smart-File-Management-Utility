"""Directory browsing and navigation for the file explorer view."""

from __future__ import annotations

import os
import string
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from error_handler import OperationResult, handle_exception
from file_metadata import format_size, get_category, get_file_type
from logger import get_logger
from validation import validate_folder

LOG = get_logger()


@dataclass(frozen=True)
class FileEntry:
    name: str
    path: Path
    is_dir: bool
    size: int = 0
    modified: float = 0.0
    extension: str = ""
    type_label: str = "Folder"
    category: str = "Folder"
    is_symlink: bool = False

    @property
    def size_text(self) -> str:
        return "—" if self.is_dir else format_size(self.size)

    @property
    def modified_text(self) -> str:
        try:
            return datetime.fromtimestamp(self.modified).strftime("%d-%m-%Y %H:%M")
        except (OSError, ValueError, OverflowError):
            return "Unknown"

    @classmethod
    def from_path(cls, path: Path) -> "FileEntry":
        stats = path.stat()
        is_dir = path.is_dir()
        extension = "" if is_dir else path.suffix.lower()
        return cls(
            name=path.name,
            path=path,
            is_dir=is_dir,
            size=0 if is_dir else stats.st_size,
            modified=stats.st_mtime,
            extension=extension,
            type_label="Folder" if is_dir else get_file_type(extension),
            category="Folder" if is_dir else get_category(extension),
            is_symlink=path.is_symlink(),
        )


def list_directory(folder: str | Path, show_hidden: bool = False) -> list[FileEntry]:
    """List a directory's contents with folders first and files sorted by name."""
    if not validate_folder(folder):
        LOG.warning("Cannot list invalid folder: %s", folder)
        return []
    entries: list[FileEntry] = []
    try:
        for child in Path(folder).expanduser().iterdir():
            if not show_hidden and child.name.startswith(".") and os.name != "nt":
                continue
            try:
                entries.append(FileEntry.from_path(child))
            except OSError as error:
                LOG.warning("Skipping %s: %s", child, error)
    except OSError as error:
        LOG.error("Could not list %s: %s", folder, error)
    return sorted(entries, key=lambda item: (not item.is_dir, item.name.lower()))


def navigate_parent(folder: str | Path) -> Path:
    path = Path(folder).expanduser().resolve()
    return path.parent if path.parent != path else path


def open_path(path: str | Path) -> OperationResult:
    """Open a file or folder with the operating system's default application."""
    target = Path(path).expanduser()
    if not target.exists():
        return OperationResult.fail("File or folder not found", str(target))
    try:
        if os.name == "nt":
            os.startfile(str(target))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(target)], check=False)
        else:
            subprocess.run(["xdg-open", str(target)], check=False)
        LOG.info("Opened %s", target)
        return OperationResult.ok(f"Opened {target.name}", str(target))
    except Exception as error:
        return handle_exception("open", error, str(target))


def get_quick_locations() -> list[tuple[str, Path]]:
    """Existing common folders plus available drives, for the navigation pane."""
    home = Path.home()
    candidates: list[tuple[str, Path]] = [
        ("Home", home),
        ("Desktop", home / "Desktop"),
        ("Downloads", home / "Downloads"),
        ("Documents", home / "Documents"),
        ("Pictures", home / "Pictures"),
        ("Videos", home / "Videos"),
        ("Music", home / "Music"),
    ]
    if os.name == "nt":
        candidates.extend(
            (f"{letter}:\\", Path(f"{letter}:\\"))
            for letter in string.ascii_uppercase
            if Path(f"{letter}:\\").exists()
        )
    return [(label, path) for label, path in candidates if path.exists()]
