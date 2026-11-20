"""Recursive file search with name, extension, category, size and date filters."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from file_explorer import FileEntry
from file_metadata import get_category
from logger import get_logger
from validation import is_symlink, validate_extension, validate_folder, validate_file_size

LOG = get_logger()


@dataclass
class SearchFilters:
    keyword: str = ""
    extension: str = ""
    category: str = ""
    min_size_mb: float | None = None
    max_size_mb: float | None = None
    modified_within_days: int | None = None
    recursive: bool = True
    case_sensitive: bool = False

    def validate(self) -> tuple[bool, str]:
        if not any((self.keyword.strip(), self.extension.strip(), self.category)):
            return False, "Enter a keyword or choose an extension/category filter"
        if self.extension.strip() and not validate_extension(self.extension):
            return False, "Invalid extension format"
        if self.min_size_mb is not None and not validate_file_size(self.min_size_mb):
            return False, "Minimum size must be non-negative"
        if self.max_size_mb is not None and not validate_file_size(self.max_size_mb):
            return False, "Maximum size must be non-negative"
        if (
            self.min_size_mb is not None
            and self.max_size_mb is not None
            and self.min_size_mb > self.max_size_mb
        ):
            return False, "Minimum size cannot exceed maximum size"
        return True, "OK"


def search_files(root: str | Path, filters: SearchFilters) -> list[FileEntry]:
    """Return files matching all supplied filters; symlinks are skipped."""
    valid, message = filters.validate()
    if not valid or not validate_folder(root):
        LOG.warning("Search skipped: %s", message)
        return []

    root_path = Path(root).expanduser()
    keyword = filters.keyword.strip()
    if not filters.case_sensitive:
        keyword = keyword.lower()
    extension = filters.extension.strip().lower().lstrip(".")
    min_bytes = None if filters.min_size_mb is None else filters.min_size_mb * 1024 * 1024
    max_bytes = None if filters.max_size_mb is None else filters.max_size_mb * 1024 * 1024
    cutoff = (
        datetime.now() - timedelta(days=filters.modified_within_days)
        if filters.modified_within_days is not None
        else None
    )
    results: list[FileEntry] = []

    for current, directories, filenames in os.walk(root_path, followlinks=False):
        directories[:] = [d for d in directories if not is_symlink(Path(current) / d)]
        if not filters.recursive:
            directories.clear()
        for filename in filenames:
            path = Path(current) / filename
            if is_symlink(path):
                continue
            name_to_check = filename if filters.case_sensitive else filename.lower()
            if keyword and keyword not in name_to_check:
                continue
            if extension and path.suffix.lower().lstrip(".") != extension:
                continue
            if filters.category and get_category(path) != filters.category:
                continue
            try:
                stats = path.stat()
            except OSError:
                continue
            if min_bytes is not None and stats.st_size < min_bytes:
                continue
            if max_bytes is not None and stats.st_size > max_bytes:
                continue
            if cutoff is not None and datetime.fromtimestamp(stats.st_mtime) < cutoff:
                continue
            try:
                results.append(FileEntry.from_path(path))
            except OSError:
                continue

    return sorted(results, key=lambda item: (str(item.path.parent).lower(), item.name.lower()))
