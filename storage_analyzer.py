"""Folder size, category distribution and large-file analysis."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from file_explorer import FileEntry
from file_metadata import format_size, get_category
from logger import get_logger
from validation import is_protected_path, is_symlink, validate_folder

LOG = get_logger()


@dataclass
class StorageReport:
    root: Path
    total_size: int = 0
    file_count: int = 0
    folder_count: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    largest_files: list[FileEntry] = field(default_factory=list)
    largest_folders: list[tuple[Path, int]] = field(default_factory=list)
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def analyze_folder(root: str | Path, top: int = 10) -> StorageReport:
    """Recursively analyse a folder without following symbolic links."""
    folder = Path(root).expanduser()
    report = StorageReport(root=folder)
    if not validate_folder(folder) or is_protected_path(folder):
        report.errors.append("Selected folder is invalid or protected")
        return report

    all_entries: list[FileEntry] = []
    child_folders: dict[str, int] = {}

    for current, directories, filenames in os.walk(folder, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            d for d in directories
            if not is_symlink(current_path / d) and not is_protected_path(current_path / d)
        ]
        report.folder_count += len(directories)
        try:
            relative = current_path.relative_to(folder)
        except ValueError:
            relative = Path()

        for filename in filenames:
            path = current_path / filename
            if is_symlink(path):
                report.skipped += 1
                continue
            try:
                stats = path.stat()
                entry = FileEntry.from_path(path)
            except OSError as error:
                report.skipped += 1
                report.errors.append(f"{filename}: {error}")
                continue
            report.total_size += stats.st_size
            report.file_count += 1
            category = get_category(path)
            report.by_category[category] = report.by_category.get(category, 0) + stats.st_size
            all_entries.append(entry)
            if relative.parts:
                top_name = relative.parts[0]
                child_folders[top_name] = child_folders.get(top_name, 0) + stats.st_size

    report.largest_files = sorted(all_entries, key=lambda item: item.size, reverse=True)[:top]
    report.largest_folders = [
        (folder / name, size)
        for name, size in sorted(child_folders.items(), key=lambda item: item[1], reverse=True)[:top]
    ]
    LOG.info("Storage scan %s: %d files, %s", folder, report.file_count, format_size(report.total_size))
    return report
