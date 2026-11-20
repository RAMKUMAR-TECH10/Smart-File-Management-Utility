"""Preview-driven automatic organization of files by extension."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from error_handler import OperationResult
from file_metadata import CATEGORIES, get_category
from file_operations import move_file
from logger import get_logger
from validation import is_protected_path, is_symlink, validate_folder

LOG = get_logger()


@dataclass
class OrganizationItem:
    source: Path
    destination: Path
    category: str
    size: int
    conflict: bool = False

    @property
    def relative_source(self) -> str:
        return self.source.name


def build_organization_plan(
    folder: str | Path,
    selected_categories: list[str] | None = None,
) -> tuple[list[OrganizationItem], list[str]]:
    """Build a preview plan. No file is moved by this function."""
    root = Path(folder).expanduser()
    if not validate_folder(root) or is_protected_path(root):
        return [], ["Selected folder is invalid or protected"]
    allowed = set(selected_categories) if selected_categories else set(CATEGORIES)
    items: list[OrganizationItem] = []
    warnings: list[str] = []
    try:
        children = list(root.iterdir())
    except OSError as error:
        return [], [f"Could not scan folder: {error}"]

    for child in children:
        try:
            if child.is_dir() or is_symlink(child) or child.name.startswith("."):
                continue
            category = get_category(child)
            if category not in allowed:
                continue
            if child.parent.name == category:
                continue
            target = root / category / child.name
            conflict = target.exists()
            if conflict:
                warnings.append(f"{child.name}: {category}/{child.name} already exists")
            items.append(OrganizationItem(child, target, category, child.stat().st_size, conflict))
        except OSError as error:
            warnings.append(f"{child.name}: {error}")
    return sorted(items, key=lambda item: (item.category, item.source.name.lower())), warnings


@dataclass
class OrganizationSummary:
    applied: list[Path]
    failed: list[str]
    skipped: list[str]


def apply_organization_plan(
    items: list[OrganizationItem],
    history: object | None = None,
    overwrite: bool = False,
    confirmed: bool = False,
) -> OrganizationSummary:
    """Execute a preview only after explicit confirmation."""
    summary = OrganizationSummary([], [], [])
    if not confirmed:
        summary.failed.append("Organization cancelled: confirmation is required")
        return summary
    if not items:
        return summary

    for item in items:
        if item.conflict and not overwrite:
            summary.skipped.append(f"{item.source.name}: destination already exists")
            continue
        try:
            item.destination.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            summary.failed.append(f"{item.destination.parent.name}: {error}")
            continue
        result = move_file(item.source, item.destination, overwrite=overwrite, history=history)
        if result.success:
            summary.applied.append(item.source)
        else:
            summary.failed.append(f"{item.source.name}: {result}")

    if summary.applied and history is not None and hasattr(history, "record"):
        roots = {item.source.parent for item in items if item.source in summary.applied}
        for root in roots:
            history.record(
                "Organize",
                root,
                "Success",
                "",
                f"{len(summary.applied)} file(s) organized into category folders",
            )
    LOG.info("Organization finished: %d applied, %d failed, %d skipped",
             len(summary.applied), len(summary.failed), len(summary.skipped))
    return summary
