"""Copy, move, rename, create and safe-delete operations."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from error_handler import OperationResult, handle_exception, require_confirmation
from file_metadata import format_size
from logger import get_logger
from validation import (
    ensure_within_scope,
    is_protected_path,
    is_symlink,
    validate_delete,
    validate_destination,
    validate_filename,
    validate_folder,
    validate_move,
    validate_rename,
)

LOG = get_logger()


def _history_record(history: object | None, operation: str, source: Path, status: str, destination: object = "", details: str = "") -> None:
    if history is not None and hasattr(history, "record"):
        history.record(operation, source, status, destination, details)


def _safe_checks(source: Path) -> OperationResult | None:
    if not source.exists():
        return OperationResult.fail("Source not found", str(source))
    if is_symlink(source):
        return OperationResult.fail("Symbolic links are not supported", str(source))
    if is_protected_path(source):
        return OperationResult.fail("Protected system folder: operation blocked", str(source))
    return None


def _resolve_destination(source: Path, destination: str | Path) -> Path:
    target = Path(destination).expanduser()
    if target.is_dir():
        return target / source.name
    return target


def copy_file(
    source: str | Path,
    destination: str | Path,
    overwrite: bool = False,
    history: object | None = None,
) -> OperationResult:
    src = Path(source).expanduser()
    blocked = _safe_checks(src)
    if blocked:
        return blocked
    target = _resolve_destination(src, destination)
    if not validate_destination(target.parent):
        return OperationResult.fail("Destination folder not found or not writable", str(target))
    if target.exists() and not overwrite:
        return OperationResult.fail(
            "Destination already exists (choose overwrite to replace it)", str(target)
        )
    if is_protected_path(target.parent):
        return OperationResult.fail("Protected system folder: operation blocked", str(target))
    try:
        if target.is_dir():
            return OperationResult.fail("Destination is a folder", str(target))
        shutil.copy2(src, target)
        LOG.info("Copied %s -> %s", src, target)
        _history_record(history, "Copy", src, "Success", target, format_size(src.stat().st_size))
        return OperationResult.ok(f"Copied {src.name} successfully", str(target))
    except Exception as error:
        result = handle_exception("copy", error, str(src))
        _history_record(history, "Copy", src, "Failed", target, str(result))
        return result


def move_file(
    source: str | Path,
    destination: str | Path,
    overwrite: bool = False,
    history: object | None = None,
) -> OperationResult:
    src = Path(source).expanduser()
    blocked = _safe_checks(src)
    if blocked:
        return blocked
    target = _resolve_destination(src, destination)
    allowed, reason = validate_move(src, target)
    if not allowed:
        return OperationResult.fail(reason, str(target))
    if not validate_destination(target.parent):
        return OperationResult.fail("Destination folder not found or not writable", str(target))
    if is_protected_path(target.parent):
        return OperationResult.fail("Protected system folder: operation blocked", str(target))
    if target.exists() and not overwrite:
        return OperationResult.fail(
            "Destination already exists (choose overwrite to replace it)", str(target)
        )
    try:
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(src), str(target))
        LOG.info("Moved %s -> %s", src, target)
        _history_record(history, "Move", src, "Success", target)
        return OperationResult.ok(f"Moved {src.name} successfully", str(target))
    except Exception as error:
        result = handle_exception("move", error, str(src))
        _history_record(history, "Move", src, "Failed", target, str(result))
        return result


def rename_file(
    source: str | Path,
    new_name: str,
    history: object | None = None,
) -> OperationResult:
    src = Path(source).expanduser()
    blocked = _safe_checks(src)
    if blocked:
        return blocked
    allowed, reason = validate_rename(src, new_name)
    if not allowed:
        return OperationResult.fail(reason, str(src))
    target = src.parent / new_name.strip()
    if is_protected_path(src.parent):
        return OperationResult.fail("Protected system folder: operation blocked", str(src))
    try:
        src.rename(target)
        LOG.info("Renamed %s -> %s", src, target)
        _history_record(history, "Rename", src, "Success", target)
        return OperationResult.ok(f"Renamed {src.name} to {target.name}", str(target))
    except Exception as error:
        result = handle_exception("rename", error, str(src))
        _history_record(history, "Rename", src, "Failed", target, str(result))
        return result


def create_folder(
    parent: str | Path,
    name: str,
    history: object | None = None,
) -> OperationResult:
    folder = Path(parent).expanduser()
    if not validate_folder(folder):
        return OperationResult.fail("Parent folder not found", str(folder))
    if not validate_filename(name):
        return OperationResult.fail("Invalid folder name", str(folder))
    target = folder / name.strip()
    if target.exists():
        return OperationResult.fail("Folder already exists", str(target))
    if is_protected_path(folder):
        return OperationResult.fail("Protected system folder: operation blocked", str(folder))
    try:
        target.mkdir()
        LOG.info("Created folder %s", target)
        _history_record(history, "Create folder", target, "Success")
        return OperationResult.ok(f"Created folder {target.name}", str(target), created=str(target))
    except Exception as error:
        result = handle_exception("create folder", error, str(target))
        _history_record(history, "Create folder", target, "Failed", details=str(result))
        return result


def _recycle_path(source: Path) -> Path:
    recycle = Path.home() / ".smart_file_manager" / "recycle_bin"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return recycle / f"{stamp}__{source.name}"


def delete_file(
    path: str | Path,
    confirmed: bool = False,
    history: object | None = None,
    safe_delete: bool = True,
) -> OperationResult:
    """Move an item to a recovery folder, or permanently remove it when asked."""
    guard = require_confirmation(confirmed, "Delete")
    if guard:
        return guard
    src = Path(path).expanduser()
    allowed, reason = validate_delete(src)
    if not allowed:
        return OperationResult.fail(reason, str(src))
    if is_symlink(src):
        return OperationResult.fail("Symbolic links are not supported", str(src))
    try:
        if safe_delete:
            target = _recycle_path(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(target))
            message = f"Moved {src.name} to recovery folder"
            LOG.info("Safe deleted %s -> %s", src, target)
            _history_record(history, "Safe delete", src, "Success", target)
            return OperationResult.ok(message, str(src), recovery_path=str(target))
        if src.is_dir():
            shutil.rmtree(src)
        else:
            src.unlink()
        LOG.info("Permanently deleted %s", src)
        _history_record(history, "Delete", src, "Success")
        return OperationResult.ok(f"Deleted {src.name} permanently", str(src))
    except Exception as error:
        result = handle_exception("delete", error, str(src))
        _history_record(history, "Delete", src, "Failed", details=str(result))
        return result


def delete_empty_folder(
    path: str | Path,
    confirmed: bool = False,
    history: object | None = None,
) -> OperationResult:
    guard = require_confirmation(confirmed, "Delete folder")
    if guard:
        return guard
    folder = Path(path).expanduser()
    allowed, reason = validate_delete(folder)
    if not allowed:
        return OperationResult.fail(reason, str(folder))
    if not folder.is_dir():
        return OperationResult.fail("Not a folder", str(folder))
    try:
        if any(folder.iterdir()):
            return OperationResult.fail("Folder is not empty", str(folder))
        folder.rmdir()
        LOG.info("Deleted empty folder %s", folder)
        _history_record(history, "Delete folder", folder, "Success")
        return OperationResult.ok(f"Deleted empty folder {folder.name}", str(folder))
    except Exception as error:
        result = handle_exception("delete folder", error, str(folder))
        _history_record(history, "Delete folder", folder, "Failed", details=str(result))
        return result


def restore_from_recycle(recovery_path: str | Path, destination: str | Path) -> OperationResult:
    """Restore a file previously removed with safe delete."""
    source = Path(recovery_path).expanduser()
    if not source.exists():
        return OperationResult.fail("Recovery file not found", str(source))
    target = Path(destination).expanduser()
    if target.exists():
        return OperationResult.fail("Restore destination already exists", str(target))
    if not ensure_within_scope(source, Path.home() / ".smart_file_manager" / "recycle_bin"):
        return OperationResult.fail("Not a recovery folder item", str(source))
    try:
        shutil.move(str(source), str(target))
        LOG.info("Restored %s -> %s", source, target)
        return OperationResult.ok(f"Restored {target.name}", str(target))
    except Exception as error:
        return handle_exception("restore", error, str(source))
