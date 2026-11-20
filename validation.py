"""Input validation for paths, names, extensions and destructive operations."""

from __future__ import annotations

import os
import re
from pathlib import Path

INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
VALID_EXTENSION = re.compile(r"^\.?[A-Za-z0-9]{1,10}$")
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

if os.name == "nt":
    _PROTECTED = {
        r"c:\windows",
        r"c:\program files",
        r"c:\program files (x86)",
        r"c:\programdata",
        r"c:\system volume information",
        r"c:\$recycle.bin",
    }
else:
    _PROTECTED = {"/etc", "/bin", "/sbin", "/usr", "/sys", "/proc", "/dev", "/boot"}


def _resolved(path: str | os.PathLike[str]) -> Path:
    return Path(path).expanduser().resolve()


def validate_folder(folder_path: str | os.PathLike[str]) -> bool:
    """True when the path exists and is a directory."""
    try:
        path = Path(folder_path).expanduser()
        return path.exists() and path.is_dir()
    except (OSError, ValueError):
        return False


def validate_file(file_path: str | os.PathLike[str]) -> bool:
    """True when the path exists and is a regular file."""
    try:
        path = Path(file_path).expanduser()
        return path.exists() and path.is_file()
    except (OSError, ValueError):
        return False


def validate_filename(filename: str) -> bool:
    """Validate a file or folder name (not a full path)."""
    if not isinstance(filename, str) or not filename.strip():
        return False
    name = filename.strip()
    if name in {".", ".."} or INVALID_FILENAME_CHARS.search(name):
        return False
    if name.endswith((" ", ".")) or len(name) > 255:
        return False
    if os.name == "nt" and name.split(".")[0].upper() in WINDOWS_RESERVED_NAMES:
        return False
    return True


validate_directory_name = validate_filename


def validate_extension(extension: str) -> bool:
    """Accept extensions such as 'py', '.PY' or '.tar.gz' components."""
    if not isinstance(extension, str) or not extension.strip():
        return False
    parts = extension.strip().lstrip(".").split(".")
    return all(VALID_EXTENSION.fullmatch(part) for part in parts if part)


def validate_destination(destination: str | os.PathLike[str]) -> bool:
    """A destination directory must exist, be a directory and be writable."""
    try:
        parent = _resolved(destination)
        return parent.is_dir() and os.access(parent, os.W_OK)
    except (OSError, ValueError):
        return False


def validate_search_keyword(keyword: str) -> bool:
    return isinstance(keyword, str) and bool(keyword.strip())


def validate_file_size(size: object) -> bool:
    if isinstance(size, bool) or not isinstance(size, (int, float)):
        return False
    return size >= 0


def is_symlink(path: str | os.PathLike[str]) -> bool:
    try:
        return Path(path).is_symlink()
    except (OSError, ValueError):
        return False


def is_protected_path(path: str | os.PathLike[str]) -> bool:
    """Block drive roots and operating-system folders from destructive operations."""
    try:
        resolved = _resolved(path)
        lowered = str(resolved).lower()
        if len(resolved.parts) <= 1:
            return True
        if os.name == "nt":
            if any(part.lower() in {"system volume information", "$recycle.bin"} for part in resolved.parts):
                return True
        return any(
            lowered == root or lowered.startswith(root + os.sep)
            for root in _PROTECTED
        )
    except (OSError, ValueError):
        return True


def ensure_within_scope(path: str | os.PathLike[str], root: str | os.PathLike[str]) -> bool:
    """True when path is root itself or lives below root."""
    try:
        target, scope = _resolved(path), _resolved(root)
        return target == scope or scope in target.parents
    except (OSError, ValueError):
        return False


def validate_move(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> tuple[bool, str]:
    """Prevent moving a directory into itself or onto itself."""
    try:
        src, dst = _resolved(source), _resolved(destination)
        if src == dst:
            return False, "Source and destination are the same"
        if src.is_dir() and (dst == src or src in dst.parents):
            return False, "Cannot move a folder into itself"
        return True, "OK"
    except (OSError, ValueError) as error:
        return False, str(error)


def validate_rename(source: str | os.PathLike[str], new_name: str) -> tuple[bool, str]:
    src = Path(source)
    if not validate_filename(new_name):
        return False, "Invalid filename"
    if src.parent / new_name == src:
        return False, "Name is unchanged"
    if (src.parent / new_name).exists():
        return False, "A file with that name already exists"
    return True, "OK"


def validate_delete(path: str | os.PathLike[str]) -> tuple[bool, str]:
    if not Path(path).exists():
        return False, "Path not found"
    if is_protected_path(path):
        return False, "Protected system folder: operation blocked"
    return True, "OK"


def validation_message(result: tuple[bool, str]) -> str:
    return "OK" if result[0] else result[1]
