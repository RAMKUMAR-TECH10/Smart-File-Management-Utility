"""File metadata, friendly type labels, size formatting and category rules."""

from __future__ import annotations

import os
import stat
from datetime import datetime
from pathlib import Path

CATEGORIES: dict[str, tuple[str, ...]] = {
    "Images": ("jpg", "jpeg", "png", "gif", "svg", "bmp", "webp", "ico"),
    "Documents": ("pdf", "docx", "doc", "txt", "rtf", "odt", "md"),
    "Videos": ("mp4", "mkv", "avi", "mov", "wmv", "flv", "webm"),
    "Audio": ("mp3", "wav", "aac", "flac", "ogg", "m4a"),
    "Archives": ("zip", "rar", "7z", "tar", "gz"),
    "Code": ("py", "java", "html", "css", "js", "json", "cpp", "c", "sql"),
    "Spreadsheets": ("xlsx", "xls", "csv", "ods"),
    "Others": (),
}

TYPE_NAMES: dict[str, str] = {
    ".pdf": "PDF Document",
    ".doc": "Word Document", ".docx": "Word Document",
    ".txt": "Text Document", ".md": "Markdown Document",
    ".xls": "Excel Spreadsheet", ".xlsx": "Excel Spreadsheet", ".csv": "CSV Spreadsheet",
    ".jpg": "JPEG Image", ".jpeg": "JPEG Image", ".png": "PNG Image",
    ".gif": "GIF Image", ".svg": "SVG Image", ".bmp": "Bitmap Image", ".webp": "WebP Image",
    ".mp4": "MP4 Video", ".mkv": "Matroska Video", ".avi": "AVI Video", ".mov": "QuickTime Video",
    ".mp3": "MP3 Audio", ".wav": "WAV Audio", ".aac": "AAC Audio", ".flac": "FLAC Audio",
    ".zip": "ZIP Archive", ".rar": "RAR Archive", ".7z": "7-Zip Archive",
    ".py": "Python Source File", ".java": "Java Source File",
    ".html": "HTML Document", ".css": "CSS Stylesheet", ".js": "JavaScript File",
}


def format_size(size: float | int | None) -> str:
    """Human readable size, e.g. 2.5 MB."""
    if size is None:
        return "—"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{int(value)} B" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TB"


def normalize_extension(path: str | Path) -> str:
    suffix = Path(path).suffix
    return suffix.lower() if suffix else ""


def get_category(path_or_extension: str | Path) -> str:
    """Return the destination category folder name for a file."""
    extension = normalize_extension(path_or_extension).lstrip(".")
    for category, extensions in CATEGORIES.items():
        if extension in extensions:
            return category
    return "Others"


def get_file_type(path: str | Path) -> str:
    extension = normalize_extension(path)
    return TYPE_NAMES.get(extension, f"{extension[1:].upper()} File" if extension else "File")


def _timestamp(value: float) -> str:
    try:
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError, OverflowError):
        return "Unknown"


def get_metadata(path: str | Path) -> dict[str, str]:
    """Return display-ready information about a file or folder."""
    item = Path(path).expanduser()
    info: dict[str, str] = {
        "Name": item.name,
        "Extension": item.suffix or "—",
        "Location": str(item.parent),
        "Full path": str(item),
    }
    try:
        if item.is_dir():
            info.update({
                "Type": "Folder",
                "Size": "—",
                "Category": "Folder",
                "Permissions": "Read/Write" if os.access(item, os.W_OK) else "Read-only",
            })
        else:
            stats = item.stat()
            info.update({
                "Type": get_file_type(item),
                "Size": format_size(stats.st_size),
                "Size (bytes)": str(stats.st_size),
                "Category": get_category(item),
                "Permissions": "Read/write" if stats.st_mode & stat.S_IWRITE else "Read-only",
            })
        created = getattr(item.stat(), "st_birthtime", None)
        info["Created"] = _timestamp(created) if created else _timestamp(item.stat().st_ctime)
        info["Modified"] = _timestamp(item.stat().st_mtime)
        info["Accessed"] = _timestamp(item.stat().st_atime)
    except OSError as error:
        info["Error"] = f"Metadata unavailable: {error}"
    return info
