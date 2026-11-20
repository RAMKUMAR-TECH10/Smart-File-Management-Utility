"""SHA-256 based duplicate file detection with manual deletion only."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

from error_handler import OperationResult
from file_metadata import format_size
from file_operations import delete_file
from logger import get_logger
from validation import is_protected_path, is_symlink, validate_folder

LOG = get_logger()
CHUNK_SIZE = 1024 * 1024


@dataclass
class DuplicateGroup:
    file_hash: str
    size: int
    paths: list[Path]

    @property
    def wasted_bytes(self) -> int:
        return self.size * (len(self.paths) - 1)


@dataclass
class DuplicateReport:
    groups: list[DuplicateGroup] = field(default_factory=list)
    files_scanned: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def duplicate_count(self) -> int:
        return sum(len(group.paths) for group in self.groups)

    @property
    def total_wasted_bytes(self) -> int:
        return sum(group.wasted_bytes for group in self.groups)


def hash_file(path: Path) -> str:
    """Hash a file in chunks so large files do not consume excessive memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicates(
    root: str | Path,
    min_size: int = 1,
    max_file_size: int | None = None,
) -> DuplicateReport:
    """Group identical files by size, then by SHA-256 hash. Never deletes anything."""
    report = DuplicateReport()
    folder = Path(root).expanduser()
    if not validate_folder(folder) or is_protected_path(folder):
        report.errors.append("Selected folder is invalid or protected")
        return report

    by_size: dict[int, list[Path]] = {}
    for current, directories, filenames in os.walk(folder, followlinks=False):
        directories[:] = [
            d for d in directories
            if not is_symlink(Path(current) / d) and not is_protected_path(Path(current) / d)
        ]
        for filename in filenames:
            path = Path(current) / filename
            if is_symlink(path):
                report.skipped += 1
                continue
            try:
                size = path.stat().st_size
            except OSError as error:
                report.skipped += 1
                report.errors.append(f"{filename}: {error}")
                continue
            if size < min_size or (max_file_size is not None and size > max_file_size):
                report.skipped += 1
                continue
            report.files_scanned += 1
            by_size.setdefault(size, []).append(path)

    by_hash: dict[tuple[str, int], list[Path]] = {}
    for size, candidates in by_size.items():
        if len(candidates) < 2:
            continue
        for path in candidates:
            try:
                by_hash.setdefault((hash_file(path), size), []).append(path)
            except OSError as error:
                report.skipped += 1
                report.errors.append(f"{path.name}: {error}")

    for (file_hash, size), paths in by_hash.items():
        if len(paths) < 2:
            continue
        report.groups.append(DuplicateGroup(file_hash, size, sorted(paths)))
    report.groups.sort(key=lambda group: (-group.wasted_bytes, group.file_hash))
    LOG.info("Duplicate scan: %d files, %d duplicate groups", report.files_scanned, len(report.groups))
    return report


def delete_duplicates(
    paths: list[str | Path],
    confirmed: bool = False,
    history: object | None = None,
) -> list[OperationResult]:
    """Delete only duplicates explicitly selected by the user."""
    return [delete_file(path, confirmed=confirmed, history=history) for path in paths]


def duplicate_summary(report: DuplicateReport) -> str:
    return (
        f"{report.duplicate_count} duplicate file(s) in {len(report.groups)} group(s); "
        f"recoverable space: {format_size(report.total_wasted_bytes)}"
    )
